import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

from WLMclass import WLMclass

""" Class for processing multiple Wavelength Meter (WLM) files. Processes selected 'wlm' files, creates the following comparison plots:
         - Current vs Wavelength for all devices
         - Voltage vs Current for all devices
"""

class multi_WLM:
    def __init__(self, parent_path, selected_files=None, overwrite_existing=False):
        p = Path(parent_path)
        self.parent_path = parent_path
        self.cmap = plt.get_cmap('inferno')

        selected_files = self.filter_wlm(selected_files) if selected_files else None

        if not selected_files:
            # auto‑scan for every CSV under parent_path (including subfolders)
            self.selected_files = [
                fp
                for fp in p.rglob('*.csv')
                if fp.is_file()
                and 'loss' not in fp.name.lower()
                and 'wlm'  in fp.name.lower()
            ]
        else:
            # assume selected_files is a list of basenames WITHOUT path, e.g.
            # ["2025_04_04_17_10_53_OSA_1330nm_ChipC32_R1", ...]
            wanted = {name.lower() for name in selected_files}

            # still recurse via rglob, but only keep those whose stem is in wanted
            self.selected_files = [
                fp
                for fp in p.rglob('*.csv')
                if fp.is_file() and fp.stem.lower() in wanted
            ]

        if not self.selected_files:
            print("No WLM files found!")
            return
        
        self.save_dir = p / "WLM_Comparison"
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
                    wlm_instance = WLMclass(csv_fp, output_folder=csv_fp.parent)
                except Exception as e:
                    print(f"Error processing {csv_fp}: {e}")
                    continue
            else:
                print(f"Loss data already exists: {loss_path}. Skipping processing.")

            # read it back in
            df = pd.read_csv(loss_path)
            idtag = self.get_IDtag(csv_fp.name)

            self.loss_data[idtag] = df
            print(f"   ✓ loaded loss_data for {idtag}  ({len(df)} rows)")
        #self.check_data()
        plt.close('all')  # Close any existing plots
        self.plot_wl_v_I()
        self.plot_voltage_vs_current()
        #plt.show()

    def filter_wlm(self, selected_files = []):
        filtered = []
        for f in selected_files:
            # get just the filename portion
            name = os.path.basename(f)
            if 'wlm' in name.lower():
                filtered.append(f)
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
        if "Chip" in base:
            return base[base.index("Chip"):]
        else:
            return "Unknown_ID"
        
    def plot_voltage_vs_current(self):
        """Plot voltage vs current for all devices"""
        
        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0.2, 0.9, len(idtags)))  # Use visible range of inferno

        VIfig, VIax = plt.subplots(figsize=(8, 6))

        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]
            
            # Convert current to mA and filter for >= 25mA
            cur_A = df['current'].astype(float)
            cur_mA = cur_A * 1000               # now in mA
            voltage = df['voltage'].astype(float)
            
            # Filter for current >= 25mA
            mask = cur_mA >= 25.0
            filtered_current = cur_mA[mask]
            filtered_voltage = voltage[mask]
            
            VIax.plot(
                filtered_current,
                filtered_voltage,
                label=idtag,
                color=color,
                linewidth=2
            )

        VIax.set_xlabel('Current (mA)')
        VIax.set_ylabel('Voltage (V)')
        VIax.set_title('Voltage vs Current for all devices')
        VIax.legend(title='ID Tag')
        VIax.grid(True, alpha=0.3)
        VIax.set_xlim(left=25)  # Start x-axis from 25mA
        VIfig.tight_layout()

        out_path = Path(self.save_dir) / 'Voltage_vs_Current.png'
        VIfig.savefig(out_path)
        print(f"Saved plot to {out_path}")
        return
        
    def plot_wl_v_I(self):
        """Plot wavelength vs current for all devices"""
        
        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0.2, 0.9, len(idtags)))  # Use visible range of inferno

        WIfig, WIax = plt.subplots(figsize=(8, 6))

        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]

            # Convert current to mA and filter for >= 25mA
            cur_A = df['current'].astype(float)
            cur_mA = cur_A * 1000               # now in mA
            wl = df['wavelength'].astype(float)
            
            # Filter for current >= 25mA
            mask = cur_mA >= 25.0
            filtered_current = cur_mA[mask]
            filtered_wavelength = wl[mask]

            WIax.plot(
                filtered_current,
                filtered_wavelength,
                color=color,
                label=idtag,
                linewidth=2
            )

        WIax.set_xlabel('Current (mA)')
        WIax.set_ylabel('Wavelength (nm)')
        WIax.set_title('Wavelength vs Current for all devices')
        WIax.legend(title='ID Tag')
        WIax.grid(True, alpha=0.3)
        WIax.set_xlim(left=25)  # Start x-axis from 25mA
        WIfig.tight_layout()

        out_path = Path(self.save_dir) / 'Wavelength_vs_Current.png'
        WIfig.savefig(out_path)
        print(f"Saved plot to {out_path}")
        return

        
if __name__ == "__main__":
    parent_path = r"C:\Users\OWNER\Desktop\LIV_0604\LIV"
    multi = multi_WLM(parent_path, overwrite_existing=False)
    plt.show()  # Show all plots at once
