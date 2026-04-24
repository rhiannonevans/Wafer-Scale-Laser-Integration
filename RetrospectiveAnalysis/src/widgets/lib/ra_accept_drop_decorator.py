from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent


def accept_drop(cls=None, on_file: bool = False):
    """# decorator to make any QWidget subclass accept drops

    * need to enable setAcceptDrops(True).

    * signal_drop(str) will be emitted when a drop is accepted
    """

    def wrap(cls):
        cls.signal_drop = Signal(str)

        def dragEnterEvent(self, event: QDragEnterEvent):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            else:
                super(cls, self).dragEnterEvent(event)

        def dragMoveEvent(self, event: QDragMoveEvent):
            super(cls, self).dragMoveEvent(event)

        def dropEvent(self, event: QDropEvent):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    if on_file and url.isLocalFile():
                        self.signal_drop.emit(url.toLocalFile())
                event.acceptProposedAction()
            else:
                super(cls, self).dropEvent(event)

        cls.dragEnterEvent = dragEnterEvent
        cls.dragMoveEvent = dragMoveEvent
        cls.dropEvent = dropEvent
        return cls

    return wrap if cls is None else wrap(cls)
