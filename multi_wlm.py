import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import re
import scipy
import glob
import ast

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

        print("Debug: Selected files (raw):", selected_files)
        # Normalize selected_files: allow a single string/Path or an iterable of strings/Paths
        if isinstance(selected_files, (str, Path)):
            # If user accidentally passed a Python-list-as-string (e.g. "['a','b']") try to parse it
            s = str(selected_files).strip()
            parsed = None
            if (s.startswith('[') or s.startswith('(')):
                try:
                    parsed = ast.literal_eval(s)
                    print("Debug: parsed selected_files string as sequence via ast.literal_eval")
                except Exception:
                    parsed = None

            if parsed is None and ',' in s:
                # Try simple comma split (handles "a, b, c" or "'a','b'")
                parts = [p.strip().strip('\"\'') for p in s.split(',') if p.strip()]
                if len(parts) > 1:
                    parsed = parts
                    print("Debug: split selected_files string on commas into list")

            if parsed is not None:
                selected_files = list(parsed)
            else:
                print("Debug: selected_files was a single string/Path — converting to one-item list")
                selected_files = [selected_files]

        selected_files = self.filter_wlm(selected_files) if selected_files else None

        if not selected_files:
            all_files = [fp for fp in p.rglob('*.csv') if fp.is_file()]
            print("Debug: All files found by rglob:", [str(fp) for fp in all_files])
            self.selected_files = [
                fp for fp in all_files
                if 'loss' not in fp.name.lower()
                and 'wlm'  in fp.name.lower()
            ]
        else:
            # If user passed explicit file paths (absolute or relative), prefer those directly
            # But DON'T treat directories as explicit files - let them fall through to rglob logic
            candidate_paths = [Path(name) for name in selected_files]
            explicit_files = [fp for fp in candidate_paths if fp.is_file() and not fp.is_dir()]
            
            # Filter out directories from explicit_files
            explicit_files = [fp for fp in explicit_files if fp.is_file()]
            
            if explicit_files and len(explicit_files) == len(selected_files):
                # ALL selections are explicit files (not mixed with folders)
                print("Debug: Using explicit selected file paths:", [str(fp) for fp in explicit_files])
                # Apply same name-based filtering as the rglob branch (but remove 'wlm' requirement)
                self.selected_files = [
                    fp for fp in explicit_files
                    if 'loss' not in fp.name.lower()
                ]
            else:
                # Fall back to searching within parent_path for stems/folder names matching requested names
                # Wanted may be stems, folder names, or partial names. Match against CSV stem
                # and the CSV's parent directory name so selections of folder names work.
                wanted = {Path(name).stem.lower() for name in selected_files}
                all_files = [fp for fp in p.rglob('*.csv') if fp.is_file()]
                print("Debug: All files found by rglob:", [str(fp) for fp in all_files])
                def matches_wanted(fp):
                    stem = fp.stem.lower()
                    parent = fp.parent.name.lower()
                    pathstr = str(fp).lower()
                    
                    # Check all ancestor folder names in the path
                    ancestor_names = [part.lower() for part in fp.parts]
                    
                    if stem in wanted or parent in wanted:
                        return True
                    # Check if any ancestor folder name matches
                    if any(name in wanted for name in ancestor_names):
                        return True
                    # allow partial matching if user provided a shorter identifier
                    for w in wanted:
                        if w and w in pathstr:
                            return True
                    return False

                self.selected_files = [fp for fp in all_files if matches_wanted(fp)]

        print("Debug: Final selected files:", [str(fp) for fp in self.selected_files])
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
            base_idtag = self.get_IDtag(csv_fp.name)
            
            # Always try to extract datetime from filename
            datetime_match = re.search(r'(\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2})', csv_fp.name)
            
            # If this ID tag already exists, append datetime to make it unique
            if base_idtag in self.loss_data:
                print(f"   ⚠ Duplicate ID detected: {base_idtag}")
                if datetime_match:
                    datetime_str = datetime_match.group(1)
                    idtag = f"{base_idtag}_{datetime_str}"
                    print(f"   → Renamed to: {idtag}")
                else:
                    # Fallback: use entire stem if no datetime found
                    idtag = csv_fp.stem
                    print(f"   → Renamed to: {idtag}")
            else:
                # First occurrence - check if we have datetime in filename
                # If yes, append it to be consistent (optional but cleaner)
                if datetime_match:
                    datetime_str = datetime_match.group(1)
                    idtag = f"{base_idtag}_{datetime_str}"
                else:
                    idtag = base_idtag

            self.loss_data[idtag] = df
            print(f"   ✓ loaded loss_data for {idtag}  ({len(df)} rows)")
        
        # Print summary of loaded data
        print(f"\n{'='*60}")
        print(f"SUMMARY: Loaded {len(self.loss_data)} unique devices:")
        for idtag in self.loss_data.keys():
            print(f"  - {idtag}")
        print(f"{'='*60}\n")
        
        #self.check_data()
        plt.close('all')  # Close any existing plots
        # Ensure voltage-vs-current plot is created
        try:
            self.plot_voltage_vs_current()
        except Exception as e:
            print(f"Warning: plot_voltage_vs_current() failed: {e}")
        
        # Only plot wavelength if at least one file has wavelength data
        has_any_wavelength = any(
            df.attrs.get('has_wavelength', False) for df in self.loss_data.values()
        )
        if has_any_wavelength:
            try:
                self.plot_wl_v_I()
            except Exception as e:
                print(f"Warning: plot_wl_v_I() failed: {e}")
        else:
            print("Info: Skipping wavelength plots - no wavelength data found in any files")

        try:
            self.plot_power_at_current()
        except Exception as e:
            print(f"Warning: plot_power_at_current() failed: {e}")
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
        
        # Check if voltage and temperature are swapped (voltage > 20 indicates it's actually temperature)
        if np.any(voltage > 20):
            print(f"Info: Detected swapped voltage/temperature in {mat_file.name} - swapping them back")
            voltage, temperature = temperature, voltage
        
        # Wavelength is optional - may not be present in all files
        wavelength = None
        has_wavelength = False
        if 'wavelength' in mat:
            try:
                wavelength = mat['wavelength'].flatten()
                has_wavelength = True
            except Exception as e:
                print(f"Warning: Could not extract wavelength from {mat_file}: {e}")
                wavelength = np.full_like(current, np.nan)
        else:
            print(f"Info: No wavelength data found in {mat_file}")
            wavelength = np.full_like(current, np.nan)

        peak_power = mat['peak_power'].item()
        peak_power_I = mat['peak_power_I'].item()
        peak_power_V = mat['peak_power_V'].item()
        
        # peak_power_wl is optional
        peak_power_wl = None
        if 'peak_power_wl' in mat:
            try:
                peak_power_wl = mat['peak_power_wl'].item()
            except Exception:
                peak_power_wl = np.nan
        else:
            peak_power_wl = np.nan

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
        # Store has_wavelength as an attribute, not a column
        df.attrs['has_wavelength'] = has_wavelength
        return df

    def filter_wlm(self, selected_files = []):
        # Log the initial list of selected files
        print("Debug: Initial selected files:", selected_files)
        filtered = []
        for entry in selected_files:
            entry_str = str(entry)
            # Expand glob patterns
            if any(ch in entry_str for ch in ('*', '?', '[')):
                matches = glob.glob(entry_str, recursive=True)
                for m in matches:
                    if os.path.isfile(m):
                        filtered.append(Path(m))
                continue

            p = Path(entry)
            # If it's an explicit file, accept it
            if p.is_file():
                filtered.append(p)
                continue

            # If it's a directory, collect CSVs inside
            if p.is_dir():
                for m in p.rglob('*.csv'):
                    filtered.append(m)
                continue

            # Otherwise assume it's a filename stem or pattern to match later
            # Keep as string for downstream stem-matching fallback
            filtered.append(entry_str)

        # Apply basic name-based filtering for explicit files (remove 'wlm' requirement)
        explicit_files = [f for f in filtered if isinstance(f, Path)]
        final = []
        for f in explicit_files:
            if 'loss' not in f.name.lower():
                final.append(f)

        # Also include any non-file stems to be used by the fallback logic
        non_files = [f for f in filtered if not isinstance(f, Path)]
        final.extend(non_files)

        print("Debug: Filtered files (expanded):", [str(f) for f in final])
        return final
    
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
        Ch3fig, Ch3ax = plt.subplots(figsize=(8, 6))

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
                df['current'],
                df['temperature'],
                label=idtag,
                color=color
            )
            Ch3ax.plot(
                df['current'],
                df['channel_3'],
                label=idtag,
                color=color
            )

        LIax.set_xlabel('Current')
        LIax.set_ylabel('Channel 1')
        LIax.set_title('Channel 1 vs Current for all devices')
        # Put legend inside if 10 or fewer devices, otherwise outside
        if len(idtags) <= 10:
            LIax.legend(title='ID Tag', loc='best')
        else:
            LIax.legend(title='ID Tag', bbox_to_anchor=(1.05, 1), loc='upper left')
        LIfig.tight_layout()

        VIax.set_xlabel('Current')
        VIax.set_ylabel('Voltage')
        VIax.set_title('Voltage vs Current for all devices')
        if len(idtags) <= 10:
            VIax.legend(title='ID Tag', loc='best')
        else:
            VIax.legend(title='ID Tag', bbox_to_anchor=(1.05, 1), loc='upper left')
        VIfig.tight_layout()

        TIax.set_xlabel('Current')
        TIax.set_ylabel('Temperature')
        TIax.set_title('Temperature vs Current for all devices')
        if len(idtags) <= 10:
            TIax.legend(title='ID Tag', loc='best')
        else:
            TIax.legend(title='ID Tag', bbox_to_anchor=(1.05, 1), loc='upper left')
        TIfig.tight_layout()

        Ch3ax.set_xlabel('Current')
        Ch3ax.set_ylabel('Channel 3 Power (mW)')
        Ch3ax.set_title('Channel 3 vs Current for all devices')
        if len(idtags) <= 10:
            Ch3ax.legend(title='ID Tag', loc='best')
        else:
            Ch3ax.legend(title='ID Tag', bbox_to_anchor=(1.05, 1), loc='upper left')
        Ch3fig.tight_layout()

        #save the figures
        LIfig.savefig(Path(self.save_dir) / 'LI_comparison.png')
        VIfig.savefig(Path(self.save_dir) / 'VI_comparison.png')
        TIfig.savefig(Path(self.save_dir) / 'TI_comparison.png')
        Ch3fig.savefig(Path(self.save_dir) / 'Ch3_comparison.png')
        print("Comparison plots successfully saved as LI_comparison.png, VI_comparison.png, TI_comparison.png, and Ch3_comparison.png")
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

        plotted_any = False
        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]
            print(df.columns)

            # Check if this file has valid wavelength data
            has_wl = df.attrs.get('has_wavelength', False)
            if not has_wl:
                print(f"Info: Skipping {idtag} - no wavelength data")
                continue
            
            # Check if wavelength column exists and has non-NaN values
            if 'wavelength' not in df.columns:
                print(f"Info: Skipping {idtag} - wavelength column missing")
                continue
            
            wl = df['wavelength'].astype(float)
            if wl.isna().all():
                print(f"Info: Skipping {idtag} - all wavelength values are NaN")
                continue

            # Convert current to mA and filter for >= 25mA
            cur_A = df['current'].astype(float)
            cur_mA = cur_A * 1000               # now in mA
            
            # Filter for current >= 25mA
            mask = cur_mA >= 25.0
            filtered_current = cur_mA[mask]
            filtered_wavelength = wl[mask]

            if len(filtered_current) > 0 and not filtered_wavelength.isna().all():
                WIax.plot(
                    filtered_current,
                    filtered_wavelength,
                    color=color,
                    label=idtag,
                    linewidth=2
                )
                plotted_any = True

        if not plotted_any:
            print("Warning: No valid wavelength data to plot")
            plt.close(WIfig)
            return

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
