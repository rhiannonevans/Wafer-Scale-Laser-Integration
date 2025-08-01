import tkinter as tk
import tkinter.filedialog as filedialog
from multi_LIV import multi_LIV
from multi_osa import multi_OSA
from multi_wlm  import multi_WLM
import multi_select

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Ask for the parent directory and select subfolders
    parent_dir = filedialog.askdirectory(title="Select Parent Directory for Data Processing")
    file_selection = multi_select.scrape_filenames(root, parent_dir)  # Open the selection GUI

    # Ask if the user wants to overwrite existing files
    overwrite_existing = tk.messagebox.askyesno("Overwrite Existing Files", "Do you want to overwrite existing files?")

    ## TODO: fix threshold box plot for wlm and liv - works but doesnt look right

    # Create instances of each multi_ class - will check file names and only run if 'liv', 'osa', or 'wlm' is in the file name 
    print("Processing WLM files...")
    multi_wlm = multi_WLM(parent_dir, selected_files=file_selection, overwrite_existing=overwrite_existing)
    print("Processing LIV files...")
    multi_liv = multi_LIV(parent_dir, selected_files=file_selection, overwrite_existing=overwrite_existing)
    print("Processing OSA files...")
    multi_osa = multi_OSA(parent_dir, selected_files=file_selection, overwrite_existing=overwrite_existing)


    root.destroy()