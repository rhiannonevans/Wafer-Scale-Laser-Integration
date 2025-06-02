#author: sheri and co-pilot
#date: 2025-04-14
# This script processes the data from a benchtop CSV file, extracts wavelength and channel data, converts power values from dBm to mW if requested, 
# and saves the processed data to a .mat file.

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.io
import tkinter as tk
from tkinter import filedialog


def process_benchtop(file_path_str, output_folder=None, convert_to_mW=False):
    # Expand the file path and determine the base name and location
    file_path = os.path.expanduser(file_path_str)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    file_loc = os.path.dirname(file_path)
    print(f"Looking for the file at: {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist. Please check the file path.")

    # Load the CSV file
    df = pd.read_csv(file_path, header=None, on_bad_lines="skip", engine="python", skiprows=16)

    # Define search terms for each target row
    search_terms = {
        "wavelength": "wavelength",  # Update to match the actual label in the CSV
        "channel_1": "channel_1" ,    # Update to match the actual label in the CSV
        "channel_2": "channel_2",    # Update to match the actual label in the CSV
        "channel_3": "channel_3",   # Update to match the actual label in the CSV
        "channel_4": "channel_4",   # Update to match the actual label in the CSV
    }

    # Find indices where these terms occur
    indices = {}
    for key, term in search_terms.items():
        matches = df[0].str.contains(term, case=False, na=False)
        if matches.any():
            indices[key] = matches.idxmax()
        else:
            indices[key] = None

    # Debugging: Print indices
    print(f"Found indices: {indices}")

    # Remove the first column (used for matching)
    del df[0]

    # Extract data rows from the DataFrame
    try:
        # Extract wavelength data
        if indices["wavelength"] is not None:
            wavelength = pd.to_numeric(df.loc[indices["wavelength"]], errors='coerce')
            if wavelength.isnull().all():
                raise ValueError("Invalid or missing wavelength data.")
        else:
            raise ValueError("Wavelength data not found.")

        # Extract channel data
        try:
            # Dynamically determine the maximum channel number
            max_channel = max(
                int(key.split('_')[1]) for key in indices.keys() if key.startswith("channel_") and indices[key] is not None
            )

            channels = {}
            for i in range(1, max_channel + 1):  # Dynamically adjust the range
                ch_key = f"channel_{i}"
                if indices[ch_key] is not None:
                    print(f"Channel {i} row content: {df.loc[indices[ch_key]]}")  # Debugging
                    channels[ch_key] = pd.to_numeric(df.loc[indices[ch_key]], errors='coerce')
                else:
                    channels[ch_key] = None

        except Exception as e:
            print(f"Error extracting channel data: {str(e)}")
            return

        # Convert power values from dBm to mW if requested
        channels_mW = {}
        if convert_to_mW:
            for key, value in channels.items():
                if value is not None:
                    channels_mW[key] = 10 ** (value / 10)

        # Build a dictionary with the core data for saving to a .mat file
        data_dict = {"wavelength": wavelength}
        data_dict.update(channels)
        if convert_to_mW:
            for key, value in channels_mW.items():
                data_dict[f"{key}_mW"] = value

        # Save the data dictionary to a .mat file in the output folder
        if output_folder is None:
            output_folder = file_loc  # Use the parent folder if no output folder is specified

        mat_filename = base_name + "_data.mat"
        save_path_mat = os.path.join(output_folder, mat_filename)
        scipy.io.savemat(save_path_mat, data_dict)
        print(f"Data dictionary saved to {save_path_mat}")

        # Plot wavelength vs all channels' power in mW
        if convert_to_mW:
            plt.figure(figsize=(10, 6))
            for key, value in channels_mW.items():
                if value is not None:
                    plt.plot(wavelength, value, label=key)
            plt.xlabel("Wavelength (nm)")
            plt.ylabel("Power (mW)")
            plt.title("Wavelength vs Channel Power (mW)")
            plt.legend()
            plt.grid(True)

            # Save the plot as a PNG file
            plot_filename = base_name + "_wavelength_vs_power_mW.png"
            save_path_plot = os.path.join(output_folder, plot_filename)
            plt.savefig(save_path_plot, bbox_inches="tight")
            print(f"Plot saved to {save_path_plot}")
            plt.close()

    except Exception as e:
        print(f"Error extracting data from file: {file_path}\nReason: {str(e)}")
        return


# Process all files in the parent folder
if __name__ == "__main__":
    # Prompt user to select the parent folder
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    parent_folder = filedialog.askdirectory(
        title="Select the parent folder containing CSV files"
    )
    if not parent_folder:
        print("No folder selected. Exiting.")
        exit()

    # Ask user if they want to convert to mW
    convert_to_mW = input("Convert power values from dBm to mW? (y/n): ").strip().lower() == "y"

    # Process all CSV files in the parent folder
    for file_name in os.listdir(parent_folder):
        if file_name.endswith(".csv"):
            file_path = os.path.join(parent_folder, file_name)
            try:
                process_benchtop(file_path, output_folder=parent_folder, convert_to_mW=convert_to_mW)
            except Exception as e:
                print(f"Failed to process file: {file_path}\nReason: {str(e)}")