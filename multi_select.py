"""
    Import this script to create a GUI for selecting subfolders from a specified parent folder.

    [Author: Rhiannon H Evans]
    [Date: 2025-06-12]
"""


import os
import math
from tkinter import (
    Tk, Toplevel, Label, Button, Checkbutton, IntVar, Frame, Canvas, Scrollbar, VERTICAL, RIGHT, LEFT, BOTH, Y
)
from tkinter.filedialog import askdirectory

def scrape_filenames(root):
    root.withdraw()

    folder_path = askdirectory(title="Select a Folder Containing the CSV Files")
    if not folder_path:
        print("No folder selected. Exiting.")
        return

    subfolder_names = [name for name in os.listdir(folder_path)
                       if os.path.isdir(os.path.join(folder_path, name))]

    selected_names = []

    def select_all():
        for var in vars:
            var.set(1)

    def unselect_all():
        for var in vars:
            var.set(0)

    def on_submit():
        for name, var in zip(subfolder_names, vars):
            if var.get():
                selected_names.append(name)
        selection_window.destroy()

    selection_window = Toplevel(root)
    selection_window.title("Select Subfolders")
    width, height = 650, 500
    selection_window.geometry(f"{width}x{height}")
    x = (selection_window.winfo_screenwidth() // 2) - (width // 2)
    y = (selection_window.winfo_screenheight() // 2) - (height // 2)
    selection_window.geometry(f"{width}x{height}+{x}+{y}")

    Label(selection_window, text="Select subfolders:").pack(anchor="w", padx=10, pady=5)

    # Outer frame with canvas and scrollbar
    outer_frame = Frame(selection_window)
    outer_frame.pack(padx=10, pady=10, fill=BOTH, expand=True)

    canvas = Canvas(outer_frame)
    scrollbar = Scrollbar(outer_frame, orient=VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side=RIGHT, fill=Y)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)

    # Frame inside the canvas to hold checkboxes
    checkbox_frame = Frame(canvas)
    canvas.create_window((0, 0), window=checkbox_frame, anchor="nw")

    # Adjust column layout dynamically
    num_items = len(subfolder_names)
    max_rows = 20
    max_columns = 5
    num_columns = min(math.ceil(num_items / max_rows), max_columns)
    num_rows = math.ceil(num_items / num_columns)

    vars = []
    for index, name in enumerate(subfolder_names):
        var = IntVar()
        vars.append(var)
        row = index % num_rows
        col = index // num_rows
        cb = Checkbutton(checkbox_frame, text=name, variable=var)
        cb.grid(row=row, column=col, sticky="w", padx=5, pady=2)

    # Update scroll region after rendering
    def on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    checkbox_frame.bind("<Configure>", on_configure)

    # Buttons
    button_frame = Frame(selection_window)
    button_frame.pack(pady=10)

    Button(button_frame, text="Select All", command=select_all).pack(side="left", padx=5)
    Button(button_frame, text="Unselect All", command=unselect_all).pack(side="left", padx=5)
    Button(button_frame, text="Submit", command=on_submit).pack(side="left", padx=5)

    root.wait_window(selection_window)
    return selected_names, folder_path

if __name__ == "__main__":
    root = Tk()
    selections, parent_folder = scrape_filenames(root)
    print("User selected:", selections)
    print("Parent folder:", parent_folder)
