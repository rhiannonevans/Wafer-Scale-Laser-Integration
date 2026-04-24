import logging
import os

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

from src.core.passive_tools import PassiveAnalyzer

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    channels = {0, 1, 2, 3, 4, 5}
    analyzer = PassiveAnalyzer(os.path.expanduser("~/path/to/folder"), 0.25)

    # Plot spectrogram

    step = 1
    data = analyzer.get_spectrograms(channels, step)
    x_labels = np.vectorize(lambda x: "{:.2f}".format(x))(analyzer.timestamps[::step])
    y_labels = np.vectorize(lambda x: "{:.2f}".format(x))(analyzer.wavelengths[::-1])
    x_formatter = FuncFormatter(lambda x, _: x_labels[int(x)])
    y_formatter = FuncFormatter(lambda y, _: y_labels[int(y)])
    for c in channels:
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.imshow(data[c], cmap="inferno")
        tick_step = 50
        ax.set_xticks(list(range(len(x_labels)))[::tick_step], x_labels[::tick_step])
        ax.set_yticks(list(range(len(y_labels)))[::tick_step], y_labels[::tick_step])
        ax.xaxis.set_major_formatter(x_formatter)
        ax.yaxis.set_major_formatter(y_formatter)
        fig.tight_layout()
    plt.show()

    # Plot traces

    all_traces, all_peaks = analyzer.analyze(channels, (0, None, 1), 0.5, 30)
    for c in channels:
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_title(f"Power{c+1}")

        ys = [x for x in all_traces[c][0]]

        for y in ys:
            ax.plot(y)

    plt.show()
