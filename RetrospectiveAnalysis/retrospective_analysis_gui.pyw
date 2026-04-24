import argparse
import logging
import os
import sys
import time

import darkdetect
import pyqtgraph as pg
from PySide6.QtGui import qt_set_sequence_auto_mnemonic
from PySide6.QtWidgets import QApplication

from src.window.ra_start_window import RaStartWindow

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--theme",
        nargs="?",
        required=False,
        choices=["light", "dark", "auto"],
        default="auto",
        help="set the theme of pyqtgraph plotting widgets",
    )
    match parser.parse_args().theme:
        case "light":
            pg.setConfigOption("background", "w")
            pg.setConfigOption("foreground", "k")
        case "dark":
            pass
        case "auto":
            if darkdetect.isLight():
                pg.setConfigOption("background", "w")
                pg.setConfigOption("foreground", "k")
        case _:
            pass

    logging.basicConfig(
        level=logging.INFO,
        format="{levelname:^7s}::{asctime}::{name}::{message}",
        style="{",
        datefmt="%H:%M:%S",
        force=True,
    )

    log_folder_name = ".log"
    os.makedirs(f"{log_folder_name}", exist_ok=True)
    t = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    file_handler = logging.FileHandler(os.path.join(log_folder_name, f"{t}.log"))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("{asctime}::{name}::{levelname:^7s}::{message}", style="{")
    )
    logging.getLogger().addHandler(file_handler)

    app = QApplication(sys.argv)

    qt_set_sequence_auto_mnemonic(True)

    startup_window = RaStartWindow()
    startup_window.show()

    sys.exit(app.exec())
