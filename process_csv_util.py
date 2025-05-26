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
    osa_condition = "osa" in file_name.lower() or file_size > SIZE_THRESHOLD
    output_folder = create_output_folder(file_path, base_folder)

    if process_mode == "osa":
        if osa_condition:
            print(f"Processing {file_path} with OSA")
            osa.sweep_osa(file_path, output_folder=output_folder)
        else:
            print(f"Skipping {file_path}: does not meet OSA criteria.")
            
    elif process_mode == "liv":
        if not osa_condition:
            print(f"Processing {file_path} with WLM")
            wlm.process_other(file_path, output_folder=output_folder)
        else:
            print(f"Skipping {file_path}: qualifies as OSA, not WLM.")
            
    elif process_mode == "both":
        if osa_condition:
            print(f"Processing {file_path} with OSA (both mode)")
            osa.sweep_osa(file_path, output_folder=output_folder)
        else:
            print(f"Processing {file_path} with WLM (both mode)")
            wlm.process_other(file_path, output_folder=output_folder)
    else:
        raise ValueError("Invalid processing mode specified.")

    print(f"Output for {file_path} saved in {output_folder}")