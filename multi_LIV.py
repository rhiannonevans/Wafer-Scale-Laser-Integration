import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd
from pathlib import Path
import re

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

            loss_path = csv_fp.with_name(csv_fp.stem + '_loss_data.csv')
            if self.overwrite_existing or not loss_path.exists():
                try:
                    liv_instance = LIVclass(csv_fp, output_folder=csv_fp.parent)
                except Exception as e:
                    print(f"Error processing {csv_fp}: {e}")
                    continue
            else:
                print(f"Loss data already exists: {loss_path}. Skipping processing.")

            # read it back in
            df = pd.read_csv(loss_path)
            print(f"Processing file: {csv_fp.name}")
            idtag = self.get_IDtag(csv_fp.name)
            print(f"Extracted ID tag: {idtag}")
            if idtag in self.loss_data:
                print(f"Warning: Duplicate ID tag detected for {idtag}. Overwriting previous data.")

            self.loss_data[idtag] = df
            print(f"   ✓ loaded loss_data for {idtag}  ({len(df)} rows)")
        
        plt.close('all')  # Close any existing plots


        self.compPlots()
        self.plot_thresholds()
        self.plot_power_at_current(currents=[0.025, 0.050])  # 25mA and 50mA
        self.plot_chip_thresholds()
        #plt.show()

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
        match = re.search(r"Chip\w+_R\d+", base)
        if match:
            id_tag = match.group(0)
        else:
            # Attempt to extract ID even if '_clad' or other suffixes are present
            match_clad = re.search(r"Chip\w+_R\d+(_clad)?", base)
            if match_clad:
                id_tag = match_clad.group(0).replace("_clad", "")
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
            #thresh[idtag] = df['threshold_ch1'].values[0] 
            # assume your loss_data DataFrame has columns 'current' and 'channel 2'
            LIax.plot(
                df['current'],
                df['channel 2'],
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

        LIax.set_xlabel('Current')
        LIax.set_ylabel('Channel 2')
        LIax.set_title('Channel 2 vs Current for all devices')
        LIax.legend(title='ID Tag')
        LIfig.tight_layout()

        VIax.set_xlabel('Current')
        VIax.set_ylabel('Voltage')
        VIax.set_title('Voltage vs Current for all devices')
        VIax.legend(title='ID Tag')
        VIfig.tight_layout()

        TIax.set_xlabel('Current')
        TIax.set_ylabel('Temperature')
        TIax.set_title('Temperature vs Current for all devices')
        TIax.legend(title='ID Tag')
        TIfig.tight_layout()

        #save the figures
        LIfig.savefig(Path(self.save_dir) / 'LI_comparison.png')
        VIfig.savefig(Path(self.save_dir) / 'VI_comparison.png')
        TIfig.savefig(Path(self.save_dir) / 'TI_comparison.png')
        print("Comparison plots successfully saved as LI_comparison.png, VI_comparison.png, and TI_comparison.png")
        return 
    
    def plot_thresholds(self):
        """Generates a boxplot of threshold currents for each IDtag."""

        # grab all IDtags and assign each a color
        idtags = list(self.loss_data.keys())
        #colors = self.cmap(np.linspace(0, 1, len(idtags)))

        threshold_lists = [self.loss_data[id]['threshold_ch1'].values
                    for id in idtags]

        stats = []
        for arr in threshold_lists:
            arr = np.asarray(arr)
            m   = arr.mean()
            σ   = arr.std()
            stats.append({
                'med':    np.median(arr),
                'q1':     np.percentile(arr, 25),
                'q3':     np.percentile(arr, 75),
                'whislo': m - σ,
                'whishi': m + σ,
                'fliers': [],
                'mean':   m
            })

        # Plot
        Threshfig, Threshax = plt.subplots(figsize=(8,6))
        Threshax.bxp(
            stats,
            showmeans=True,
            meanprops=dict(marker='D', markerfacecolor='orange', markeredgecolor='black')
        )

        # Now set the x‑axis ticks and labels
        positions = np.arange(1, len(idtags) + 1)
        Threshax.set_xticks(positions)
        Threshax.set_xticklabels(idtags, rotation=45, ha='right')

        Threshax.set_xlabel('Chip ID')
        Threshax.set_ylabel('Threshold Current (mA)')
        Threshax.set_title('Threshold Currents\n(box = IQR, whiskers = ±1σ, ♦ = mean)')
        Threshfig.tight_layout()

        # Save the plot
        Threshfig.savefig(Path(self.save_dir) / 'Thresholds_comparison.png')
        print("Thresholds comparison plot saved as Thresholds_comparison.png")
        return

    def plot_power_at_current(self, currents=[0.025, 0.050]):
        """
        currents in A, e.g. [0.025, 0.050]. - looking at 25mA and 50mA
        Assumes self.loss_data[idtag]['current'] is in A.
        """

        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0, 1, len(idtags)))

        Powerfig, Powerax = plt.subplots(figsize=(8, 6))

        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]

            # convert to floats
            cur_A = df['current'].astype(float)
            cur_mA = cur_A * 1000               # now in mA
            power = df['channel 1'].astype(float)

            first_point = True
            for target in currents:
                # find any row within 0.1 mA of target
                mask = np.isclose(cur_mA, target, atol=0.1)
                if mask.any():
                    p = power[mask].iloc[0]
                    Powerax.scatter(
                        target,
                        p,
                        color=color,
                        label=idtag if first_point else None,
                        edgecolor='k'
                    )
                    first_point = False
                    #print(f"{idtag}: found I={target} mA → P={p:.3f}")
                else:
                    print(f"{idtag}: no I≈{target} mA (available: {np.round(cur_mA.unique(),3)[:5]} …)")

        Powerax.set_xlabel('Current (mA)')
        Powerax.set_ylabel('Power (mW)')
        Powerax.set_title('Power at Specified Currents for all devices')
        Powerax.legend(title='ID Tag')
        Powerfig.tight_layout()

        out_path = Path(self.save_dir) / 'Power_at_current.png'
        Powerfig.savefig(out_path)
        print(f"Saved plot to {out_path}")
        return
    
    def plot_chip_thresholds(self):
        """Generates a simple plot of chip ID vs threshold_ch2 data."""

        # grab all IDtags and their corresponding threshold_ch2 data
        idtags = list(self.loss_data.keys())
        threshold_ch2 = [
            self.loss_data[id]['threshold_ch2'].values[0]
            if 'threshold_ch2' in self.loss_data[id] and len(self.loss_data[id]['threshold_ch2'].values) > 0
            else None
            for id in idtags
        ]

        # Filter out None values and corresponding idtags
        filtered_data = [(idtag, current) for idtag, current in zip(idtags, threshold_ch2) if current is not None]
        if not filtered_data:
            print("No valid threshold_ch2 data found to plot.")
            return

        idtags, threshold_ch2 = zip(*filtered_data)

        # Plot
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.bar(idtags, threshold_ch2, color='skyblue')

        # Set labels and title
        ax.set_xlabel('Chip ID')
        ax.set_ylabel('Threshold Current (mA)')
        ax.set_title('Chip ID vs Threshold Current (Channel 2)')
        ax.set_xticks(range(len(idtags)))
        ax.set_xticklabels(idtags, rotation=45, ha='right')

        # Save the plot
        fig.tight_layout()
        fig.savefig(Path(self.save_dir) / 'Chip_Thresholds_Channel2.png')
        print("Chip ID vs Threshold Current (Channel 2) plot saved as Chip_Thresholds_Channel2.png")
        return
    
if __name__ == "__main__":
    parent_path = r"C:\Users\OWNER\Desktop\liv_data"
    multi = multi_LIV(parent_path, overwrite_existing=False)
    plt.show()  # Show all plots at once

