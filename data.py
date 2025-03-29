import osa
import wlm
import os
from tkinter import Tk, simpledialog
from tkinter.filedialog import askdirectory, askopenfilename

# Define the size threshold for processing as OSA (50 KB)
SIZE_THRESHOLD = 50 * 1024

def create_output_folder(file_path):
    """
    Create an output folder in the same directory as the original file.
    The folder is named after the original file (without extension).
    """
    directory = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_folder = os.path.join(directory, base_name)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    return output_folder

def process_file(file_path, process_mode):
    """
    Process a single CSV file based on the process_mode:
      - "osa": process only files that qualify as OSA
      - "wlm": process only files that qualify as WLM
      - "both": process each file according to its qualification

    A file qualifies for OSA processing if its name (case-insensitive)
    contains "osa" or if its size exceeds SIZE_THRESHOLD.
    
    Any output is saved in a new folder (created by create_output_folder)
    located in the same folder as the original file.
    """
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    # Determine if file qualifies for OSA processing
    osa_condition = "osa" in file_name.lower() or file_size > SIZE_THRESHOLD
    output_folder = create_output_folder(file_path)
    processed = False

    if process_mode == "osa":
        if osa_condition:
            print(f"Processing {file_path} with OSA")
            osa.sweep_osa(file_path, output_folder=output_folder)
            processed = True
        else:
            print(f"Skipping {file_path}: does not meet OSA criteria.")
            
    elif process_mode == "wlm":
        if not osa_condition:
            print(f"Processing {file_path} with WLM")
            wlm.process_other(file_path, True, output_folder=output_folder)
            processed = True
        else:
            print(f"Skipping {file_path}: qualifies as OSA, not WLM.")
            
    elif process_mode == "both":
        if osa_condition:
            print(f"Processing {file_path} with OSA (both mode)")
            osa.sweep_osa(file_path, output_folder=output_folder)
        else:
            print(f"Processing {file_path} with WLM (both mode)")
            wlm.process_other(file_path, True, output_folder=output_folder)
        processed = True
    else:
        print("Invalid process mode specified.")
    
    if processed:
        print(f"Output for {file_path} saved in {output_folder}")

def main():
    # Initialize Tkinter and hide the main window
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
            # Folder selection mode
            print("Folder selection mode")
            folder_path = askdirectory(title="Select a Folder Containing the CSV Files")
            if not folder_path:
                print("No folder selected. Exiting.")
                return
            
            # Prompt the user for which type(s) of files to process
            processing_choice = simpledialog.askstring("Processing Mode", 
                                        "Select processing mode for folder:\n"
                                        "(1) OSA files only\n"
                                        "(2) WLM files only\n"
                                        "(3) Both\nEnter 1, 2, or 3:")
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
            # Process each CSV file in the selected folder
            for file_name in os.listdir(folder_path):
                if file_name.endswith(".csv"):
                    file_path = os.path.join(folder_path, file_name)
                    process_file(file_path, process_mode)
                    
        elif selection_choice.strip() == '2':
            # File selection mode
            print("File selection mode")
            file_path = askopenfilename(title="Select a CSV File", filetypes=[("CSV Files", "*.csv")])
            if not file_path:
                print("No file selected. Exiting.")
                return
            print(f"Selected file: {file_path}")
            # Automatically decide processing based on file criteria
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            if "osa" in file_name.lower() or file_size > SIZE_THRESHOLD:
                process_mode = "osa"
            else:
                process_mode = "wlm"
            process_file(file_path, process_mode)
            
        else:
            print("Invalid selection mode. Exiting.")
    finally:
        root.destroy()

if __name__ == '__main__':
    main()
