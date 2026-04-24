import numpy as np
from pyqtgraph import PlotCurveItem
from PySide6.QtCore import Qt


class RaPlotCurveItem(PlotCurveItem):
    def __init__(self, fsr: float, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__fsr = fsr
        _, self.__y = self.getData()

    def mouseDragEvent(self, ev):
        if (
            ev.button() != Qt.MouseButton.LeftButton
            and ev.button() != Qt.MouseButton.RightButton
        ):
            ev.ignore()
            return

        if ev.isStart():
            _, y = self.getData()
            self.__drag_y_offsets = y - ev.buttonDownPos().y()
        elif ev.isFinish():
            return

        x, y = self.getData()
        if ev.button() == Qt.MouseButton.LeftButton:
            # left click, free drag
            self.updateData(x, ev.pos().y() + self.__drag_y_offsets)
        elif ev.button() == Qt.MouseButton.RightButton:
            # magnet effect, attach to the nearest fsr
            y_ideal = ev.pos().y() + self.__drag_y_offsets
            y_diff = y_ideal - self.__y
            y_diff = np.round(y_diff / self.__fsr) * self.__fsr
            y_final = self.__y + y_diff
            self.updateData(x, y_final)
        ev.accept()