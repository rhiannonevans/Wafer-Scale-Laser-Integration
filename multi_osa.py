import os
import io
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import scipy.io
import glob
import ast
from OSAclass import OSAclass

""" Class for processing multiple OSA (Optical Spectrum Analyzer) files. Processes selected 'osa' files, creates the following comparison plots:
         - Peak Power vs Current for all devices
         - Peak Wavelength vs Current for all devices
         - Peak Wavelength vs Current with 2nd Order Polynomial Fits
"""

class multi_OSA:
    # Font size constants - change these in one place to update all plots
    FONT_AXIS_LABEL = 25
    FONT_AXIS_TICKS = 25
    FONT_LEGEND = 22
    FONT_TITLE = 14
    FONT_ANNOTATION = 9
    
    def __init__(self, parent_path, selected_files=None, overwrite_existing=False):
        p = Path(parent_path)
        self.parent_path = parent_path
        self.cmap = plt.get_cmap('inferno')
        self.idtag_to_mat_file = {}  # Store mapping of IDtag to mat file path
        
        # Log selected files for debugging
        print("Debug: Selected files (raw):", selected_files)
        
        # Normalize selected_files: allow a single string/Path or an iterable of strings/Paths
        if isinstance(selected_files, (str, Path)):
            s = str(selected_files).strip()
            parsed = None
            if (s.startswith('[') or s.startswith('(')):
                try:
                    parsed = ast.literal_eval(s)
                    print("Debug: parsed selected_files string as sequence via ast.literal_eval")
                except Exception:
                    parsed = None

            if parsed is None and ',' in s:
                parts = [p.strip().strip('\"\'') for p in s.split(',') if p.strip()]
                if len(parts) > 1:
                    parsed = parts
                    print("Debug: split selected_files string on commas into list")

            if parsed is not None:
                selected_files = list(parsed)
            else:
                print("Debug: selected_files was a single string/Path — converting to one-item list")
                selected_files = [selected_files]
        
        # Filter selected files to only include OSA files
        selected_files = self.filter_osa(selected_files) if selected_files else None
        
        if not selected_files:
            # Auto-scan for every OSA CSV under parent_path (including subfolders)
            all_files = [
                fp
                for fp in p.rglob('*.csv')
                if fp.is_file()
            ]
            print("Debug: All files found by rglob:", [str(fp) for fp in all_files])
            
            # Filter for raw OSA files (excluding loss_data files)
            raw_files = [
                fp
                for fp in all_files
                if 'loss' not in fp.name.lower() and 'osa' in fp.name.lower()
            ]
        else:
            # If user passed explicit file paths, prefer those directly
            candidate_paths = [Path(name) for name in selected_files]
            explicit_files = [fp for fp in candidate_paths if fp.is_file()]
            if explicit_files:
                print("Debug: Using explicit selected file paths:", [str(fp) for fp in explicit_files])
                raw_files = [
                    fp for fp in explicit_files
                    if 'loss' not in fp.name.lower()
                ]
            else:
                # Fall back to searching within parent_path for stems/folder names
                wanted = {Path(name).stem.lower() for name in selected_files}
                
                all_files = [
                    fp
                    for fp in p.rglob('*.csv')
                    if fp.is_file()
                ]
                
                def matches_wanted(fp):
                    stem = fp.stem.lower()
                    parent = fp.parent.name.lower()
                    pathstr = str(fp).lower()
                    if stem in wanted or parent in wanted:
                        return True
                    for w in wanted:
                        if w and w in pathstr:
                            return True
                    return False
                
                raw_files = [fp for fp in all_files if matches_wanted(fp)]
                print("Debug: Selected OSA raw files:", [str(fp) for fp in raw_files])

        print("Debug: Final selected files:", [str(fp) for fp in raw_files])
        self.raw_files = raw_files
        print(f"Found {len(raw_files)} raw files to process")

        # STEP 3: Process raw files with OSAclass if overwrite_existing is True
        if overwrite_existing:
            print("Overwrite flag is set, processing raw OSA files...")
            # Process raw files with OSAclass
            for raw_file in raw_files:
                print(f"Processing {raw_file}")
                try:
                    osa = OSAclass(str(raw_file))
                    # The OSAclass will save outputs in the same directory as the raw file
                except Exception as e:
                    print(f"Error processing {raw_file}: {e}")
        else:
            print("Skipping raw file processing (use overwrite_existing=True to reprocess)")
            
        # STEP 4: Find all the processed .mat files for comparison plots
        mat_files = []
        # First check if each raw file has a corresponding .mat file
        for raw_file in raw_files:
            # Look for a .mat file in the same directory with the same name but ending in _new.mat
            mat_name = raw_file.stem + "_new.mat"
            mat_path = raw_file.parent / mat_name
            if mat_path.exists():
                mat_files.append(mat_path)
            else:
                print(f"Warning: No matching .mat file found for {raw_file}")

        # If no .mat files were found corresponding to raw files, do a broader search
        if not mat_files:
            print("No direct matches found, searching for all _new.mat files...")
            # Search for all _new.mat files under parent_path
            mat_files = [
                fp for fp in p.rglob("*_new.mat") if fp.is_file()
            ]

        if not mat_files:
            print("No OSA .mat file found with _new.mat suffix!")
            return

        # Store the processed mat files
        self.mat_files = mat_files
        print(f"Found {len(mat_files)} processed .mat files")
        
        # Create output directory for comparison plots
        self.save_dir = Path(parent_path) / "OSA_Comparison"
        os.makedirs(self.save_dir, exist_ok=True)
        
        # Build a dictionary mapping IDtags to mat files for faster lookup
        self.build_idtag_mapping()
        
        # STEP 5: Create comparison plots
        self.create_comparison_plots()
                
    def filter_osa(self, selected_files):
        """Filter and expand selected files - globs, directories, explicit paths"""
        if not selected_files:
            return None
        
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
            filtered.append(entry_str)

        # Apply basic name-based filtering for explicit files (remove 'osa' requirement)
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
        
    def build_idtag_mapping(self):
        """Build a dictionary mapping IDtags to mat files for faster lookup"""
        self.idtag_to_mat_file = {}
        
        for mat_file in self.mat_files:
            try:
                data = scipy.io.loadmat(str(mat_file))
                if 'IDtag' in data:
                    idtag = str(data['IDtag'][0])
                    self.idtag_to_mat_file[idtag] = mat_file
                else:
                    print(f"Warning: No IDtag found in {mat_file}")
            except Exception as e:
                print(f"Error reading {mat_file}: {e}")
        
    def create_comparison_plots(self):
        """Create all comparison plots"""
        print(f"\n--- Generating comparison plots in: {self.save_dir} ---")
        # ...existing code...
        device_data = {}
        for mat_file in self.mat_files:
            try:
                data = scipy.io.loadmat(str(mat_file))
                print(f"Keys in {mat_file}: {list(data.keys())}")
                if 'IDtag' in data:
                    idtag = str(data['IDtag'][0])
                else:
                    idtag = self.get_IDtag(mat_file.name)
                    print(f"Generated IDtag: {idtag} from filename: {mat_file.name}")
                print(f"Checking for keys: ['current_mA', 'peak_power', 'peak_wavelength']")
                if all(key in data for key in ['current_mA', 'peak_power', 'peak_wavelength']):
                    i_values = data['current_mA'].flatten()
                    peak_power = data['peak_power'].flatten()
                    peak_wl = data['peak_wavelength'].flatten()
                    linewidth_3dB = None
                    if 'peak_width_3dB_pm' in data:
                        linewidth_3dB = data['peak_width_3dB_pm'].flatten()
                        print(f"Found -3dB linewidth data: {len(linewidth_3dB)} points")
                    else:
                        print(f"Warning: No -3dB linewidth data found in {mat_file}")
                    linewidth_20dB = None
                    if 'peak_width_20dB_pm' in data:
                        linewidth_20dB = data['peak_width_20dB_pm'].flatten()
                        print(f"Found -20dB linewidth data: {len(linewidth_20dB)} points")
                    else:
                        print(f"Warning: No -20dB linewidth data found in {mat_file}")
                    print(f"Found data - Current: {len(i_values)} points, Power: {len(peak_power)} points, WL: {len(peak_wl)} points")
                    device_data[idtag] = {
                        'current': i_values,
                        'peak_power': peak_power,
                        'peak_wl': peak_wl,
                        'linewidth_3dB': linewidth_3dB,
                        'linewidth_20dB': linewidth_20dB,
                        'file_path': mat_file
                    }
                    print(f"Loaded data for {idtag} ({len(i_values)} points)")
                else:
                    print(f"Warning: Missing required data keys in {mat_file}")
                    missing_keys = [key for key in ['current_mA', 'peak_power', 'peak_wavelength'] if key not in data]
                    print(f"Missing keys: {missing_keys}")
            except Exception as e:
                print(f"Error loading {mat_file}: {e}")
        print(f"Total devices loaded: {len(device_data)}")
        if len(device_data) == 0:
            print("No device data loaded - cannot generate plots")
            return
        self.plot_peak_power_vs_current(device_data)
        self.plot_peak_wl_vs_current(device_data)
        self.plot_peak_wl_vs_current_with_fit(device_data)
        self.plot_peak_power_at_25mA(device_data)
        self.plot_peak_power_at_50mA(device_data)
        self.plot_linewidth_3dB_boxplot(device_data)
        self.plot_linewidth_violin(device_data)
        self.plot_linewidth_mean_median(device_data)
        self.plot_linewidth_20dB_boxplot(device_data)
        self.plot_linewidth_20dB_violin(device_data)
        self.plot_linewidth_20dB_mean_median(device_data)
        self.save_linewidth_summary_report(device_data)
        # --- New overlay fit plot for 1310nm and 1330nm ---
        self.plot_overlay_fit_by_wavelength(device_data)

    def plot_overlay_fit_by_wavelength(self, device_data):
        """
        Overlay fit plot for 1310nm and 1330nm files:
        - 1330nm: viridis colormap (top)
        - 1310nm: inferno colormap (bottom)
        - Y-axis is broken so both groups are visually closer
        - No legends
        - Global y-axis label
        - Y-axis range reduced by 2nm from both ends
        - Both groups use solid linestyle
        """
        import matplotlib.patches as mpatches
        # Group devices by wavelength from file name
        group_1310 = []
        group_1330 = []
        for idtag, data in device_data.items():
            fname = str(data['file_path'])
            if '1330' in fname:
                group_1330.append((idtag, data))
            elif '1310' in fname:
                group_1310.append((idtag, data))
        viridis = plt.get_cmap('viridis')
        inferno = plt.get_cmap('inferno')
        n_1330 = len(group_1330)
        n_1310 = len(group_1310)
        colors_1330 = [viridis(i/n_1330) for i in range(n_1330)] if n_1330 else []
        colors_1310 = [inferno(i/n_1310) for i in range(n_1310)] if n_1310 else []
        # Broken axis: 1330nm on top, 1310nm on bottom
        fig, (ax_top, ax_bottom) = plt.subplots(2, 1, sharex=True, figsize=(10, 7), gridspec_kw={'height_ratios': [1, 1]})
        # Plot 1330nm group (top axis)
        for i, (idtag, data) in enumerate(group_1330):
            current = data['current']
            wavelength = data['peak_wl']
            if len(current) < 3:
                continue
            try:
                coeffs = np.polyfit(current, wavelength, 2)
                poly = np.poly1d(coeffs)
                x_smooth = np.linspace(min(current), max(current), 100)
                y_smooth = poly(x_smooth)
                ax_top.plot(current, wavelength, 'o', color=colors_1330[i], markersize=6, alpha=0.7)
                ax_top.plot(x_smooth, y_smooth, '-', color=colors_1330[i], linewidth=2)
            except Exception:
                continue
        # Plot 1310nm group (bottom axis)
        for i, (idtag, data) in enumerate(group_1310):
            current = data['current']
            wavelength = data['peak_wl']
            if len(current) < 3:
                continue
            try:
                coeffs = np.polyfit(current, wavelength, 2)
                poly = np.poly1d(coeffs)
                x_smooth = np.linspace(min(current), max(current), 100)
                y_smooth = poly(x_smooth)
                ax_bottom.plot(current, wavelength, 'o', color=colors_1310[i], markersize=6, alpha=0.7)
                ax_bottom.plot(x_smooth, y_smooth, '-', color=colors_1310[i], linewidth=2)
            except Exception:
                continue
        # Set y-limits for each axis, reduced by 2nm from both ends
        min_1330 = min([min(data['peak_wl']) for _, data in group_1330]) if n_1330 else None
        max_1330 = max([max(data['peak_wl']) for _, data in group_1330]) if n_1330 else None
        min_1310 = min([min(data['peak_wl']) for _, data in group_1310]) if n_1310 else None
        max_1310 = max([max(data['peak_wl']) for _, data in group_1310]) if n_1310 else None
        if min_1330 is not None and max_1330 is not None:
            ax_top.set_ylim(min_1330-1, max_1330+1)
        if min_1310 is not None and max_1310 is not None:
            ax_bottom.set_ylim(min_1310-1, max_1310+1)
        # Hide spines between axes and add break marks
        ax_top.spines['bottom'].set_visible(False)
        ax_bottom.spines['top'].set_visible(False)
        d = .015  # size of diagonal break
        kwargs = dict(transform=ax_top.transAxes, color='k', clip_on=False)
        ax_top.plot((-d, +d), (-d, +d), **kwargs)        # top-left diagonal
        ax_top.plot((1 - d, 1 + d), (-d, +d), **kwargs)  # top-right diagonal
        kwargs.update(transform=ax_bottom.transAxes)  # switch to the lower axes
        ax_bottom.plot((-d, +d), (1 - d, 1 + d), **kwargs)  # bottom-left diagonal
        ax_bottom.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)  # bottom-right diagonal
        # Axis labels and title
        ax_bottom.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        fig.text(0.04, 0.5, 'Peak Wavelength (nm)', va='center', rotation='vertical', fontsize=self.FONT_AXIS_LABEL)
        fig.suptitle('Overlay Fit: 1310nm (inferno) vs 1330nm (viridis)', fontsize=self.FONT_TITLE)
        ax_top.grid(True, alpha=0.3)
        ax_bottom.grid(True, alpha=0.3)
        ax_top.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        ax_bottom.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        plt.tight_layout(rect=[0.05, 0, 1, 0.97])
        save_path = self.save_dir / "OSA_overlay_fit_1310_vs_1330.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved overlay fit plot to {save_path}")
        
    def plot_peak_power_vs_current(self, device_data):
        """Plot peak power vs current for all devices"""
        plt.figure(figsize=(10, 6))
        num_devices = len(device_data)
        if num_devices == 1:
            colors = ['#FCA50A']
        else:
            colors = [self.cmap(0.2 + i * 0.7/(num_devices-1)) for i in range(num_devices)]
        for i, (idtag, data) in enumerate(device_data.items()):
            plt.plot(data['current'], data['peak_power'], 'o-', 
                    label=f"{idtag}", color=colors[i], markersize=4, linewidth=2)
        plt.xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        plt.ylabel('Peak Power (dBm)', fontsize=self.FONT_AXIS_LABEL)
        plt.title('Peak Power vs Current', fontsize=self.FONT_TITLE)
        plt.grid(True, alpha=0.3)
        plt.xticks(fontsize=self.FONT_AXIS_TICKS)
        plt.yticks(fontsize=self.FONT_AXIS_TICKS)
        if num_devices <= 6:
            plt.legend(loc='best', fontsize=self.FONT_LEGEND)
        plt.xlim(left=25)
        save_path = self.save_dir / "OSA_comparison_peak_power.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved peak power vs current plot to {save_path}")
        
    def plot_peak_wl_vs_current(self, device_data):
        """Plot peak wavelength vs current for all devices"""
        plt.figure(figsize=(10, 6))
        num_devices = len(device_data)
        if num_devices == 1:
            colors = ['#FCA50A']
        else:
            colors = [self.cmap(0.2 + i * 0.7/(num_devices-1)) for i in range(num_devices)]
        for i, (idtag, data) in enumerate(device_data.items()):
            plt.plot(data['current'], data['peak_wl'], 'o-', 
                    label=f"{idtag}", color=colors[i], markersize=4, linewidth=2)
        plt.xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        plt.ylabel('Peak Wavelength (nm)', fontsize=self.FONT_AXIS_LABEL)
        plt.title('Peak Wavelength vs Current', fontsize=self.FONT_TITLE)
        plt.grid(True, alpha=0.3)
        plt.xticks(fontsize=self.FONT_AXIS_TICKS)
        plt.yticks(fontsize=self.FONT_AXIS_TICKS)
        if num_devices <= 6:
            plt.legend(loc='best', fontsize=self.FONT_LEGEND)
        plt.xlim(left=25)
        save_path = self.save_dir / "OSA_comparison_peak_wl.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved peak wavelength vs current plot to {save_path}")
        
    def plot_peak_wl_vs_current_with_fit(self, device_data):
        """Plot peak wavelength vs current with 2nd order polynomial fit"""
        plt.figure(figsize=(10, 6))
        num_devices = len(device_data)
        if num_devices == 1:
            colors = ['#FCA50A']
        else:
            colors = [self.cmap(0.2 + i * 0.7/(num_devices-1)) for i in range(num_devices)]
        fit_results = {}
        for i, (idtag, data) in enumerate(device_data.items()):
            current = data['current']
            wavelength = data['peak_wl']
            if len(current) < 3:
                print(f"Warning: Not enough data points for {idtag} to perform polynomial fit")
                continue
            try:
                coeffs = np.polyfit(current, wavelength, 2)
                poly = np.poly1d(coeffs)
                residuals = wavelength - poly(current)
                ss_res = np.sum(residuals**2)
                ss_tot = np.sum((wavelength - np.mean(wavelength))**2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                x_smooth = np.linspace(min(current), max(current), 100)
                y_smooth = poly(x_smooth)
                plt.plot(current, wavelength, 'o', label=f"{idtag} data", 
                         color=colors[i], markersize=6)
                plt.plot(x_smooth, y_smooth, '-', 
                         label=f"{idtag} fit (R²={r_squared:.3f})", 
                         color=colors[i], linewidth=2)
                fit_results[idtag] = {
                    'coeffs': coeffs,
                    'r_squared': r_squared
                }
            except Exception as e:
                print(f"Error fitting data for {idtag}: {e}")
        plt.xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        plt.ylabel('Peak Wavelength (nm)', fontsize=self.FONT_AXIS_LABEL)
        plt.title('Peak Wavelength vs Current with Polynomial Fits', fontsize=self.FONT_TITLE)
        plt.grid(True, alpha=0.3)
        plt.xticks(fontsize=self.FONT_AXIS_TICKS)
        plt.yticks(fontsize=self.FONT_AXIS_TICKS)
        if num_devices <= 6:
            plt.legend(loc='best', fontsize=self.FONT_LEGEND)
        plt.xlim(left=25)
        save_path = self.save_dir / "OSA_comparison_peak_wl_with_fit.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved peak wavelength vs current with fit plot to {save_path}")
        
    def plot_peak_power_at_25mA(self, device_data):
        """Plot peak power at 25mA for all devices as a bar chart"""
        plt.figure(figsize=(10, 6))
        
        # Extract peak power values at 25mA for each device
        device_names = []
        power_values = []
        
        for i, (idtag, data) in enumerate(device_data.items()):
            current = data['current']
            peak_power = data['peak_power']
            
            # Find the index closest to 25mA
            current_array = np.array(current)
            closest_idx = np.argmin(np.abs(current_array - 25.0))
            actual_current = current_array[closest_idx]
            
            # Only include if the closest current is within 2mA of 25mA
            if abs(actual_current - 25.0) <= 2.0:
                device_names.append(idtag)
                power_values.append(peak_power[closest_idx])
                print(f"Device {idtag}: Power at {actual_current:.1f}mA = {peak_power[closest_idx]:.2f} dBm")
            else:
                print(f"Warning: No data point close to 25mA for {idtag} (closest: {actual_current:.1f}mA)")
        
        if not power_values:
            print("No devices have data points close to 25mA")
            return
            
        # Create bar plot with skyblue color
        bars = plt.bar(device_names, power_values, color='skyblue', alpha=0.8, linewidth=1)
        
        # Add value labels on top of bars
        for bar, value in zip(bars, power_values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f'{value:.2f}', ha='center', va='bottom', fontweight='bold')
        
        plt.xlabel('Device ID')
        plt.ylabel('Peak Power (dBm)')
        plt.title('Peak Power Comparison at 25mA')
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45, ha='right')
        plt.tick_params(axis='x', labelsize=self.FONT_AXIS_TICKS)
        # Save the plot (overwrite if exists)
        save_path = self.save_dir / "OSA_comparison_peak_power_25mA.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')  # High quality output
        plt.close()
        print(f"Saved peak power at 25mA comparison plot to {save_path}")
        
    def plot_peak_power_at_50mA(self, device_data):
        """Plot peak power at 50mA for all devices as a bar chart"""
        plt.figure(figsize=(10, 6))
        
        # Extract peak power values at 50mA for each device
        device_names = []
        power_values = []
        
        for i, (idtag, data) in enumerate(device_data.items()):
            current = data['current']
            peak_power = data['peak_power']
            
            # Find the index closest to 50mA
            current_array = np.array(current)
            closest_idx = np.argmin(np.abs(current_array - 50.0))
            actual_current = current_array[closest_idx]
            
            # Only include if the closest current is within 2mA of 50mA
            if abs(actual_current - 50.0) <= 2.0:
                device_names.append(idtag)
                power_values.append(peak_power[closest_idx])
                print(f"Device {idtag}: Power at {actual_current:.1f}mA = {peak_power[closest_idx]:.2f} dBm")
            else:
                print(f"Warning: No data point close to 50mA for {idtag} (closest: {actual_current:.1f}mA)")
        
        if not power_values:
            print("No devices have data points close to 50mA")
            return
            
        # Create bar plot with lightcoral color
        bars = plt.bar(device_names, power_values, color='lightcoral', alpha=0.8, linewidth=1)
        
        # Add value labels on top of bars
        for bar, value in zip(bars, power_values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f'{value:.2f}', ha='center', va='bottom', fontweight='bold')
        
        plt.xlabel('Device ID')
        plt.ylabel('Peak Power (dBm)')
        plt.title('Peak Power Comparison at 50mA')
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45, ha='right')
        plt.tick_params(axis='x', labelsize=self.FONT_AXIS_TICKS)
        # Save the plot (overwrite if exists)
        save_path = self.save_dir / "OSA_comparison_peak_power_50mA.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')  # High quality output
        plt.close()
        print(f"Saved peak power at 50mA comparison plot to {save_path}")
    
    def plot_linewidth_3dB_boxplot(self, device_data):
        """Plot -3dB linewidth variation across devices at each current using boxplots"""
        print("\n--- Creating -3dB Linewidth Boxplot ---")
        
        # Check if any device has linewidth data
        has_linewidth = any(data.get('linewidth_3dB') is not None for data in device_data.values())
        
        if not has_linewidth:
            print("Warning: No -3dB linewidth data available in any device. Skipping boxplot.")
            print("Note: Run OSAclass with the updated code to generate linewidth data.")
            return
        
        # Collect all unique current values across all devices
        all_currents = set()
        for data in device_data.values():
            if data.get('linewidth_3dB') is not None:
                all_currents.update(data['current'])
        
        # Sort currents
        sorted_currents = sorted(all_currents)
        
        # Organize linewidth data by current value
        # For each current, collect linewidth values from all devices
        linewidth_by_current = {current: [] for current in sorted_currents}
        device_contribution = {current: [] for current in sorted_currents}  # Track which devices contributed
        
        for idtag, data in device_data.items():
            if data.get('linewidth_3dB') is None:
                print(f"Skipping {idtag} (no linewidth data)")
                continue
                
            current_array = data['current']
            linewidth_array = data['linewidth_3dB']
            
            # Debug: Print linewidth values for this device
            print(f"\nDevice {idtag} linewidth data:")
            for curr, lw in zip(current_array, linewidth_array):
                if np.isnan(lw):
                    print(f"  {curr:.1f} mA: NaN (calculation failed)")
                elif lw > 1000:  # Flag unusually large values
                    print(f"  {curr:.1f} mA: {lw:.2f} pm ⚠️ UNUSUALLY LARGE")
                else:
                    print(f"  {curr:.1f} mA: {lw:.2f} pm")
            
            for curr, lw in zip(current_array, linewidth_array):
                if not np.isnan(lw):  # Skip NaN values
                    # Skip 20mA data for now
                    if abs(curr - 20.0) < 0.5:
                        print(f"  → Skipping 20 mA data point for {idtag}")
                        continue
                    
                    # Find closest matching current in sorted_currents
                    closest_curr = min(sorted_currents, key=lambda x: abs(x - curr))
                    if abs(closest_curr - curr) < 0.5:  # Within 0.5 mA tolerance
                        linewidth_by_current[closest_curr].append(lw)
                        device_contribution[closest_curr].append(idtag)
                else:
                    # Track NaN values too
                    print(f"  → Skipped NaN value at {curr:.1f} mA for {idtag}")

        
        # Filter out currents with no data
        valid_currents = [curr for curr in sorted_currents if len(linewidth_by_current[curr]) > 0]
        valid_linewidths = [linewidth_by_current[curr] for curr in valid_currents]
        
        if not valid_currents:
            print("No valid linewidth data found across devices")
            return
        
        # Print detailed breakdown of data contribution
        print("\nData contribution by current:")
        total_devices_with_data = sum(1 for d in device_data.values() if d.get('linewidth_3dB') is not None)
        for curr in valid_currents:
            devices_at_curr = set(device_contribution[curr])
            n = len(linewidth_by_current[curr])
            print(f"  {curr:.0f} mA: n={n} data points from {len(devices_at_curr)} devices")
            if len(devices_at_curr) < total_devices_with_data:
                missing = set(d for d in device_data.keys() if device_data[d].get('linewidth_3dB') is not None) - devices_at_curr
                print(f"           Missing: {', '.join(missing)}")

        
        # Create the boxplot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Create boxplot
        bp = ax.boxplot(valid_linewidths, positions=valid_currents, widths=1.5,
                       patch_artist=True, showfliers=True,
                       boxprops=dict(facecolor='lightblue', alpha=0.7),
                       medianprops=dict(color='red', linewidth=2),
                       whiskerprops=dict(color='black', linewidth=1.5),
                       capprops=dict(color='black', linewidth=1.5),
                       flierprops=dict(marker='o', markerfacecolor='red', markersize=6, 
                                      alpha=0.5, markeredgecolor='darkred'))
        
        # Add individual data points overlaid on boxplot
        for i, (curr, lw_list) in enumerate(zip(valid_currents, valid_linewidths)):
            # Add jitter to x-position for visibility
            x_jitter = curr + np.random.normal(0, 0.2, len(lw_list))
            ax.scatter(x_jitter, lw_list, alpha=0.4, s=30, c='darkblue', zorder=3)
        
        # Add sample size annotation
        for curr, lw_list in zip(valid_currents, valid_linewidths):
            n = len(lw_list)
            n_devices = len(set(device_contribution[curr]))
            # Show both number of data points and number of devices
            ax.text(curr, max(lw_list) * 1.02, f'n={n}\n({n_devices} dev)', 
                   ha='center', va='bottom', fontsize=self.FONT_ANNOTATION, color='black',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('-3dB Linewidth (pm)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Spectral Linewidth Variation Across Devices\n(-3dB Width from Peak Maximum)', 
                    fontsize=self.FONT_TITLE, pad=15)
        ax.grid(True, alpha=0.3, axis='y')
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        ax.set_xlim([min(valid_currents) - 2, max(valid_currents) + 2])
        
        # Add statistics text box
        stats_text = f"Total devices with linewidth data: {sum(1 for d in device_data.values() if d.get('linewidth_3dB') is not None)}\n"
        stats_text += f"Current range: {min(valid_currents):.0f}-{max(valid_currents):.0f} mA\n"
        stats_text += f"n = data points at each current"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               fontsize=self.FONT_ANNOTATION, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Save the plot
        save_path = self.save_dir / "OSA_comparison_linewidth_3dB_boxplot.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved -3dB linewidth boxplot to {save_path}")
        
        # Identify and print outliers
        print("\n=== OUTLIER ANALYSIS ===")
        print("(Outliers are points beyond 1.5×IQR from quartiles)")
        
        for curr, lw_list in zip(valid_currents, valid_linewidths):
            if len(lw_list) < 4:  # Need at least 4 points for meaningful outlier detection
                continue
            
            # Calculate quartiles and IQR
            q1 = np.percentile(lw_list, 25)
            q3 = np.percentile(lw_list, 75)
            iqr = q3 - q1
            
            # Define outlier bounds (standard boxplot definition)
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            # Find outliers and their device IDs
            outliers_found = False
            devices_at_curr = device_contribution[curr]
            
            for lw, device_id in zip(lw_list, devices_at_curr):
                if lw < lower_bound or lw > upper_bound:
                    if not outliers_found:
                        print(f"\n  {curr:.0f} mA (Q1={q1:.1f}, Q3={q3:.1f}, IQR={iqr:.1f} pm):")
                        outliers_found = True
                    
                    outlier_type = "LOW" if lw < lower_bound else "HIGH"
                    deviation = abs(lw - (q1 if lw < lower_bound else q3))
                    print(f"    • {device_id}: {lw:.1f} pm [{outlier_type} outlier, {deviation:.1f} pm from nearest quartile]")
            
            if not outliers_found and len(lw_list) >= 4:
                print(f"  {curr:.0f} mA: No outliers detected")
        
        # Print summary statistics
        print("\n-3dB Linewidth Statistics by Current:")
        for curr, lw_list in zip(valid_currents, valid_linewidths):
            if len(lw_list) > 0:
                mean_lw = np.mean(lw_list)
                std_lw = np.std(lw_list)
                min_lw = np.min(lw_list)
                max_lw = np.max(lw_list)
                print(f"  {curr:.0f} mA: {mean_lw:.1f} ± {std_lw:.1f} pm (range: {min_lw:.1f}-{max_lw:.1f} pm, n={len(lw_list)})")
    
    def plot_linewidth_violin(self, device_data):
        """Plot linewidth distribution using violin plots (better than boxplots for showing distribution shape)"""
        print("\n--- Creating -3dB Linewidth Violin Plot ---")
        
        # Check if any device has linewidth data
        has_linewidth = any(data.get('linewidth_3dB') is not None for data in device_data.values())
        if not has_linewidth:
            print("No linewidth data available. Skipping violin plot.")
            return
        
        # Collect data by current
        all_currents = set()
        for data in device_data.values():
            if data.get('linewidth_3dB') is not None:
                all_currents.update(data['current'])
        sorted_currents = sorted(all_currents)
        
        linewidth_by_current = {current: [] for current in sorted_currents}
        
        for idtag, data in device_data.items():
            if data.get('linewidth_3dB') is None:
                continue
            current_array = data['current']
            linewidth_array = data['linewidth_3dB']
            
            for curr, lw in zip(current_array, linewidth_array):
                if not np.isnan(lw) and abs(curr - 20.0) > 0.5:  # Skip 20mA and NaN
                    closest_curr = min(sorted_currents, key=lambda x: abs(x - curr))
                    if abs(closest_curr - curr) < 0.5:
                        linewidth_by_current[closest_curr].append(lw)
        
        # Filter valid currents
        valid_currents = [curr for curr in sorted_currents if len(linewidth_by_current[curr]) > 0]
        valid_linewidths = [linewidth_by_current[curr] for curr in valid_currents]
        
        if not valid_currents:
            print("No valid linewidth data found")
            return
        
        # Create violin plot
        fig, ax = plt.subplots(figsize=(12, 6))
        parts = ax.violinplot(valid_linewidths, positions=valid_currents, widths=2.0,
                             showmeans=True, showmedians=True, showextrema=True)
        
        # Color the violins
        for pc in parts['bodies']:
            pc.set_facecolor('lightblue')
            pc.set_alpha(0.7)
            pc.set_edgecolor('black')
        
        # Customize the mean/median lines
        parts['cmedians'].set_edgecolor('red')
        parts['cmedians'].set_linewidth(2)
        parts['cmeans'].set_edgecolor('green')
        parts['cmeans'].set_linewidth(2)
        
        ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('-3dB Spectral Width (pm)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Spectral Linewidth Distribution (Violin Plot)\nRed=Median, Green=Mean', 
                    fontsize=self.FONT_TITLE, pad=15)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xlim([min(valid_currents) - 3, max(valid_currents) + 3])
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        
        save_path = self.save_dir / "OSA_comparison_linewidth_3dB_violin.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved violin plot to {save_path}")
    
    def plot_linewidth_vs_current_lines(self, device_data):
        """Plot linewidth vs current with individual device traces"""
        print("\n--- Creating Linewidth vs Current Line Plot ---")
        
        has_linewidth = any(data.get('linewidth_3dB') is not None for data in device_data.values())
        if not has_linewidth:
            print("No linewidth data available. Skipping line plot.")
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Color scheme
        num_devices = sum(1 for d in device_data.values() if d.get('linewidth_3dB') is not None)
        if num_devices == 1:
            colors = ['#FCA50A']
        else:
            colors = [self.cmap(0.2 + i * 0.7/(num_devices-1)) for i in range(num_devices)]
        
        device_idx = 0
        for idtag, data in device_data.items():
            if data.get('linewidth_3dB') is None:
                continue
            
            current_array = data['current']
            linewidth_array = data['linewidth_3dB']
            
            # Filter out NaN and 20mA
            valid_data = [(c, lw) for c, lw in zip(current_array, linewidth_array) 
                         if not np.isnan(lw) and abs(c - 20.0) > 0.5]
            
            if valid_data:
                currents, linewidths = zip(*valid_data)
                ax.plot(currents, linewidths, 'o-', label=idtag, 
                       color=colors[device_idx], linewidth=2, markersize=6, alpha=0.8)
                device_idx += 1
        
        ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('-3dB Linewidth (pm)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Spectral Linewidth vs Current (Individual Devices)', fontsize=self.FONT_TITLE, pad=15)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=self.FONT_LEGEND)
        ax.set_xlim(left=20)
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        
        save_path = self.save_dir / "OSA_comparison_linewidth_vs_current.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved linewidth vs current plot to {save_path}")
    
    def plot_linewidth_heatmap(self, device_data):
        """Plot linewidth as a heatmap: devices vs current"""
        print("\n--- Creating Linewidth Heatmap ---")
        
        has_linewidth = any(data.get('linewidth_3dB') is not None for data in device_data.values())
        if not has_linewidth:
            print("No linewidth data available. Skipping heatmap.")
            return
        
        # Collect all currents and devices
        all_currents = set()
        devices_with_data = []
        
        for idtag, data in device_data.items():
            if data.get('linewidth_3dB') is not None:
                devices_with_data.append(idtag)
                all_currents.update(data['current'])
        
        sorted_currents = sorted([c for c in all_currents if abs(c - 20.0) > 0.5])  # Exclude 20mA
        
        if not sorted_currents or not devices_with_data:
            print("Insufficient data for heatmap")
            return
        
        # Create matrix: rows=devices, columns=currents
        heatmap_data = np.full((len(devices_with_data), len(sorted_currents)), np.nan)
        
        for i, idtag in enumerate(devices_with_data):
            data = device_data[idtag]
            current_array = data['current']
            linewidth_array = data['linewidth_3dB']
            
            for curr, lw in zip(current_array, linewidth_array):
                if not np.isnan(lw) and abs(curr - 20.0) > 0.5:
                    # Find matching current index
                    curr_idx = min(range(len(sorted_currents)), 
                                  key=lambda x: abs(sorted_currents[x] - curr))
                    if abs(sorted_currents[curr_idx] - curr) < 0.5:
                        heatmap_data[i, curr_idx] = lw
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(12, max(6, len(devices_with_data) * 0.4)))
        
        im = ax.imshow(heatmap_data, aspect='auto', cmap='viridis', interpolation='nearest')
        
        # Set ticks
        ax.set_xticks(np.arange(len(sorted_currents)))
        ax.set_yticks(np.arange(len(devices_with_data)))
        ax.set_xticklabels([f'{c:.0f}' for c in sorted_currents], fontsize=self.FONT_AXIS_TICKS)
        ax.set_yticklabels(devices_with_data, fontsize=self.FONT_ANNOTATION)
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)

        ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('Device ID', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Spectral Linewidth Heatmap (-3dB Width)', fontsize=self.FONT_TITLE, pad=15)        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Linewidth (pm)', fontsize=self.FONT_LEGEND)
        
        # Add text annotations
        for i in range(len(devices_with_data)):
            for j in range(len(sorted_currents)):
                if not np.isnan(heatmap_data[i, j]):
                    text = ax.text(j, i, f'{heatmap_data[i, j]:.1f}',
                                 ha="center", va="center", color="white", fontsize=self.FONT_ANNOTATION, 
                                 weight='bold')
        
        plt.tight_layout()
        save_path = self.save_dir / "OSA_comparison_linewidth_heatmap.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved linewidth heatmap to {save_path}")
    
    def plot_linewidth_mean_median(self, device_data):
        """Plot mean and median linewidth vs current with error bars"""
        print("\n--- Creating Mean/Median Linewidth Plot ---")
        
        has_linewidth = any(data.get('linewidth_3dB') is not None for data in device_data.values())
        if not has_linewidth:
            print("No linewidth data available. Skipping mean/median plot.")
            return
        
        # Collect data by current
        all_currents = set()
        for data in device_data.values():
            if data.get('linewidth_3dB') is not None:
                all_currents.update(data['current'])
        sorted_currents = sorted([c for c in all_currents if abs(c - 20.0) > 0.5])  # Exclude 20mA
        
        linewidth_by_current = {current: [] for current in sorted_currents}
        
        for idtag, data in device_data.items():
            if data.get('linewidth_3dB') is None:
                continue
            current_array = data['current']
            linewidth_array = data['linewidth_3dB']
            
            for curr, lw in zip(current_array, linewidth_array):
                if not np.isnan(lw) and abs(curr - 20.0) > 0.5:
                    closest_curr = min(sorted_currents, key=lambda x: abs(x - curr))
                    if abs(closest_curr - curr) < 0.5:
                        linewidth_by_current[closest_curr].append(lw)
        
        valid_currents = [curr for curr in sorted_currents if len(linewidth_by_current[curr]) > 0]
        
        if not valid_currents:
            print("No valid linewidth data found")
            return
        
        # Calculate statistics
        means = []
        medians = []
        stds = []
        q1s = []
        q3s = []
        
        for curr in valid_currents:
            lw_list = linewidth_by_current[curr]
            means.append(np.mean(lw_list))
            medians.append(np.median(lw_list))
            stds.append(np.std(lw_list))
            q1s.append(np.percentile(lw_list, 25))
            q3s.append(np.percentile(lw_list, 75))
        
        # Create plot
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Plot mean with standard deviation error bars
        ax.errorbar(valid_currents, means, yerr=stds, 
                   fmt='o-', color='blue', linewidth=2.5, markersize=8,
                   capsize=5, capthick=2, label='Mean ± Std Dev', zorder=3)
        
        # Plot median with IQR (interquartile range) error bars
        iqr_lower = [medians[i] - q1s[i] for i in range(len(medians))]
        iqr_upper = [q3s[i] - medians[i] for i in range(len(medians))]
        
        ax.errorbar(valid_currents, medians, 
                   yerr=[iqr_lower, iqr_upper],
                   fmt='s-', color='red', linewidth=2.5, markersize=8,
                   capsize=5, capthick=2, label='Median ± IQR', zorder=3)
        
        # Add value annotations
        for i, curr in enumerate(valid_currents):
            # Mean annotation (above)
            ax.text(curr, means[i] + stds[i] + 1, 
                   f'{means[i]:.1f}', ha='center', va='bottom', 
                   fontsize=self.FONT_ANNOTATION, color='blue', weight='bold')
            # Median annotation (below)
            ax.text(curr, medians[i] - iqr_lower[i] - 1, 
                   f'{medians[i]:.1f}', ha='center', va='top', 
                   fontsize=self.FONT_ANNOTATION, color='red', weight='bold')
        
        ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('-3dB Linewidth (pm)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Mean vs Median Linewidth Across Devices\n(Error bars: Std Dev for Mean, IQR for Median)', 
                    fontsize=self.FONT_TITLE, pad=15)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=self.FONT_LEGEND)
        ax.set_xlim([min(valid_currents) - 2, max(valid_currents) + 2])
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        
        # Add text box with interpretation
        textstr = 'Interpretation:\n'
        textstr += '• Mean sensitive to outliers\n'
        textstr += '• Median robust to outliers\n'
        textstr += '• Close values → symmetric data\n'
        textstr += '• Far apart → skewed/outliers'
        ax.text(0.98, 0.02, textstr, transform=ax.transAxes, 
               fontsize=self.FONT_ANNOTATION, verticalalignment='bottom', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        save_path = self.save_dir / "OSA_comparison_linewidth_mean_median.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved mean/median linewidth plot to {save_path}")
        
        # Print comparison table
        print("\nMean vs Median Comparison:")
        print(f"{'Current':<10} {'Mean':<12} {'Median':<12} {'Std Dev':<12} {'IQR':<12} {'Diff':<10}")
        print("-" * 70)
        for i, curr in enumerate(valid_currents):
            iqr = q3s[i] - q1s[i]
            diff = abs(means[i] - medians[i])
            print(f"{curr:.0f} mA     {means[i]:6.2f} pm    {medians[i]:6.2f} pm    "
                  f"{stds[i]:6.2f} pm    {iqr:6.2f} pm    {diff:6.2f} pm")
    
    def plot_linewidth_20dB_boxplot(self, device_data):
        """Plot -20dB linewidth variation across devices at each current using boxplots"""
        print("\n--- Creating -20dB Linewidth Boxplot ---")
        
        # Check if any device has linewidth data
        has_linewidth = any(data.get('linewidth_20dB') is not None for data in device_data.values())
        
        if not has_linewidth:
            print("Warning: No -20dB linewidth data available. Skipping boxplot.")
            return
        
        # Collect all unique current values
        all_currents = set()
        for data in device_data.values():
            if data.get('linewidth_20dB') is not None:
                all_currents.update(data['current'])
        
        sorted_currents = sorted(all_currents)
        
        # Organize linewidth data by current
        linewidth_by_current = {current: [] for current in sorted_currents}
        device_contribution = {current: [] for current in sorted_currents}
        
        for idtag, data in device_data.items():
            if data.get('linewidth_20dB') is None:
                continue
                
            current_array = data['current']
            linewidth_array = data['linewidth_20dB']
            
            for curr, lw in zip(current_array, linewidth_array):
                if not np.isnan(lw) and abs(curr - 20.0) > 0.5:  # Skip 20mA and NaN
                    closest_curr = min(sorted_currents, key=lambda x: abs(x - curr))
                    if abs(closest_curr - curr) < 0.5:
                        linewidth_by_current[closest_curr].append(lw)
                        device_contribution[closest_curr].append(idtag)
        
        # Filter valid currents
        valid_currents = [curr for curr in sorted_currents if len(linewidth_by_current[curr]) > 0]
        valid_linewidths = [linewidth_by_current[curr] for curr in valid_currents]
        
        if not valid_currents:
            print("No valid -20dB linewidth data found")
            return
        
        # Create boxplot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bp = ax.boxplot(valid_linewidths, positions=valid_currents, widths=1.5,
                       patch_artist=True, showfliers=True,
                       boxprops=dict(facecolor='lightcoral', alpha=0.7),
                       medianprops=dict(color='darkred', linewidth=2),
                       whiskerprops=dict(color='black', linewidth=1.5),
                       capprops=dict(color='black', linewidth=1.5),
                       flierprops=dict(marker='o', markerfacecolor='red', markersize=6, 
                                      alpha=0.5, markeredgecolor='darkred'))
        
        # Add individual data points
        for i, (curr, lw_list) in enumerate(zip(valid_currents, valid_linewidths)):
            x_jitter = curr + np.random.normal(0, 0.2, len(lw_list))
            ax.scatter(x_jitter, lw_list, alpha=0.4, s=30, c='darkred', zorder=3)
        
        # Add sample size annotation
        for curr, lw_list in zip(valid_currents, valid_linewidths):
            n = len(lw_list)
            n_devices = len(set(device_contribution[curr]))
            ax.text(curr, max(lw_list) * 1.02, f'n={n}\n({n_devices} dev)', 
                   ha='center', va='bottom', fontsize=self.FONT_ANNOTATION, color='black',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('-20dB Linewidth (pm)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Spectral Linewidth Variation Across Devices\n(-20dB Width from Peak Maximum)', 
                    fontsize=self.FONT_TITLE, pad=15)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xlim([min(valid_currents) - 2, max(valid_currents) + 2])
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        
        # Add statistics text box
        stats_text = f"Total devices with linewidth data: {sum(1 for d in device_data.values() if d.get('linewidth_20dB') is not None)}\n"
        stats_text += f"Current range: {min(valid_currents):.0f}-{max(valid_currents):.0f} mA\n"
        stats_text += f"n = data points at each current"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               fontsize=self.FONT_ANNOTATION, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        save_path = self.save_dir / "OSA_comparison_linewidth_20dB_boxplot.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved -20dB linewidth boxplot to {save_path}")
    
    def plot_linewidth_20dB_violin(self, device_data):
        """Plot -20dB linewidth distribution using violin plots"""
        print("\n--- Creating -20dB Linewidth Violin Plot ---")
        
        has_linewidth = any(data.get('linewidth_20dB') is not None for data in device_data.values())
        if not has_linewidth:
            print("No -20dB linewidth data available. Skipping violin plot.")
            return
        
        # Collect data by current
        all_currents = set()
        for data in device_data.values():
            if data.get('linewidth_20dB') is not None:
                all_currents.update(data['current'])
        sorted_currents = sorted(all_currents)
        
        linewidth_by_current = {current: [] for current in sorted_currents}
        
        for idtag, data in device_data.items():
            if data.get('linewidth_20dB') is None:
                continue
            current_array = data['current']
            linewidth_array = data['linewidth_20dB']
            
            for curr, lw in zip(current_array, linewidth_array):
                if not np.isnan(lw) and abs(curr - 20.0) > 0.5:
                    closest_curr = min(sorted_currents, key=lambda x: abs(x - curr))
                    if abs(closest_curr - curr) < 0.5:
                        linewidth_by_current[closest_curr].append(lw)
        
        valid_currents = [curr for curr in sorted_currents if len(linewidth_by_current[curr]) > 0]
        valid_linewidths = [linewidth_by_current[curr] for curr in valid_currents]
        
        if not valid_currents:
            print("No valid -20dB linewidth data found")
            return
        
        # Create violin plot
        fig, ax = plt.subplots(figsize=(12, 6))
        parts = ax.violinplot(valid_linewidths, positions=valid_currents, widths=2.0,
                             showmeans=True, showmedians=True, showextrema=True)
        
        for pc in parts['bodies']:
            pc.set_facecolor('lightcoral')
            pc.set_alpha(0.7)
            pc.set_edgecolor('black')
        
        parts['cmedians'].set_edgecolor('darkred')
        parts['cmedians'].set_linewidth(2)
        parts['cmeans'].set_edgecolor('green')
        parts['cmeans'].set_linewidth(2)
        
        ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('-20dB Spectral Width (pm)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Spectral Linewidth Distribution (Violin Plot, -20dB)\nDark Red=Median, Green=Mean', 
                    fontsize=self.FONT_TITLE, pad=15)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xlim([min(valid_currents) - 3, max(valid_currents) + 3])
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        
        save_path = self.save_dir / "OSA_comparison_linewidth_20dB_violin.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved -20dB violin plot to {save_path}")
    
    def plot_linewidth_20dB_mean_median(self, device_data):
        """Plot mean and median -20dB linewidth vs current with error bars"""
        print("\n--- Creating Mean/Median -20dB Linewidth Plot ---")
        
        has_linewidth = any(data.get('linewidth_20dB') is not None for data in device_data.values())
        if not has_linewidth:
            print("No -20dB linewidth data available. Skipping mean/median plot.")
            return
        
        # Collect data by current
        all_currents = set()
        for data in device_data.values():
            if data.get('linewidth_20dB') is not None:
                all_currents.update(data['current'])
        sorted_currents = sorted([c for c in all_currents if abs(c - 20.0) > 0.5])
        
        linewidth_by_current = {current: [] for current in sorted_currents}
        
        for idtag, data in device_data.items():
            if data.get('linewidth_20dB') is None:
                continue
            current_array = data['current']
            linewidth_array = data['linewidth_20dB']
            
            for curr, lw in zip(current_array, linewidth_array):
                if not np.isnan(lw) and abs(curr - 20.0) > 0.5:
                    closest_curr = min(sorted_currents, key=lambda x: abs(x - curr))
                    if abs(closest_curr - curr) < 0.5:
                        linewidth_by_current[closest_curr].append(lw)
        
        valid_currents = [curr for curr in sorted_currents if len(linewidth_by_current[curr]) > 0]
        
        if not valid_currents:
            print("No valid -20dB linewidth data found")
            return
        
        # Calculate statistics
        means = []
        medians = []
        stds = []
        q1s = []
        q3s = []
        
        for curr in valid_currents:
            lw_list = linewidth_by_current[curr]
            means.append(np.mean(lw_list))
            medians.append(np.median(lw_list))
            stds.append(np.std(lw_list))
            q1s.append(np.percentile(lw_list, 25))
            q3s.append(np.percentile(lw_list, 75))
        
        # Create plot
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Plot mean with standard deviation
        ax.errorbar(valid_currents, means, yerr=stds, 
                   fmt='o-', color='darkred', linewidth=2.5, markersize=8,
                   capsize=5, capthick=2, label='Mean ± Std Dev', zorder=3)
        
        # Plot median with IQR
        iqr_lower = [medians[i] - q1s[i] for i in range(len(medians))]
        iqr_upper = [q3s[i] - medians[i] for i in range(len(medians))]
        
        ax.errorbar(valid_currents, medians, 
                   yerr=[iqr_lower, iqr_upper],
                   fmt='s-', color='orange', linewidth=2.5, markersize=8,
                   capsize=5, capthick=2, label='Median ± IQR', zorder=3)
        
        # Add value annotations
        for i, curr in enumerate(valid_currents):
            ax.text(curr, means[i] + stds[i] + 2, 
                   f'{means[i]:.1f}', ha='center', va='bottom', 
                   fontsize=self.FONT_ANNOTATION, color='darkred', weight='bold')
            ax.text(curr, medians[i] - iqr_lower[i] - 2, 
                   f'{medians[i]:.1f}', ha='center', va='top', 
                   fontsize=self.FONT_ANNOTATION, color='orange', weight='bold')
        
        ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('-20dB Linewidth (pm)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Mean vs Median Linewidth Across Devices (-20dB)\n(Error bars: Std Dev for Mean, IQR for Median)', 
                    fontsize=self.FONT_TITLE, pad=15)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=self.FONT_LEGEND)
        ax.set_xlim([min(valid_currents) - 2, max(valid_currents) + 2])
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        
        # Add interpretation text
        textstr = 'Interpretation:\n'
        textstr += '• Mean sensitive to outliers\n'
        textstr += '• Median robust to outliers\n'
        textstr += '• Close values → symmetric data\n'
        textstr += '• Far apart → skewed/outliers'
        ax.text(0.98, 0.02, textstr, transform=ax.transAxes, 
               fontsize=self.FONT_ANNOTATION, verticalalignment='bottom', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        save_path = self.save_dir / "OSA_comparison_linewidth_20dB_mean_median.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved -20dB mean/median linewidth plot to {save_path}")
        
        # Print comparison table
        print("\n-20dB Mean vs Median Comparison:")
        print(f"{'Current':<10} {'Mean':<12} {'Median':<12} {'Std Dev':<12} {'IQR':<12} {'Diff':<10}")
        print("-" * 70)
        for i, curr in enumerate(valid_currents):
            iqr = q3s[i] - q1s[i]
            diff = abs(means[i] - medians[i])
            print(f"{curr:.0f} mA     {means[i]:6.2f} pm    {medians[i]:6.2f} pm    "
                  f"{stds[i]:6.2f} pm    {iqr:6.2f} pm    {diff:6.2f} pm")
    
    def save_linewidth_summary_report(self, device_data):
        """Save comprehensive linewidth analysis report to text file"""
        print("\n--- Generating Linewidth Summary Report ---")
        
        report_path = self.save_dir / "Linewidth_Analysis_Summary.txt"
        
        with open(report_path, 'w') as f:
            # Header
            f.write("="*80 + "\n")
            f.write("SPECTRAL LINEWIDTH ANALYSIS SUMMARY REPORT\n")
            f.write("="*80 + "\n\n")
            
            from datetime import datetime
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Analysis Directory: {self.save_dir}\n")
            f.write(f"Total Devices Analyzed: {len(device_data)}\n\n")
            
            # Device list
            f.write("-"*80 + "\n")
            f.write("DEVICES INCLUDED IN ANALYSIS:\n")
            f.write("-"*80 + "\n")
            for i, idtag in enumerate(device_data.keys(), 1):
                f.write(f"  {i}. {idtag}\n")
            f.write("\n")
            
            # Process -3dB data
            self._write_linewidth_section(f, device_data, 'linewidth_3dB', '-3dB')
            
            # Process -20dB data
            self._write_linewidth_section(f, device_data, 'linewidth_20dB', '-20dB')
            
            f.write("="*80 + "\n")
            f.write("END OF REPORT\n")
            f.write("="*80 + "\n")
        
        print(f"Summary report saved to: {report_path}")
    
    def _write_linewidth_section(self, f, device_data, linewidth_key, label):
        """Helper method to write a linewidth analysis section"""
        
        # Check if data exists
        has_data = any(data.get(linewidth_key) is not None for data in device_data.values())
        if not has_data:
            f.write(f"\n{'='*80}\n")
            f.write(f"{label} LINEWIDTH ANALYSIS\n")
            f.write(f"{'='*80}\n")
            f.write(f"No {label} linewidth data available.\n\n")
            return
        
        # Collect data by current
        all_currents = set()
        for data in device_data.values():
            if data.get(linewidth_key) is not None:
                all_currents.update(data['current'])
        sorted_currents = sorted([c for c in all_currents if abs(c - 20.0) > 0.5])  # Exclude 20mA
        
        linewidth_by_current = {current: [] for current in sorted_currents}
        device_contribution = {current: [] for current in sorted_currents}
        
        for idtag, data in device_data.items():
            if data.get(linewidth_key) is None:
                continue
            current_array = data['current']
            linewidth_array = data[linewidth_key]
            
            for curr, lw in zip(current_array, linewidth_array):
                if not np.isnan(lw) and abs(curr - 20.0) > 0.5:
                    closest_curr = min(sorted_currents, key=lambda x: abs(x - curr))
                    if abs(closest_curr - curr) < 0.5:
                        linewidth_by_current[closest_curr].append(lw)
                        device_contribution[closest_curr].append(idtag)
        
        valid_currents = [curr for curr in sorted_currents if len(linewidth_by_current[curr]) > 0]
        
        if not valid_currents:
            f.write(f"\n{'='*80}\n")
            f.write(f"{label} LINEWIDTH ANALYSIS\n")
            f.write(f"{'='*80}\n")
            f.write(f"No valid {label} linewidth data found.\n\n")
            return
        
        # Write section header
        f.write(f"\n{'='*80}\n")
        f.write(f"{label} LINEWIDTH ANALYSIS\n")
        f.write(f"{'='*80}\n\n")
        
        # Calculate statistics
        means = []
        medians = []
        stds = []
        q1s = []
        q3s = []
        
        for curr in valid_currents:
            lw_list = linewidth_by_current[curr]
            means.append(np.mean(lw_list))
            medians.append(np.median(lw_list))
            stds.append(np.std(lw_list))
            q1s.append(np.percentile(lw_list, 25))
            q3s.append(np.percentile(lw_list, 75))
        
        # Mean vs Median Comparison Table
        f.write("MEAN vs MEDIAN COMPARISON:\n")
        f.write("-"*80 + "\n")
        f.write(f"{'Current':<10} {'Mean':<12} {'Median':<12} {'Std Dev':<12} {'IQR':<12} {'Diff':<10}\n")
        f.write("-" * 70 + "\n")
        for i, curr in enumerate(valid_currents):
            iqr = q3s[i] - q1s[i]
            diff = abs(means[i] - medians[i])
            f.write(f"{curr:.0f} mA     {means[i]:6.2f} pm    {medians[i]:6.2f} pm    "
                   f"{stds[i]:6.2f} pm    {iqr:6.2f} pm    {diff:6.2f} pm\n")
        f.write("\n")
        
        # Outlier Analysis
        f.write("OUTLIER ANALYSIS:\n")
        f.write("(Outliers defined as points beyond 1.5×IQR from quartiles)\n")
        f.write("-"*80 + "\n")
        
        outliers_found_overall = False
        for i, curr in enumerate(valid_currents):
            lw_list = linewidth_by_current[curr]
            
            if len(lw_list) < 4:  # Need at least 4 points
                continue
            
            q1 = q1s[i]
            q3 = q3s[i]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            devices_at_curr = device_contribution[curr]
            outliers_at_current = []
            
            for lw, device_id in zip(lw_list, devices_at_curr):
                if lw < lower_bound or lw > upper_bound:
                    outlier_type = "LOW" if lw < lower_bound else "HIGH"
                    deviation = abs(lw - (q1 if lw < lower_bound else q3))
                    outliers_at_current.append((device_id, lw, outlier_type, deviation))
            
            if outliers_at_current:
                outliers_found_overall = True
                f.write(f"\n  {curr:.0f} mA (Q1={q1:.1f} pm, Q3={q3:.1f} pm, IQR={iqr:.1f} pm):\n")
                for device_id, lw, outlier_type, deviation in outliers_at_current:
                    f.write(f"    • {device_id}: {lw:.1f} pm [{outlier_type} outlier, "
                           f"{deviation:.1f} pm from nearest quartile]\n")
            else:
                f.write(f"  {curr:.0f} mA: No outliers detected\n")
        
        if not outliers_found_overall:
            f.write("  No outliers detected at any current level.\n")
        
        f.write("\n")
        
        # Detailed Statistics by Current
        f.write("DETAILED STATISTICS BY CURRENT:\n")
        f.write("-"*80 + "\n")
        for i, curr in enumerate(valid_currents):
            lw_list = linewidth_by_current[curr]
            devices_at_curr = set(device_contribution[curr])
            
            f.write(f"\n{curr:.0f} mA:\n")
            f.write(f"  Number of data points: {len(lw_list)}\n")
            f.write(f"  Number of devices: {len(devices_at_curr)}\n")
            f.write(f"  Mean: {means[i]:.2f} pm\n")
            f.write(f"  Median: {medians[i]:.2f} pm\n")
            f.write(f"  Std Dev: {stds[i]:.2f} pm\n")
            f.write(f"  Min: {np.min(lw_list):.2f} pm\n")
            f.write(f"  Max: {np.max(lw_list):.2f} pm\n")
            f.write(f"  Q1 (25%): {q1s[i]:.2f} pm\n")
            f.write(f"  Q3 (75%): {q3s[i]:.2f} pm\n")
            f.write(f"  IQR: {q3s[i] - q1s[i]:.2f} pm\n")
            
            # List contributing devices
            f.write(f"  Contributing devices: {', '.join(sorted(devices_at_curr))}\n")
            
            # Check for missing devices
            total_devices = sum(1 for d in device_data.values() if d.get(linewidth_key) is not None)
            if len(devices_at_curr) < total_devices:
                all_devices = set(d for d in device_data.keys() if device_data[d].get(linewidth_key) is not None)
                missing = all_devices - devices_at_curr
                f.write(f"  Missing devices: {', '.join(sorted(missing))}\n")
        
        f.write("\n")
        
    def get_IDtag(self, filename: str) -> str:
        """Extract IDtag from filename using same method as multi_LIV"""
        base = Path(filename).stem
        # Remove _new suffix if present
        if base.endswith('_new'):
            base = base[:-4]
        # Expanded regex to handle more variations, including '_clad' and other suffixes
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

        # Detailed logging for debugging
        print(f"Debug: Filename: {filename}, Base: {base}, Extracted ID Tag: {id_tag}")
        return id_tag