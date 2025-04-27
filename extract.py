import osa
import wlm
import os
from tkinter import Tk, simpledialog
from tkinter.filedialog import askdirectory, askopenfilename
import numpy as np
import matplotlib.pyplot as plt



# This script is designed to extract data from .mat files and plot the results.
# .mat fliles must have been produced from (MOST RECENT VERSION OF) data.py or it will fail. 

def extract_ldc(mat_file_path):
    print("LDC Extraction")
    vars = ['peak_power', 'peak_power_I', 'threshold_current']
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
    vars = ['peak_power', 'peak_power_I', 'threshold_current', 'peak_power_WL', 'peak_power_V']
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

  
    plt.show()
    # Save the plot to the specified folder
    plot_path = os.path.join(folder_path, '_osa_plots.png')
    plt.savefig(plot_path)
    print(f"Plots saved to {plot_path}")

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

  
    plt.show()
    # Save the plot to the specified folder
    plot_path = os.path.join(folder_path, '_wlm_plots.png')
    plt.savefig(plot_path)
    print(f"Plots saved to {plot_path}")

def plot_ldc(data_dict, folder_path):
    # Plotting function for LDC data.

    data = data_dict.get('ldc', {})
    print(data)

    # Extract data for plotting
    peak_power = data.get('peak_power', [])
    peak_power_I = data.get('peak_power_I', [])
    threshold_current = data.get('threshold_current', [])

    print(f"Peak Power: {peak_power}")
    print(f"Peak Power I: {peak_power_I}")
    print(f"Threshold Current: {threshold_current}")

    # Create plots
    plt.figure(figsize=(10, 6))
    
    plt.subplot(1, 2, 1)
    plt.scatter(peak_power_I, peak_power, label='Peak Power by Assoc Current')
    plt.title('Peak Power - Assoc Current')
    plt.xlabel('Current (A)')
    plt.ylabel('Peak Power (mW)')

    print("Plot 1 successful - peak power vs current")
    
    plt.subplot(1, 2, 2)
    plt.scatter(threshold_current, peak_power, label='Peak Power by Assoc Threshold Current')
    plt.xlabel('Threshold Current (A)')
    plt.ylabel('Peak Power (mW)')
    plt.title('Peak Power - Assoc Threshold Current')
    
    print("Plot 2 successful - peak power vs threshold current")

  
    plt.show()
    # Save the plot to the specified folder
    plot_path = os.path.join(folder_path, '_ldc_plots.png')
    plt.savefig(plot_path)
    print(f"Plots saved to {plot_path}")


def setup_compdictionaries():
    # Initialize dictionaries to hold the comparison data.
    comp_dict = {
        "osa": {
            "peak_power": [],
            "peak_power_wl": [],
            "peak_power_I": [],
            "peak_power_temp": [],
        },
        "wlm": {
            "threshold_current": [],
            "peak_power": [],
            "peak_power_I": [],
            "peak_power_WL": [],
            "peak_power_V": [],
        },
        "ldc": {
            "threshold_current": [],
            "peak_power": [],
            "peak_power_I": [],
        }
    }
    return comp_dict

def update_osa_dict(comp_dict, data, file_path):
    # Update the OSA dictionary with data from the .mat file.
    if 'peak_power' in data:
        arr = data['peak_power'].flatten()
        comp_dict["osa"]["peak_power"].append(float(np.max(arr)) if arr.size > 0 else None)
    if 'peak_power_I' in data:
        arr = data['peak_power_I'].flatten()
        comp_dict["osa"]["peak_power_I"].append(float(np.max(arr)) if arr.size > 0 else None)
    if 'peak_power_wl' in data: 
        arr = data['peak_power_wl'].flatten()
        comp_dict["osa"]["peak_power_wl"].append(float(np.max(arr)) if arr.size > 0 else None)
    if 'peak_power_temp' in data:
        arr = data['peak_power_temp'].flatten()
        comp_dict["osa"]["peak_power_temp"].append(float(np.max(arr)) if arr.size > 0 else None)

def update_wlm_dict(comp_dict, data, file_path):
    # Update the WLM dictionary with data from the .mat file.
    if 'threshold_current' in data:
        arr = data['threshold_current'].flatten()
        comp_dict["wlm"]["threshold_current"].append(float(np.max(arr)) if arr.size > 0 else None)
    if 'peak_power' in data:
        arr = data['peak_power'].flatten()
        comp_dict["wlm"]["peak_power"].append(float(np.max(arr)) if arr.size > 0 else None)
    if 'peak_power_I' in data:
        arr = data['peak_power_I'].flatten()
        comp_dict["wlm"]["peak_power_I"].append(float(np.max(arr)) if arr.size > 0 else None)
    if 'peak_power_WL' in data: 
        arr = data['peak_power_WL'].flatten()
        comp_dict["wlm"]["peak_power_WL"].append(float(np.max(arr)) if arr.size > 0 else None)
    if 'peak_power_V' in data:
        arr = data['peak_power_V'].flatten()
        comp_dict["wlm"]["peak_power_V"].append(float(np.max(arr)) if arr.size > 0 else None)

def update_ldc_dict(comp_dict, data, file_path):
    # Update the LDC dictionary with data from the .mat file.
    if 'threshold_current' in data:
        arr = data['threshold_current'].flatten()
        comp_dict["ldc"]["threshold_current"].append(float(np.max(arr)) if arr.size > 0 else None)
    if 'peak_power' in data:
        arr = data['peak_power'].flatten()
        comp_dict["ldc"]["peak_power"].append(float(np.max(arr)) if arr.size > 0 else None)
    if 'peak_power_I' in data:
        arr = data['peak_power_I'].flatten()
        comp_dict["ldc"]["peak_power_I"].append(float(np.max(arr)) if arr.size > 0 else None)
 
def main():
    # Initialize Tkinter and hide the root window.
    root = Tk()
    root.withdraw()
    dictionaries = setup_compdictionaries()

    try:
        # Ask whether to process a folder or a single file.
        selection_choice = simpledialog.askstring("Select Mode", 
                                        "Select mode:\n(1) Folder\n(2) Add a File (Not functional)\nEnter 1 (or 2):")
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
            # @TODO: Consider including option for all or multiple, then would need to sort datatypes as we do (complicated )
            comp_choice = simpledialog.askstring("Comparison Mode", 
                                        "Select comparison mode for folder:\n"
                                        "(1) OSA files only\n"
                                        "(2) WLM files only\n"
                                        "(3) LDC files only\nEnter 1, 2, or 3:")
            if not comp_choice:
                print("No comparison mode selected. Exiting.")
                return
            
            comp_choice = comp_choice.strip()
            if comp_choice == '1':
                comp_mode = "osa"
            elif comp_choice == '2':
                comp_mode = "wlm"
            elif comp_choice == '3':
                comp_mode = "ldc"
            else:
                print("Invalid processing mode selection. Exiting.")
                return

            print(f"Selected folder: {folder_path}")
            # Recursively process every .mat file in the folder and its subfolders.
            for current_root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith(".mat"):
                        file_path = os.path.join(current_root, file)
                        if "osa" not in file.lower() and comp_mode == "osa":
                            print(f"Skipping file (not OSA): {file_path}")
                            continue
                        elif "wlm" not in file.lower() and comp_mode == "wlm":
                            print(f"Skipping file (not WLM): {file_path}")
                            continue
                        elif "ldc" not in file.lower() and comp_mode == "ldc":
                            print(f"Skipping file (not LDC): {file_path}")
                            continue
                        try:
                            if comp_mode == "osa":
                                data = extract_osa(file_path)
                                update_osa_dict(dictionaries, data, file_path)
                            elif comp_mode == "wlm":
                                data = extract_wlm(file_path)
                                update_wlm_dict(dictionaries, data, file_path)
                            elif comp_mode == "ldc":
                                data = extract_ldc(file_path)
                                print("LDC not functional yet")
                        except Exception as e:
                            # Print the full file name and a summary of the error, then continue.
                            print(f"Failed processing file: {file_path}\nReason: {str(e)}\n")
                        
        elif selection_choice.strip() == '2':
            # File selection mode.
            # print("File selection mode")
            # file_path = askopenfilename(title="Select a CSV File", filetypes=[("CSV Files", "*.csv")])
            # if not file_path:
            #     print("No file selected. Exiting.")
            #     return
            # print(f"Selected file: {file_path}")
            # try:
            #     file_name = os.path.basename(file_path)
            #     file_size = os.path.getsize(file_path)
            #     # Automatically choose processing based on file criteria.
            #     if "osa" in file_name.lower():
            #         comp_mode = "osa"
            #     else:
            #         comp_mode = "wlm"
            #     # For file mode, base_folder is left as None.
            #     readMat(file_path, comp_mode, base_folder=None)
            # except Exception as e:
            #     print(f"Failed processing file: {file_path}\nReason: {str(e)}")
            print("File selection mode is not functional yet.")
        else:
            print("Invalid selection mode. Exiting.")
    finally:
        print(dictionaries)
        if comp_mode == "osa":
            # Call the plotting function for OSA data.
            plot_osa(dictionaries, folder_path)
        elif comp_mode == "wlm":
            plot_wlm(dictionaries, folder_path)
        elif comp_mode == "ldc":
            plot_ldc(dictionaries, folder_path)
        root.destroy()

if __name__ == '__main__':
    main()


