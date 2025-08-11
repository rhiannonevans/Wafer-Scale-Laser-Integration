import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd
from pathlib import Path
import re
import ast
import scipy

from LIVclass import LIVclass

""" Class for processing multiple LIV (Power, current, voltage) files. Processes selected 'liv' files, creates the following comparison plots:
         - LI, VI, and TI curves for all devices (channel 1 - although this is changeable)
         - Threshold currents for each IDtag
         - Power at specified currents (default: 25mA and 50mA)
"""

class multi_LIV:
    def __init__(self, parent_path, selected_files=None, overwrite_existing=False):
        p = Path(parent_path)
        self.parent_path = parent_path
        self.cmap = plt.get_cmap('inferno')

        # Log selected files for debugging
        print("Debug: Selected files:", selected_files)

        selected_files = self.filter_liv(selected_files) if selected_files else None

        if not selected_files:
            # auto‑scan for every CSV under parent_path (including subfolders)
            all_files = [
                fp
                for fp in p.rglob('*.csv')
                if fp.is_file()
            ]
            # Log all files found by rglob
            print("Debug: All files found by rglob:", [str(fp) for fp in all_files])

            self.selected_files = [
                fp
                for fp in all_files
                if 'loss' not in fp.name.lower()
                and 'liv'  in fp.name.lower()
                and 'wlm' not in fp.name.lower()
            ]
        else:
            # assume selected_files is a list of basenames WITHOUT path, e.g.
            # ["2025_04_04_17_10_53_OSA_1330nm_ChipC32_R1", ...]
            # Normalize filenames for comparison
            wanted = {Path(name).stem.lower() for name in selected_files}

            # still recurse via rglob, but only keep those whose stem matches
            all_files = [
                fp
                for fp in p.rglob('*.csv')
                if fp.is_file()
            ]
            # Log all files found by rglob
            print("Debug: All files found by rglob:", [str(fp) for fp in all_files])

            self.selected_files = [
                fp
                for fp in all_files
                if fp.stem.lower() in wanted
            ]

        # Log the final list of selected files
        print("Debug: Final selected files:", [str(fp) for fp in self.selected_files])

        if not self.selected_files:
            print("No LIV files found!")
            return

        self.save_dir = p / "LIV_Comparison"
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        self.overwrite_existing = overwrite_existing

        # 2) Process each base CSV into a loss_data CSV, then load it
        self.loss_data = {}
        for csv_fp in self.selected_files:
            print(f"→ Processing base file: {csv_fp.name}")

            # sanitize_data should write out a file like "foo_loss_data.csv"
            # and return its path (as a str or Path)

            loss_path = csv_fp.with_name(csv_fp.stem + '.mat')
            if self.overwrite_existing or not loss_path.exists():
                try:
                    liv_instance = LIVclass(csv_fp, output_folder=csv_fp.parent)
                except Exception as e:
                    print(f"Error processing {csv_fp}: {e}")
                    continue
            else:
                print(f"Loss data already exists: {loss_path}. Skipping processing.")

            # read it back in
            df = self.read_mat(loss_path)
            print(df)
            print(f"Processing file: {csv_fp.name}")
            idtag = self.get_IDtag(csv_fp.name)
            print(f"Extracted ID tag: {idtag}")
            if idtag in self.loss_data:
                print(f"Warning: Duplicate ID tag detected for {idtag}. Overwriting previous data.")

            # Add metadata (vals like peak pow, threshold) from comments to the DataFrame
            #df = self._extract_and_inject_comments(df, loss_path)
            self.loss_data[idtag] = df 

            print(f"   ✓ loaded loss_data for {idtag}  ({len(df)} rows)")
        
        plt.close('all')  # Close any existing plots
        self.compPlots()
        self.plot_thresholds()
        self.plot_power_at_current()  # 25mA and 50mA
        self.plot_chip_thresholds()
        #plt.show()

    def read_mat(self, mat_file: Path) -> pd.DataFrame:
        mat = scipy.io.loadmat(mat_file)

        # Manually extract each known variable
        ch0_threshold = mat['ch0_threshold'].item()
        ch1_threshold = mat['ch1_threshold'].item()
        ch2_threshold = mat['ch2_threshold'].item()
        ch3_threshold = mat['ch3_threshold'].item()

        channel_0 = mat['channel_0'].flatten()
        channel_0_log = mat['channel_0_log'].flatten()
        channel_1 = mat['channel_1'].flatten()
        channel_1_log = mat['channel_1_log'].flatten()
        channel_2 = mat['channel_2'].flatten()
        channel_2_log = mat['channel_2_log'].flatten()
        channel_3 = mat['channel_3'].flatten()
        channel_3_log = mat['channel_3_log'].flatten()

        current = mat['current'].flatten()
        voltage = mat['voltage'].flatten()
        temperature = mat['temperature'].flatten()

        peak_power = mat['peak_power'].item()
        peak_power_I = mat['peak_power_I'].item()
        peak_power_V = mat['peak_power_V'].item()

        # Combine into DataFrame (only variables with 1D array shape can go into DataFrame columns)
        df = pd.DataFrame({
            'current': current,
            'voltage': voltage,
            'temperature': temperature,
            'channel_0': channel_0,
            'channel_0_log': channel_0_log,
            'channel_1': channel_1,
            'channel_1_log': channel_1_log,
            'channel_2': channel_2,
            'channel_2_log': channel_2_log,
            'channel_3': channel_3,
            'channel_3_log': channel_3_log,
        })

        # Add scalar values as metadata or new columns (same value repeated)
        df['ch0_threshold'] = ch0_threshold
        df['ch1_threshold'] = ch1_threshold
        df['ch2_threshold'] = ch2_threshold
        df['ch3_threshold'] = ch3_threshold
        df['peak_power'] = peak_power
        df['peak_power_I'] = peak_power_I
        df['peak_power_V'] = peak_power_V
        return df


    def filter_liv(self, selected_files = []):
        # Log the initial list of selected files
        print("Debug: Initial selected files:", selected_files)

        filtered = []
        for f in selected_files:
            # get just the filename portion
            name = os.path.basename(f)
            if 'liv' in name.lower():
                filtered.append(f)

        # Log the filtered list of files
        print("Debug: Filtered files:", filtered)
        return filtered
            
    def check_data(self):
        """Prints out the loaded IDtags and first few rows of each DataFrame."""
        print("All IDtags loaded:", list(self.loss_data.keys()))
        # To inspect the first few rows of each DataFrame in the dictionary:
        for idtag, df in self.loss_data.items():
            print(f"First rows for {idtag}:")
            print(df.head())

    def get_IDtag(self, filename: str) -> str:
        base = Path(filename).stem
        # Expanded regex to handle more variations, including '_clad' and other suffixes
        matchR = re.search(r"Chip\w+_R\d+(_clad)?(__iter\d+)?", base)
        matchL = re.search(r"Chip\w+_L\d+(_clad)?(__iter\d+)?", base)
        matchD = re.search(r"Chip\w+_D\d+(_clad)?(__iter\d+)?", base)
        if matchR:
            id_tag = matchR.group(0)  # Retain '_clad' if present
        elif matchL:
            id_tag = matchL.group(0)  # Retain '_clad' if present
        elif matchD:
            id_tag = matchD.group(0)  # Retain '_clad' if present
        else:
            id_tag = "Unknown_ID"

        # Detailed logging for debugging
        print(f"Debug: Filename: {filename}, Base: {base}, Extracted ID Tag: {id_tag}")
        return id_tag
        
    def compPlots(self):
        """Generates comparison plots for LI, VI, and TI curves."""
        LIfig, LIax = plt.subplots(figsize=(8, 6))
        VIfig, VIax = plt.subplots(figsize=(8, 6))
        TIfig, TIax = plt.subplots(figsize=(8, 6))

        # grab all IDtags and assign each a color
        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0.2, 0.8, len(idtags)))

        # plot each device’s Current vs Channel 2 on the same plot
        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]
            LIax.plot(
                df['current'],
                df['channel_2'],
                label=idtag,
                color=color
            )
            VIax.plot(
                df['current'],
                df['voltage'],
                label=idtag,
                color=color
            )
            TIax.plot(
                df['current'],
                df['temperature'],
                label=idtag,
                color=color
            )

        LIax.set_xlabel('Current', fontsize=16)
        LIax.set_ylabel('Channel 2', fontsize=16)
        LIax.set_title('Channel 2 vs Current for all devices', fontsize=16)
        LIax.legend(fontsize=14)
        LIax.tick_params(axis='both', labelsize=14)
        LIfig.tight_layout()

        VIax.set_xlabel('Current', fontsize=16)
        VIax.set_ylabel('Voltage', fontsize=16)
        VIax.set_title('Voltage vs Current for all devices', fontsize=16)
        VIax.legend(fontsize=14)
        VIax.tick_params(axis='both', labelsize=14)
        VIfig.tight_layout()

        TIax.set_xlabel('Current', fontsize=16)
        TIax.set_ylabel('Temperature', fontsize=16)
        TIax.set_title('Temperature vs Current for all devices', fontsize=16)
        TIax.legend(fontsize=14)
        TIax.tick_params(axis='both', labelsize=14)
        TIfig.tight_layout()

        # save the figures
        LIfig.savefig(Path(self.save_dir) / 'LI_comparison.png')
        VIfig.savefig(Path(self.save_dir) / 'VI_comparison.png')
        TIfig.savefig(Path(self.save_dir) / 'TI_comparison.png')
        print("Comparison plots successfully saved as LI_comparison.png, VI_comparison.png, and TI_comparison.png")
        return 

    def plot_thresholds(self):
        """Generates a boxplot of (ch1) threshold currents for each IDtag."""
        idtags = list(self.loss_data.keys())
        threshold_list = [self.loss_data[id]['ch1_threshold'].values[0] for id in idtags]
        # Replace None values in threshold_list with np.nan
        threshold_list = [np.nan if v is None else v for v in threshold_list]
        print(threshold_list)


        

        Threshfig, Threshax = plt.subplots(figsize=(8, 6))
        Threshax.boxplot(
            threshold_list,
            notch=False,              # Show notch (median CI)
            vert=True,               # Vertical boxplot
            whis=1.5,                 # Whisker length in IQR multiples
            patch_artist=True,        # Enable fill color
            boxprops=dict(facecolor="lightblue", color="blue"),
            medianprops=dict(color="red", linewidth=2),
            whiskerprops=dict(color="black", linewidth=1.5),
            capprops=dict(color="black", linewidth=1.5),
            flierprops=dict(marker='o', color='green', markersize=6, alpha=0.5)
        )

        # positions = np.arange(1, len(idtags) + 1)
        # Threshax.set_xticks(positions)
        # Threshax.set_xticklabels(idtags, rotation=45, ha='right', fontsize=14)

        Threshax.set_xlabel('Device Channel 1', fontsize=16)
        Threshax.set_ylabel('Threshold Current (mA)', fontsize=16)
        Threshax.set_title('Threshold Currents\n(box = IQR, whiskers = ±1σ, ♦ = mean)', fontsize=16)
        Threshax.tick_params(axis='both', labelsize=14)
        Threshfig.tight_layout()

        Threshfig.savefig(Path(self.save_dir) / 'Thresholds_comparison.png')
        print("Thresholds comparison plot saved as Thresholds_comparison.png")
        return

    def plot_power_at_current(self, allowance= 0.01):

        # Generates two separate bar plots for power at 25mA and 50mA for each chip ID. Allowance is the tolerance for current matching (i.e. 24.5 ~ 25.5 for 25mA).
        idtags = list(self.loss_data.keys())
        power_25mA = []
        for idtag in idtags:
            df = self.loss_data[idtag]
            cur_mA = df['current'].astype(float)  # Convert current to mA
            power = df['channel_2'].astype(float) #Ensure to use the correct channel
            mask = np.isclose(cur_mA, 25, atol=allowance)
            if mask.any():
                power_25mA.append(power[mask].iloc[0])
            else:
                power_25mA.append(np.nan)

        fig_25, ax_25 = plt.subplots(figsize=(8, 6))
        ax_25.bar(idtags, power_25mA, color='skyblue')
        ax_25.set_xlabel('Chip ID', fontsize=16)
        ax_25.set_ylabel('Power (mW)', fontsize=16)
        ax_25.set_title('Power at 25mA for all devices', fontsize=16)
        ax_25.set_xticks(range(len(idtags)))
        ax_25.set_xticklabels(idtags, rotation=45, ha='right', fontsize=8)
        ax_25.tick_params(axis='y', labelsize=14)
        fig_25.tight_layout()
        fig_25.savefig(Path(self.save_dir) / 'Power_at_25mA.png')
        print("Power at 25mA plot saved as Power_at_25mA.png")
        

        # Power at 50mA
        power_50mA = []
        for idtag in idtags:
            df = self.loss_data[idtag]
            cur_mA = df['current'].astype(float) # Convert current to mA
            power = df['channel_1'].astype(float) #Ensure to use the correct channel
            mask = np.isclose(cur_mA, 50, atol=allowance)
            if mask.any():
                power_50mA.append(power[mask].iloc[0])
            else:
                power_50mA.append(np.nan)

        fig_50, ax_50 = plt.subplots(figsize=(8, 6))
        ax_50.bar(idtags, power_50mA, color='lightcoral')
        ax_50.set_xlabel('Chip ID', fontsize=16)
        ax_50.set_ylabel('Power (mW)', fontsize=16)
        ax_50.set_title('Power at 50mA for all devices', fontsize=16)
        ax_50.set_xticks(range(len(idtags)))
        ax_50.set_xticklabels(idtags, rotation=45, ha='right', fontsize=8)
        ax_50.tick_params(axis='y', labelsize=14)
        fig_50.tight_layout()
        fig_50.savefig(Path(self.save_dir) / 'Power_at_50mA.png')
        print("Power at 50mA plot saved as Power_at_50mA.png")

        # Power at 25mA (dBm)
        power_25mA_dBm = []
        for idtag in idtags:
            df = self.loss_data[idtag]
            cur_mA = df['current'].astype(float)  # Convert current to mA
            power_dBm = df['channel_2_log'].astype(float)  #
            mask = np.isclose(cur_mA, 25, atol=allowance)
            if mask.any():
                power_25mA_dBm.append(power_dBm[mask].iloc[0])
            else:
                power_25mA_dBm.append(np.nan)

        fig_25_dBm, ax_25_dBm = plt.subplots(figsize=(8, 6))
        ax_25_dBm.bar(idtags, power_25mA_dBm, color='skyblue')
        ax_25_dBm.set_xlabel('Chip ID', fontsize=16)
        ax_25_dBm.set_ylabel('Power (dBm)', fontsize=16)
        ax_25_dBm.set_title('Power at 25mA (dBm) for all devices', fontsize=16)
        ax_25_dBm.set_xticks(range(len(idtags)))
        ax_25_dBm.set_xticklabels(idtags, rotation=45, ha='right', fontsize=8)
        ax_25_dBm.tick_params(axis='y', labelsize=14)
        fig_25_dBm.tight_layout()
        fig_25_dBm.savefig(Path(self.save_dir) / 'Power_at_25mA_dBm.png')
        print("Power at 25mA (dBm) plot saved as Power_at_25mA_dBm.png")

        # Power at 50mA (dBm)
        power_50mA_dBm = []
        for idtag in idtags:
            df = self.loss_data[idtag]
            cur_mA = df['current'].astype(float)  # Convert current to mA
            power_dBm = df['channel_2_log'].astype(float)  # Assuming channel 2 contains dBm values
            mask = np.isclose(cur_mA, 50, atol=allowance)
            if mask.any():
                power_50mA_dBm.append(power_dBm[mask].iloc[0])
            else:
                power_50mA_dBm.append(np.nan)

        fig_50_dBm, ax_50_dBm = plt.subplots(figsize=(8, 6))
        ax_50_dBm.bar(idtags, power_50mA_dBm, color='lightcoral')
        ax_50_dBm.set_xlabel('Chip ID', fontsize=16)
        ax_50_dBm.set_ylabel('Power (dBm)', fontsize=16)
        ax_50_dBm.set_title('Power at 50mA (dBm) for all devices', fontsize=16)
        ax_50_dBm.set_xticks(range(len(idtags)))
        ax_50_dBm.set_xticklabels(idtags, rotation=45, ha='right', fontsize=8)
        ax_50_dBm.tick_params(axis='y', labelsize=14)
        fig_50_dBm.tight_layout()
        fig_50_dBm.savefig(Path(self.save_dir) / 'Power_at_50mA_dBm.png')
        print("Power at 50mA (dBm) plot saved as Power_at_50mA_dBm.png")
        return

    def plot_chip_thresholds(self):
        """Generates a simple plot of chip ID vs threshold_ch2 data."""
        idtags = list(self.loss_data.keys())
        threshold_ch2 = [
            self.loss_data[id]['ch2_threshold'].values[0]
            if 'ch2_threshold' in self.loss_data[id]
            else None
            for id in idtags
        ]

        filtered_data = [(idtag, current) for idtag, current in zip(idtags, threshold_ch2) if current is not None]
        if not filtered_data:
            print("No valid ch2_threshold data found to plot.")
            return

        idtags, ch2_threshold = zip(*filtered_data)

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.bar(idtags, ch2_threshold, color='skyblue')

        ax.set_xlabel('Chip ID', fontsize=16)
        ax.set_ylabel('Threshold Current (mA)', fontsize=16)
        ax.set_title('Chip ID vs Threshold Current for All Devices', fontsize=16)
        ax.set_xticks(range(len(idtags)))
        ax.set_xticklabels(idtags, rotation=45, ha='right', fontsize=8)
        ax.tick_params(axis='y', labelsize=14)

        fig.tight_layout()
        fig.savefig(Path(self.save_dir) / 'Chip_Thresholds_Channel2.png')
        print("Chip ID vs Threshold Current (Channel 2) plot saved as Chip_Thresholds_Channel2.png")
        return
    
if __name__ == "__main__":
    parent_path = r"C:\Users\OWNER\Desktop\liv_data"
    multi = multi_LIV(parent_path, overwrite_existing=False)
    plt.show()  # Show all plots at once

