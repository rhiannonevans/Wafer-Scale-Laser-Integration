import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import re
import scipy

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

            loss_path = csv_fp.with_name(csv_fp.stem + '.mat')
            if self.overwrite_existing or not loss_path.exists():
                try:
                    wlm_instance = WLMclass(csv_fp, output_folder=csv_fp.parent)
                except Exception as e:
                    print(f"Error processing {csv_fp}: {e}")
                    continue
            else:
                print(f"Loss data already exists: {loss_path}. Skipping processing.")

            # read it back in
            df = self.read_mat(loss_path.with_suffix('.mat'))
            idtag = self.get_IDtag(csv_fp.name)

            self.loss_data[idtag] = df
            print(f"   ✓ loaded loss_data for {idtag}  ({len(df)} rows)")
        #self.check_data()
        plt.close('all')  # Close any existing plots
        self.plot_wl_v_I()

        self.plot_power_at_current()  
        #plt.show()

    def read_mat(self, mat_file: Path) -> pd.DataFrame:
        mat = scipy.io.loadmat(mat_file)

        # Manually extract each known variable
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
        wavelength = mat['wavelength'].flatten()

        peak_power = mat['peak_power'].item()
        peak_power_I = mat['peak_power_I'].item()
        peak_power_V = mat['peak_power_V'].item()
        peak_power_wl = mat['peak_power_wl'].item()

        # Combine into DataFrame (only variables with 1D array shape can go into DataFrame columns)
        df = pd.DataFrame({
            'current': current,
            'voltage': voltage,
            'temperature': temperature,
            'wavelength': wavelength,
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
        df['peak_power'] = peak_power
        df['peak_power_I'] = peak_power_I
        df['peak_power_V'] = peak_power_V
        df['peak_power_wl'] = peak_power_wl
        return df

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
        matchR = re.search(r"Chip\w+_R\d+(_clad)?", base)
        matchL = re.search(r"Chip\w+_L\d+(_clad)?", base)
        matchD = re.search(r"Chip\w+_D\d+(_clad)?", base)
        if matchR:
            id_tag = matchR.group(0)  # Retain '_clad' if present
        elif matchL:
            id_tag = matchL.group(0)  # Retain '_clad' if present
        elif matchD:
            id_tag = matchD.group(0)  # Retain '_clad' if present
        else:
            id_tag = "Unknown_ID"

        return id_tag
        
    def plot_voltage_vs_current(self):
        """Plot voltage vs current for all devices"""
        
        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0.2, 0.9, len(idtags)))  # Use visible range of inferno

        VIfig, VIax = plt.subplots(figsize=(8, 6))
        TIfig, TIax = plt.subplots(figsize=(8, 6))
        LIfig, LIax = plt.subplots(figsize=(8, 6))

        # grab all IDtags and assign each a color
        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0, 1, len(idtags)))

        # plot each device’s Current vs Channel 1 on the same plot
        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]
            # assume your loss_data DataFrame has columns 'current' and 'channel 1'
            LIax.plot(
                df['current'],
                df['channel_1'],
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
                df['temperature'],
                df['voltage'],
                label=idtag,
                color=color
            )

        LIax.set_xlabel('Current')
        LIax.set_ylabel('Channel 1')
        LIax.set_title('Channel 1 vs Current for all devices')
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
    
    def plot_power_at_current(self, allowance=0.5, currents=None):
        """
        currents in mA, e.g. [25, 50]. - looking at 25mA and 50mA
        Assumes self.loss_data[idtag]['current'] is in mA.
        """
        if currents is None:
            currents = [25, 50]

        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0, 1, len(idtags)))

        Powerfig, Powerax = plt.subplots(figsize=(8, 6))
        VIfig, VIax = plt.subplots(figsize=(8, 6))


        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]
            
            # Convert current to mA and filter for >= 25mA
            cur_A = df['current'].astype(float)
            cur_mA = cur_A * 1000               # now in mA
            voltage = df['voltage'].astype(float)
            power = df['channel_1'].astype(float)  # Ensure to use the correct channel
            
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

            first_point = True
            for target in currents:
                # find any row within 0.1 mA of target
                mask = np.isclose(cur_mA, target, atol=allowance)
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
                    print(f"{idtag}: no I≈{target} mA (available: {np.round(cur_mA.unique(),3)} …)")
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
            print(df.columns)

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
