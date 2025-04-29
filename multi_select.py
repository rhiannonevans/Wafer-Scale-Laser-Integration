import os
from tkinter import Tk, Toplevel, Label, Button, Checkbutton, IntVar, Frame
from tkinter.filedialog import askdirectory

# Prompts user to select parent folder, then brings up a multi-select menu where user selects subfolders to process. Returns a list of selected subfolder names.

def scrape_filenames():
    root = Tk()
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
            print(f"Checkbox for {name}: {var.get()}")
            if var.get():
                selected_names.append(name)
        print("Selected:", selected_names)
        selection_window.destroy()

    selection_window = Toplevel(root)
    selection_window.title("Select Subfolders")
    selection_window.geometry("400x600")  # Set the window size (width x height)

    # Center the window on the screen
    selection_window.update_idletasks()
    width = 400
    height = 600
    x = (selection_window.winfo_screenwidth() // 2) - (width // 2)
    y = (selection_window.winfo_screenheight() // 2) - (height // 2)
    selection_window.geometry(f"{width}x{height}+{x}+{y}")

    Label(selection_window, text="Select subfolders:").pack(anchor="w", padx=10, pady=5)

    vars = []
    for name in subfolder_names:
        var = IntVar()
        vars.append(var)
        cb = Checkbutton(selection_window, text=name, variable=var)
        cb.pack(anchor="w", padx=10)

    # Frame to hold buttons horizontally
    button_frame = Frame(selection_window)
    button_frame.pack(pady=10)

    Button(button_frame, text="Select All", command=select_all).pack(side="left", padx=5)
    Button(button_frame, text="Unselect All", command=unselect_all).pack(side="left", padx=5)
    Button(button_frame, text="Submit", command=on_submit).pack(side="left", padx=5)

    root.wait_window(selection_window)

    print("Returning:", selected_names)
    return selected_names

if __name__ == "__main__":
    scrape_filenames()
