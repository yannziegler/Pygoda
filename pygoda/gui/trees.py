# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import time
import strictyaml as yaml

import geopandas as gpd
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely import wkt

import cartopy.crs as ccrs
from cartopy.feature import ShapelyFeature

import config as cfg
import constants as cst

class TreeItem():

    def __init__(self, item_name, fields=None, parent_item=None):

        self.parent_item = parent_item

        self.item_name = item_name
        # self.item_count = ... # number of stations in the area
        self.item_state = QtCore.Qt.Checked

        self.children = []

        self.fields = fields
        if self.fields is None:
            self.fields = dict()

    def appendChild(self, item):
        self.children.append(item)

    def child(self, row):
        if row < 0 or row >= len(self.children):
            return None
        else:
            return self.children[row]

    def childCount(self):
        return len(self.children)

    def columnCount(self):
        return 1

    def data(self, column):
        if column == 0:
            return self.item_name, self.fields
        else:
            return None
        # if column < 0 or column >= len(self.item_data):
        #     return None
        # else:
        #     self.item_data[column]

    def row(self):
        if self.parent_item:
            return self.parent_item.children.index(self)
        else:
            return None # Never used by the model

    def parentItem(self):
        return self.parent_item

    def getState(self):
        return self.item_state

    def setState(self, state, update_children=True):
        self.item_state = state
        changed_items = [self]
        if state != QtCore.Qt.PartiallyChecked and update_children:
            for child in self.children:
                if state != child.getState():
                    changed_items += child.setState(state)

        return changed_items

    def setParentState(self):

        parent_item = self.parentItem()
        if not parent_item or not parent_item.parentItem():
            # (1) We don't go above the root
            # (2) We don't worry about the root (which has no parent)
            return []

        all_checked, all_unchecked = True, True
        for child in parent_item.children:
            child_state = child.getState()
            if child_state != QtCore.Qt.Checked:
                all_checked = False
            if child_state != QtCore.Qt.Unchecked:
                all_unchecked = False

        if not all_checked and not all_unchecked:
            parent_item.setState(QtCore.Qt.PartiallyChecked, update_children=False)
        elif all_checked:
            parent_item.setState(QtCore.Qt.Checked, update_children=False)
        elif all_unchecked:
            parent_item.setState(QtCore.Qt.Unchecked, update_children=False)

        # Let say that the parents are always changed to simplify for now
        changed_items = [parent_item]
        changed_items += parent_item.setParentState()

        return changed_items


class TreeProxyModel(QtCore.QSortFilterProxyModel):

    expandNode = QtCore.Signal()#type(QtCore.QModelIndex()))

    def __init__(self, parent=None):
        QtCore.QSortFilterProxyModel.__init__(self, parent)

        self.setRecursiveFilteringEnabled(True)
        self.accepted_indices = []

    def setFilterRegExp(self, regex):
        self.accepted_indices = []

        return super().setFilterRegExp(regex)

    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent, froms='filter')
        if not index.isValid():
            return True # Following the original Qt implementation

        data_text = self.sourceModel().data(index, QtCore.Qt.DisplayRole)

        if self.filterRegExp().pattern() == '':
            return True

        match_data = (self.filterRegExp().indexIn(data_text, 0) != -1)

        if match_data:
            self.accepted_indices.append(index)

        return match_data

    def getAcceptedIndices(self):
        return self.accepted_indices


class TreeModel(QtCore.QAbstractItemModel):

    def __init__(self, tree_data, root_name="root"):
        QtCore.QAbstractItemModel.__init__(self, None)

        self.root_name = root_name
        self.root_item = TreeItem(self.root_name)

        self.states = [QtCore.Qt.Unchecked, QtCore.Qt.PartiallyChecked, QtCore.Qt.Checked]

        # self.setupModelData(tree_data, self.root_item)

    def data(self, index, role=None, key=None):
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            return item.getState()

        if role == QtCore.Qt.DisplayRole and index.column() == 0:
            item_id, item_data = item.data(index.column())
            return item_data.get('fullname', item_id)

        if role is None:
            item_id, _ = item.data(index.column())
            return item_id

        if role == -1 and key is not None:
            _, item_data = item.data(index.column())
            return item_data.get(role, key)

        return None

    def setData(self, index, value, role):
        if not index.isValid():
            return None

        item = index.internalPointer()

        changed_items = None
        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            changed_items = item.setState(self.states[value])
            changed_items += item.setParentState()

        for changed_item in changed_items:
            changed_index = self.createIndex(changed_item.row(), 0, changed_item)
            self.dataChanged.emit(changed_index, changed_index,
                                  (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole))

        return True if changed_items else False

    def flags(self, index):
        if not index.isValid():
            return int(QtCore.Qt.NoItemFlags)

        flag = int(QtCore.Qt.ItemIsEnabled) | int(QtCore.Qt.ItemIsSelectable)

        if index.column() == 0:
            flag |= int(QtCore.Qt.ItemIsUserCheckable)
            flag |= int(QtCore.Qt.ItemIsTristate)

        return super().flags(index) | flag

    def headerData(self, column, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            name, _ = self.root_item.data(column)
            return name

        return None

    def index(self, row, column, parent_index=QtCore.QModelIndex(), froms=''):
        if not self.hasIndex(row, column, parent_index):
            return QtCore.QModelIndex()

        if not parent_index.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent_index.internalPointer()

        child_item = parent_item.child(row)
        if not child_item:
            return QtCore.QModelIndex()

        return self.createIndex(row, column, child_item)

    def hasIndex(self, row, column, parent_index):
        if (row < 0 or column < 0):
            return False

        return row < self.rowCount(parent_index) and \
               column < self.columnCount(parent_index)

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parentItem()

        if (not parent_item) or (parent_item == self.root_item):
            # (1) The root is a child without parent :-(
            # (2) By Qt convention, the root has no index
            return QtCore.QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent_index=QtCore.QModelIndex()):
        if not parent_index.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent_index.internalPointer()

        return parent_item.childCount()

    def columnCount(self, parent_index):
        if parent_index.isValid():
            return parent_index.internalPointer().columnCount()
        else:
            return self.root_item.columnCount()

    def setupModelData(self, tree_data, parent_item):

        # Implemented in children classes
        pass

    def checkAll(self, top_item=None):
        if top_item is None:
            top_item = self.root_item
        else:
            top_item.setState(QtCore.Qt.Checked)

        for i in range(top_item.childCount()):
            child_item = top_item.child(i)
            self.checkAll(child_item)
            child_index = self.createIndex(child_item.row(), 0, child_item)
            self.dataChanged.emit(child_index,
                                  child_index, 
                                  (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole))

    def uncheckAll(self, top_item=None):
        if top_item is None:
            top_item = self.root_item
        else:
            top_item.setState(QtCore.Qt.Unchecked)

        for i in range(top_item.childCount()):
            child_item = top_item.child(i)
            self.uncheckAll(child_item)
            child_index = self.createIndex(child_item.row(), 0, child_item)
            self.dataChanged.emit(child_index,
                                  child_index,
                                  (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole))

    def toggleAll(self, top_item=None):
        #TODO: doesn't work yet
        if top_item is None:
            top_item = self.root_item
        else:
            if top_item.getState() in (QtCore.Qt.Checked, QtCore.Qt.PartiallyChecked):
                top_item.setState(QtCore.Qt.Unchecked)
            else:
                top_item.setState(QtCore.Qt.Checked)

        for i in range(top_item.childCount()):
            child_item = top_item.child(i)
            child_index = self.createIndex(child_item.row(), 0, child_item)
            self.dataChanged.emit(child_index,
                                  child_index,
                                  (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole))
            self.toggleAll(child_item)

    def getTreeData(self,
                    top_item=None,
                    tree_data=None,
                    states=None,
                    remove_keys=[]):
        if tree_data is None:
            tree_data = dict()

        if states is None:
            states = (QtCore.Qt.Checked, QtCore.Qt.Unchecked)

        if top_item is None:
            top_item = self.root_item
            top_name = self.root_name
            tree_data[top_name] = {'state': None,
                                   'data': None,
                                   'children': dict()}
        else:
            state = top_item.getState()
            if state not in states and state != QtCore.Qt.PartiallyChecked:
                return tree_data
            top_index = self.createIndex(top_item.row(), 0, top_item)
            top_name, data = top_item.data(top_index.column())
            for key in remove_keys:
                if key in data:
                    del data[key]
            tree_data[top_name] = {'state': state,
                                   'data': None,
                                   'children': dict(),}
            tree_data[top_name]['data'] = data

        for i in range(top_item.childCount()):
            child_item = top_item.child(i)
            self.getTreeData(child_item,
                             tree_data[top_name]['children'],
                             states=states)

        return tree_data

    def getCheckedData(self, remove_keys=[]):

        return self.getTreeData(states=(QtCore.Qt.Checked, ),
                                remove_keys=remove_keys)

    def getUncheckedData(self, remove_keys=[]):

        return self.getTreeData(states=(QtCore.Qt.Unchecked, ),
                                remove_keys=remove_keys)

    def findFirst(self,
                  search_data,
                  role=None,
                  key=None,
                  #hits=-1,
                  top_item=None):

        item = None

        if top_item is None:
            top_item = self.root_item

        for i in range(top_item.childCount()):
            child_item = top_item.child(i)
            item = self.findFirst(search_data,
                                  role=None,
                                  key=None,
                                  top_item=child_item)
            if item is not None:
                break
            child_index = self.createIndex(child_item.row(), 0, child_item)
            current_data = self.data(child_index, role, key)
            if current_data == search_data:
                item = child_item
                break
                #find_list.append(index.internalPointer())
                #if hits == len(find_list):
                #    return find_list

        return item


class GeographyTreeModel(TreeModel):

    def __init__(self,
                 tree_data,
                 root_name="Planet Earth",
                 display_mode='geographic',
                 dependencies_key='',
                 geounits_key='',
                 subdivisions_key=''):
        TreeModel.__init__(self, tree_data, root_name=root_name)

        self.dependencies_key = dependencies_key
        self.geounits_key = geounits_key
        self.subdivisions_key = subdivisions_key

        self.setupModelData(tree_data,
                            self.root_item,
                            display_mode)

    def setupModelData(self, tree_data, parent_item, display_mode):

        if display_mode not in ('geographic', 'admin'):
            raise ValueError("unknown type of display for geographic tree: %s" % display_mode)

        self.display_mode = display_mode

        if self.display_mode == 'geographic':
            self.setupModelDataUNM49(cst.UNSD_M49, self.root_item)
            self.setupModelDataGeo(tree_data, self.root_item)
        elif self.display_mode == 'admin':
            self.setupModelDataAdmin(tree_data, self.root_item)

    def setupModelDataAdmin(self,
                            tree_data,
                            parent_item):

        if isinstance(tree_data, list):
            # If it's just a list, it's a list of leaves
            for leaf_code in tree_data:
                leaf = TreeItem(leaf_code,
                                {'fullname': leaf_code},
                                parent_item)
                parent_item.appendChild(leaf)
            return

        for branch_code, fields in tree_data.items():
            branch = TreeItem(branch_code, fields, parent_item)
            parent_item.appendChild(branch)
            if self.subdivisions_key and fields.get(self.subdivisions_key, None):
                dep_branch = TreeItem('ADMIN_' + branch_code,
                                      {'fullname': 'ADMIN'},
                                      branch)
                branch.appendChild(dep_branch)
                self.setupModelDataAdmin(fields[self.subdivisions_key], dep_branch)
            if self.dependencies_key and fields.get(self.dependencies_key, None):
                dep_branch = TreeItem('DEP_' + branch_code,
                                      {'fullname': 'DEPENDENCIES'},
                                      branch)
                branch.appendChild(dep_branch)
                self.setupModelDataAdmin(fields[self.dependencies_key], dep_branch)
            if self.geounits_key and fields.get(self.geounits_key, None):
                self.setupModelDataAdmin(fields[self.geounits_key], branch)

    def setupModelDataUNM49(self, tree_data, parent_item):

        #if isinstance(tree_data, tuple):
        #    # If it's just a tuple, it's a tuple of territories
        #    for leaf_code in tree_data:
        #        leaf_name = cst.UNSD_M49_NAMES.get(leaf_code, leaf_code)
        #        leaf = TreeItem(leaf_code, {'fullname': leaf_name}, parent_item)
        #        parent_item.appendChild(leaf)
        #    return

        for branch_code, sub_codes in tree_data.items():
            branch_name = cst.UNSD_M49_NAMES.get(branch_code, branch_code)
            branch = TreeItem(branch_code,
                              {'fullname': branch_name},
                              parent_item)
            parent_item.appendChild(branch)
            if isinstance(sub_codes, tuple):
                 for code in sub_codes:
                     if isinstance(code, dict):
                         self.setupModelDataUNM49(code, branch)
            else:
                self.setupModelDataUNM49(sub_codes, branch)

    def setupModelDataGeo(self, tree_data, parent_item):

        if isinstance(tree_data, list):
            # If it's just a list, it's a list of leaves
            for leaf_code in tree_data:
                #prefix = ''
                #if parent := leaf_data.get('parent', ''):
                #     prefix = f'[{parent:s}] '
                leaf = TreeItem(leaf_code,
                                {'fullname': leaf_code},
                                parent_item)
                parent_item.appendChild(leaf)
            return

        for branch_code, fields in tree_data.items():
            unsd_m49 = fields.get('world_region', '')
            if unsd_m49:
                unsd_m49 = unsd_m49.split('/')[-1]
                item = self.findFirst(unsd_m49, role=None)
                if item:
                    parent_item = item
            elif 'parent' not in fields:
                parent_item = self.root_item
            branch = TreeItem(branch_code, fields, parent_item)
            parent_item.appendChild(branch)
            if self.subdivisions_key and fields.get(self.subdivisions_key, None):
                self.setupModelDataGeo(fields[self.subdivisions_key],
                                       branch)
            if self.dependencies_key and fields.get(self.dependencies_key, None):
                self.setupModelDataGeo(fields[self.dependencies_key],
                                       self.root_item) # might be anywhere
            if self.geounits_key and fields.get(self.geounits_key, None):
                self.setupModelDataGeo(fields[self.geounits_key],
                                       branch)

    # def setupModelData(self, tree_data, parent_item):
    #     adding_branches = isinstance(tree_data, dict)
    #     # if tree_data is a list, the loop actually creates leaves

    #     for branch_name in tree_data:
    #         branch = TreeItem(branch_name, parent_item)
    #         parent_item.appendChild(branch)
    #         if adding_branches:
    #             self.setupModelData(tree_data[branch_name], branch)
