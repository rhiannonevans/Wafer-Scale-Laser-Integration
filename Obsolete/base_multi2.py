import process_csv
import os
from tkinter import Tk, simpledialog
from tkinter import filedialog
from tkinter.filedialog import askdirectory, askopenfilename
import multi_select
import process_csv
import extract
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import time

"""
    Script for processing and comparing CSV files for either OSA or LIV/WLM data. Allows user to select a parent folder,
    then either sweep through all files in that folder or select specific files to run. 
    If a file has been processed previously (a .mat exists with the same name), it will skip processing that file. (To re-process that file, either 
    delete the existing .mat file or run process_csv.py on it.)

    If user chooses to compare files, it will extract relevant data from the processed files and plot either current vs peak power and wavelength vs peak power for OSA data,
    or current vs peak power and threshold current for LIV/WLM data. The plots will be saved in the parent folder as PNG and SVG files.

    [Author: Rhiannon H Evans]
"""

def plot_scatter(data1, data2, x_label, y_label, title, save_title, parent_path=None, remove_outliers=True, outlier_threshold=-70, file_name=None):
    # Filters out data for which max power is below a certain threshold (default -70 dBm)
    if remove_outliers:
        filtered_data = [(x, y) for x, y in zip(data1, data2) if y >= outlier_threshold]
        if filtered_data:
            data1, data2 = zip(*filtered_data)
        else:
            data1, data2 = [], []
    plt.figure()
    # Use inferno colormap, avoid light colors by restricting to 0.2-0.8
    colormap = cm.get_cmap('inferno')
    color = colormap(0.2)
    # Add legend with file name if provided
    label = file_name if file_name else save_title
    plt.scatter(data1, data2, c=color, label=label, alpha=0.7)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.legend(loc='best')
    plt.grid(True)
    if parent_path:
        png_path = os.path.join(parent_path, f"{save_title}.png")
        svg_path = os.path.join(parent_path, f"{save_title}.svg")
        plt.savefig(png_path, bbox_inches='tight')
        plt.savefig(svg_path, bbox_inches='tight')
    else:
        print("Error: parent_path is None. Cannot save the plot.")
    plt.show()

def mat_file_exists_anywhere(parent_path, file_base_name):
    mat_filename = f"{file_base_name}.mat"
    for current_root, dirs, files in os.walk(parent_path):
        if mat_filename in files:
            return True
    return False
        

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
                                    "(3) WLM files only\nEnter 1, 2, or 3:")
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
            process_mode = "wlm"
            print("Processing WLM...")
        else:
            print("Invalid processing mode selection. Exiting.")
            return

                # Ask if the user wants to overwrite existing .mat files
        overwrite_choice = simpledialog.askstring("Overwrite Existing Files", 
                                    "Overwrite existing .mat files? (y = overwrite, n = skip existing):")
        if not overwrite_choice:
            print("No overwrite choice selected. Exiting.")
            return
        overwrite_existing = overwrite_choice.strip().lower() == 'y'

        #start timer to track processing time
        start_time = time.time()
        
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
                                if mat_file_exists_anywhere(parent_path, file_base_name) and not overwrite_existing:
                                    print(f"Skipping existing file: {file_base_name}.mat (found in subdirectory)")
                                    continue
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

        
        start_prompt_time = time.time()
        # Ask the user if they would like to compare the files.
        compare_choice = simpledialog.askstring("Compare Files", 
                        "Would you like to compare the processed files? (y/n):")
        start_comp_time = time.time()
        prompt_deadtime = start_comp_time - start_prompt_time

        if compare_choice and compare_choice.strip().lower() == 'y':
            try:
                dataD = extract.iterate_files(parent_path, selection_choice, process_mode, files_to_run)
                print(dataD)
                if process_mode == 'osa':
                    # Aggregate data across all files before plotting
                    peak_power_I = dataD["osa"].get("peak_power_I", [])
                    peak_power = dataD["osa"].get("peak_power", [])
                    peak_power_wl = dataD["osa"].get("peak_power_wl", [])
                    # Collect file names for legend (from extraction, not .mat)
                    osa_file_names = dataD["osa"].get("file_names", [])
                    if not osa_file_names:
                        osa_file_names = files_to_run if process_mode == "osa" else []
                    print("Plotting current power comparison...")
                    for idx, file_name in enumerate(osa_file_names):
                        color = cm.get_cmap('inferno')(0.2 + 0.6 * (idx / max(len(osa_file_names) - 1, 1)))
                        # Clean label to show only part after OSA_
                        if "OSA_" in file_name:
                            label = file_name.split("OSA_")[-1].replace('.mat', '')
                        else:
                            label = file_name
                        plt.scatter([peak_power_I[idx]], [peak_power[idx]], color=color, label=label)
                    plt.xlabel("Peak Power Current (mA)")
                    plt.ylabel("Peak Power (mW)")
                    plt.title("Peak Power by Current Comparison")
                    plt.legend(loc='best', fontsize='small')
                    plt.grid(True)
                    png_path = os.path.join(parent_path, "peak_power_current_comparison_osa.png")
                    plt.savefig(png_path, bbox_inches='tight')
                    plt.show()

                    print("Plotting wl power comparison...")
                    for idx, file_name in enumerate(osa_file_names):
                        color = cm.get_cmap('inferno')(0.2 + 0.6 * (idx / max(len(osa_file_names) - 1, 1)))
                        # Clean label to show only part after OSA_
                        if "OSA_" in file_name:
                            label = file_name.split("OSA_")[-1].replace('.mat', '')
                        else:
                            label = file_name
                        plt.scatter([peak_power_wl[idx]], [peak_power[idx]], color=color, label=label)
                    plt.xlabel("Peak Power Wavelength (nm)")
                    plt.ylabel("Peak Power (mW)")
                    plt.title("Peak Power by Assoc. Wavelength Comparison")
                    plt.legend(loc='best', fontsize='small')
                    plt.grid(True)
                    png_path = os.path.join(parent_path, "peak_power_wl_comparison_osa.png")
                    plt.savefig(png_path, bbox_inches='tight')
                    plt.show()
                elif process_mode == 'liv':
                    # Aggregate data across all files before plotting
                    peak_power_I = dataD["liv"].get("peak_power_I", [])
                    peak_power = dataD["liv"].get("peak_power", [])
                    ch1_threshI = dataD["liv"].get("threshold_ch2", [])
                    IDs = dataD["liv"].get("IDTag", [])
                    
                    # Get current and channel data directly
                    current_data = dataD["liv"].get("current", None)
                    channel_2_data = dataD["liv"].get("channel_2", None)
                    currents = []
                    channels_3 = []
                    
                    if current_data is not None and channel_2_data is not None:
                        # Convert to list if numpy array
                        if hasattr(current_data, 'tolist'):
                            currents = current_data.tolist()
                        else:
                            currents = current_data
                            
                        if hasattr(channel_2_data, 'tolist'):
                            channels_3 = channel_2_data.tolist()
                        else:
                            channels_3 = channel_2_data
                    
                    # Collect file names for legend (from extraction, not .mat)
                    liv_file_names = dataD["liv"].get("file_names", [])
                    if not liv_file_names:
                        liv_file_names = files_to_run if process_mode == "liv" else []
                        
                    print("\nDiagnostic Information:")
                    print(f"Files to process: {len(liv_file_names)}")
                    print(f"Current arrays available: {len(currents)}")
                    print(f"Channel 3 arrays available: {len(channels_3)}")

                    # for file_data in dataD["liv"].values():
                    #     if isinstance(file_data, dict):
                    #         peak_power_I.extend(file_data.get("peak_power_I", []))
                    #         peak_power.extend(file_data.get("peak_power", []))
                    #         ch1_threshI.extend(file_data.get("threshold_ch1", []))
                    print("Plotting current v power comparison...")
                    # Create plot with cleaned filenames in legend (part after LIV_)
                    plt.figure()
                    num_files = len(liv_file_names)
                    
                    # Verify we have data to plot
                    if not currents or not channels_3 or len(currents) != num_files or len(channels_3) != num_files:
                        print(f"Warning: Mismatched data lengths - Files: {num_files}, Current: {len(currents) if currents else 0}, channel_2: {len(channels_3) if channels_3 else 0}")
                        return
                        
                    for i, file_name in enumerate(liv_file_names):
                        color = plt.colormaps['inferno'](0.2 + 0.6 * (i / max(num_files - 1, 1)))
                        # Clean label to show only part after LIV_
                        if "LIV_" in file_name:
                            label = file_name.split("LIV_")[-1].replace('.mat', '')
                        else:
                            label = file_name
                        
                        try:
                            # Plot all points in the arrays
                            if currents[i] is not None and channels_3[i] is not None:
                                # Flatten the arrays and convert to numpy arrays
                                curr_array = np.array(currents[i]).flatten()
                                ch3_array = np.array(channels_3[i]).flatten()
                                # Plot the data
                                plt.plot(curr_array, ch3_array, color=color, label=label)
                            else:
                                print(f"Warning: No data for {file_name}")
                        except Exception as e:
                            print(f"Error plotting {file_name}: {str(e)}")
                    plt.xlabel("Current (mA)")
                    plt.ylabel("Channel 3 Power (mW)")
                    plt.title("Current vs Channel 3 Power")
                    plt.legend(loc='upper left', fontsize=13, borderaxespad=0)
                    plt.grid(True)
                    png_path = os.path.join(parent_path, "current_vs_channel3_liv.png")
                    plt.savefig(png_path, bbox_inches='tight')
                    plt.show()


                    print("Plotting peak power v current comparison...")
                    # Create plot with cleaned filenames in legend (part after LIV_)
                    plt.figure()
                    num_files = len(liv_file_names)
                    for i, file_name in enumerate(liv_file_names):
                        color = cm.get_cmap('inferno')(0.2 + 0.6 * (i / max(num_files - 1, 1)))
                        # Clean label to show only part after LIV_
                        if "LIV_" in file_name:
                            label = file_name.split("LIV_")[-1].replace('.mat', '')
                        else:
                            label = file_name
                        plt.scatter([peak_power_I[i]], [peak_power[i]], color=color, label=label)
                    plt.xlabel("Peak Power Current (mA)")
                    plt.ylabel("Peak Power (mW)")
                    plt.title("Peak Power by Current Comparison")
                    plt.legend(loc='upper left', fontsize=13, borderaxespad=0)
                    plt.grid(True)
                    png_path = os.path.join(parent_path, "peak_power_current_comparison_liv.png")
                    plt.savefig(png_path, bbox_inches='tight')
                    plt.show()

                    
                    print("Plotting threshold current (channel 2) by peak power comparison...")
                    # Scatter plot
                    plt.figure()
                    num_files = len(liv_file_names)
                    for i, file_name in enumerate(liv_file_names):
                        color = cm.get_cmap('inferno')(0.2 + 0.6 * (i / max(num_files - 1, 1)))
                        if "LIV_" in file_name:
                            label = file_name.split("LIV_")[-1].replace('.mat', '')
                        else:
                            label = file_name
                        plt.scatter([ch1_threshI[i]], [peak_power[i]], color=color, label=label)
                    plt.xlabel("Threshold Current (mA)")
                    plt.ylabel("Peak Power (mW)")
                    plt.title("Peak Power by Threshold current")
                    plt.legend(loc='upper left', fontsize=13, borderaxespad=0)
                    plt.grid(True)
                    png_path = os.path.join(parent_path, "threshI_comparison_liv.png")
                    plt.savefig(png_path, bbox_inches='tight')
                    plt.show()

                    # Boxplot of threshold currents
                    plt.figure(figsize=(10, 6))
                    plt.boxplot([ch1_threshI], labels=['Channel 1'])
                    plt.ylabel("Threshold Current (mA)")
                    plt.title("Distribution of Threshold Currents")
                    # Add individual points as scatter
                    for i, thresh in enumerate(ch1_threshI):
                        color = cm.get_cmap('inferno')(0.2 + 0.6 * (i / max(num_files - 1, 1)))
                        file_name = liv_file_names[i]
                        if "LIV_" in file_name:
                            label = file_name.split("LIV_")[-1].replace('.mat', '')
                        else:
                            label = file_name
                        plt.scatter(1, thresh, color=color, alpha=0.6, label=label)
                    plt.grid(True)
                    plt.legend(loc='upper right', fontsize=13, borderaxespad=0)
                    png_path = os.path.join(parent_path, "threshI_boxplot_liv.png")
                    plt.savefig(png_path, bbox_inches='tight')
                    plt.show()

                    # Only plot points where current (ch1_threshI) < 20
                    filtered = [(i, p, f) for i, p, f in zip(ch1_threshI, peak_power, liv_file_names) if i < 20]
                    if filtered:
                        filtered_ch1_threshI, filtered_peak_power, filtered_names = zip(*filtered)
                        plt.figure()
                        for i, (thresh_i, power, name) in enumerate(zip(filtered_ch1_threshI, filtered_peak_power, filtered_names)):
                            color = cm.get_cmap('inferno')(0.2 + 0.6 * (i / max(len(filtered_names) - 1, 1)))
                            if "LIV_" in name:
                                label = name.split("LIV_")[-1].replace('.mat', '')
                            else:
                                label = name
                            plt.scatter([thresh_i], [power], color=color, label=label)
                        plt.xlabel("Threshold Current (mA)")
                        plt.ylabel("Peak Power (mW)")
                        plt.title("Peak Power by Threshold current (I < 20 mA) - Filtered")
                        plt.legend(loc='upper left', fontsize=13, borderaxespad=0)
                        plt.grid(True)
                        png_path = os.path.join(parent_path, "threshI_comparison_filtered_liv.png")
                        plt.savefig(png_path, bbox_inches='tight')
                        plt.show()
                    else:
                        filtered_ch1_threshI, filtered_peak_power = [], []
                elif process_mode == 'wlm':
                    # Aggregate data across all files before plotting
                    peak_power_I = dataD["wlm"].get("peak_power_I", [])
                    peak_power = dataD["wlm"].get("peak_power", [])
                    peak_power_wl = dataD["wlm"].get("peak_power_WL", [])
                    # Collect file names for legend (from extraction, not .mat)
                    wlm_file_names = dataD["wlm"].get("file_names", [])
                    if not wlm_file_names:
                        wlm_file_names = files_to_run if process_mode == "wlm" else []
                    ch1_threshI = dataD["wlm"].get("threshold_ch1", [])
                    IDs = dataD["wlm"].get("IDTag", [])
                    # for file_data in dataD["wlm"].values():
                    #     if isinstance(file_data, dict):
                    #         peak_power_I.extend(file_data.get("peak_power_I", []))
                    #         peak_power.extend(file_data.get("peak_power", []))
                    #         ch1_threshI.extend(file_data.get("threshold_ch1", []))
                    print("Plotting peak power v current comparison...")
                    # Only plot points where peak power > 1e-6
                    plot_scatter(peak_power_I, peak_power, "Peak Power Current (mA)", "Peak Power (mW)", "Peak Power by Current Comparison", "peak_power_current_comparison_wlm", parent_path)
                    filtered = [(i, p) for i, p in zip(peak_power_I, peak_power) if p > 1e-6]
                    if filtered:
                        filtered_peak_power_I, filtered_peak_power = zip(*filtered)
                        plot_scatter(filtered_peak_power_I, filtered_peak_power, "Peak Power Current (mA)", "Peak Power (mW)", "Peak Power by Current Comparison", "peak_power_current_comparison_filtered_wlm", parent_path)
                    else:
                        filtered_peak_power_I, filtered_peak_power = [], []
                    
                    print("Plotting threshold current (channel 1) by peak power comparison...")
                    plot_scatter(ch1_threshI, peak_power, "Threshold Current (mA)", "Peak Power (mW)", "Peak Power by Threshold current (I < 20 mA)", "threshI_comparison_wlm", parent_path)
                    # Only plot points where current (ch1_threshI) < 20
                    filtered = [(i, p) for i, p in zip(ch1_threshI, peak_power) if i < 20]
                    if filtered:
                        filtered_ch1_threshI, filtered_peak_power = zip(*filtered)
                        plot_scatter(filtered_ch1_threshI, filtered_peak_power, "Threshold Current (mA)", "Peak Power (mW)", "Peak Power by Threshold current (I < 20 mA)", "threshI_comparison_filtered_wlm", parent_path)     
                    else:
                        filtered_ch1_threshI, filtered_peak_power = [], []
            except Exception as e:
                print(f"Failed to compare files.\nReason: {str(e)}\n")
    finally:
        root.destroy()
    # Print the total processing time.
    print(f"Took {start_prompt_time-start_time:.2f} seconds to process {len(files_to_run)} files.")
    print(f"Took: {time.time()-start_comp_time:.2f} seconds to compare {len(files_to_run)} files.")
    print(f"Total script time: {time.time()-start_time - prompt_deadtime:.2f} seconds")

if __name__ == '__main__':
    main()