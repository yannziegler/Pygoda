# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import constants as cst
import config as cfg

class SignalDispatcher(QtCore.QObject):

    ctrl_to_gui = QtCore.Signal(dict)
    ctrl_to_status = QtCore.Signal(dict)
    ctrl_to_dataset = QtCore.Signal(dict)

    def __init__(self):
        QtCore.QObject.__init__(self)

        self.id = id(self) # used to 'sign' signals

        # Order matters (more or less)!
        # E.g.: UPDATE_FEATURES must be done before SORT_BY or DISPLAY_FEATURE
        self.SIGNALS_DISPATCH = {
        'MODE': self.switchMode, # switch to another mode
        'CATEGORY_CHANGED': self.updateDataset, # stations have been assigned to a new category
        'REFERENCE_POINT': self.setReferencePoint, # a new georeference has been selected
        'UPDATE_FEATURES': self.updateFeatures, # recompute some features
        'SORT_ORDER': self.setSortOrder, # reverse sort order
        'SORT_BY': self.setSortFeature, # another feature has been selected for sorting
        'FILTER': self.filterStations, # filter using the provided list of stations
        'COMPONENT': self.setDataComponent, # another component has been selected in the dataset
        'CURRENT_CAT_GROUP': self.setCurrentCategoriesGroup, # switch to another group of categories
        'PLOTTED': self.updatePlottedStations, # stations have been plotted
        'DISPLAY_FEATURE': self.setDisplayedFeature, # another feature has been selected for display
        }

    # def addReceivers(self, slot_list):
    #     for slot in slot_list:
    #         self.signal.connect(slot)

    @QtCore.Slot(dict)
    def receiveSignal(self, sta_events):

        print(sta_events)

        broadcast = True
        for event in self.SIGNALS_DISPATCH.keys():
            if event in sta_events.keys():
                print(f'Handling event {event}...')
                self.SIGNALS_DISPATCH[event](sta_events)
                broadcast = False

        if broadcast:
            # Broadcast explicitly if none of the signals were known
            print('Broadcasting:', sta_events)
            self.broadcastSignal(sta_events)

    def broadcastSignal(self, sta_events):
        # Forward the message to all the connected GUI elements
        self.ctrl_to_gui.emit(sta_events)

    def switchMode(self, sta_events):
        cfg.mode = sta_events['MODE']
        self.updateStatus(mode=cst.MODES_NAME[cfg.mode])
        self.broadcastSignal(sta_events)

    def updatePlottedStations(self, sta_events):
        if cfg.pending_sort:
            self.sortStations(silent_sort=True)
        # This is a non-permanent interaction, just update the view
        for staname, state in sta_events['PLOTTED'].items():
            # Update the list of stations plotted in the grid
            # Set to False the ones which are not plotted anymore
            cfg.plotted_sta[staname] = state

        self.updateStatus(grid='New stations plotted')
        self.broadcastSignal(sta_events)

    def setDataComponent(self, sta_events):
        # The user has selected another component in the dataset
        # ...or applied different corrections
        # (then we have both 'COMPONENT' and 'CORRECTIONS')
        cfg.data_component = sta_events['COMPONENT']

        for sta, data in cfg.dataset.getData().items():
            data.setMainComponent(cfg.data_component)
            if 'CORRECTIONS' in sta_events:
                data.applyCorrections(sta_events['CORRECTIONS'])

        self.broadcastSignal(sta_events)

    def updateDataset(self, sta_events):
        # The user has modified something in the metadata
        self.ctrl_to_dataset.emit(sta_events)

    def setCurrentCategoriesGroup(self, sta_events):
        cfg.current_grp = sta_events['CURRENT_CAT_GROUP']
        self.broadcastSignal(sta_events)

    def sortStations(self, delayed=False, silent_sort=False):
        if delayed:
            cfg.pending_sort = True
            return

        # Heavy GUI update, similar to full reload
        cfg.stalist_all = cfg.features.sortByFeature(cfg.sort_by, cfg.sort_asc)
        cfg.pending_sort = False

        # Keep only the stations which were not filtered out
        sorted_sta = []
        for sta in cfg.stalist_all:
            if sta in cfg.stalist:
                sorted_sta.append(sta)
        cfg.stalist = sorted_sta

        if not silent_sort:
            self.send({'SORTED': (cfg.sort_by, cfg.sort_asc)})

    def setSortOrder(self, sta_events):
        cfg.sort_asc = sta_events['SORT_ORDER']
        # Note: overwritten by SORT_BY if present

    def setSortFeature(self, sta_events):
        sort_by, sort_asc = sta_events['SORT_BY']
        cfg.sort_by = sort_by if sort_by else cfg.sort_by
        cfg.sort_asc = sort_asc
        delayed = sta_events.get('DELAY_SORT', False)
        self.sortStations(delayed=delayed)

    def setDisplayedFeature(self, sta_events):
        old_feature = cfg.displayed_feature
        cfg.displayed_feature = sta_events['DISPLAY_FEATURE']
        if 'SORT_BY' not in sta_events and cfg.displayed_feature != old_feature:
            if not cfg.features.getStationsFeature(cfg.displayed_feature):
                cfg.features.computeFeatures(cfg.displayed_feature)
        self.send({'DISPLAY_FEATURE': cfg.displayed_feature})

    def updateFeatures(self, sta_events):
        cfg.features.computeFeatures(sta_events['UPDATE_FEATURES'])
        #TODO: update the sorting automatically if needed

    def filterStations(self, sta_events):
        if sta_events['FILTER']:
            if sta_events['FROM'] not in cfg.filter_history:
                # Store the previous list of stations
                cfg.filter_history[sta_events['FROM']] = cfg.stalist.copy()
            filter_stalist = sta_events['FILTER']
        else:
            # Reset the filter
            filter_stalist = cfg.filter_history.get(sta_events['FROM'], cfg.stalist_all).copy()
            if sta_events['FROM'] in cfg.filter_history:
                del cfg.filter_history[sta_events['FROM']]

        cfg.stalist = filter_stalist.copy()
        cfg.nsta = len(cfg.stalist)
        self.updateStatus(main='Filtering the stations')

        if cfg.pending_sort or cfg.sort_by:
            self.sortStations(silent_sort=True)

        sta_events['FILTER'] = cfg.stalist.copy()
        self.send(sta_events)

    def setReferencePoint(self, sta_events):
        cfg.reference_point = sta_events['REFERENCE_POINT']
        cfg.features.computeFeatures('SPACE.D0')
        if cfg.sort_by == 'SPACE.D0':
            # Update immediately
            self.sortStations()

    def updateStatus(self, main=None, mode=None, grid=None):
        message_dict = dict()
        if main is not None:
            message_dict['main_status'] = main
        if mode is not None:
            message_dict['mode_status'] = mode
        if grid is not None:
            message_dict['grid_status'] = grid

        self.ctrl_to_status.emit(message_dict)

    def send(self, message):
        message['FROM'] = self.id
        self.ctrl_to_gui.emit(message)
