import os
import tkinter as tk
from tkinter import filedialog, simpledialog
import scipy.io
import matplotlib.pyplot as plt
import matplotlib.cm as cm

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
                    data.append((mat_data, file))
    return data

def plot_scatter(data, x_key, y_key, x_label, y_label, title, save_title):
        
        colormap = cm.get_cmap('inferno')
        plt.figure()
        num_files = len(data)
        for i, (mat_data, filename) in enumerate(data):
            if x_key in mat_data and y_key in mat_data:
                x_data = mat_data[x_key].flatten()
                y_data = mat_data[y_key].flatten()
                color = colormap(0.2 + 0.6 * (i / max(num_files - 1, 1)))  # Avoid the lightest colors

                # Extract label after "OSA_", fallback to filename without extension
                if "OSA_" in filename:
                    label = filename.split("OSA_")[-1].replace('.mat', '')
                else:
                    label = os.path.splitext(filename)[0]  # Use filename without extension
                
                plt.scatter(x_data, y_data, color=color, label=label)
            else:
                print(f"{filename} missing '{x_key}' or '{y_key}'")

        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.title(title)
        plt.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize='small', borderaxespad=0)
        plt.grid(True)
        plt.subplots_adjust(right=0.75)

        # Save the plot
        plot_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")], title=f"Save {save_title} Plot")
        if plot_path:
            plt.savefig(plot_path, bbox_inches='tight')
        plt.show()  # Show the plot after saving


def plot_scatter2(data1, data2, x_label, y_label, title, save_title, parent_path = None):
        plt.figure()
        plt.scatter(data1, data2, cmap=cm.get_cmap('inferno'), alpha=0.7, edgecolors='none', s=50)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.title(title)
        plt.grid(True)

        if parent_path:
            png_path = os.path.join(parent_path, f"{save_title}.png")
            svg_path = os.path.join(parent_path, f"{save_title}.svg")
            plt.savefig(png_path, bbox_inches='tight')
            plt.savefig(svg_path, bbox_inches='tight')
        else:
            print("Error: parent_path is None. Cannot save the plot.")
        plt.show()
        


def plot_data(data, newVer = False, parent_path = None):
    
    # Plot Current vs Peak Wavelength
    plot_scatter(data, 'current_mA', 'peak_wavelength', 'Current (mA)', 'Peak Wavelength (nm)', 
                "Overlay Plot of Current vs Peak Wavelength", "Current vs Peak Wavelength")

    # Plot Current vs Peak Power
    plot_scatter(data, 'current_mA', 'peak_power', 'Current (mA)', 'Peak Power (mW)', 
                "Overlay Plot of Current vs Peak Power", "Current vs Peak Power")

    # Plot Current vs Peak Power (Single Point per File)
    def plot_single_point(data, x_key, y_key, x_label, y_label, title, save_title):
        plt.figure()
        x_values = []
        y_values = []
        labels = []

        for mat_data, filename in data:
            if x_key in mat_data and y_key in mat_data:
                x_data = mat_data[x_key].flatten()
                y_data = mat_data[y_key].flatten()
                if len(x_data) > 0 and len(y_data) > 0:
                    x_values.append(x_data[0])  # Take the first data point
                    y_values.append(y_data[0])  # Take the first data point
                    if "OSA_" in filename:
                        labels.append(filename.split("OSA_")[-1].replace('.mat', ''))
                    else:
                        labels.append(os.path.splitext(filename)[0])  # Use filename without extension

        plt.scatter(x_values, y_values, color='blue', label='Data Points')
        for i, label in enumerate(labels):
            plt.annotate(label, (x_values[i], y_values[i]), fontsize=8, alpha=0.7)

        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.title(title)
        plt.grid(True)

        # Save the plot
        plot_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")], title=f"Save {save_title} Plot")
        if newVer:
            plot_path1 = os.path.join(os.path.dirname(parent_path), f"compPlot1.png")
            plot_path2 = os.path.join(os.path.dirname(parent_path), f"compPlot2.png")
        elif plot_path:
            plt.savefig(plot_path, bbox_inches='tight')
            plt.show()  # Show the plot after saving

    plot_single_point(data, 'current_mA', 'peak_power', 'Current (mA)', 'Peak Power (mW)', 
                      "Single Point Plot of Current vs Peak Power", "Single Point Current vs Peak Power")
    


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
        plot_data(data)
    else:
        print("No valid folders selected.")