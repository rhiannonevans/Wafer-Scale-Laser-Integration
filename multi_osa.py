import os
import io
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import scipy.io
from OSAclass import OSAclass

""" Class for processing multiple OSA (Optical Spectrum Analyzer) files. Processes selected 'osa' files, creates the following comparison plots:
         - Peak Power vs Current for all devices
         - Peak Wavelength vs Current for all devices
         - Peak Wavelength vs Current with 2nd Order Polynomial Fits
"""

class multi_OSA:
    def __init__(self, parent_path, selected_files=None, overwrite_existing=False):
        p = Path(parent_path)
        self.parent_path = parent_path
        self.cmap = plt.get_cmap('inferno')
        self.idtag_to_mat_file = {}  # Store mapping of IDtag to mat file path
        
        # Log selected files for debugging
        print("Debug: Selected files:", selected_files)
        
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
            # Use the selected files to find matching CSV files
            wanted = {Path(name).stem.lower() for name in selected_files}
            
            all_files = [
                fp
                for fp in p.rglob('*.csv')
                if fp.is_file()
            ]
            
            # Find CSVs that match selected files and are OSA files
            raw_files = [
                fp
                for fp in all_files
                if fp.stem.lower() in wanted and 'osa' in fp.name.lower()
            ]
            print("Debug: Selected OSA raw files:", [str(fp) for fp in raw_files])

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
        """Filter selected files to only include OSA files"""
        if not selected_files:
            return None
            
        # Only keep files that have "OSA" in their name
        filtered = []
        for fname in selected_files:
            if 'osa' in Path(fname).name.lower():
                filtered.append(fname)
            else:
                print(f"Skipping non-OSA file: {fname}")
                
        return filtered
        
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
        
        # Load data from all mat files
        device_data = {}
        
        for mat_file in self.mat_files:
            try:
                # Load the mat file
                data = scipy.io.loadmat(str(mat_file))
                
                # Debugging: Print available keys in the .mat file
                print(f"Keys in {mat_file}: {list(data.keys())}")
                
                # Extract IDtag
                if 'IDtag' in data:
                    idtag = str(data['IDtag'][0])
                else:
                    # Generate IDtag from filename using same method as multi_LIV
                    idtag = self.get_IDtag(mat_file.name)
                    print(f"Generated IDtag: {idtag} from filename: {mat_file.name}")
                    
                # Extract current, peak power and wavelength data
                print(f"Checking for keys: ['current_mA', 'peak_power', 'peak_wavelength']")
                if all(key in data for key in ['current_mA', 'peak_power', 'peak_wavelength']):
                    i_values = data['current_mA'].flatten()
                    peak_power = data['peak_power'].flatten()
                    peak_wl = data['peak_wavelength'].flatten()
                    
                    print(f"Found data - Current: {len(i_values)} points, Power: {len(peak_power)} points, WL: {len(peak_wl)} points")
                    
                    # Store data in a dictionary
                    device_data[idtag] = {
                        'current': i_values,
                        'peak_power': peak_power,
                        'peak_wl': peak_wl,
                        'file_path': mat_file
                    }
                    print(f"Loaded data for {idtag} ({len(i_values)} points)")
                else:
                    print(f"Warning: Missing required data keys in {mat_file}")
                    missing_keys = [key for key in ['current_mA', 'peak_power', 'peak_wavelength'] if key not in data]
                    print(f"Missing keys: {missing_keys}")
            except Exception as e:
                print(f"Error loading {mat_file}: {e}")
                
        # Generate comparison plots
        print(f"Total devices loaded: {len(device_data)}")
        if len(device_data) == 0:
            print("No device data loaded - cannot generate plots")
            return
            
        self.plot_peak_power_vs_current(device_data)
        self.plot_peak_wl_vs_current(device_data)
        self.plot_peak_wl_vs_current_with_fit(device_data)
        self.plot_peak_power_at_25mA(device_data)
        self.plot_peak_power_at_50mA(device_data)
        
    def plot_peak_power_vs_current(self, device_data):
        """Plot peak power vs current for all devices"""
        plt.figure(figsize=(10, 6))
        
        # Create inferno color cycle for different devices
        num_devices = len(device_data)
        if num_devices == 1:
            colors = ['#FCA50A']  # Use a bright inferno color for single device
        else:
            # Use range 0.2 to 0.9 to avoid too dark and too light colors
            colors = [self.cmap(0.2 + i * 0.7/(num_devices-1)) for i in range(num_devices)]
        
        for i, (idtag, data) in enumerate(device_data.items()):
            plt.plot(data['current'], data['peak_power'], 'o-', 
                    label=f"{idtag}", color=colors[i], markersize=4, linewidth=2)
        
        plt.xlabel('Current (mA)')
        plt.ylabel('Peak Power (dBm)')
        plt.title('Peak Power vs Current')
        plt.grid(True, alpha=0.3)
        plt.legend(loc='best')
        plt.xlim(left=25)  # Start x-axis from 25mA
        
        # Save the plot (overwrite if exists)
        save_path = self.save_dir / "OSA_comparison_peak_power.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')  # High quality output
        plt.close()
        print(f"Saved peak power vs current plot to {save_path}")
        
    def plot_peak_wl_vs_current(self, device_data):
        """Plot peak wavelength vs current for all devices"""
        plt.figure(figsize=(10, 6))
        
        # Create inferno color cycle for different devices
        num_devices = len(device_data)
        if num_devices == 1:
            colors = ['#FCA50A']  # Use a bright inferno color for single device
        else:
            # Use range 0.2 to 0.9 to avoid too dark and too light colors
            colors = [self.cmap(0.2 + i * 0.7/(num_devices-1)) for i in range(num_devices)]
        
        for i, (idtag, data) in enumerate(device_data.items()):
            plt.plot(data['current'], data['peak_wl'], 'o-', 
                    label=f"{idtag}", color=colors[i], markersize=4, linewidth=2)
        
        plt.xlabel('Current (mA)')
        plt.ylabel('Peak Wavelength (nm)')
        plt.title('Peak Wavelength vs Current')
        plt.grid(True, alpha=0.3)
        plt.legend(loc='best')
        plt.xlim(left=25)  # Start x-axis from 25mA
        
        # Save the plot (overwrite if exists)
        save_path = self.save_dir / "OSA_comparison_peak_wl.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')  # High quality output
        plt.close()
        print(f"Saved peak wavelength vs current plot to {save_path}")
        
    def plot_peak_wl_vs_current_with_fit(self, device_data):
        """Plot peak wavelength vs current with 2nd order polynomial fit"""
        plt.figure(figsize=(10, 6))
        
        # Create inferno color cycle for different devices
        num_devices = len(device_data)
        if num_devices == 1:
            colors = ['#FCA50A']  # Use a bright inferno color for single device
        else:
            # Use range 0.2 to 0.9 to avoid too dark and too light colors
            colors = [self.cmap(0.2 + i * 0.7/(num_devices-1)) for i in range(num_devices)]
        
        # For tracking fit quality
        fit_results = {}
        
        for i, (idtag, data) in enumerate(device_data.items()):
            current = data['current']
            wavelength = data['peak_wl']
            
            # Skip if not enough data points
            if len(current) < 3:
                print(f"Warning: Not enough data points for {idtag} to perform polynomial fit")
                continue
                
            # Create polynomial fit (2nd order)
            try:
                coeffs = np.polyfit(current, wavelength, 2)
                poly = np.poly1d(coeffs)
                
                # Calculate fit quality (R^2)
                residuals = wavelength - poly(current)
                ss_res = np.sum(residuals**2)
                ss_tot = np.sum((wavelength - np.mean(wavelength))**2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                
                # Generate smooth curve for plotting
                x_smooth = np.linspace(min(current), max(current), 100)
                y_smooth = poly(x_smooth)
                
                # Plot original data and fit with inferno colors
                plt.plot(current, wavelength, 'o', label=f"{idtag} data", 
                         color=colors[i], markersize=6)
                plt.plot(x_smooth, y_smooth, '-', 
                         label=f"{idtag} fit (R²={r_squared:.3f})", 
                         color=colors[i], linewidth=2)
                
                # Store fit results for later use
                fit_results[idtag] = {
                    'coeffs': coeffs,
                    'r_squared': r_squared
                }
                
            except Exception as e:
                print(f"Error fitting data for {idtag}: {e}")
        
        plt.xlabel('Current (mA)')
        plt.ylabel('Peak Wavelength (nm)')
        plt.title('Peak Wavelength vs Current with Polynomial Fits')
        plt.grid(True, alpha=0.3)
        plt.legend(loc='best')
        plt.xlim(left=25)  # Start x-axis from 25mA
        
        # Save the plot (overwrite if exists)
        save_path = self.save_dir / "OSA_comparison_peak_wl_with_fit.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')  # High quality output
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
        bars = plt.bar(device_names, power_values, color='skyblue', alpha=0.8, edgecolor='black', linewidth=1)
        
        # Add value labels on top of bars
        for bar, value in zip(bars, power_values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f'{value:.2f}', ha='center', va='bottom', fontweight='bold')
        
        plt.xlabel('Device ID')
        plt.ylabel('Peak Power (dBm)')
        plt.title('Peak Power Comparison at 25mA')
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45, ha='right')
        
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
        bars = plt.bar(device_names, power_values, color='lightcoral', alpha=0.8, edgecolor='black', linewidth=1)
        
        # Add value labels on top of bars
        for bar, value in zip(bars, power_values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f'{value:.2f}', ha='center', va='bottom', fontweight='bold')
        
        plt.xlabel('Device ID')
        plt.ylabel('Peak Power (dBm)')
        plt.title('Peak Power Comparison at 50mA')
        plt.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45, ha='right')
        
        # Save the plot (overwrite if exists)
        save_path = self.save_dir / "OSA_comparison_peak_power_50mA.png"
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')  # High quality output
        plt.close()
        print(f"Saved peak power at 50mA comparison plot to {save_path}")
        
    def get_IDtag(self, filename: str) -> str:
        """Extract IDtag from filename using same method as multi_LIV"""
        base = Path(filename).stem
        # Remove _new suffix if present
        if base.endswith('_new'):
            base = base[:-4]
        # Expanded regex to handle more variations, including '_clad' and other suffixes
        match = re.search(r"Chip\w+_R\d+(_clad)?", base)
        if match:
            id_tag = match.group(0)  # Retain '_clad' if present
        else:
            id_tag = "Unknown_ID"

        # Detailed logging for debugging
        print(f"Debug: Filename: {filename}, Base: {base}, Extracted ID Tag: {id_tag}")
        return id_tag