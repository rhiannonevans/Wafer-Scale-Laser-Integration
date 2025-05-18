import process_csv
import os
from tkinter import Tk, simpledialog
from tkinter.filedialog import askdirectory, askopenfilename
import multi_select
import process_csv
import extract
import multi_osa
import multi_wlm
import multi_LIV


def main():
    # Initialize Tkinter and hide the root window.
    root = Tk()
    root.withdraw()
    processALL = True #True to process from csv, False to process from mat files

    try:
        # Ask whether to process a folder or a single file.
        selection_choice = simpledialog.askstring("Select Mode", 
                                        "Select mode:\n(1) Sweep entire Parent Folder\n(2) Select from Parent Folder \nEnter 1 or 2:")
        if not selection_choice:
            print("No selection made. Exiting.")
            return
        
        

        if selection_choice.strip() == '2':
            # User has opted to select files from parent folder

            print("Select Parent folder...")
            files_to_run, parent_path = multi_select.scrape_filenames(root)
            print(f"Chosen Files: {files_to_run} \n Parent folder: {parent_path}")
        else:
            # User has opted to sweep entire Parent folder
            parent_path = askdirectory(title="Select a Parent Folder")
            files = []
            if not parent_path:
                print("No folder selected. Exiting.")
                return
            print(f"Sweeping Parent Folder at {parent_path}")

        # Ask for processing type.
        processing_choice = simpledialog.askstring("Processing Mode", 
                                    "Select processing mode for folder:\n"
                                    "(1) OSA files only\n"
                                    "(2) LIV files only\n"
                                    "(3) All\nEnter 1, 2, or 3:")
        if not processing_choice:
            print("No processing mode selected. Exiting.")
            return
        
        processing_choice = processing_choice.strip()
        if processing_choice == '1':
            process_mode = "osa"
            print("Processing OSA...")
        elif processing_choice == '2':
            process_mode = "liv"
            print("Processing LIV...")
        elif processing_choice == '3':
            process_mode = "both"
            print("Processing all...")
        else:
            print("Invalid processing mode selection. Exiting.")
            return
        
        if selection_choice == '1':
            files_to_run = []
        
        if processALL:
            for current_root, dirs, files in os.walk(parent_path):
                for file in files:
                    if file.endswith(".csv"):
                        file_path = os.path.join(current_root, file)
                        file_base_name = os.path.splitext(file)[0]
                        if selection_choice == '1':
                            files_to_run.append(file_base_name)

                        if selection_choice == '2' and file_base_name not in files_to_run:
                            print(f"Skipping file (unselected):  {file_base_name}")
                        else:
                            try:
                                process_csv.process_file(file_path, process_mode, base_folder=parent_path)
                            except Exception as e:
                                # Print the full file name and a summary of the error, then continue.
                                print(f"Failed processing file: {file_path}\nReason: {str(e)}\n")
        else:
            for current_root, dirs, files in os.walk(parent_path):
                for file in files:
                    if file.endswith(".csv"):
                        file_path = os.path.join(current_root, file)
                        file_base_name = os.path.splitext(file)[0]
                        if selection_choice == '1':
                            files_to_run.append(file_base_name)

        # Ask the user if they would like to compare the files.
        compare_choice = simpledialog.askstring("Compare Files", 
                        "Would you like to compare the processed files? (y/n):")
        if compare_choice and compare_choice.strip().lower() == 'y':
            try:
                dataD = extract.iterate_files(parent_path, selection_choice, files_to_run)
                print(dataD)
                print(dataD['osa'])
                if process_mode == 'osa':
                    print("Plotting current power comparison...")
                    multi_osa.plot_scatter2(dataD["osa"]["peak_power_I"], dataD["osa"]["peak_power"], "Peak Power Current (mA)", "Peak Power (mW)", "Peak Power by Current Comparison", "peak_power_current_comparison", parent_path)
                    print("Plotting wl power comparison...")
                    multi_osa.plot_scatter2(dataD['osa']["peak_power_wl"], dataD["osa"]["peak_power"], "Peak Power Wavelength (nm)", "Peak Power (mW)", "Peak Power by Current Comparison", "peak_power_wl_comparison", parent_path) 
                else:
                    print("Plotting only for OSA currently")                
            except Exception as e:
                print(f"Failed to compare files.\nReason: {str(e)}\n")
    finally:
        root.destroy()

if __name__ == '__main__':
    main()