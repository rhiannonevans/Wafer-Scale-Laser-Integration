import numpy as np
from numpy.typing import NDArray
from pyqtgraph import PlotCurveItem, PlotWidget, ScatterPlotItem
from PySide6.QtWidgets import QHBoxLayout, QWidget
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score


class RaActiveConverterFSRTabWidget(QWidget):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setLayout(QHBoxLayout())

        self.__left_plot_widget = PlotWidget()
        self.__right_plot_widget = PlotWidget()

        self.layout().addWidget(self.__left_plot_widget)
        self.layout().addWidget(self.__right_plot_widget)

    def clear(self):
        self.__left_plot_widget.clear()
        self.__left_plot_widget.clear()

    def set_scatter_plot(
        self,
        x: NDArray,
        y: NDArray,
        fit: bool,
        order: int,
        outlier_range: float,
    ):
        self.__left_plot_widget.clear()
        self.__left_plot_widget.getPlotItem().addLegend()  # type: ignore
        if not fit:
            self.__left_plot_widget.getPlotItem().addItem(ScatterPlotItem(x, y, name="scatter plot"))  # type: ignore
        else:  # fitting enabled
            indices = np.argsort(x)
            x = x[indices]
            y = y[indices]

            def polynomial(x, *coefficients):
                return sum([c * x**i for i, c in enumerate(coefficients)])

            coefficients, _ = curve_fit(
                polynomial, x, y, p0=[0 for _ in range(order + 1)]
            )

            fit_curve: NDArray = polynomial(x, *coefficients)  # type: ignore

            indices_in_range = [
                i for i, x in enumerate(y) if abs(x - fit_curve[i]) < outlier_range
            ]

            indices_outliers = [i for i in range(len(x)) if i not in indices_in_range]

            self.__left_plot_widget.getPlotItem().addItem(ScatterPlotItem(x[indices_outliers], y[indices_outliers], name="outliers", symbol="o", brush=None))  # type: ignore
            self.__left_plot_widget.getPlotItem().addItem(ScatterPlotItem(x[indices_in_range], y[indices_in_range], name="scatter plot"))  # type: ignore

            try:
                r2 = r2_score(y[indices_in_range], fit_curve[indices_in_range])
            except Exception:
                r2 = np.nan

            std = np.std(y[indices_in_range])

            fit_string = (
                "+".join([f"{c:.4g}*x^{i:.4g}" for i, c in enumerate(coefficients)])
                + f" | R2: {r2:.4g}"
                + f" | std: {std:.4g}"
            )
            curve_item = PlotCurveItem(
                x, fit_curve, pen="r", name=f"polynomial fit: {fit_string}"
            )
            self.__left_plot_widget.getPlotItem().addItem(curve_item)  # type: ignore
            self.__left_plot_widget.getPlotItem().getAxis("bottom").setScale(1e-9)  # type: ignore
            self.__left_plot_widget.getPlotItem().getAxis("bottom").setLabel(text="Peak Wavelength", units="m")  # type: ignore
            self.__left_plot_widget.getPlotItem().getAxis("left").setScale(1e-9)  # type: ignore
            self.__left_plot_widget.getPlotItem().getAxis("left").setLabel(text="FSR", units="m")  # type: ignore
            self.__left_plot_widget.getPlotItem().setTitle("FSR vs. Peak Wavelength")  # type: ignore

    def set_stream_plot(self, y: NDArray):
        self.__right_plot_widget.clear()
        self.__right_plot_widget.getPlotItem().plot(y)  # type: ignore
        self.__right_plot_widget.getPlotItem().setTitle("Equalized Data Stream")  # type: ignore
        self.__right_plot_widget.getPlotItem().getAxis("bottom").setLabel(text="#Sample Point")  # type: ignore
        self.__right_plot_widget.getPlotItem().getAxis("left").setLabel(text="Power")  # type: ignore
