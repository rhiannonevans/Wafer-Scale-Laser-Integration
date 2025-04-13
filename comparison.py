import os
import re
import tkinter as tk
from tkinter.filedialog import askdirectory
from tkinter.simpledialog import askstring
import numpy as np
import pandas as pd
import scipy.io as sio
import datetime
import matplotlib.pyplot as plt

class LaserComparator:
    def __init__(self, laser_df, compare_mode):
        self.laser_df = laser_df
        self.compare_mode = compare_mode

    def create_comparison_plots(self):
        figs = []

        # Peak Power
        fig1, ax1 = plt.subplots()
        valid_pp = self.laser_df.dropna(subset=['PeakPower'])
        ax1.bar(valid_pp['LaserID'].astype(str), valid_pp['PeakPower'])
        ax1.set_title("Peak Power by Laser ID")
        ax1.set_xlabel("Laser ID")
        ax1.set_ylabel("Peak Power (dBm)")
        ax1.grid(True)
        plt.xticks(rotation=45, ha='right')
        fig1.tight_layout()
        figs.append(fig1)

        # Peak Wavelength
        fig2, ax2 = plt.subplots()
        valid_wl = self.laser_df.dropna(subset=['PeakWavelength'])
        ax2.scatter(valid_wl['LaserID'].astype(str), valid_wl['PeakWavelength'], marker='o')
        ax2.set_title("Peak Wavelength by Laser ID")
        ax2.set_xlabel("Laser ID")
        ax2.set_ylabel("Peak Wavelength (nm)")
        ax2.grid(True)
        plt.xticks(rotation=45, ha='right')
        fig2.tight_layout()
        figs.append(fig2)

        # Threshold Current (only for LDC)
        if self.compare_mode == "LDC":
            fig3, ax3 = plt.subplots()
            valid_thr = self.laser_df.dropna(subset=['ThresholdCurrent'])
            ax3.bar(valid_thr['LaserID'].astype(str), valid_thr['ThresholdCurrent'])
            ax3.set_title("Threshold Current by Laser ID")
            ax3.set_xlabel("Laser ID")
            ax3.set_ylabel("Threshold Current (A)")
            ax3.grid(True)
            plt.xticks(rotation=45, ha='right')
            fig3.tight_layout()
            figs.append(fig3)

        return figs

    def save_data_and_plots(self, out_dir, out_name=None):
        if not out_name:
            out_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        mat_file_path = os.path.join(out_dir, out_name + ".mat")
        svg_file_base = os.path.join(out_dir, out_name)

        data_dict = {col: self.laser_df[col].to_numpy(object) for col in self.laser_df.columns}
        sio.savemat(mat_file_path, data_dict)
        print(f"Saved compiled data to {mat_file_path}")

        figs = self.create_comparison_plots()
        for i, fig in enumerate(figs, start=1):
            svg_file = f"{svg_file_base}_plot{i}.svg"
            fig.savefig(svg_file, format="svg", bbox_inches="tight")
            print(f"Saved plot {i} to {svg_file}")
            #plt.close(fig)
            plt.show()  # Show the plot for debugging

def compile_laser_data(parent_folder, compare_mode, output_folder=None):
    if output_folder is None:
        output_folder = parent_folder

    laser_ids, mat_paths = [], []
    peak_powers, peak_wavelengths, threshold_currs = [], [], []
    reference_lines = []

    for root, dirs, files in os.walk(parent_folder):
        mat_files = [f for f in files if f.endswith(".mat")]
        if len(mat_files) == 1:
            mat_file = mat_files[0]
            mat_path = os.path.join(root, mat_file)
            folder_name = os.path.basename(root)
            base_name = os.path.splitext(mat_file)[0]
            match = re.search(r'_([A-Za-z0-9-]+)$', base_name)
            laser_id = match.group(1) if match else folder_name
            data = sio.loadmat(mat_path, squeeze_me=True, struct_as_record=False)

            pk_power = pk_wl = thr_curr = None
            if 'peak_power' in data:
                arr = np.array(data['peak_power']).flatten()
                pk_power = float(np.max(arr)) if arr.size > 0 else None
            if 'peak_wavelength' in data:
                arr = np.array(data['peak_wavelength']).flatten()
                pk_wl = float(np.max(arr)) if arr.size > 0 else None
            if compare_mode == "LDC":
                if 'threhold_current' in data:
                    thr_curr = float(data['threhold_current'])
                elif 'threshold_current' in data:
                    thr_curr = float(data['threshold_current'])

            laser_ids.append(laser_id)
            mat_paths.append(mat_path)
            peak_powers.append(pk_power)
            peak_wavelengths.append(pk_wl)
            threshold_currs.append(thr_curr)
            reference_lines.append(f"LaserID: {laser_id}  ->  {folder_name}/{mat_file}")

    df = pd.DataFrame({
        'LaserID': laser_ids,
        'MatFilePath': mat_paths,
        'PeakPower': peak_powers,
        'PeakWavelength': peak_wavelengths,
        'ThresholdCurrent': threshold_currs
    })

    ref_file = os.path.join(output_folder, f"LaserID_reference_{compare_mode}.txt")
    with open(ref_file, 'w') as f:
        f.write(f"Laser ID to file map for {compare_mode} mode:\n\n")
        f.write("\n".join(reference_lines))
    print(f"Saved reference map to {ref_file}")

    print(df)

    return df

def main():
    root = tk.Tk()
    root.withdraw()
    try:
        folder_path = askdirectory(title="Select Folder with Processed Subfolders")
        if not folder_path:
            print("No folder selected. Exiting.")
            return

        comparison_choice = askstring("Comparison Type",
                                      "What data do you want to compare?\n(1) OSA\n(2) LDC\nEnter 1 or 2:")
        if not comparison_choice:
            print("No comparison choice made. Exiting.")
            return

        compare_mode = "OSA" if comparison_choice.strip() == '1' else "LDC"
        compiled_df = compile_laser_data(folder_path, compare_mode)
        comparator = LaserComparator(compiled_df, compare_mode)

        out_name = askstring("Output Name (Optional)",
                             "Enter name for .mat/.svg output, or leave blank for auto-naming:")
        comparator.save_data_and_plots(folder_path, out_name)

    finally:
        root.destroy()

if __name__ == "__main__":
    main()