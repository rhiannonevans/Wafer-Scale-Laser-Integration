import pandas as pd
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

""" 
    OSA class for processing Optical Spectrum Analyzer (OSA) files. Processes raw OSA measurement csvs, organizes data 
    and computed values of interest, then saves to a '_loss_data.csv' file and generates plots.
    Plots (plotted by sweep):
            - Peak Power vs Current
            - Wavelength at Peak Power vs Current - with fit
            - Wavelength vs Optical Power
            - Wavelength vs Peak Power
    
    Computed Values:
            - Peak Power (dBm) for each sweep
            - Wavelength (nm) at peak power for each sweep
            - 2nd and 3rd degree polynomial fit coefficients for Current vs Peak Wavelength across sweeps
"""

class OSAclass:
    def __init__(self, path, output_folder=None):
        plt.close('all')  # Close all existing plots to avoid clutter
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Cannot find input CSV: {self.path}")

        self.base_name = self.path.stem
        self.output_folder = output_folder

        # Process the file and generate outputs
        self.sweep_osa()

    def sweep_osa(self):
        import scipy.io as sio
        import matplotlib.pyplot as plt
        import numpy as np
        import os

        # Load the file as a CSV
        df = pd.read_csv(self.path, header=None, skiprows=24, on_bad_lines="skip", engine="python")

        # Organize into sweeps
        df["Sweep"] = df.index // 2

        # Re-read file for longer data rows
        df2 = pd.read_csv(self.path, header=None, skiprows=26, on_bad_lines="skip", engine="python")

        # Filter rows to extract the desired titles
        extract = ["Wavelength (nm)", "Optical power (dBm)"]
        df2 = df2[df2[0].isin(extract)]

        # Group rows in sequential pairs
        df2["Sweep"] = df2.index // 2
        df2["Sweep"] = df2["Sweep"].rank(method="dense").astype(int) - 1

        waves = df2[df2[0] == "Wavelength (nm)"].copy()
        pows = df2[df2[0] == "Optical power (dBm)"].copy()

        waves["Property"] = "Wavelength (nm)"
        pows["Property"] = "Optical power (dBm)"

        # Combine wavelength and power frames
        combined_rows = pd.concat([waves, pows])
        del combined_rows[0]

        # Reshape the dataframe into a long format
        df_long = combined_rows.melt(id_vars=["Sweep", "Property"], value_name="Value")

        # Pivot the data to get each property as a column for each sweep
        pivot_df = df_long.pivot_table(index=["Sweep"], columns="Property", values="Value", aggfunc=list)

        # Extract "Current (A)" and "Temperature (C)" rows from df
        currents = ["Current (A)"]
        temperatures = ["Temperature (C)"]
        curr = df[df[0].isin(currents)].reset_index(drop=True)
        temp = df[df[0].isin(temperatures)].reset_index(drop=True)
        curr[1] = curr[1].astype(float) * 1000  # Convert current from A to mA

        # Combine current and temperature data into one DataFrame
        conditions = pd.DataFrame({
            "Sweep": range(len(curr)),
            "Current (mA)": curr[1].values,
            "Temperature (C)": temp[1].values
        })

        # Merge pivot data with conditions based on "Sweep"
        df2_merged = pivot_df.merge(conditions, on="Sweep")
        df2_merged.set_index("Sweep", inplace=True)

        # Rename and reorder columns for clarity
        df2_merged.columns = ["Optical Power (dBm)", "Wavelength (nm)", "Current (mA)", "Temperature (C)"]
        df2_merged = df2_merged[["Current (mA)", "Temperature (C)", "Optical Power (dBm)", "Wavelength (nm)"]]

        OSA_df = df2_merged

        # Generate plots
        cmap = plt.get_cmap('inferno')
        colors = cmap(np.linspace(0.2, 0.9, len(OSA_df.index)))

        fig1, ax1 = plt.subplots()  # Spectrum figure
        fig2, ax2 = plt.subplots()  # Peak power vs wavelength
        fig3, ax3 = plt.subplots()  # Peak power vs current
        fig4, ax4 = plt.subplots()  # Peak wavelength vs current

        peak_pows = []
        peak_wls = []
        currents = []

        for sweep in OSA_df.index:
            wavelength = OSA_df.at[sweep, "Wavelength (nm)"]
            power = OSA_df.at[sweep, "Optical Power (dBm)"]
            current = OSA_df.at[sweep, "Current (mA)"]
            temperatures = OSA_df.at[sweep, "Temperature (C)"]

            max_power = max(power)
            peak_pows.append(max_power)
            max_wavelength = wavelength[power.index(max_power)]
            peak_wls.append(max_wavelength)
            currents.append(current)

            # Always plot spectrum (ax1) for all sweeps
            ax1.plot(wavelength, power, label=f"{current} / {temperatures}", color=colors[sweep])

            # Only plot current-dependent plots (ax2, ax3, ax4) starting from 25mA (skip first sweep at 20mA)
            if current >= 25:
                ax2.scatter(current, max_wavelength, label=f"{current}mA", color=colors[sweep])
                ax3.scatter(current, max_power, label=f"{current}mA", color=colors[sweep])
                ax4.scatter(current, max_wavelength, label=f"{current}mA", color=colors[sweep])

        # Set plot titles and labels
        idtag = self.get_IDtag(self.path.name)
        ax1.set_xlabel('Wavelength (nm)')
        ax1.set_ylabel('Optical Power (dBm)')
        ax1.set_title(f'OSA Spectrum vs Wavelength - {idtag}')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        ax2.set_xlabel('Current (mA)')
        ax2.set_ylabel('Peak Wavelength (nm)')
        ax2.set_title(f'Peak Wavelength vs Current (with 2nd Order Fit) - {idtag}')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.set_xlim(left=25)  # Start x-axis from 25mA
        
        ax3.set_xlabel('Current (mA)')
        ax3.set_ylabel('Peak Power (dBm)')
        ax3.set_title(f'Peak Power vs Current - {idtag}')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        ax3.set_xlim(left=25)  # Start x-axis from 25mA
        
        ax4.set_xlabel('Current (mA)')
        ax4.set_ylabel('Peak Wavelength (nm)')
        ax4.set_title(f'Peak Wavelength vs Current (with 3rd Order Fit) - {idtag}')
        ax4.grid(True, alpha=0.3)
        ax4.legend()
        ax4.set_xlim(left=25)  # Start x-axis from 25mA
            
        # Polynomial fits: 2nd and 3rd degree fit for peak wavelength vs current
        if len(currents) > 3:  # Need at least 4 points for a 3rd degree fit
            # Filter data for currents between 25mA and 50mA
            fit_indices = [i for i, curr in enumerate(currents) if 25 <= curr <= 50]
            
            if len(fit_indices) >= 3:  # Need at least 3 points for a 2nd degree fit
                # Filter the data using the indices
                fit_x = np.array([currents[i] for i in fit_indices])  # current in mA (25-50mA range)
                fit_y = np.array([peak_wls[i] for i in fit_indices])  # peak wavelengths
                
                print(f"Using {len(fit_x)} points between 25mA and 50mA for polynomial fits")
            else:
                print("Not enough data points between 25mA and 50mA, using all data points")
                fit_x = np.array(currents)  # current in mA
                fit_y = np.array(peak_wls)  # peak wavelengths
            
            # 2nd degree polynomial fit
            poly_coeffs = np.polyfit(fit_x, fit_y, 2)
            poly_func = np.poly1d(poly_coeffs)
            
            # 3rd degree polynomial fit - only if we have enough points
            if len(fit_x) >= 4:
                poly_coeffs2 = np.polyfit(fit_x, fit_y, 3)
                poly_func2 = np.poly1d(poly_coeffs2)
            else:
                # Use a 2nd degree fit for both if not enough points
                print("Not enough data points for 3rd degree fit, using 2nd degree fit instead")
                poly_coeffs2 = poly_coeffs
                poly_func2 = poly_func
            
            # Generate fit lines - extend to full range for visualization
            fit_x_vals = np.linspace(min(currents), max(currents), 300)
            fit_y_vals = poly_func(fit_x_vals)
            fit_y_vals2 = poly_func2(fit_x_vals)
            
            ax2.plot(fit_x_vals, fit_y_vals, 'k--', linewidth=2, label="2nd Deg. Fit")
            ax4.plot(fit_x_vals, fit_y_vals2, 'k--', linewidth=2, label="3rd Deg. Fit")
            
            # Update legends to include fit lines
            ax2.legend()
            ax4.legend()
            
            # Annotate polynomial equations
            eq_text = f"Fit: y = {poly_coeffs[0]:.3e}x² + {poly_coeffs[1]:.3e}x + {poly_coeffs[2]:.3f}"
            eq_text2 = (f"Fit: y = {poly_coeffs2[0]:.3e}x³ + {poly_coeffs2[1]:.3e}x² + "
                        f"{poly_coeffs2[2]:.3e}x + {poly_coeffs2[3]:.3f}")
            
            ax2.text(0.05, 0.95, eq_text, transform=ax2.transAxes, fontsize=9, 
                     verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.6))
            ax4.text(0.05, 0.95, eq_text2, transform=ax4.transAxes, fontsize=9, 
                     verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.6))

        # Save plots
        save_dir = self.output_folder if self.output_folder else self.path.parent
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Save as both PNG and SVG formats
        fig1.savefig(os.path.join(save_dir, f"{self.base_name}_new_spectrum.png"), bbox_inches="tight")
        fig2.savefig(os.path.join(save_dir, f"{self.base_name}_new_WLpeaks.png"), bbox_inches="tight")
        fig3.savefig(os.path.join(save_dir, f"{self.base_name}_new_Ipeaks.png"), bbox_inches="tight")
        fig4.savefig(os.path.join(save_dir, f"{self.base_name}_new_WLpeaks2.png"), bbox_inches="tight")
        
        fig1.savefig(os.path.join(save_dir, f"{self.base_name}_new_spectrum.svg"), bbox_inches="tight")
        fig2.savefig(os.path.join(save_dir, f"{self.base_name}_new_WLpeaks.svg"), bbox_inches="tight")
        fig3.savefig(os.path.join(save_dir, f"{self.base_name}_new_Ipeaks.svg"), bbox_inches="tight")
        fig4.savefig(os.path.join(save_dir, f"{self.base_name}_new_WLpeaks2.svg"), bbox_inches="tight")

        # Save data to .mat file
        d_OSA = {
            "IDtag": self.get_IDtag(self.path.name),  # Add IDtag for multi_osa compatibility
            "peak_power": peak_pows,
            "peak_wavelength": peak_wls,
            "current_mA": OSA_df["Current (mA)"].tolist(),
            "temperature_C": OSA_df["Temperature (C)"].tolist(),
            "optical_power_dBm": OSA_df["Optical Power (dBm)"].tolist(),
            "wavelength_nm": OSA_df["Wavelength (nm)"].tolist()
        }
        
        # Add polynomial fit data if available
        if 'poly_coeffs' in locals() and 'poly_coeffs2' in locals():
            d_OSA["polyfit_peakWL_vs_I_deg2_coeffs"] = poly_coeffs.tolist()
            d_OSA["polyfit_peakWL_vs_I_deg3_coeffs"] = poly_coeffs2.tolist()
            
        # Save with _new suffix for compatibility with multi_osa.py
        sio.savemat(os.path.join(save_dir, f"{self.base_name}_new.mat"), d_OSA, appendmat=True)

        print(f"Outputs saved in: {save_dir}")
        #print(d_OSA)
        print(OSA_df)
        
    def get_IDtag(self, filename: str) -> str:
        """Extract IDtag from filename using same method as multi_LIV"""
        import re
        from pathlib import Path
        
        base = Path(filename).stem
        # Expanded regex to handle more variations, including '_clad' and other suffixes
        match = re.search(r"Chip\w+_R\d+(_clad)?", base)
        if match:
            id_tag = match.group(0)  # Retain '_clad' if present
        else:
            id_tag = "Unknown_ID"

        # Detailed logging for debugging
        print(f"Debug: OSAclass - Filename: {filename}, Base: {base}, Extracted ID Tag: {id_tag}")
        return id_tag
    



if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        # Use command line argument as the file path
        csv_file = Path(sys.argv[1])
    else:
        # Default test file path - update to your local path
        csv_file = Path(r"C:\Users\jsheri1\Desktop\20250403_Shuksan_ANT_Light2025_WaferscaleMeasurements\OSA\Oband_DelayLines")
        # Find the first CSV file
        csv_files = list(csv_file.rglob("*.csv"))
        if csv_files:
            csv_file = csv_files[0]
        else:
            print("No CSV files found in the default directory")
            sys.exit(1)
            
    if not csv_file.exists():
        raise FileNotFoundError(f"Cannot find input CSV: {csv_file}")
    
    print(f"Processing file: {csv_file}")
    osa = OSAclass(str(csv_file))


