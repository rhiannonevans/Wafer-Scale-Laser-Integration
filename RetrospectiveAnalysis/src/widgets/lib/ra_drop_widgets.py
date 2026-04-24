from PySide6.QtWidgets import QLineEdit, QPushButton

from .ra_accept_drop_decorator import accept_drop


@accept_drop(on_file=True)
class RaDropPushButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)


@accept_drop(on_file=True)
class RaDropLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
