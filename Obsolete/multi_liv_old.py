import os
import tkinter as tk
from tkinter import filedialog, simpledialog
import scipy.io
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

def ask_selection_mode():
    root = tk.Tk()
    root.withdraw()
    return simpledialog.askstring("Selection Mode", "Enter 'multi' to select multiple folders or 'parent' to select a parent folder:")


def select_multiple_folders():
    root = tk.Tk()
    root.withdraw()
    folder_paths = []
    while True:
        folder = filedialog.askdirectory(title="Select Folder (Cancel to finish)")
        if folder:
            folder_paths.append(folder)
        else:
            break
    return folder_paths


def select_parent_folder():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title="Select Parent Folder")


def gather_mat_data(folder_paths):
    data = []
    for folder_path in folder_paths:
        for root_dir, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.mat'):
                    file_path = os.path.join(root_dir, file)
                    mat_data = scipy.io.loadmat(file_path)
                    data.append((mat_data, file, root_dir))
    return data


def plot_data(data, save_folder = "C:/Users/OWNER/Desktop/"):
    colormap = cm.get_cmap('inferno')

    def plot_line(data, x_key, y_key, x_label, y_label, title, save_title):
        plt.figure()
        num_files = len(data)
        for i, (mat_data, filename, folder) in enumerate(data):
            if x_key in mat_data and y_key in mat_data:
                x_data = mat_data[x_key].flatten()
                y_data = mat_data[y_key].flatten()

                # # Normalize the y-axis data
                # if np.max(y_data) != 0:
                #     y_data = y_data / np.max(y_data)

                color = colormap(0.2 + 0.6 * (i / max(num_files - 1, 1)))  # Avoid the lightest colors

                # Extract label after "LIV_", fallback to filename without extension
                if "LIV_" in filename:
                    label = filename.split("LIV_")[-1].replace('.mat', '')
                else:
                    label = os.path.splitext(filename)[0]  # Use filename without extension

                plt.plot(x_data, y_data, color=color, label=label)
            else:
                print(f"{filename} missing '{x_key}' or '{y_key}'")

        # Set axis labels with larger font size
        plt.xlabel(x_label, fontsize=16)
        plt.ylabel(y_label, fontsize=16)

        # Set title with larger font size
        plt.title(title, fontsize=14)

        # Adjust tick label font size
        plt.tick_params(axis='both', which='major', labelsize=14)

        # Add legend
    # plt.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize='small', borderaxespad=0) 
        plt.legend(loc='upper left', fontsize=13, borderaxespad=0)

        # Add grid and adjust layout
        plt.grid(True)
        plt.subplots_adjust(right=0.75)

        # Prompt user for file name to save the plots
        root = tk.Tk()
        root.withdraw()
        save_title = simpledialog.askstring("Save Plot", "Enter the file name to save the plot (without extension):")
        if not save_title:
            print("No file name provided. Plot will not be saved.")
            return

        # Save the plot in the specified folder
        if data:
            #save_folder = r"C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\20250403_Shuksan_ANT_Light2025_WaferscaleMeasurements\Plots"
            os.makedirs(save_folder, exist_ok=True)
            save_path = os.path.join(save_folder, f"{save_title}.png")
            plt.savefig(save_path, bbox_inches='tight')
            print(f"Plot saved to {save_path}")

        # Show the plot
        plt.show()

    # # Plot Current vs Normalized Power
    # plot_line(data, 'current', 'channel2', 'Current (mA)', 'Normalized Power',
    #           "LI Curves-Ybranches - Current vs Normalized Power for Oband", "Normalized LI - Oband")
    
        ##Plot Current vs Power
    # plot_line(data, 'current', 'channel3', 'Current (mA)', 'Power (mW)',
    #          "LI Curves-DelayLines - Current vs Power for Oband", "LI - Oband-DelayLines") #for delaylines choose channel2
    plot_line(data, 'current', 'temperature','Current(A)', 'Temp(C)',
            "LI Curves-DelayLines - Current vs Power for Oband", "LI - Oband-DelayLines")#for delaylines choose channel2


if __name__ == "__main__":
    mode = ask_selection_mode()
    if mode == 'multi':
        folders = select_multiple_folders()
    elif mode == 'parent':
        parent_folder = select_parent_folder()
        folders = [parent_folder] if parent_folder else []
    else:
        folders = []

    if folders:
        data = gather_mat_data(folders)
        plot_data(data,parent_folder)
    else:
        print("No valid folders selected.")