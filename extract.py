import osa
import wlm
import os
from tkinter import Tk, simpledialog
from tkinter.filedialog import askdirectory, askopenfilename
import numpy as np
import matplotlib.pyplot as plt
import multi_select

"""
    Central script for extracting data from .mat files and plotting results. This is intended to be used with files 
    produced by the most recent version of process_csv.py. It is IMPERATIVE that the .mat files are produced by the 
    most recent version of process_csv.py, otherwise this script will fail. This is because the data collection method 
    looks for specific variable names in the .mat files, which may differ between versions.

    Creates and updates a dictionary with the data of intrest (items to extract and use in comparison plots).

    If run directly, compiles and plots the extracted data from the .mat files in a user-selected folder (and its subfolders).
"""

def extract_liv(mat_file_path):
    print("LIV Extraction")
    vars = ['peak_power', 'peak_power_I', 'threshold_currents']
    data = read_mat_file(mat_file_path, vars)
    return data

def extract_osa(mat_file_path):
    print("OSA Extraction")
    vars = ['peak_power', 'peak_power_I', 'peak_power_wl', 'peak_power_temp']
    data = read_mat_file(mat_file_path, vars)
    print(data)
    return data

def extract_wlm(mat_file_path):
    print("WLM Extraction")
    vars = ['peak_power', 'peak_power_I', 'threshold_currents', 'peak_power_WL', 'peak_power_V']
    data = read_mat_file(mat_file_path, vars)
    print(data)
    return data


def read_mat_file(mat_file_path, variables):
    """
    Given a .mat file name and a list of variables to extract, this function reads the .mat file and returns a dictionary of the extracted variables.
    
    Parameters:
    - mat_file_path: str, path to the .mat file
    - variables: list of str, names of the variables to extract from the .mat file
    
    Returns:
    - data_dict: dict, dictionary containing the extracted variables
    """
    import scipy.io as sio

    # Load the .mat file
    mat_data = sio.loadmat(mat_file_path)

    # Extract specified variables
    data_dict = {var: mat_data[var] for var in variables if var in mat_data}

    return data_dict

def plot_osa(data_dict, folder_path):
    # Plotting function for OSA data.

    data = data_dict.get('osa', {})
    print(data)

    # Extract data for plotting
    peak_power = data.get('peak_power', [])
    peak_power_I = data.get('peak_power_I', [])
    #threshold_current = data.get('threshold_current', [])
    peak_power_wl = data.get('peak_power_wl', [])
    peak_power_temp = data.get('peak_power_temp', [])

    print(f"Peak Power: {peak_power}")
    print(f"Peak Power I: {peak_power_I}")
    #print(f"Threshold Current: {threshold_current}")
    print(f"Peak Power Wavelength: {peak_power_wl}")
    print(f"Peak Power Temp: {peak_power_temp}")

    # Create plots
    plt.figure(figsize=(10, 6))
    
    plt.subplot(1, 2, 1)
    plt.scatter(peak_power_I, peak_power, label='Peak Power by Assoc Current')
    plt.title('Peak Power - Assoc Current')
    plt.xlabel('Current (A)')
    plt.ylabel('Peak Power (mW)')

    print("Plot 1 successful - peak power vs current")
    
    plt.subplot(1, 2, 2)
    plt.scatter(peak_power_wl, peak_power, label='Peak Power by Assoc Wavelength')
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Peak Power (mW)')
    plt.title('Peak Power - Assoc Wavelength')
    
    print("Plot 2 successful - peak power vs wl")
    # Save the plot to the specified folder
    plot_path = os.path.join(folder_path, '_osa_plots.png')
    plt.savefig(plot_path)
    print(f"Plots saved to {plot_path}")
    plt.close()  # Close the plot to avoid displaying it again

def plot_wlm(data_dict, folder_path):
    # Plotting function for WLM data.

    data = data_dict.get('wlm', {})
    print(data)

    # Extract data for plotting
    peak_power = data.get('peak_power', [])
    peak_power_I = data.get('peak_power_I', [])
    threshold_current = data.get('threshold_current', [])
    peak_power_WL = data.get('peak_power_WL', [])
    peak_power_V = data.get('peak_power_V', [])

    print(f"Peak Power: {peak_power}")
    print(f"Peak Power I: {peak_power_I}")
    print(f"Threshold Current: {threshold_current}")
    print(f"Peak Power Wavelength: {peak_power_WL}")
    print(f"Peak Power Voltage: {peak_power_V}")

    # Create plots
    plt.figure(figsize=(10, 6))
    
    plt.subplot(2, 2, 1)
    plt.scatter(peak_power_I, peak_power, label='Peak Power by Assoc Current')
    plt.title('Peak Power - Assoc Current')
    plt.xlabel('Current (A)')
    plt.ylabel('Peak Power (mW)')

    print("Plot 1 successful - peak power vs current")
    
    plt.subplot(2, 2, 2)
    plt.scatter(peak_power_V, peak_power, label='Peak Power by Assoc Wavelength')
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Peak Power (mW)')
    plt.title('Peak Power - Assoc Wavelength')
    
    print("Plot 2 successful - peak power vs wl")

    plt.subplot(2, 2, 3)
    plt.scatter(threshold_current, peak_power, label='Peak Power by Thresh Current')
    plt.xlabel('Current (mA)')
    plt.ylabel('Peak Power (mW)')
    plt.title('Peak Power - Thresh Current')
    
    print("Plot 3 successful - thresh current vs peak power")

  
    #plt.show()
    # Save the plot to the specified folder
    plot_path = os.path.join(folder_path, '_wlm_plots.png')
    plt.savefig(plot_path)
    plt.close()  # Close the plot to avoid displaying it again
    print(f"Plots saved to {plot_path}")

def plot_liv(data_dict, folder_path):
    # Plotting function for liv data.

    data = data_dict.get('liv', {})
    print(data)

    # Extract data for plotting
    peak_power = data.get('peak_power', [])
    peak_power_I = data.get('peak_power_I', [])
    threshold_currents = data.get('threshold_currents', [])

    print(f"Peak Power: {peak_power}")
    print(f"Peak Power I: {peak_power_I}")
    print(f"Threshold Currents: {threshold_currents}")

    # Create plots
    plt.figure(figsize=(10, 6))
    
    plt.subplot(1, 2, 1)
    plt.scatter(peak_power_I, peak_power, label='Peak Power by Assoc Current')
    plt.title('Peak Power - Assoc Current')
    plt.xlabel('Current (A)')
    plt.ylabel('Peak Power (mW)')

    print("Plot 1 successful - peak power vs current")
    
    # plt.subplot(1, 2, 2)
    # plt.scatter(threshold_current, peak_power, label='Peak Power by Assoc Threshold Current')
    # plt.xlabel('Threshold Current (A)')
    # plt.ylabel('Peak Power (mW)')
    # plt.title('Peak Power - Assoc Threshold Current')
    
    # print("Plot 2 successful - peak power vs threshold current")

      # Save the plot to the specified folder
    plot_path = os.path.join(folder_path, '_liv_plots.png')
    plt.savefig(plot_path)
    print(f"Plots saved to {plot_path}")


def setup_compdictionaries():
    # Initialize dictionaries to hold the comparison data.
    comp_dict = {
        "osa": {
            "IDtag": [],
            "peak_power": [],
            "peak_power_wl": [],
            "peak_power_I": [],
            "peak_power_temp": [],
        },
        "wlm": {
            "IDtag": [],
            "threshold_ch1": [],
            "peak_power": [],
            "peak_power_I": [],
            "peak_power_WL": [],
            "peak_power_V": [],
        },
        "liv": {
            "IDtag": [],
            "threshold_ch1": [],
            "peak_power": [],
            "peak_power_I": [],
        }
    }
    return comp_dict

def update_osa_dict(comp_dict, data, file_path=None):
    # Update the OSA dictionary with data from the .mat file.
    peak_sweep = data.get('peak_sweep', None)

    if 'peak_power' in data:
        arr = data['peak_power']
        try:
            val = arr[peak_sweep].flatten()[0] if peak_sweep is not None else np.max(arr)
            comp_dict["osa"]["peak_power"].append(float(val))
            print("Saved peak power")
        except Exception as e:
            print(f"Error saving peak power: {e}")
            comp_dict["osa"]["peak_power"].append(None)

    if 'peak_power_I' in data:
        try:
            arr = data['peak_power_I'].flatten()
            val = arr[peak_sweep] if peak_sweep is not None else np.max(arr)
            comp_dict["osa"]["peak_power_I"].append(float(val))
            print("Saved peak power current")
        except Exception as e:
            print(f"Error saving peak power current: {e}")
            comp_dict["osa"]["peak_power_I"].append(None)

    if 'peak_power_wl' in data:
        try:
            arr = data['peak_power_wl'].flatten()
            val = arr[peak_sweep] if peak_sweep is not None else np.max(arr)
            comp_dict["osa"]["peak_power_wl"].append(float(val))
            print("Saved peak power wl")
        except Exception as e:
            print(f"Error saving peak power wl: {e}")
            comp_dict["osa"]["peak_power_wl"].append(None)

    if 'peak_power_temp' in data:
        try:
            arr = data['peak_power_temp'].flatten()
            val = arr[peak_sweep] if peak_sweep is not None else np.max(arr)
            comp_dict["osa"]["peak_power_temp"].append(float(val))
            print("Saved peak power temp")
        except Exception as e:
            print(f"Error saving peak power temp: {e}")
            comp_dict["osa"]["peak_power_temp"].append(None)


def update_wlm_dict(comp_dict, data, file_path):
    keys = list(comp_dict["wlm"].keys())
    for key in keys:
            if key in data:
                val = data[key]
                # Flatten and cast to float
                if isinstance(val, (list, tuple)) or val.ndim > 1:
                    val = val.flatten()[0]
                comp_dict["wlm"][key].append(float(val))
            else:
                print(f"Warning: '{key}' not found at {file_path}. Skipping this key.")


def update_liv_dict(comp_dict, data, file_path):
    # Update the liv dictionary with data from the .mat file.
    keys = list(comp_dict["liv"].keys())
    for key in keys:
            if key in data:
                val = data[key]
                # Flatten and cast to float
                if isinstance(val, (list, tuple)) or val.ndim > 1:
                    val = val.flatten()[0]
                comp_dict["liv"][key].append(float(val))
            else:
                print(f"Warning: '{key}' not found at {file_path}. Skipping this key.")


def get_IDtag(file):
    file_base_name = os.path.splitext(file)[0]
    file_name_parts = file.split('_')

    # Find the substring containing "Chip" followed by numbers
    chipstring = next((part for part in file_name_parts if part.startswith("Chip") and any(char.isdigit() for char in part)), None)

    # Find the substring containing 'R' followed by a number
    rstring = next((part for part in file_name_parts if part.startswith("R") and any(char.isdigit() for char in part)), None)

    # # Find the index of chipstring in file_name_parts
    # if chipstring and chipstring in file_name_parts:
    #     chip_idx = file_name_parts.index(chipstring)
    #     idstring = "_".join(file_name_parts[chip_idx:])
    # else:
    #     print("Something went horribly wrong, check your file naming conventions.")

    # Extract the end of the file name (excluding the file extension)
    file_base_name = os.path.splitext(file)[0]
    end_identifier = file_base_name.split('_')[-1]

    # Create the IDtag
    if chipstring and rstring and end_identifier:
        IDtag = f"{chipstring}_{rstring}_{end_identifier}"
    elif chipstring and rstring:
        IDtag = f"{chipstring}_{rstring}_Unknown"
    else:
        IDtag = "Unknown_ID"

    print(f"Processing file: {file_base_name} with IDtag: {IDtag}")
    return IDtag

def update(comp_dict, file_path, file, process_mode):
    # Update the dictionary with data from the .mat file.
    if 'osa' in file.lower() and process_mode == 'osa':
        data = extract_osa(file_path)
        update_osa_dict(comp_dict, data, file_path)
    elif 'wlm' in file.lower() and process_mode == 'wlm':
        data = extract_wlm(file_path)
        update_wlm_dict(comp_dict, data, file_path)
    elif 'liv' in file.lower() and process_mode == 'liv':
        data = extract_liv(file_path)
        update_liv_dict(comp_dict, data, file_path)

def iterate_files(parent_path, selection_mode='1', comp_mode ='osa', selected_files=None):
    dictionaries = setup_compdictionaries()
    for current_root, dirs, files in os.walk(parent_path):
        for file in files:
            if file.endswith(".mat"):
                file_path = os.path.join(current_root, file)
                file_base_name = os.path.splitext(file)[0]
                IDtag = get_IDtag(file)
                if selection_mode == '2' and selected_files is not None and file_base_name not in selected_files:
                    print(f"Skipping file (not selected): {file_path}")
                    continue
                try:
                    print(f"Processing file: {file_path}")
                    dictionaries[comp_mode]["IDtag"].append(IDtag)
                    update(dictionaries, file_path, file, comp_mode)
                    # if "osa" in file.lower():
                    #     dictionaries['osa']["IDtag"].append(IDtag)
                    #     data = extract_osa(file_path)
                    #     update_osa_dict(dictionaries, data)
                    # elif "wlm" in file.lower():
                    #     dictionaries['wlm']['IDtag'].append(IDtag)
                    #     data = extract_wlm(file_path)
                    #     update_wlm_dict(dictionaries, data, file_path)
                    # elif "liv" in file.lower():
                    #     dictionaries["liv"]["IDtag"].append(IDtag)
                    #     data = extract_liv(file_path)
                    #     update_liv_dict(dictionaries, data, file_path)
                except Exception as e:
                    print(f"Failed processing file: {file_path}\nReason: {str(e)}\n")
    return dictionaries

def main():
    # Initialize Tkinter and hide the root window.
    root = Tk()
    root.withdraw()
    save_plot_folder = "C:/Users/OWNER/Desktop"  # Path for saving plots
    try:
        # Ask for file selection mode
        selection_choice = simpledialog.askstring(
            "Select Mode",
            "Select mode:\n(1) Folder\n(2) Select from Parent Folder\n(3) Add a File (Not functional)\nEnter 1, 2, or 3:"
        )
        if not selection_choice:
            print("No selection made. Exiting.")
            return

        # Ask for comparison mode
        comp_choice = simpledialog.askstring(
            "Comparison Mode",
            "Select comparison mode:\n(1) OSA files only\n(2) WLM files only\n(3) LIV files only\nEnter 1, 2, or 3:"
        )
        if not comp_choice:
            print("No comparison mode selected. Exiting.")
            return
        
        comp_choice = comp_choice.strip()
        comp_mode = {"1": "osa", "2": "wlm", "3": "liv"}.get(comp_choice)
        
        if comp_mode is None:
            print("Invalid processing mode selection. Exiting.")
            return

        selection_choice = selection_choice.strip()
        if selection_choice == '1':
            # Folder selection mode
            folder_path = askdirectory(title="Select a Folder Containing the .mat Files")
            if not folder_path:
                print("No folder selected. Exiting.")
                return

            print(f"Selected folder: {folder_path}")
            dictionaries = iterate_files(folder_path, selection_mode='1', comp_mode=comp_mode)

        elif selection_choice == '2':
            # Parent folder + selected subfiles mode
            print("Parent folder selection mode")
            selected_files, folder_path = multi_select.scrape_filenames(root)
            if not selected_files or not folder_path:
                print("No files or folder selected. Exiting.")
                return

            print(f"Selected parent folder: {folder_path}")
            print(f"Selected files: {selected_files}")
            dictionaries = iterate_files(folder_path, selection_mode='2', comp_mode=comp_mode, selected_files=selected_files)

        elif selection_choice == '3':
            print("File selection mode is not functional yet.")
            return

        else:
            print("Invalid selection mode. Exiting.")
            return

    finally:
        # If no dictionary was created (e.g., error), skip
        if 'dictionaries' not in locals():
            root.destroy()
            return
        
        print(f"Processed chip IDs: {dictionaries[comp_mode]['IDtag']}")
        if comp_mode == "osa":
            plot_osa(dictionaries, save_plot_folder)
        elif comp_mode == "wlm":
            plot_wlm(dictionaries, save_plot_folder)
        elif comp_mode == "liv":
            plot_liv(dictionaries, save_plot_folder)

        root.destroy()

if __name__ == '__main__':
    main()


