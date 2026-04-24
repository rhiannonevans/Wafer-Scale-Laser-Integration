import logging

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .ra_active_converter_window import RaActiveConverterWindow
from .ra_passive_analyzer_window import RaPassiveAnalyzerWindow
from .ra_passive_analyzer_window2 import RaPassiveAnalyzerWindow_new
from .ra_quick_analyzer_window import RaQuickAnalyzerWindow
from .ra_watcher_window import RaWatcherWindow

logger = logging.getLogger(__name__)


class RaStartWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__central_widget = self.RaStartupWindowCentralWidget()
        self.setCentralWidget(self.__central_widget)

        self.__status_bar = QStatusBar()
        self.setStatusBar(self.__status_bar)
        self.__status_bar.addWidget(QLabel("Retrospective Analysis - Start Page"))
        self.__status_bar.addPermanentWidget(QLabel("UBC Biosensor"))

        self.__central_widget.passive_button.clicked.connect(self.slot_passive_analyzer)
        self.__central_widget.passive_button_new.clicked.connect(
            self.slot_passive_analyzer_new
        )
        self.__central_widget.active_button.clicked.connect(self.slot_active_converter)
        self.__central_widget.passive_watch_mode_button.clicked.connect(
            self.slot_watch_mode
        )
        self.__central_widget.quick_analyzer_button.clicked.connect(
            self.slot_quick_analyzer
        )

    def slot_passive_analyzer(self):
        passive_analyzer_window = RaPassiveAnalyzerWindow()
        passive_analyzer_window.signal_close.connect(self.show)
        self.hide()
        passive_analyzer_window.show()

    def slot_passive_analyzer_new(self):
        passive_analyzer_window = RaPassiveAnalyzerWindow_new()
        passive_analyzer_window.signal_close.connect(self.show)
        self.hide()
        passive_analyzer_window.show()

    def slot_active_converter(self):
        dir = QFileDialog.getExistingDirectory()
        if dir:
            active_converter_dialog = RaActiveConverterWindow(dir)
            active_converter_dialog.signal_close.connect(self.show)
            self.hide()
            active_converter_dialog.show()

    def slot_watch_mode(self):
        watcher_window = RaWatcherWindow()
        watcher_window.signal_close.connect(self.show)
        self.hide()
        watcher_window.show()

    def slot_quick_analyzer(self):
        quick_analyzer_window = RaQuickAnalyzerWindow()
        quick_analyzer_window.signal_close.connect(self.show)
        self.hide()
        quick_analyzer_window.show()

    class RaStartupWindowCentralWidget(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setLayout(QVBoxLayout())

            passive_group_box = QGroupBox("Passive")
            active_group_box = QGroupBox("Active")

            # &[*] to make alt + * the shortcut for that button
            self.__passive_button = QPushButton("&Passive Analyzer - Archived September 2023")
            self.__passive_button_new = QPushButton("&Passive Analyzer")
            self.__active_button = QPushButton("Active &Converter")
            self.__passive_watch_mode_button = QPushButton("&Watch Mode")
            self.__quick_analyzer_button = QPushButton("&Quick Analyzer")
            self.__active_watch_mode_button = QPushButton("&Active Watch Mode")
            self.__active_watch_mode_button.setDisabled(True)

            passive_group_box.setLayout(QVBoxLayout())
            passive_group_box.layout().addWidget(self.__passive_button_new)
            passive_group_box.layout().addWidget(self.__passive_button)

            passive_watch_mode_widget = QWidget()
            passive_watch_mode_widget.setLayout(QHBoxLayout())
            passive_watch_mode_widget.layout().addWidget(
                self.__passive_watch_mode_button
            )
            passive_watch_mode_widget.layout().addWidget(self.__quick_analyzer_button)
            passive_group_box.layout().addWidget(passive_watch_mode_widget)

            active_group_box.setLayout(QVBoxLayout())
            active_group_box.layout().addWidget(self.__active_button)
            active_group_box.layout().addWidget(self.__active_watch_mode_button)

            self.layout().addWidget(passive_group_box)
            self.layout().addWidget(active_group_box)

        @property
        def passive_button(self):
            return self.__passive_button

        @property
        def passive_button_new(self):
            return self.__passive_button_new

        @property
        def active_button(self):
            return self.__active_button

        @property
        def passive_watch_mode_button(self):
            return self.__passive_watch_mode_button

        @property
        def quick_analyzer_button(self):
            return self.__quick_analyzer_button

        @property
        def active_watch_mode_button(self):
            return self.__active_watch_mode_button
