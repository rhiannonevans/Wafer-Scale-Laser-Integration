# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ra_peak_tracker_tab_setting_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.5.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QGroupBox, QHBoxLayout,
    QPushButton, QSizePolicy, QSplitter, QWidget)

class Ui_PeakTrackerTabSettingWidget(object):
    def setupUi(self, PeakTrackerTabSettingWidget):
        if not PeakTrackerTabSettingWidget.objectName():
            PeakTrackerTabSettingWidget.setObjectName(u"PeakTrackerTabSettingWidget")
        PeakTrackerTabSettingWidget.resize(1018, 127)
        self.horizontalLayout_2 = QHBoxLayout(PeakTrackerTabSettingWidget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.splitter = QSplitter(PeakTrackerTabSettingWidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Vertical)
        self.groupBox = QGroupBox(self.splitter)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout = QHBoxLayout(self.groupBox)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.autoSaveCheckBox = QCheckBox(self.groupBox)
        self.autoSaveCheckBox.setObjectName(u"autoSaveCheckBox")

        self.horizontalLayout.addWidget(self.autoSaveCheckBox)

        self.plotOffsetSpectrogramButton = QPushButton(self.groupBox)
        self.plotOffsetSpectrogramButton.setObjectName(u"plotOffsetSpectrogramButton")

        self.horizontalLayout.addWidget(self.plotOffsetSpectrogramButton)

        self.plotPeakOffsetButton = QPushButton(self.groupBox)
        self.plotPeakOffsetButton.setObjectName(u"plotPeakOffsetButton")

        self.horizontalLayout.addWidget(self.plotPeakOffsetButton)

        self.plotOverlayButton = QPushButton(self.groupBox)
        self.plotOverlayButton.setObjectName(u"plotOverlayButton")

        self.horizontalLayout.addWidget(self.plotOverlayButton)

        self.splitter.addWidget(self.groupBox)

        self.horizontalLayout_2.addWidget(self.splitter)


        self.retranslateUi(PeakTrackerTabSettingWidget)

        QMetaObject.connectSlotsByName(PeakTrackerTabSettingWidget)
    # setupUi

    def retranslateUi(self, PeakTrackerTabSettingWidget):
        PeakTrackerTabSettingWidget.setWindowTitle(QCoreApplication.translate("PeakTrackerTabSettingWidget", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("PeakTrackerTabSettingWidget", u"Plot", None))
        self.autoSaveCheckBox.setText(QCoreApplication.translate("PeakTrackerTabSettingWidget", u"Auto-Save", None))
        self.plotOffsetSpectrogramButton.setText(QCoreApplication.translate("PeakTrackerTabSettingWidget", u"Offset+Spectrogram", None))
        self.plotPeakOffsetButton.setText(QCoreApplication.translate("PeakTrackerTabSettingWidget", u"Peak Offset", None))
        self.plotOverlayButton.setText(QCoreApplication.translate("PeakTrackerTabSettingWidget", u"Overlay", None))
    # retranslateUi

