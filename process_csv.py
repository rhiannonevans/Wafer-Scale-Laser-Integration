import osa
import wlm
import os
from tkinter import Tk, simpledialog
from tkinter.filedialog import askdirectory, askopenfilename

# Define the size threshold for processing as OSA (50 KB)
SIZE_THRESHOLD = 50 * 1024

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
        # Compare normalized paths to avoid issues with trailing slashes
        if os.path.normpath(directory) == os.path.normpath(base_folder):
            # File is in the top-level folder; create a subfolder.
            output_folder = os.path.join(directory, base_name)
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            return output_folder
        else:
            # File is in a subfolder; save outputs directly in that subfolder.
            return directory
    else:
        # File mode: always create a new folder in the file's directory.
        output_folder = os.path.join(directory, base_name)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        return output_folder

def process_file(file_path, process_mode, base_folder=None):
    """
    Process a single CSV file according to process_mode:
      - "osa": Process only if the file qualifies as OSA.
      - "wlm": Process only if the file qualifies as WLM.
      - "both": Process according to the file's qualification.
    
    A file qualifies for OSA if its name (case-insensitive) contains "osa"
    or its size exceeds SIZE_THRESHOLD.
    
    Outputs are saved to an output folder determined by create_output_folder.
    """
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    osa_condition = "OSA" in file_name.lower() or file_size > SIZE_THRESHOLD
    output_folder = create_output_folder(file_path, base_folder)

    if process_mode == "osa":
        if osa_condition:
            print(f"Processing {file_path} as OSA")
            osa.sweep_osa(file_path, output_folder=output_folder)
        else:
            print(f"Skipping {file_path}: does not meet OSA criteria. Skipping...")
            
    elif process_mode == "liv":
        if not osa_condition:
            print(f"Processing {file_path} as LIV")
            wlm.process_other(file_path, output_folder=output_folder)
        else:
            print(f"Skipping {file_path}: qualifies as OSA, not LIV. Skipping...")
            
    elif process_mode == "both":
        if osa_condition:
            print(f"Processing {file_path} as OSA (both mode)")
            osa.sweep_osa(file_path, output_folder=output_folder)
        else:
            print(f"Processing {file_path} as LIV (both mode)")
            wlm.process_other(file_path, output_folder=output_folder)
    else:
        raise ValueError("Invalid processing mode specified.")

    print(f"Output for {file_path} saved in {output_folder}")

def main():
    # Initialize Tkinter and hide the root window.
    root = Tk()
    root.withdraw()

    try:
        # Ask whether to process a folder or a single file.
        selection_choice = simpledialog.askstring("Select Mode", 
                                        "Select mode:\n(1) Folder\n(2) File\nEnter 1 or 2:")
        if not selection_choice:
            print("No selection made. Exiting.")
            return
        
        if selection_choice.strip() == '1':
            # Folder selection mode.
            print("Folder selection mode")
            folder_path = askdirectory(title="Select a Folder Containing the CSV Files")
            if not folder_path:
                print("No folder selected. Exiting.")
                return
            
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
            elif processing_choice == '2':
                process_mode = "wlm"
            elif processing_choice == '3':
                process_mode = "both"
            else:
                print("Invalid processing mode selection. Exiting.")
                return

            print(f"Selected folder: {folder_path}")
            # Recursively process every CSV file in the folder and its subfolders.
            for current_root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith(".csv"):
                        file_path = os.path.join(current_root, file)
                        try:
                            process_file(file_path, process_mode, base_folder=folder_path)
                        except Exception as e:
                            # Print the full file name and a summary of the error, then continue.
                            print(f"Failed processing file: {file_path}\nReason: {str(e)}\n")
                        
        elif selection_choice.strip() == '2':
            # File selection mode.
            print("File selection mode")
            file_path = askopenfilename(title="Select a CSV File", filetypes=[("CSV Files", "*.csv")])
            if not file_path:
                print("No file selected. Exiting.")
                return
            print(f"Selected file: {file_path}")
            try:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                # Automatically choose processing based on file criteria.
                if "osa" in file_name.lower() or file_size > SIZE_THRESHOLD:
                    process_mode = "osa"
                else:
                    process_mode = "wlm"
                # For file mode, base_folder is left as None.
                process_file(file_path, process_mode, base_folder=None)
            except Exception as e:
                print(f"Failed processing file: {file_path}\nReason: {str(e)}")
            
        else:
            print("Invalid selection mode. Exiting.")
    finally:
        root.destroy()

if __name__ == '__main__':
    main()
