
from OSAclass import OSAclass
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import io
import numpy as np
import os

""" Class for processing multiple OSA (Optical Spectrum Analyzer) files. Processes selected 'osa' files, creates the following comparison plots:
         - Peak Power vs Current for all devices
         - Wavelength at peak power vs Current for all devices
"""

class multi_OSA:
    def __init__(self, parent_path, selected_files=None, overwrite_existing=False):
        p = Path(parent_path)
        self.parent_path = parent_path
        self.cmap = plt.get_cmap('inferno')
        

        selected_files = self.filter_osa(selected_files) if selected_files else None

        if not selected_files:
            # auto‑scan for every CSV under parent_path (including subfolders)
            self.selected_files = [
                fp
                for fp in p.rglob('*.csv')
                if fp.is_file()
                and 'loss' not in fp.name.lower()
                and 'osa'  in fp.name.lower()
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
            print("No OSA files found!")
            return

        self.save_dir = p / "OSA_Comparison"
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
        self.overwrite_existing = overwrite_existing

        # 2) Process each base CSV into a loss_data CSV, then load it
        self.loss_data = {}
        self.metadata = {}
        for csv_fp in self.selected_files:
            print(f"→ Processing base file: {csv_fp.name}")

            # sanitize_data should write out a file like "foo_loss_data.csv"
            # and return its path (as a str or Path)

            loss_path = csv_fp.with_name(csv_fp.stem + '_loss_data.csv')
            if self.overwrite_existing or not loss_path.exists():
                try:
                    osa_instance = OSAclass(csv_fp)
                except Exception as e:
                    print(f"Error processing {csv_fp}: {e}")
                    continue
            else:
                print(f"Loss data already exists: {loss_path}. Skipping processing.")
                # read data from previously processed csv
            
            meta, df = self.read_data(loss_path)

            idtag = self.get_IDtag(csv_fp.name)

            self.loss_data[idtag] = df
            self.metadata[idtag] = meta
            print(f"   ✓ loaded loss_data for {idtag}  ({len(df)} rows)")

        plt.close('all')  # Close all plots to free up memory
        self.plot_peak_pow_v_I()
        self.plot_peak_wl_v_I()

    def filter_osa(self, selected_files = []):
        filtered = []
        for f in selected_files:
            # get just the filename portion
            name = os.path.basename(f)
            if 'osa' in name.lower():
                filtered.append(f)
        return filtered
        
    def read_data(self, data_file):
        # 1) Read all lines
        with open(data_file, 'r') as f:
            lines = f.readlines()

        # read metadata
        meta = {}
        for line in lines:
            if not line.startswith("#"):
                break
            key, val_str = line[1:].split(":", 1)
            val_str = val_str.strip()

            if val_str.startswith("[") and val_str.endswith("]"):
                # strip brackets and parse space‐sep floats
                arr = np.fromstring(val_str.strip("[]"), sep=" ")
                meta[key.strip()] = arr
            else:
                # scalar float
                meta[key.strip()] = float(val_str)

        # 3) Load the actual table
        data_io = io.StringIO("".join(l for l in lines if not l.startswith("#")))
        df = pd.read_csv(data_io, index_col=0)
        return meta, df

    def check_data(self):
        """Prints out the loaded IDtags and first few rows of each DataFrame."""
        print("All IDtags loaded:", list(self.loss_data.keys()))
        # To inspect the first few rows of each DataFrame in the dictionary:
        for idtag, df in self.loss_data.items():
            print(f"Metadata for {idtag}:")
            print(self.metadata[idtag])
            print(f"First rows for {idtag}:")
            print(df.head())
        print(self.loss_data.items())

    def get_IDtag(self, filename: str) -> str:
        base = Path(filename).stem
        if "Chip" in base:
            return base[base.index("Chip"):]
        else:
            return "Unknown_ID"
        
    def plot_peak_pow_v_I(self):
        
        """Plots the peak power vs current for each IDtag."""

        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0, 1, len(idtags)))

        plt.figure(figsize=(10, 6))
        for idtag, df in self.loss_data.items():
            plt.plot(df['Current (mA)'], df['Peak Power (dBm)'], label=idtag, color=colors[idtags.index(idtag)])


        
        plt.xlabel('Current (mA)')
        plt.ylabel('Peak Power (dBm)')
        plt.title('Peak Power vs Current')
        plt.legend()
        plt.grid()
        plt.savefig(Path(self.save_dir) / 'Peak_Power_vs_Current.png', bbox_inches='tight')

    def plot_peak_wl_v_I(self):

        """Plots the wavelength at peak power vs current for each IDtag."""

        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0, 1, len(idtags)))

        plt.figure(figsize=(10, 6))
        for idtag, df in self.loss_data.items():
            plt.plot(df['Current (mA)'], df['Peak Wavelength (nm)'], label=idtag, color=colors[idtags.index(idtag)])


        
        plt.xlabel('Current (mA)')
        plt.ylabel('Peak Wavelength (nm)')
        plt.title('Peak Wavelength vs Current')
        plt.legend()
        plt.grid()
        plt.savefig(Path(self.save_dir) / 'Peak_Wavelength_vs_Current.png', bbox_inches='tight')


if __name__ == "__main__":
    parent_path = r"C:\Users\OWNER\Desktop\osa_data"
    multi = multi_OSA(parent_path, overwrite_existing=False)

    plt.show()