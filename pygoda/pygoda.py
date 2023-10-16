# coding: utf-8

from PySide2 import QtCore, QtWidgets, QtGui

import glob
import hashlib
import os
import platform
import shutil
import sys

import strictyaml as yaml

import constants as cst
import projects
from gui import new_project
from gui import project

# class EmittingStream(QtCore.QObject):
#     def __init__(self):
#         super().__init__()

#         self.textWritten = QtCore.Signal(str)

#     def write(self, text):
#         self.textWritten.emit(str(text))


class Pygoda(QtWidgets.QMainWindow):

    def __init__(self, project_name='', screens=None):
        QtWidgets.QMainWindow.__init__(self)
        self.setWindowTitle('Pygoda')

        # Menu
        self.menu = self.menuBar()

        # Main menu
        self.project_menu = self.menu.addMenu("&Pygoda")
        self.new_project = QtWidgets.QAction("&New project")
        #self.new_project.triggered.connect(self.newProject)
        self.new_project.triggered.connect(self.workInProgress)
        self.project_menu.addAction(self.new_project)
        # self.load_project = QtWidgets.QAction("Open project")
        # self.load_project.triggered.connect(self.openProject)
        # self.project_menu.addAction(self.load_project)
        # self.project_menu.addMenu("Recent projects...")

        # Help/about
        self.help_menu = self.menu.addMenu("&Help")
        self.getting_started = QtWidgets.QAction("Getting &started")
        self.getting_started.triggered.connect(self.gettingStartedPage)
        self.help_menu.addAction(self.getting_started)
        self.documentation = QtWidgets.QAction("&Documentation")
        self.documentation.triggered.connect(self.documentationPage)
        self.help_menu.addAction(self.documentation)
        self.repository = QtWidgets.QAction("GitHub &repository")
        self.repository.triggered.connect(self.repositoryPage)
        self.help_menu.addAction(self.repository)
        self.help_menu.addSeparator()
        self.about = QtWidgets.QAction("&About")
        self.about.triggered.connect(self.aboutMessage)
        self.help_menu.addAction(self.about)
        self.copy_about = QtWidgets.QAction("Copy &Pygoda Information")
        self.copy_about.triggered.connect(self.copyAbout)
        self.help_menu.addAction(self.copy_about)
        self.copy_info = QtWidgets.QAction("Copy &Technical Information")
        self.copy_info.triggered.connect(self.copyTechnicalInfo)
        self.help_menu.addAction(self.copy_info)

        # Exit QAction
        self.exit_action = QtWidgets.QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.exitApp)
        self.project_menu.addSeparator()
        self.project_menu.addAction(self.exit_action)

        self.screens = screens

        # List YAML config files
        self.listConfigFiles()

        # Get projects list
        self.projects = projects.Projects(cst.DEFAULT_PROJECTS_FILE,
                                          default_config=self.default_config_files,
                                          default_themes=self.default_themes_files)

        # Open project immediately if provided
        # if project_name:
        #     self.openProject(project_name)
        #     QtWidgets.QApplication.quit()

        if not project_name:
            project_name = self.projects.getProjectsList()[0]

        # self.openProject(project_name)
        # QtWidgets.QApplication.quit()

        # Layout
        self.main_widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QGridLayout()

        # self.line_edit = QtWidgets.QLineEdit()
        # self.layout.addWidget(self.line_edit)

        # self.text_edit = QtWidgets.QTextEdit()
        # layout.addWidget(self.text_edit)

        self.project_list_widget = QtWidgets.QListWidget()
        self.project_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.layout.addWidget(self.project_list_widget)

        self.project_list = self.projects.getProjectsList()
        if not self.project_list:
            self.newProject()

        self.refreshProjectsList()

        self.button = QtWidgets.QPushButton('Load selected project')
        self.button.clicked.connect(self.openProject)
        self.layout.addWidget(self.button)

        self.main_widget.setLayout(self.layout)

        self.setCentralWidget(self.main_widget)

        self.show()

    def listConfigFiles(self):

        # Default files
        self.default_config_files = [cst.DEFAULT_CONFIG_FILE]
        self.default_themes_files = [cst.DEFAULT_THEMES_FILE]

        # Global user files (if any) in config directory
        config_path = os.path.join(cst.CONFIG_PATH, 'config*.yaml')
        themes_path = os.path.join(cst.CONFIG_PATH, 'themes*.yaml')
        config_list = glob.glob(config_path).sort()
        themes_list = glob.glob(themes_path).sort()
        if config_list:
            self.default_config_files += config_list
        if themes_list:
            self.default_themes_files += themes_list

    @QtCore.Slot()
    def openProject(self, project_name=''):
        if not project_name:
            project_name = self.projects.getProjectsList()[0]
            selected_project = self.project_list_widget.selectedItems()
            if selected_project:
                project_name = selected_project[0].text()

        print(f'Opening project {project_name}...')
        selected_project = self.projects.getProject(project_name)
        self.project_gui = project.ProjectWindow(selected_project)
        #if self.screens is not None and len(self.screens) >= 2:
        #    self.project_gui.windowHandle().setScreen(self.screens[1])
        # self.project_gui.showFullScreen()
        self.project_gui.show()
        # self.project_gui.data_grid.createPlotsGrid()

    def refreshProjectsList(self):

        self.project_list = self.projects.getProjectsList()

        self.project_list_widget.clear()
        for project_name in self.project_list:
            project = QtWidgets.QListWidgetItem(project_name)
            project.setData(QtCore.Qt.UserRole, project_name)
            self.project_list_widget.addItem(project)

    def newProject(self):

        project_wizard = new_project.ProjectWizard()
        # project_wizard.show()
        project_wizard.exec()

        # Update project list
        self.refreshProjectsList()

    def workInProgress(self):

        msg = f'<span style="font-weight: bold">Please bear with me!</span><br />'
        msg += '<span >The <span style="font-style: italic">New Project</span> wizard is still under development.</span><br />'
        msg += '<span >Contact me (Yann Ziegler) if you would like to use Pygoda with your project:</span><br />'
        msg += f'<a href="https://github.com/yannziegler/Pygoda">https://github.com/yannziegler/Pygoda</a>'

        msg_box = QtWidgets.QMessageBox(self)
        # msg_box.addButton(copy_btn)
        msg_box.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        msg_box.about(self, 'Work In Progress', msg)

    def gettingStartedPage(self):

        QtGui.QDesktopServices.openUrl(QtCore.QUrl(cst.DOCUMENTATION + '/user/quickstart.html'))

    def documentationPage(self):

        QtGui.QDesktopServices.openUrl(QtCore.QUrl(cst.DOCUMENTATION))

    def repositoryPage(self):

        QtGui.QDesktopServices.openUrl(QtCore.QUrl(cst.GITHUB))

    def aboutMessage(self):

        version = f'v<a href="">{cst.VERSION}</a>'
        if cst.DEVELOP:
            about_msg = f'<span style="font-weight: bold">{cst.APPNAME} &alpha; (last release: {version}, {cst.DATE})</span><br />'
        else:
            about_msg = f'<span style="font-weight: bold">{cst.APPNAME} {version} ({cst.DATE})</span><br />'
        author = f'<a href="{cst.AUTHOR_URL}">{cst.AUTHOR}</a>'
        licence = f'<a href="{cst.LICENCE_URL}">{cst.LICENCE}</a>'
        birthplace = f'<a href="{cst.BIRTHPLACE_URL}">{cst.BIRTHPLACE}</a>'
        about_msg += f'<span >Created by {author} @ {birthplace}</span><br />'
        about_msg += f'<span >Licence {licence}</span><br />'
        about_msg += '<br />'
        about_msg += f'<span style="font-weight: bold">Library information:</span><br />'
        about_msg += f'<span >Qt version: {QtCore.__version__}</span><br />'
        full_version = sys.version.split('|', 1)
        py_version = full_version[0].strip()
        about_msg += f'<span >Python version: {py_version}</span><br />'
        py_details = full_version[1].strip() if len(full_version) > 1 else ''
        if py_details:
            about_msg += f'<span >{py_details}</span><br />'

        msg_box = QtWidgets.QMessageBox(self)
        # msg_box.addButton(copy_btn)
        msg_box.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        msg_box.about(self, 'About Pygoda', about_msg)

    def copyAbout(self):

        info = f'{cst.APPNAME} v{cst.VERSION} ({cst.DATE})\n'
        info += f'Created by {cst.AUTHOR} ({cst.AUTHOR_URL})\n'
        info += f'Licence {cst.LICENCE} ({cst.LICENCE_URL})\n'
        info += f'Documentation: {cst.DOCUMENTATION}\n'
        info += f'GitHub repository: {cst.GITHUB}'

        QtGui.QGuiApplication.clipboard().setText(info)

    def copyTechnicalInfo(self):

        info = f'{cst.APPNAME} v{cst.VERSION} ({cst.DATE})\n'
        arch = platform.architecture()
        if isinstance(arch, tuple):
            arch = ' '.join(arch)
        info += f'OS: {platform.platform()} ({arch})\n'
        info += f'Python version: {sys.version}\n'
        info += f'Qt version: {QtCore.__version__}'

        QtGui.QGuiApplication.clipboard().setText(info)

    @QtCore.Slot()
    def exitApp(self):
        QtWidgets.QApplication.quit()

#     # Install the custom output stream
#     sys.stdout = EmittingStream(textWritten=self.normalOutputWritten)

# def __del__(self):
#     # Restore sys.stdout
#     sys.stdout = sys.__stdout__

# def normalOutputWritten(self, text):
#     """Append text to the QTextEdit."""
#     # Maybe QTextEdit.append() works as well, but this is how I do it:
#     cursor = self.text_edit.textCursor()
#     cursor.movePosition(QtGui.QTextCursor.End)
#     cursor.insertText(text)
#     self.textEdit.setTextCursor(cursor)
#     self.textEdit.ensureCursorVisible()


if __name__ == "__main__":
    print(QtCore.__version__)
    print(sys.version, sys.version_info)

    ## Some sanity checks, copy files if needed
    def replaceIfDifferent(old_file, new_file):
        """Replace old_file with new_file if they are different"""

        if not os.path.isfile(old_file):
            shutil.copyfile(new_file, old_file)
        else:
            with open(new_file, mode='rb') as f:
                # new_version = yaml.load(f.read()).data['VERSION']
                new_hash = hashlib.sha256(f.read()).digest()

            with open(old_file, mode='rb') as f:
                # current_version = yaml.load(f.read()).data.get('VERSION', '')
                current_hash = hashlib.sha256(f.read()).digest()

            if current_hash != new_hash:
                shutil.copyfile(new_file, old_file)

    # Create user config directory
    os.makedirs(cst.CONFIG_PATH, exist_ok=True)

    # Copy the config file template in user directory
    replaceIfDifferent(cst.USER_CONFIG_TEMPLATE, cst.DEFAULT_CONFIG_TEMPLATE)

    # Copy the themes file template in user directory
    replaceIfDifferent(cst.USER_THEMES_TEMPLATE, cst.DEFAULT_THEMES_TEMPLATE)

    ## Prepare project
    if len(sys.argv) > 1:
        selected_project = sys.argv[1]
    else:
        selected_project = ''

    ## Launch main QApplication

    # Remove error 'js: Not allowed to load local resource'
    sys.argv += ['--disable-web-security']
    app = QtWidgets.QApplication(sys.argv)

    main_window = Pygoda(project_name=selected_project, screens=app.screens())
    # main_window.resize(250, 200)
    # main_window.show()

    sys.exit(app.exec_())

