"""
    Main processing script for CSV files. Will detect file type based on naming conventions and process accordingly. 
    If a file has been processed previously, it will overwrite the previous outputs with the most up-to-date (including .mat file and all plots).
    User can select to process all files in a folder or a single file, and choose the processing mode (which file type(s) to process).
    Will create an output folder named after the file (without extension) in the same directory as the file. All outputs (.mat and plots)
    are saved in this folder.

    For details on processing, see the respective modules: `osa`, `liv`, and `wlm`.

    [Author: Rhiannon H Evans]
"""

import Obsolete.osa as osa
import Obsolete.liv as liv  
import Obsolete.wlm as wlm
import os
from tkinter import Tk, simpledialog
from tkinter.filedialog import askdirectory, askopenfilename

def create_output_folder(file_path, base_folder=None):
    """
    Determine the output folder for a processed file.
    - In folder mode (base_folder provided):
      * If the file is directly in the selected folder (i.e. its parent equals base_folder),
        create a new folder named after the file (without extension) in that folder.
      * If the file is in a subfolder of the selected folder, simply return the file's directory.
    - In file mode (base_folder is None):
      * Always create a new folder (named after the file) in its directory.
    """
    directory = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    if base_folder is not None:
        if os.path.normpath(directory) == os.path.normpath(base_folder):
            output_folder = os.path.join(directory, base_name)
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            return output_folder
        else:
            return directory
    else:
        output_folder = os.path.join(directory, base_name)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        return output_folder

def process_file(file_path, process_mode, base_folder=None):
    """
    Process a single CSV file according to process_mode:
      - "osa": Process only if the file qualifies as OSA.
      - "liv_wlm": Process only if the file qualifies as WLM or LIV.
      - "all": Processes all valid files, regardless of type.

    A file qualifies for OSA if its name (case-insensitive) contains "osa".
    Outputs are saved to an output folder determined by create_output_folder.
    """
    file_name = os.path.basename(file_path)
    osa_condition = "osa" in file_name.lower()
    liv_condition = "liv" in file_name.lower() 
    wlm_condition = "wlm" in file_name.lower()
    output_folder = create_output_folder(file_path, base_folder)

    if process_mode == "osa" and osa_condition:
        print(f"Processing {file_path} as OSA")
        osa.sweep_osa(file_path, output_folder)
    
    if process_mode == "liv" and liv_condition:
        print(f"Processing {file_path} as LIV")
        liv.process_liv(file_path, output_folder)
    if process_mode == "wlm" and wlm_condition:
        print(f"Processing {file_path} as WLM")
        wlm.process_wlm(file_path, output_folder)

    # if process_mode == "all":
    #     if osa_condition:
    #         print(f"Processing {file_path} as OSA (all mode)")
    #         osa.sweep_osa(file_path, output_folder)
    #     elif wlm_condition:
    #         print(f"Processing {file_path} as WLM (all mode)")
    #         wlm.process_wlm(file_path, output_folder)
    #     elif liv_condition:
    #         print(f"Processing {file_path} as LIV (all mode)")
    #         liv.process_liv(file_path)  # Uncomment to use LIV instead of WLM
    #     else:
    #         print(f"Skipping {file_path}: name must contain 'osa', 'liv', or 'wlm'. Skipping...")



    print(f"Output for {file_path} saved in {output_folder}")

def main():
    root = Tk()
    root.withdraw()

    try:
        selection_choice = simpledialog.askstring("Select Mode", 
                                    "Select mode:\n(1) Folder\n(2) File\nEnter 1 or 2:")
        if not selection_choice:
            print("No selection made. Exiting.")
            return

        if selection_choice.strip() == '1':
            print("Folder selection mode")
            folder_path = askdirectory(title="Select a Folder Containing the CSV Files")
            if not folder_path:
                print("No folder selected. Exiting.")
                return

            processing_choice = simpledialog.askstring("Processing Mode", 
                                        "Select processing mode for folder:\n"
                                        "(1) OSA files only\n"
                                        "(2) LIV files only\n"
                                        "(3) WLM files only\nEnter 1, 2, or 3:")
            if not processing_choice:
                print("No processing mode selected. Exiting.")
                return

            processing_choice = processing_choice.strip()
            if processing_choice == '1':
                process_mode = "osa"
            elif processing_choice == '2':
                process_mode = "liv"
            elif processing_choice == '3':
                process_mode = "wlm"
            else:
                print("Invalid processing mode selection. Exiting.")
                return

            print(f"Selected folder: {folder_path}")
            for current_root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith(".csv"):
                        file_path = os.path.join(current_root, file)
                        try:
                            process_file(file_path, process_mode, base_folder=folder_path)
                        except Exception as e:
                            print(f"Failed processing file: {file_path}\nReason: {str(e)}\n")

        elif selection_choice.strip() == '2':
            print("File selection mode")
            file_path = askopenfilename(title="Select a CSV File", filetypes=[("CSV Files", "*.csv")])
            if not file_path:
                print("No file selected. Exiting.")
                return
            print(f"Selected file: {file_path}")
            try:
                process_file(file_path, process_mode='all', base_folder=None)
            except Exception as e:
                print(f"Failed processing file: {file_path}\nReason: {str(e)}")

        else:
            print("Invalid selection mode. Exiting.")
    finally:
        root.destroy()

if __name__ == '__main__':
    main()
