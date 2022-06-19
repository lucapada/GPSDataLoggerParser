import platform
import subprocess
import sys, os
import time

import serial

from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QFileDialog
from PyQt5 import QtCore, QtGui, QtWidgets

from modules.BackendHandler import Handler
from modules.Reporter import Observer, Reporter, Observable
from modules.Utils import msg2bits, splitBytes, strfind

# from WindowsNT
if os.name == 'nt':
    from serial.tools.list_ports_windows import comports
# Mac & Linux are POSIX compliant (UNIX like systems)
elif os.name == 'posix':
    from serial.tools.list_ports_posix import comports
else:
    raise ImportError("OS Platform not properly detected")

BAUDRATES = ['9600', '57600']
CONSTELLATIONS = ["GPS","SBAS","Galileo","BeiDou","IMES","QZSS","GLONASS"]

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def __init__(self, MainWindow):
        self.MainWindow = MainWindow
        self.setupUi()
        self.MainWindow.show()

        # blocco tutto
        self.sourcesGroupBox.setEnabled(False)
        self.rinexGroupBox.setEnabled(False)

        # aggiungo i baudrates
        self.cmbBaudRateUBX.clear()
        for b in BAUDRATES:
            self.cmbBaudRateUBX.addItem(b)

        # aggiungo le costellazioni
        self.modelCostellazioni = QStandardItemModel()
        for c in range(len(CONSTELLATIONS)):
            item = QStandardItem(CONSTELLATIONS[c])
            item.setCheckable(True)
            checked = False # di default non sono selezionati
            check = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            item.setCheckState(check)
            self.modelCostellazioni.appendRow(item)
        self.constellationsListView.setModel(self.modelCostellazioni)

        # seleziono "Serial Port" come default tab
        self.tabWidget.setCurrentIndex(0)

        # handle events
        self.btnChooseUBXPath.clicked.connect(self.chooseFolder)
        self.btnDiscoverUBXDevices.clicked.connect(self.discoverDevices)
        self.btnRecordUBX.clicked.connect(self.recordUBXs)
        self.btnStopUBX.clicked.connect(self.stopUBXs)
        self.ubxDevicesListView.clicked.connect(self.toggleUBXControl)
        self.btnRunRINEX.clicked.connect(self.startRinex)

    def setupUi(self):
        MainWindow = self.MainWindow
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1023, 589)
        MainWindow.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        MainWindow.setStatusTip("")
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_13 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_13.setObjectName("gridLayout_13")
        self.gridLayout_12 = QtWidgets.QGridLayout()
        self.gridLayout_12.setObjectName("gridLayout_12")
        self.gridLayout_5 = QtWidgets.QGridLayout()
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName("label")
        self.gridLayout_5.addWidget(self.label, 0, 0, 1, 1)
        self.txtUBXPath = QtWidgets.QLineEdit(self.centralwidget)
        self.txtUBXPath.setReadOnly(True)
        self.txtUBXPath.setObjectName("txtUBXPath")
        self.gridLayout_5.addWidget(self.txtUBXPath, 0, 1, 1, 1)
        self.btnChooseUBXPath = QtWidgets.QPushButton(self.centralwidget)
        self.btnChooseUBXPath.setObjectName("btnChooseUBXPath")
        self.gridLayout_5.addWidget(self.btnChooseUBXPath, 0, 2, 1, 1)
        self.gridLayout_12.addLayout(self.gridLayout_5, 0, 0, 1, 2)
        self.groupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout_11 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_11.setObjectName("gridLayout_11")
        self.txtLogs = QtWidgets.QTextEdit(self.groupBox)
        self.txtLogs.setReadOnly(True)
        self.txtLogs.setObjectName("txtLogs")
        self.gridLayout_11.addWidget(self.txtLogs, 0, 0, 1, 1)
        self.gridLayout_12.addWidget(self.groupBox, 0, 2, 2, 1)
        self.sourcesGroupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.sourcesGroupBox.setObjectName("sourcesGroupBox")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.sourcesGroupBox)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.tabWidget = QtWidgets.QTabWidget(self.sourcesGroupBox)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.tab)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.ubxDevicesListView = QtWidgets.QListView(self.tab)
        self.ubxDevicesListView.setObjectName("ubxDevicesListView")
        self.gridLayout.addWidget(self.ubxDevicesListView, 0, 0, 5, 1)
        self.btnDiscoverUBXDevices = QtWidgets.QPushButton(self.tab)
        font = QtGui.QFont()
        font.setStrikeOut(False)
        font.setKerning(True)
        self.btnDiscoverUBXDevices.setFont(font)
        self.btnDiscoverUBXDevices.setAcceptDrops(False)
        self.btnDiscoverUBXDevices.setObjectName("btnDiscoverUBXDevices")
        self.gridLayout.addWidget(self.btnDiscoverUBXDevices, 0, 1, 1, 3)
        self.label_3 = QtWidgets.QLabel(self.tab)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 1, 1, 1, 1)
        self.cmbBaudRateUBX = QtWidgets.QComboBox(self.tab)
        self.cmbBaudRateUBX.setObjectName("cmbBaudRateUBX")
        self.gridLayout.addWidget(self.cmbBaudRateUBX, 1, 2, 1, 2)
        #self.chkStartRecordingOnConnection = QtWidgets.QCheckBox(self.tab)
        font = QtGui.QFont()
        font.setPointSize(8)
        #self.chkStartRecordingOnConnection.setFont(font)
        #self.chkStartRecordingOnConnection.setObjectName("chkStartRecordingOnConnection")
        #self.gridLayout.addWidget(self.chkStartRecordingOnConnection, 2, 1, 1, 2)
        #self.btnStartUBXDevicesConnection = QtWidgets.QPushButton(self.tab)
        #self.btnStartUBXDevicesConnection.setObjectName("btnStartUBXDevicesConnection")
        #self.gridLayout.addWidget(self.btnStartUBXDevicesConnection, 2, 3, 1, 1)
        self.btnRecordUBX = QtWidgets.QPushButton(self.tab)
        self.btnRecordUBX.setObjectName("btnRecordUBX")
        self.gridLayout.addWidget(self.btnRecordUBX, 3, 1, 1, 3)
        self.btnStopUBX = QtWidgets.QPushButton(self.tab)
        self.btnStopUBX.setObjectName("btnStopUBX")
        self.gridLayout.addWidget(self.btnStopUBX, 4, 1, 1, 3)
        self.gridLayout_3.addLayout(self.gridLayout, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.gridLayout_14 = QtWidgets.QGridLayout(self.tab_2)
        self.gridLayout_14.setObjectName("gridLayout_14")
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.filesListView = QtWidgets.QListView(self.tab_2)
        self.filesListView.setObjectName("filesListView")
        self.gridLayout_2.addWidget(self.filesListView, 0, 0, 2, 1)
        self.btnAddFile = QtWidgets.QPushButton(self.tab_2)
        font = QtGui.QFont()
        font.setStrikeOut(False)
        font.setKerning(True)
        self.btnAddFile.setFont(font)
        self.btnAddFile.setAcceptDrops(False)
        self.btnAddFile.setObjectName("btnAddFile")
        self.gridLayout_2.addWidget(self.btnAddFile, 0, 1, 1, 1)
        self.btnRemoveSelectedFile = QtWidgets.QPushButton(self.tab_2)
        font = QtGui.QFont()
        font.setPointSize(7)
        font.setStrikeOut(False)
        font.setKerning(True)
        self.btnRemoveSelectedFile.setFont(font)
        self.btnRemoveSelectedFile.setAcceptDrops(False)
        self.btnRemoveSelectedFile.setObjectName("btnRemoveSelectedFile")
        self.gridLayout_2.addWidget(self.btnRemoveSelectedFile, 1, 1, 1, 1)
        self.gridLayout_14.addLayout(self.gridLayout_2, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tab_2, "")
        self.gridLayout_4.addWidget(self.tabWidget, 0, 0, 1, 1)
        self.gridLayout_12.addWidget(self.sourcesGroupBox, 1, 0, 1, 2)
        self.groupBox_3 = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout_10 = QtWidgets.QGridLayout(self.groupBox_3)
        self.gridLayout_10.setObjectName("gridLayout_10")
        self.constellationsListView = QtWidgets.QListView(self.groupBox_3)
        self.constellationsListView.setObjectName("constellationsListView")
        self.gridLayout_10.addWidget(self.constellationsListView, 0, 0, 1, 1)
        self.gridLayout_12.addWidget(self.groupBox_3, 2, 0, 1, 1)
        self.rinexGroupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.rinexGroupBox.setObjectName("rinexGroupBox")
        self.gridLayout_9 = QtWidgets.QGridLayout(self.rinexGroupBox)
        self.gridLayout_9.setObjectName("gridLayout_9")
        self.gridLayout_8 = QtWidgets.QGridLayout()
        self.gridLayout_8.setVerticalSpacing(40)
        self.gridLayout_8.setObjectName("gridLayout_8")
        self.groupBox_4 = QtWidgets.QGroupBox(self.rinexGroupBox)
        self.groupBox_4.setObjectName("groupBox_4")
        self.gridLayout_7 = QtWidgets.QGridLayout(self.groupBox_4)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.gridLayout_6 = QtWidgets.QGridLayout()
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.rinexVersion301_radio = QtWidgets.QRadioButton(self.groupBox_4)
        self.rinexVersion301_radio.setChecked(True)
        self.rinexVersion301_radio.setObjectName("rinexVersion301_radio")
        self.gridLayout_6.addWidget(self.rinexVersion301_radio, 0, 0, 1, 1)
        self.rinexVersion305_radio = QtWidgets.QRadioButton(self.groupBox_4)
        self.rinexVersion305_radio.setObjectName("rinexVersion305_radio")
        self.gridLayout_6.addWidget(self.rinexVersion305_radio, 0, 1, 1, 1)
        self.gridLayout_7.addLayout(self.gridLayout_6, 0, 0, 1, 1)
        self.gridLayout_8.addWidget(self.groupBox_4, 0, 0, 1, 1)
        self.btnRunRINEX = QtWidgets.QPushButton(self.rinexGroupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.btnRunRINEX.sizePolicy().hasHeightForWidth())
        self.btnRunRINEX.setSizePolicy(sizePolicy)
        self.btnRunRINEX.setObjectName("btnRunRINEX")
        self.gridLayout_8.addWidget(self.btnRunRINEX, 1, 0, 1, 1)
        self.chkSplitRinexNav = QtWidgets.QCheckBox(self.rinexGroupBox)
        self.chkSplitRinexNav.setObjectName("chkSplitRinexNav")
        self.gridLayout_8.addWidget(self.chkSplitRinexNav, 2, 0, 1, 1)
        self.gridLayout_9.addLayout(self.gridLayout_8, 0, 0, 1, 1)
        self.gridLayout_12.addWidget(self.rinexGroupBox, 2, 1, 1, 2)
        self.gridLayout_13.addLayout(self.gridLayout_12, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1023, 20))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "GPSDataLoggerParser"))
        self.label.setText(_translate("MainWindow", "NMEA and RINEX\n"
"output path:"))
        self.txtUBXPath.setPlaceholderText(_translate("MainWindow", "press \"Choose\" button to select the path where to save collected datas"))
        self.btnChooseUBXPath.setText(_translate("MainWindow", "Choose"))
        self.groupBox.setTitle(_translate("MainWindow", "Messages and Logs"))
        self.sourcesGroupBox.setTitle(_translate("MainWindow", "Sources"))
        self.btnDiscoverUBXDevices.setText(_translate("MainWindow", "Discover Devices"))
        self.label_3.setText(_translate("MainWindow", "Baud Rate:"))
        #self.chkStartRecordingOnConnection.setText(_translate("MainWindow", "Start Recording\non Connection"))
        #self.btnStartUBXDevicesConnection.setText(_translate("MainWindow", "Connect"))
        self.btnRecordUBX.setText(_translate("MainWindow", "Record"))
        self.btnStopUBX.setText(_translate("MainWindow", "Stop"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Serial Port"))
        self.btnAddFile.setText(_translate("MainWindow", "Add File(s)"))
        self.btnRemoveSelectedFile.setText(_translate("MainWindow", "Remove Selected Files"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "UBX Files"))
        self.groupBox_3.setTitle(_translate("MainWindow", "Constellations"))
        self.rinexGroupBox.setTitle(_translate("MainWindow", "RINEX Conversion"))
        self.groupBox_4.setTitle(_translate("MainWindow", "RINEX Version"))
        self.rinexVersion301_radio.setText(_translate("MainWindow", "3.01"))
        self.rinexVersion305_radio.setText(_translate("MainWindow", "3.05"))
        self.btnRunRINEX.setText(_translate("MainWindow", "Run Conversion"))
        self.chkSplitRinexNav.setText(_translate("MainWindow", "Split .nav in different files per constellation"))

    # EVENTS
    def chooseFolder(self):
        # scelgo la cartella
        folder = QFileDialog.getExistingDirectory(self.MainWindow, "Select Folder")
        self.txtUBXPath.setText(folder)
        # sblocco il pannello dei devices
        self.sourcesGroupBox.setEnabled(True)
        # ma blocco il connect, record e lo stop
        self.btnRecordUBX.setEnabled(False)
        self.btnStopUBX.setEnabled(False)

    def discoverDevices(self):
        self.cmbBaudRateUBX.setEnabled(False)
        ports = self.getPorts()
        ports.append("ciao")
        ports.append("come va")
        self.model = QStandardItemModel()
        for p in ports:
            item = QStandardItem(p)
            item.setCheckable(True)
            checked = False  # di default non sono selezionati
            check = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            item.setCheckState(check)
            self.model.appendRow(item)
        self.ubxDevicesListView.setModel(self.model)
        self.cmbBaudRateUBX.setEnabled(True)


    def recordUBXs(self):
        costellazioniAttive = 0
        for c in range(self.modelCostellazioni.rowCount()):
            if self.modelCostellazioni.item(c).checkState() == QtCore.Qt.Checked: costellazioniAttive += 1

        if costellazioniAttive > 0:
            # faccio partire la registrazione dello stream.
            # blocco la possibilità di scegliere le costellazioni e i dispositivi e abilito il pulsante di stop
            self.btnDiscoverUBXDevices.setEnabled(False)
            self.constellationsListView.setEnabled(False)
            self.ubxDevicesListView.setEnabled(False)
            self.btnStopUBX.setEnabled(True)
            self.btnRecordUBX.setEnabled(False)
            self.cmbBaudRateUBX.setEnabled(False)

            # TODO: far partire qui l'acquisizione dei thread
        else:
            QtWidgets.QMessageBox.about(self.MainWindow, "Error", "You don't have selected any GNSS.")

    def stopUBXs(self):
        # TODO: mettere qui l'interruzione dei thread

        self.btnDiscoverUBXDevices.setEnabled(True)
        self.constellationsListView.setEnabled(True)
        self.ubxDevicesListView.setEnabled(True)
        self.btnStopUBX.setEnabled(False)
        self.btnRecordUBX.setEnabled(True)
        self.cmbBaudRateUBX.setEnabled(True)

        #se l'acquisizione è valida, posso procedere alla conversione
        valid = True
        if valid:
            self.rinexGroupBox.setEnabled(True)

    def startRinex(self):
        self.btnRunRINEX.setEnabled(False)
        self.chkSplitRinexNav.setEnabled(False)
        self.rinexVersion301_radio.setEnabled(False)
        self.rinexVersion305_radio.setEnabled(False)
        self.btnDiscoverUBXDevices.setEnabled(False)
        self.constellationsListView.setEnabled(False)
        self.ubxDevicesListView.setEnabled(False)
        self.btnStopUBX.setEnabled(False)
        self.btnRecordUBX.setEnabled(False)
        self.cmbBaudRateUBX.setEnabled(False)

        # TODO: effettuare qui la conversione

        self.btnRunRINEX.setEnabled(True)
        self.chkSplitRinexNav.setEnabled(True)
        self.rinexVersion301_radio.setEnabled(True)
        self.rinexVersion305_radio.setEnabled(True)
        self.btnDiscoverUBXDevices.setEnabled(True)
        self.constellationsListView.setEnabled(True)
        self.ubxDevicesListView.setEnabled(True)
        self.btnStopUBX.setEnabled(False)
        self.btnRecordUBX.setEnabled(True)
        self.cmbBaudRateUBX.setEnabled(True)

        qm = QtWidgets.QMessageBox
        r = qm.question(self.MainWindow, "RINEX Conversion", "RINEX Conversion has been ended. Open folder with all sources and RINEX files?", qm.Yes | qm.No)
        if r == qm.Yes:
            self.openFile(self.txtUBXPath.text())

    # def update(self, obs: Observable) -> None:
    #     '''
    #     Observer update method
    #     :param obs:
    #     :return:
    #     '''
    #     self.printLog(obs._msg)

    def printLog(self, msg: str):
        self.txtLogs.append(msg)

    def openFile(self, path):
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def getPorts(self) -> list:
        serial_objects = comports()
        total = len(serial_objects)

        active_ports = []
        # -------------------------------------------------------------------
        self.printLog("Detecting u-blox(s) connected to COM ports...")
        for idx in range(total):
            so = serial_objects[idx]
            s = serial.Serial(so.device, int(self.cmbBaudRateUBX.currentText()))
            try:
                if s.is_open == False:
                    s.open()
            except serial.SerialException as e:
                self.printLog("SERIAL ERROR on opening serial port: " + so.device)
                break

            # libero i bytes letti
            bytes2read = s.in_waiting
            if bytes2read > 0:
                s.read(bytes2read)
            # poll for UBX-RXM-RAWX
            s.write(b"\xb5\x62\x02\x15\x00\x00\x17\x47")
            time.sleep(0.01)

            bytes_1 = 0
            bytes_2 = 0
            while (bytes_1 != bytes_2 or bytes_1 == 0):
                bytes_1 = s.in_waiting
                time.sleep(0.5)
                bytes_2 = s.in_waiting

            replyBIN = ''.join(msg2bits(splitBytes(s.read(bytes_1))))
            msgBIN = ''.join(msg2bits([b"\xb5", b"\x62", b"\x02", b"\x15"]))
            pos = strfind(msgBIN, replyBIN)
            if len(pos) > 0:
                l = int(replyBIN[(pos[0] + 32):(pos[0] + 39)], 2) + (
                        int(replyBIN[(pos[0] + 40):(pos[0] + 47)], 2) * pow(2, 8))
                if l != 0:
                    self.printLog("u-blox receiver detected on port " + so.device)
                    active_ports.append(so.device)
                    break
            s.close()
            del s
        # -------------------------------------------------------------------
        else:
            self.printLog("No u-blox(s) device detected...")
        return active_ports

    def toggleUBXControl(self):
        selected = 0
        for c in range(self.model.rowCount()):
            item = self.model.item(c)
            if item.checkState() == QtCore.Qt.Checked:
                selected += 1
        if selected > 0:
            self.btnRecordUBX.setEnabled(True)
            self.btnStopUBX.setEnabled(False)
        else:
            self.btnRecordUBX.setEnabled(False)
            self.btnStopUBX.setEnabled(False)

if __name__ == "__main__":
    app = QApplication([])
    window = QMainWindow()
    ui = Ui_MainWindow(window)
    exit(app.exec())
#
# class MainWindow(QMainWindow, Observer):
#     # implementazione del pattern observer
#
#         # -------------------------------------------------
#
#
#
#     def initUI(self):
#         # Port selection
#         self.port_selection = QComboBox()
#         self.port_selection.addItems(self.getPorts())
#
#         # baudrate selection
#         self.baud_selection = QComboBox()
#         self.baud_selection.addItems(BAUDRATES)
#
#         # Input text
#         self.input_device_name = QLineEdit()
#         self.input_logfile_name = QLineEdit()
#
#         # Labels
#         self.in_device_label = QLabel("Device: ")
#         self.in_logfile_name = QLabel("Logfile: ")
#         self.in_baud_label = QLabel("Baudrate: ")
#
#         # control buttons
#         self.refresh_port_btn = QPushButton("Refresh Ports")
#         self.refresh_port_btn.clicked.connect(self.updatePorts)
#
#         self.add_port_btn = QPushButton("Add")
#         self.add_port_btn.clicked.connect(self.portAdded)
#
#         # Table view widget
#         self.MAIN_TABLE = QTableWidget()
#         self.MAIN_TABLE.setRowCount(self.TABLE_ROWS)
#         self.MAIN_TABLE.setColumnCount(self.TABLE_COLUMNS)
#         self.MAIN_TABLE.showNormal()
#         self.updateTableData()
#
#     def initTimer(self):
#         self.timer = QTimer()
#         self.timer.timeout.connect(self.updateAll)
#         self.timer.start(2)
#
#         # Place all widget in main widget
#         self.MainWidgetLayout.addWidget(self.MAIN_TABLE, 0, 0, 5, 4)
#         self.MainWidgetLayout.addWidget(self.port_selection, 6, 0, 1, 1)
#         self.MainWidgetLayout.addWidget(self.refresh_port_btn, 6, 1, 1, 1)
#         self.MainWidgetLayout.addWidget(self.add_port_btn, 6, 2, 1, 2)
#         self.MainWidgetLayout.addWidget(self.in_device_label, 7, 0, 1, 1)
#         self.MainWidgetLayout.addWidget(self.input_device_name, 7, 1, 1, 1)
#         self.MainWidgetLayout.addWidget(self.in_logfile_name, 7, 2, 1, 1)
#         self.MainWidgetLayout.addWidget(self.input_logfile_name, 7, 3, 1, 1)
#         self.MainWidgetLayout.addWidget(self.in_baud_label, 8, 0, 1, 1)
#         self.MainWidgetLayout.addWidget(self.baud_selection, 8, 1, 1, 1)
#
#     def updateTableData(self):
#         self.MAIN_TABLE.setRowCount(self.TABLE_ROWS)
#         horHeaders = []
#
#         for col, key in enumerate(self.MAIN_TABLE_DATA.keys()):
#             horHeaders.append(key)
#
#             # Add new items with read only
#             for row, item in enumerate(self.MAIN_TABLE_DATA[key]):
#                 newitem = QTableWidgetItem(item)
#                 newitem.setFlags(newitem.flags() & ~Qt.ItemFlag.ItemIsEditable)
#                 self.MAIN_TABLE.setItem(row, col, newitem)
#
#         self.MAIN_TABLE.setHorizontalHeaderLabels(horHeaders)
#
#     # EVENT HANDLERS
#     def updatePorts(self):
#         connected_ports = self.getPorts()
#         current_ports = [self.port_selection.itemText(i) for i in range(self.port_selection.count())]
#         new_port = []
#         for port in connected_ports:
#             if port not in current_ports:
#                 new_port.append(port)
#
#         self.port_selection.addItems(new_port)
#
#     def portAdded(self):
#         # Update connected port list
#         new_connection = self.port_selection.currentText()
#         new_device = self.input_device_name.text()
#         new_logfile = self.input_logfile_name.text()
#         new_baud = int(self.baud_selection.currentText())
#
#         # Check if new connection is already in table
#         if new_connection not in self.MAIN_TABLE_DATA["Port"]:
#
#             # Check if logfile & device nickname is specified
#             if (len(new_device) > 0) and (len(new_logfile) > 0):
#
#                 # Try to connect
#                 # new_handler = Handler(new_connection, new_logfile, new_baud)
#                 new_GNSS = {
#                     "GPS": 1,
#                     "GAL": 0,
#                     "GLO": 0,
#                     "BEI": 0,
#                     "QZSS": 0,
#                     "IMES": 0,
#                     "SBAS": 0,
#                 }
#                 new_handler = Handler(new_connection, new_baud, new_GNSS)
#
#                 if new_handler.isActive():
#                     self.DEVICES_NAME.append(new_device)
#                     self.CONNECTED_PORTS.append(new_connection)
#                     self.LOGFILES_LIST.append(new_logfile)
#                     self.HANDLERS[new_connection] = new_handler
#                     self.HANDLERS[new_connection].handleData()
#
#                     # Update table content
#                     self.TABLE_ROWS += 1
#                     self.updateTableData()
#                     self.adjustSize()
#                 else:
#                     MainWindow.showDialog("ERROR", f"Cannot connect to {new_connection}")
#             else:
#                 MainWindow.showDialog("ERROR", "Missing information. Please provide both logfile & device name")
#         else:
#             MainWindow.showDialog("ERROR", "Cannot assign already existing port.")
#
#         # Clear text
#         self.input_device_name.setText('')
#         self.input_logfile_name.setText('')
#
#     def updateAll(self):
#         inactive = []
#         handler_keys = list(self.HANDLERS.keys())
#
#         if len(handler_keys) > 0:
#             for key in handler_keys:
#                 # remove handler if inactive
#                 if not self.HANDLERS[key].logger.is_active:
#                     self.HANDLERS.pop(key, "")
#                     inactive.append(key)
#
#         # Remove corresponding table element
#         for port in inactive:
#             print(f"[LOGGER] {port} disconnected")
#             index = self.CONNECTED_PORTS.index(port)
#             self.CONNECTED_PORTS.pop(index)
#             self.LOGFILES_LIST.pop(index)
#             self.DEVICES_NAME.pop(index)
#
#             self.TABLE_ROWS -= 1
#             self.updateTableData()
#
#     # Generic Dialog
#     @staticmethod
#     def showDialog(dialog_title: str, msg: str):
#         d = QDialog()
#         layout = QGridLayout()
#         d.setLayout(layout)
#
#         warn_msg = QLabel(msg)
#         layout.addWidget(warn_msg, 0, 0)
#
#         d.setWindowTitle(dialog_title)
#         d.exec_()
#
#
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     main = MainWindow()
#     exit(app.exec_())
