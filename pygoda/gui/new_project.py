# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import functools
import os
import sys


class ProjectWizard(QtWidgets.QWizard):

    def __init__(self):
        # super().__init__(self)
        QtWidgets.QWizard.__init__(self)

        self.addPage(self.createIntro())
        self.addPage(self.createNamePath())
        self.addPage(self.createFileFormat())
        self.addPage(self.createMetadata())

        self.setWindowTitle("Project Wizard")

    def accept(self):

        name = self.field('project_name')
        desc = self.field('project_desc')
        project_directory = self.field('project_directory')

        print('New project:', name, desc, project_directory)

    def createIntro(self):

        page = QtWidgets.QWizardPage(self)
        page.setTitle("Introduction")

        layout = QtWidgets.QVBoxLayout()

        msg = "This wizard will help you create a \
               <b>new Pygoda project</b>.<br/><br/>"
        msg += "A project is made of:"
        msg += """<ul>
                  <li>a project configuration file</li>
                  <li>a data set (one or several data files)</li>
                  <li>a data descriptor file describing the data set</li>
                  <li>additional configuration files (optional)</li>
                </ul>"""
        msg += "This wizard will guide you through all the steps needed to \
                configure your project and will create the required files for \
                you.<br/><br/>"
        msg += "<b>Important:</b> if you are creating a project for the first \
                time, or did not create any other project recently, please \
                read and follow the instructions carefully."

        label = QtWidgets.QLabel(msg)
        label.setWordWrap(True)
        layout.addWidget(label)

        page.setLayout(layout)

        return page

    def createNamePath(self):

        page = QtWidgets.QWizardPage(self)
        page.setTitle("Project description")

        page_layout = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()

        # Project unique name

        name = QtWidgets.QLineEdit()
        name.setMaxLength(50)
        name.setPlaceholderText("unique name (max 50 characters among a-z A-Z 0-9 _ -)")
        name.setValidator(QtGui.QRegExpValidator('[a-zA-Z0-9_-]+'))
        form.addRow("&Name", name)
        page.registerField('project_name*', name)

        # Project description

        def checkLength():
            nmax = 500
            if len(desc.toPlainText()) <= nmax:
                return
            text = desc.toPlainText()
            desc.setPlainText(text[:nmax])
            cursor = desc.textCursor()
            cursor.setPosition(desc.document().characterCount() - 1)
            desc.setTextCursor(cursor)

        desc = QtWidgets.QTextEdit()
        desc.textChanged.connect(checkLength)
        desc.setPlaceholderText("short project description (max 500 characters)")
        form.addRow("De&scription", desc)
        page.registerField('project_desc', desc, 'plainText')

        ## Customise paths

        paths_group = QtWidgets.QGroupBox("Project directory and paths")
        dir_layout = QtWidgets.QVBoxLayout()

        paths_form = QtWidgets.QFormLayout()

        # Project directory

        def browseDirectory(field, default_path=QtCore.QDir.currentPath()):
            selected_dir = QtWidgets.QFileDialog.getExistingDirectory(\
                            self,
                            "Select Project Directory",
                            default_path)
                            # QtCore.QDir.currentPath())
            field.setText(selected_dir)

            if field == project_directory and relative_path.isChecked():
                # Reset relative paths which are probably wrong now
                config_directory.setText('')
                data_directory.setText('')

            if relative_path.isChecked():
                project_dir = QtCore.QDir(project_directory.text())
                selected_dir = project_dir.relativeFilePath(selected_dir)
                if field == config_directory:
                    config_directory.setText(selected_dir)
                if field == data_directory:
                    data_directory.setText(selected_dir)

        def updateDirectory():
            if project_directory.text():
                config_checkbox.setEnabled(True)
                # data_checkbox.setEnabled(True)
                relative_path.setEnabled(True)
                absolute_path.setEnabled(True)
            else:
                config_checkbox.setEnabled(False)
                # data_checkbox.setEnabled(False)
                relative_path.setEnabled(False)
                absolute_path.setEnabled(False)

        directory_layout = QtWidgets.QHBoxLayout()
        project_directory = QtWidgets.QLineEdit()
        msg = "where all the files created by the project will be stored"
        project_directory.setPlaceholderText(msg)
        project_directory.textChanged.connect(updateDirectory)
        directory_layout.addWidget(project_directory)
        browse = QtWidgets.QPushButton("&Browse...")
        browse.clicked.connect(functools.partial(browseDirectory,
                                                 project_directory))
        directory_layout.addWidget(browse)
        paths_form.addRow("Project", directory_layout)
        page.registerField('project_directory*', project_directory)

        # Data location

        # def toggleDataDirectory():
        #     data_directory.setEnabled(data_checkbox.checkState())
        #     data_browse.setEnabled(data_checkbox.checkState())

        # msg = "Use a different directory for the project data"
        # data_checkbox = QtWidgets.QCheckBox(msg)
        # data_checkbox.setEnabled(False)
        # data_checkbox.stateChanged.connect(toggleDataDirectory)
        # paths_form.addRow("", data_checkbox)

        directory_layout = QtWidgets.QHBoxLayout()
        data_directory = QtWidgets.QLineEdit()
        msg = "where the data used in the project are stored"
        data_directory.setPlaceholderText(msg)
        directory_layout.addWidget(data_directory)
        data_browse = QtWidgets.QPushButton("&Browse...")
        data_browse.clicked.connect(functools.partial(browseDirectory,
                                                      data_directory,
                                                      project_directory.text()))
        directory_layout.addWidget(data_browse)
        paths_form.addRow("Data", directory_layout)
        # data_directory.setEnabled(False)
        # data_browse.setEnabled(False)
        page.registerField('data_directory*', data_directory)

        # Project file location, if different from project directory

        def toggleConfigDirectory():
            config_directory.setEnabled(config_checkbox.checkState())
            config_browse.setEnabled(config_checkbox.checkState())

        msg = "Use a different directory for the project configuration file"
        config_checkbox = QtWidgets.QCheckBox(msg)
        config_checkbox.setEnabled(False)
        config_checkbox.stateChanged.connect(toggleConfigDirectory)
        paths_form.addRow("", config_checkbox)

        directory_layout = QtWidgets.QHBoxLayout()
        config_directory = QtWidgets.QLineEdit()
        msg = "where the main configuration file will be stored"
        config_directory.setPlaceholderText(msg)
        directory_layout.addWidget(config_directory)
        config_browse = QtWidgets.QPushButton("&Browse...")
        config_browse.clicked.connect(functools.partial(browseDirectory,
                                                        config_directory,
                                                        project_directory.text()))
        directory_layout.addWidget(config_browse)
        paths_form.addRow("Config file", directory_layout)
        config_directory.setEnabled(False)
        config_browse.setEnabled(False)
        page.registerField('config_directory', config_directory)

        dir_layout.addLayout(paths_form)

        # Absolute or relative paths

        def togglePaths():
            project_dir = QtCore.QDir(project_directory.text())
            if relative_path.isChecked():
                if config_directory.text():
                    config_directory.setText(project_dir.relativeFilePath(config_directory.text()))
                if data_directory.text():
                    data_directory.setText(project_dir.relativeFilePath(data_directory.text()))
            else:
                if config_directory.text():
                    config_directory.setText(project_dir.cleanPath(project_dir.absoluteFilePath(config_directory.text())))
                if data_directory.text():
                    data_directory.setText(project_dir.cleanPath(project_dir.absoluteFilePath(data_directory.text())))

        path_layout = QtWidgets.QHBoxLayout()
        relative_or_absolute = QtWidgets.QButtonGroup()
        absolute_path = QtWidgets.QRadioButton("use absolute paths")
        msg = "absolute paths: recommended when your project files and data/config are in different directories"
        absolute_path.setToolTip(msg)
        absolute_path.setChecked(True)
        absolute_path.setEnabled(False)
        path_layout.addWidget(absolute_path)
        relative_or_absolute.addButton(absolute_path)
        relative_or_absolute.buttonToggled.connect(togglePaths)
        relative_path = QtWidgets.QRadioButton("use relative paths")
        msg = "relative paths: recommended when your data/config are in your project directory"
        relative_path.setToolTip(msg)
        # relative_path.setChecked(True)
        relative_path.setEnabled(False)
        relative_path.toggled.connect(togglePaths)
        path_layout.addWidget(relative_path)
        relative_or_absolute.addButton(relative_path)
        dir_layout.addLayout(path_layout)

        paths_group.setLayout(dir_layout)

        page_layout.addLayout(form)
        page_layout.addWidget(paths_group)

        page.setLayout(page_layout)

        return page

    def createFileFormat(self):

        return QtWidgets.QWizardPage()

    def createMetadata(self):

        return QtWidgets.QWizardPage()
