# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ra_main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.5.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDockWidget,
    QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QSplitter, QStatusBar, QTextBrowser, QTreeView,
    QVBoxLayout, QWidget)

class Ui_RaMainWindow(object):
    def setupUi(self, RaMainWindow):
        if not RaMainWindow.objectName():
            RaMainWindow.setObjectName(u"RaMainWindow")
        RaMainWindow.resize(1280, 720)
        RaMainWindow.setMinimumSize(QSize(1280, 720))
        self.actionOpen = QAction(RaMainWindow)
        self.actionOpen.setObjectName(u"actionOpen")
        self.centralwidget = QWidget(RaMainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_5 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.splitter_3 = QSplitter(self.centralwidget)
        self.splitter_3.setObjectName(u"splitter_3")
        self.splitter_3.setOrientation(Qt.Horizontal)
        self.splitter = QSplitter(self.splitter_3)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Vertical)
        self.thresholdSettingsGroupBox = QGroupBox(self.splitter)
        self.thresholdSettingsGroupBox.setObjectName(u"thresholdSettingsGroupBox")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.thresholdSettingsGroupBox.sizePolicy().hasHeightForWidth())
        self.thresholdSettingsGroupBox.setSizePolicy(sizePolicy)
        self.horizontalLayout_4 = QHBoxLayout(self.thresholdSettingsGroupBox)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_15 = QLabel(self.thresholdSettingsGroupBox)
        self.label_15.setObjectName(u"label_15")
        sizePolicy.setHeightForWidth(self.label_15.sizePolicy().hasHeightForWidth())
        self.label_15.setSizePolicy(sizePolicy)

        self.horizontalLayout_4.addWidget(self.label_15)

        self.r2ThresholdDoubleSpinBox = QDoubleSpinBox(self.thresholdSettingsGroupBox)
        self.r2ThresholdDoubleSpinBox.setObjectName(u"r2ThresholdDoubleSpinBox")
        self.r2ThresholdDoubleSpinBox.setMaximum(1.000000000000000)
        self.r2ThresholdDoubleSpinBox.setSingleStep(0.010000000000000)
        self.r2ThresholdDoubleSpinBox.setValue(0.700000000000000)

        self.horizontalLayout_4.addWidget(self.r2ThresholdDoubleSpinBox)

        self.label_16 = QLabel(self.thresholdSettingsGroupBox)
        self.label_16.setObjectName(u"label_16")
        sizePolicy.setHeightForWidth(self.label_16.sizePolicy().hasHeightForWidth())
        self.label_16.setSizePolicy(sizePolicy)

        self.horizontalLayout_4.addWidget(self.label_16)

        self.n100dBmToleranceSpinBox = QSpinBox(self.thresholdSettingsGroupBox)
        self.n100dBmToleranceSpinBox.setObjectName(u"n100dBmToleranceSpinBox")
        self.n100dBmToleranceSpinBox.setMaximum(999999999)
        self.n100dBmToleranceSpinBox.setValue(20)

        self.horizontalLayout_4.addWidget(self.n100dBmToleranceSpinBox)

        self.splitter.addWidget(self.thresholdSettingsGroupBox)
        self.treeView = QTreeView(self.splitter)
        self.treeView.setObjectName(u"treeView")
        self.treeView.setEnabled(True)
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.treeView.sizePolicy().hasHeightForWidth())
        self.treeView.setSizePolicy(sizePolicy1)
        self.treeView.setEditTriggers(QAbstractItemView.DoubleClicked|QAbstractItemView.SelectedClicked)
        self.treeView.setSortingEnabled(True)
        self.splitter.addWidget(self.treeView)
        self.analyzerSettingsGroupBox = QGroupBox(self.splitter)
        self.analyzerSettingsGroupBox.setObjectName(u"analyzerSettingsGroupBox")
        sizePolicy.setHeightForWidth(self.analyzerSettingsGroupBox.sizePolicy().hasHeightForWidth())
        self.analyzerSettingsGroupBox.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(self.analyzerSettingsGroupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(self.analyzerSettingsGroupBox)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)

        self.timeStampComboBox = QComboBox(self.analyzerSettingsGroupBox)
        self.timeStampComboBox.setObjectName(u"timeStampComboBox")
        self.timeStampComboBox.setEditable(True)

        self.gridLayout.addWidget(self.timeStampComboBox, 0, 1, 1, 2)

        self.label_3 = QLabel(self.analyzerSettingsGroupBox)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)

        self.timeMultiplierLineEdit = QLineEdit(self.analyzerSettingsGroupBox)
        self.timeMultiplierLineEdit.setObjectName(u"timeMultiplierLineEdit")

        self.gridLayout.addWidget(self.timeMultiplierLineEdit, 1, 1, 1, 1)

        self.timeUnitLineEdit = QLineEdit(self.analyzerSettingsGroupBox)
        self.timeUnitLineEdit.setObjectName(u"timeUnitLineEdit")

        self.gridLayout.addWidget(self.timeUnitLineEdit, 1, 2, 1, 1)

        self.label_6 = QLabel(self.analyzerSettingsGroupBox)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setTextFormat(Qt.MarkdownText)
        self.label_6.setOpenExternalLinks(True)
        self.label_6.setTextInteractionFlags(Qt.TextBrowserInteraction)

        self.gridLayout.addWidget(self.label_6, 2, 0, 1, 1)

        self.patternLineEdit = QLineEdit(self.analyzerSettingsGroupBox)
        self.patternLineEdit.setObjectName(u"patternLineEdit")

        self.gridLayout.addWidget(self.patternLineEdit, 2, 1, 1, 2)

        self.loadAnalyzerButton = QPushButton(self.analyzerSettingsGroupBox)
        self.loadAnalyzerButton.setObjectName(u"loadAnalyzerButton")

        self.gridLayout.addWidget(self.loadAnalyzerButton, 3, 0, 1, 3)

        self.splitter.addWidget(self.analyzerSettingsGroupBox)
        self.plotSpectrogramsGroupBox = QGroupBox(self.splitter)
        self.plotSpectrogramsGroupBox.setObjectName(u"plotSpectrogramsGroupBox")
        self.gridLayout_4 = QGridLayout(self.plotSpectrogramsGroupBox)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.spectrogramSelectAllButton = QPushButton(self.plotSpectrogramsGroupBox)
        self.spectrogramSelectAllButton.setObjectName(u"spectrogramSelectAllButton")

        self.horizontalLayout_3.addWidget(self.spectrogramSelectAllButton)

        self.spectrogramUnselectAllButton = QPushButton(self.plotSpectrogramsGroupBox)
        self.spectrogramUnselectAllButton.setObjectName(u"spectrogramUnselectAllButton")

        self.horizontalLayout_3.addWidget(self.spectrogramUnselectAllButton)


        self.verticalLayout_4.addLayout(self.horizontalLayout_3)

        self.powerListWidget = QListWidget(self.plotSpectrogramsGroupBox)
        self.powerListWidget.setObjectName(u"powerListWidget")

        self.verticalLayout_4.addWidget(self.powerListWidget)


        self.gridLayout_4.addLayout(self.verticalLayout_4, 0, 0, 4, 1)

        self.spectrogramStyleGroupBox = QGroupBox(self.plotSpectrogramsGroupBox)
        self.spectrogramStyleGroupBox.setObjectName(u"spectrogramStyleGroupBox")
        self.gridLayout_2 = QGridLayout(self.spectrogramStyleGroupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_5 = QLabel(self.spectrogramStyleGroupBox)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_5, 1, 0, 1, 1)

        self.xTicksSpinBox = QSpinBox(self.spectrogramStyleGroupBox)
        self.xTicksSpinBox.setObjectName(u"xTicksSpinBox")
        self.xTicksSpinBox.setValue(20)

        self.gridLayout_2.addWidget(self.xTicksSpinBox, 1, 1, 1, 1)

        self.label_7 = QLabel(self.spectrogramStyleGroupBox)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_7, 2, 0, 1, 1)

        self.yTicksSpinBox = QSpinBox(self.spectrogramStyleGroupBox)
        self.yTicksSpinBox.setObjectName(u"yTicksSpinBox")
        self.yTicksSpinBox.setMinimum(1)
        self.yTicksSpinBox.setValue(20)

        self.gridLayout_2.addWidget(self.yTicksSpinBox, 2, 1, 1, 1)

        self.label_8 = QLabel(self.spectrogramStyleGroupBox)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_8, 3, 0, 1, 1)

        self.powerUnitLineEdit = QLineEdit(self.spectrogramStyleGroupBox)
        self.powerUnitLineEdit.setObjectName(u"powerUnitLineEdit")

        self.gridLayout_2.addWidget(self.powerUnitLineEdit, 3, 1, 1, 1)


        self.gridLayout_4.addWidget(self.spectrogramStyleGroupBox, 0, 1, 1, 1)

        self.spectrogramSettingsGroupBox = QGroupBox(self.plotSpectrogramsGroupBox)
        self.spectrogramSettingsGroupBox.setObjectName(u"spectrogramSettingsGroupBox")
        self.gridLayout_3 = QGridLayout(self.spectrogramSettingsGroupBox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.label = QLabel(self.spectrogramSettingsGroupBox)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_3.addWidget(self.label, 0, 0, 1, 1)

        self.sampleStepSpinBox = QSpinBox(self.spectrogramSettingsGroupBox)
        self.sampleStepSpinBox.setObjectName(u"sampleStepSpinBox")
        self.sampleStepSpinBox.setMinimum(1)
        self.sampleStepSpinBox.setMaximum(999999)

        self.gridLayout_3.addWidget(self.sampleStepSpinBox, 0, 1, 1, 1)

        self.label_9 = QLabel(self.spectrogramSettingsGroupBox)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_9, 1, 0, 1, 1)

        self.sampleStartSpinBox = QSpinBox(self.spectrogramSettingsGroupBox)
        self.sampleStartSpinBox.setObjectName(u"sampleStartSpinBox")
        self.sampleStartSpinBox.setMinimum(1)

        self.gridLayout_3.addWidget(self.sampleStartSpinBox, 1, 1, 1, 1)

        self.label_10 = QLabel(self.spectrogramSettingsGroupBox)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_10, 2, 0, 1, 1)

        self.sampleStopSpinBox = QSpinBox(self.spectrogramSettingsGroupBox)
        self.sampleStopSpinBox.setObjectName(u"sampleStopSpinBox")
        self.sampleStopSpinBox.setMinimum(2)

        self.gridLayout_3.addWidget(self.sampleStopSpinBox, 2, 1, 1, 1)


        self.gridLayout_4.addWidget(self.spectrogramSettingsGroupBox, 1, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.gridLayout_4.addItem(self.verticalSpacer, 2, 1, 1, 1)

        self.spectrogramButton = QPushButton(self.plotSpectrogramsGroupBox)
        self.spectrogramButton.setObjectName(u"spectrogramButton")

        self.gridLayout_4.addWidget(self.spectrogramButton, 3, 1, 1, 1)

        self.splitter.addWidget(self.plotSpectrogramsGroupBox)
        self.splitter_3.addWidget(self.splitter)
        self.peakTracingGroupBox = QGroupBox(self.splitter_3)
        self.peakTracingGroupBox.setObjectName(u"peakTracingGroupBox")
        sizePolicy2 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy2.setHorizontalStretch(4)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.peakTracingGroupBox.sizePolicy().hasHeightForWidth())
        self.peakTracingGroupBox.setSizePolicy(sizePolicy2)
        self.verticalLayout = QVBoxLayout(self.peakTracingGroupBox)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.peakTracingSettingGroupBox = QGroupBox(self.peakTracingGroupBox)
        self.peakTracingSettingGroupBox.setObjectName(u"peakTracingSettingGroupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.peakTracingSettingGroupBox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_11 = QLabel(self.peakTracingSettingGroupBox)
        self.label_11.setObjectName(u"label_11")

        self.horizontalLayout_2.addWidget(self.label_11)

        self.peakTracingOutputPathComboBox = QComboBox(self.peakTracingSettingGroupBox)
        self.peakTracingOutputPathComboBox.setObjectName(u"peakTracingOutputPathComboBox")
        self.peakTracingOutputPathComboBox.setEditable(True)

        self.horizontalLayout_2.addWidget(self.peakTracingOutputPathComboBox)

        self.peakTracingOutputPathPushButton = QPushButton(self.peakTracingSettingGroupBox)
        self.peakTracingOutputPathPushButton.setObjectName(u"peakTracingOutputPathPushButton")

        self.horizontalLayout_2.addWidget(self.peakTracingOutputPathPushButton)

        self.label_12 = QLabel(self.peakTracingSettingGroupBox)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.label_12)

        self.peakTracingStartSpinBox = QSpinBox(self.peakTracingSettingGroupBox)
        self.peakTracingStartSpinBox.setObjectName(u"peakTracingStartSpinBox")
        self.peakTracingStartSpinBox.setMinimum(1)
        self.peakTracingStartSpinBox.setMaximum(999999)

        self.horizontalLayout_2.addWidget(self.peakTracingStartSpinBox)

        self.label_13 = QLabel(self.peakTracingSettingGroupBox)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.label_13)

        self.peakTracingStopSpinBox = QSpinBox(self.peakTracingSettingGroupBox)
        self.peakTracingStopSpinBox.setObjectName(u"peakTracingStopSpinBox")
        self.peakTracingStopSpinBox.setMinimum(2)
        self.peakTracingStopSpinBox.setMaximum(999999)

        self.horizontalLayout_2.addWidget(self.peakTracingStopSpinBox)

        self.label_14 = QLabel(self.peakTracingSettingGroupBox)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.label_14)

        self.peakTracingStepSpinBox = QSpinBox(self.peakTracingSettingGroupBox)
        self.peakTracingStepSpinBox.setObjectName(u"peakTracingStepSpinBox")
        self.peakTracingStepSpinBox.setMinimum(1)
        self.peakTracingStepSpinBox.setMaximum(999999)

        self.horizontalLayout_2.addWidget(self.peakTracingStepSpinBox)


        self.verticalLayout.addWidget(self.peakTracingSettingGroupBox)

        self.gridLayout_5 = QGridLayout()
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.peakTrackingSelectAllButton = QPushButton(self.peakTracingGroupBox)
        self.peakTrackingSelectAllButton.setObjectName(u"peakTrackingSelectAllButton")

        self.gridLayout_5.addWidget(self.peakTrackingSelectAllButton, 0, 0, 1, 1)

        self.FSRERQButton = QPushButton(self.peakTracingGroupBox)
        self.FSRERQButton.setObjectName(u"FSRERQButton")

        self.gridLayout_5.addWidget(self.FSRERQButton, 0, 1, 2, 1)

        self.trackPeakButton = QPushButton(self.peakTracingGroupBox)
        self.trackPeakButton.setObjectName(u"trackPeakButton")

        self.gridLayout_5.addWidget(self.trackPeakButton, 0, 2, 1, 1)

        self.peakTrackingUnselectAllButton = QPushButton(self.peakTracingGroupBox)
        self.peakTrackingUnselectAllButton.setObjectName(u"peakTrackingUnselectAllButton")

        self.gridLayout_5.addWidget(self.peakTrackingUnselectAllButton, 1, 0, 1, 1)

        self.saveResultsButton = QPushButton(self.peakTracingGroupBox)
        self.saveResultsButton.setObjectName(u"saveResultsButton")
        self.saveResultsButton.setEnabled(False)

        self.gridLayout_5.addWidget(self.saveResultsButton, 1, 2, 1, 1)


        self.verticalLayout.addLayout(self.gridLayout_5)

        self.splitter_2 = QSplitter(self.peakTracingGroupBox)
        self.splitter_2.setObjectName(u"splitter_2")
        self.splitter_2.setOrientation(Qt.Vertical)
        self.peakTrackerPowerListWidget = QListWidget(self.splitter_2)
        self.peakTrackerPowerListWidget.setObjectName(u"peakTrackerPowerListWidget")
        sizePolicy3 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.peakTrackerPowerListWidget.sizePolicy().hasHeightForWidth())
        self.peakTrackerPowerListWidget.setSizePolicy(sizePolicy3)
        self.splitter_2.addWidget(self.peakTrackerPowerListWidget)
        self.peakTrackerWidget = QWidget(self.splitter_2)
        self.peakTrackerWidget.setObjectName(u"peakTrackerWidget")
        self.splitter_2.addWidget(self.peakTrackerWidget)

        self.verticalLayout.addWidget(self.splitter_2)

        self.splitter_3.addWidget(self.peakTracingGroupBox)

        self.horizontalLayout_5.addWidget(self.splitter_3)

        RaMainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(RaMainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1280, 42))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        RaMainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(RaMainWindow)
        self.statusbar.setObjectName(u"statusbar")
        RaMainWindow.setStatusBar(self.statusbar)
        self.logDockWidget = QDockWidget(RaMainWindow)
        self.logDockWidget.setObjectName(u"logDockWidget")
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.horizontalLayout = QHBoxLayout(self.dockWidgetContents)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.textBrowser = QTextBrowser(self.dockWidgetContents)
        self.textBrowser.setObjectName(u"textBrowser")
        font = QFont()
        font.setFamilies([u"Cascadia Mono"])
        self.textBrowser.setFont(font)

        self.horizontalLayout.addWidget(self.textBrowser)

        self.logDockWidget.setWidget(self.dockWidgetContents)
        RaMainWindow.addDockWidget(Qt.RightDockWidgetArea, self.logDockWidget)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menuFile.addAction(self.actionOpen)

        self.retranslateUi(RaMainWindow)
        self.actionOpen.triggered.connect(RaMainWindow.slot_open_clicked)
        self.treeView.clicked.connect(RaMainWindow.slot_file_changed)
        self.treeView.activated.connect(RaMainWindow.slot_file_changed)
        self.trackPeakButton.clicked.connect(RaMainWindow.slot_track_peak)
        self.saveResultsButton.clicked.connect(RaMainWindow.slot_save_results)
        self.peakTrackingSelectAllButton.clicked.connect(RaMainWindow.slot_peak_tracking_select_all)
        self.peakTrackingUnselectAllButton.clicked.connect(RaMainWindow.slot_peak_tracking_unselect_all)
        self.peakTracingOutputPathPushButton.clicked.connect(RaMainWindow.slot_peak_tracking_select_output_path)
        self.peakTracingStartSpinBox.valueChanged.connect(RaMainWindow.slot_peak_tracking_on_start_spinbox_change)
        self.peakTracingStopSpinBox.valueChanged.connect(RaMainWindow.slot_peak_tracking_on_stop_spinbox_change)
        self.FSRERQButton.clicked.connect(RaMainWindow.slot_fsr_er_q)
        self.spectrogramSelectAllButton.clicked.connect(RaMainWindow.slot_spectrogram_select_all)
        self.sampleStartSpinBox.valueChanged.connect(RaMainWindow.slot_spectrogram_on_start_spinbox_change)
        self.spectrogramUnselectAllButton.clicked.connect(RaMainWindow.slot_spectrogram_unselect_all)
        self.loadAnalyzerButton.clicked.connect(RaMainWindow.slot_load_analyzer)
        self.sampleStopSpinBox.valueChanged.connect(RaMainWindow.slot_spectrogram_on_stop_spinbox_change)
        self.spectrogramButton.clicked.connect(RaMainWindow.slot_plot_spectrogram)

        QMetaObject.connectSlotsByName(RaMainWindow)
    # setupUi

    def retranslateUi(self, RaMainWindow):
        RaMainWindow.setWindowTitle(QCoreApplication.translate("RaMainWindow", u"Retrospective Analysis", None))
        self.actionOpen.setText(QCoreApplication.translate("RaMainWindow", u"Open Folder", None))
#if QT_CONFIG(shortcut)
        self.actionOpen.setShortcut(QCoreApplication.translate("RaMainWindow", u"Ctrl+O", None))
#endif // QT_CONFIG(shortcut)
        self.thresholdSettingsGroupBox.setTitle(QCoreApplication.translate("RaMainWindow", u"Peak Finding/Fitting Settings", None))
        self.label_15.setText(QCoreApplication.translate("RaMainWindow", u"R2 Threshold:", None))
        self.label_16.setText(QCoreApplication.translate("RaMainWindow", u"-100 dBm Tolerance:", None))
        self.analyzerSettingsGroupBox.setTitle(QCoreApplication.translate("RaMainWindow", u"1. Analyzer Settings", None))
        self.label_2.setText(QCoreApplication.translate("RaMainWindow", u"Timestamp File/Number", None))
#if QT_CONFIG(tooltip)
        self.timeStampComboBox.setToolTip(QCoreApplication.translate("RaMainWindow", u"csv timestamp file or a fix interval number", None))
#endif // QT_CONFIG(tooltip)
        self.timeStampComboBox.setCurrentText(QCoreApplication.translate("RaMainWindow", u"0.25", None))
        self.label_3.setText(QCoreApplication.translate("RaMainWindow", u"Time Multiplier:", None))
#if QT_CONFIG(tooltip)
        self.timeMultiplierLineEdit.setToolTip(QCoreApplication.translate("RaMainWindow", u"1/60 if convert from second to minute", None))
#endif // QT_CONFIG(tooltip)
        self.timeMultiplierLineEdit.setText(QCoreApplication.translate("RaMainWindow", u"1/60", None))
#if QT_CONFIG(tooltip)
        self.timeUnitLineEdit.setToolTip(QCoreApplication.translate("RaMainWindow", u"unit after conversion", None))
#endif // QT_CONFIG(tooltip)
        self.timeUnitLineEdit.setText(QCoreApplication.translate("RaMainWindow", u"min", None))
        self.label_6.setText(QCoreApplication.translate("RaMainWindow", u"Data File Pattern ([RegEx](https://saasbase.dev/tools/regex-generator)):", None))
#if QT_CONFIG(tooltip)
        self.patternLineEdit.setToolTip(QCoreApplication.translate("RaMainWindow", u"regular expression for sweep number matching. (match the number in \"()\")", None))
#endif // QT_CONFIG(tooltip)
        self.patternLineEdit.setText(QCoreApplication.translate("RaMainWindow", u"r\".*sweep_(\\d+)\\.mat\"", None))
        self.loadAnalyzerButton.setText(QCoreApplication.translate("RaMainWindow", u"Load", None))
        self.plotSpectrogramsGroupBox.setTitle(QCoreApplication.translate("RaMainWindow", u"Optional. Plot Spectrograms", None))
        self.spectrogramSelectAllButton.setText(QCoreApplication.translate("RaMainWindow", u"Select All", None))
        self.spectrogramUnselectAllButton.setText(QCoreApplication.translate("RaMainWindow", u"Unselect All", None))
        self.spectrogramStyleGroupBox.setTitle(QCoreApplication.translate("RaMainWindow", u"Style", None))
        self.label_5.setText(QCoreApplication.translate("RaMainWindow", u"X Ticks:", None))
#if QT_CONFIG(tooltip)
        self.xTicksSpinBox.setToolTip(QCoreApplication.translate("RaMainWindow", u"number of ticks in x axis, cannot be smaller than file numbers", None))
#endif // QT_CONFIG(tooltip)
        self.label_7.setText(QCoreApplication.translate("RaMainWindow", u"Y Ticks:", None))
#if QT_CONFIG(tooltip)
        self.yTicksSpinBox.setToolTip(QCoreApplication.translate("RaMainWindow", u"number of tick in y axis", None))
#endif // QT_CONFIG(tooltip)
        self.label_8.setText(QCoreApplication.translate("RaMainWindow", u"Power Unit:", None))
#if QT_CONFIG(tooltip)
        self.powerUnitLineEdit.setToolTip(QCoreApplication.translate("RaMainWindow", u"the unit to display", None))
#endif // QT_CONFIG(tooltip)
        self.powerUnitLineEdit.setText(QCoreApplication.translate("RaMainWindow", u"dBm", None))
        self.spectrogramSettingsGroupBox.setTitle(QCoreApplication.translate("RaMainWindow", u"Settings", None))
        self.label.setText(QCoreApplication.translate("RaMainWindow", u"Step:", None))
#if QT_CONFIG(tooltip)
        self.sampleStepSpinBox.setToolTip(QCoreApplication.translate("RaMainWindow", u"sample once per [step] files", None))
#endif // QT_CONFIG(tooltip)
        self.label_9.setText(QCoreApplication.translate("RaMainWindow", u"Start:", None))
#if QT_CONFIG(tooltip)
        self.sampleStartSpinBox.setToolTip(QCoreApplication.translate("RaMainWindow", u"the start number (regardless of actual sweep number)", None))
#endif // QT_CONFIG(tooltip)
        self.label_10.setText(QCoreApplication.translate("RaMainWindow", u"Stop:", None))
#if QT_CONFIG(tooltip)
        self.sampleStopSpinBox.setToolTip(QCoreApplication.translate("RaMainWindow", u"the stop number (regardless of actual sweep number)", None))
#endif // QT_CONFIG(tooltip)
        self.spectrogramButton.setText(QCoreApplication.translate("RaMainWindow", u"Spectrogram", None))
        self.peakTracingGroupBox.setTitle(QCoreApplication.translate("RaMainWindow", u"2. Peak Tracing", None))
        self.peakTracingSettingGroupBox.setTitle(QCoreApplication.translate("RaMainWindow", u"Settings", None))
        self.label_11.setText(QCoreApplication.translate("RaMainWindow", u"Output Path:", None))
#if QT_CONFIG(tooltip)
        self.peakTracingOutputPathComboBox.setToolTip(QCoreApplication.translate("RaMainWindow", u"where the output .mat files should be saved", None))
#endif // QT_CONFIG(tooltip)
        self.peakTracingOutputPathPushButton.setText(QCoreApplication.translate("RaMainWindow", u"Select...", None))
        self.label_12.setText(QCoreApplication.translate("RaMainWindow", u"From:", None))
        self.label_13.setText(QCoreApplication.translate("RaMainWindow", u"to:", None))
        self.label_14.setText(QCoreApplication.translate("RaMainWindow", u"step:", None))
        self.peakTrackingSelectAllButton.setText(QCoreApplication.translate("RaMainWindow", u"Select All", None))
        self.FSRERQButton.setText(QCoreApplication.translate("RaMainWindow", u"FSR ER Q", None))
        self.trackPeakButton.setText(QCoreApplication.translate("RaMainWindow", u"Start Track", None))
        self.peakTrackingUnselectAllButton.setText(QCoreApplication.translate("RaMainWindow", u"Unselect All", None))
        self.saveResultsButton.setText(QCoreApplication.translate("RaMainWindow", u"Save Results", None))
        self.menuFile.setTitle(QCoreApplication.translate("RaMainWindow", u"File", None))
        self.logDockWidget.setWindowTitle(QCoreApplication.translate("RaMainWindow", u"Log", None))
    # retranslateUi

