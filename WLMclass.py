
import os
import pandas as pd
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
#import threshold as thresh
import scipy.io

""" 
    WLM class for processing Wavelength Meter measurement files (LIV-type files with additional wavelength data). Processes raw measurement csvs, 
    organizes data and computed values of interest, then saves to a '_loss_data.csv' file and generates plots.
    Plots (for each readable channel):
            - LI curve (mW)
            - LI curve (dBm)
            - VI curve
            - Wavelength vs Temperature
            - Wavelength vs Current

    Computed Values:
            - Peak Power in channel 1
            - Voltage at peak power in channel 1
            - Current at peak power in channel 1
            - Wavelength at peak power in channel 1
"""

class WLMclass:
    def __init__(self, path, output_folder=None):
        plt.close('all')  # Close all plots to free up memory
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Cannot find input CSV: {self.path}")
        
        self.base_name = self.path.stem
        
        # Extract and process data and plot LI curve
        self.extract_data(output_folder=output_folder)

        #Plot IV curve and rest of WLM plots
        self.plot_iv()
        self.plot_li()
        
        # Only plot wavelength data if it exists
        if self.has_wavelength:
            self.plot_wl_vs_temp()
            self.plot_wl_vs_current()
        else:
            print("Info: Skipping wavelength plots - no wavelength data available")
        #plt.show()
        return

    def plot_iv(self):
        fig2, ax2 = plt.subplots()
        ax2.plot(self.current*1000, self.voltage, color='black', marker='o', label="IV Curve")
        ax2.set_title(f"Current vs Voltage")
        ax2.set_xlabel("Current (mA)")
        ax2.set_ylabel("Voltage (V)")
        ax2.grid(True)

        #save svg
        svg_filename2 = self.base_name + f"_IVcurve.svg"
        save_path_svg2 = os.path.join(self.save_dir, svg_filename2)
        fig2.savefig(save_path_svg2, format="svg", bbox_inches="tight")
        print(f"Saved IV curve svg to {save_path_svg2}")
        #save png
        png_filename2 = self.base_name + f"_IVcurve.png"
        save_path_png2 = os.path.join(self.save_dir, png_filename2)
        fig2.savefig(save_path_png2, format="png", bbox_inches="tight")
        print(f"Saved IV curve png to {save_path_png2}") 

        return
    

    def plot_wl_vs_temp(self):
        if self.wavelength is None or not hasattr(self, 'has_wavelength') or not self.has_wavelength:
            print("Info: Skipping wavelength vs temperature plot - no wavelength data")
            return
            
        fig, ax = plt.subplots()
        mask = self.wavelength > 1000
        ax.scatter(self.wavelength[mask], self.temperature[mask], color='black', marker='o')
        ax.set_title("Temperature vs Wavelength")
        ax.set_ylabel("Temperature (C)")
        ax.set_xlabel("Wavelength (nm)")
        ax.grid(True)

        # Save the WL vs Temp plot as an SVG file in the output folder
        wl_temp_filename = self.base_name + "_Temp_vs_WL.svg"
        save_path_wl_temp = os.path.join(self.save_dir, wl_temp_filename)
        fig.savefig(save_path_wl_temp, format="svg", bbox_inches="tight")
        print(f"Saved Temperature vs Wavelength plot to {save_path_wl_temp}")
        
         # Save the WL vs Temp plot as an SVG file in the output folder
        wl_temp_filename1 = self.base_name + "_WL_vs_Temp.png"
        save_path_wl_temp1 = os.path.join(self.save_dir, wl_temp_filename1)
        fig.savefig(save_path_wl_temp1, format="png", bbox_inches="tight")
        print(f"Saved Temperature vs Wavelength plot to {save_path_wl_temp1}")
        return

    # WL vs current plot
    def plot_wl_vs_current(self):
        if self.wavelength is None or not hasattr(self, 'has_wavelength') or not self.has_wavelength:
            print("Info: Skipping wavelength vs current plot - no wavelength data")
            return
            
        fig, ax = plt.subplots()
        mask = self.wavelength > 1000
        ax.scatter(self.current[mask]*1000, self.wavelength[mask], color='black', marker='o')
        ax.set_title("Wavelength vs Current")
        ax.set_xlabel("Current (mA)")
        ax.set_ylabel("Wavelength (nm)")
        ax.grid(True)

        # Save the WL vs current plot as an SVG file in the output folder
        wl_current_filename = self.base_name + "_WL_vs_Current.svg"
        save_path_wl_current = os.path.join(self.save_dir, wl_current_filename)
        fig.savefig(save_path_wl_current, format="svg", bbox_inches="tight")
        print(f"Saved Wavelength vs Current plot to {save_path_wl_current}")

        wl_current_filename1 = self.base_name + "_WL_vs_Current.png"
        save_path_wl_current1 = os.path.join(self.save_dir, wl_current_filename1)
        fig.savefig(save_path_wl_current1, format="png", bbox_inches="tight")
        print(f"Saved  Wavelength vs Current plot to {save_path_wl_current1}")

        return
    
    def plot_li(self):
        
        I = self.current

        for ch_i, channel in enumerate([self.ch0, self.ch1, self.ch2, self.ch3], start=0):
            if channel is None or channel.empty:
                continue  # Skip if channel data is not available

            fig_combined, (ax2, ax3) = plt.subplots(1, 2, figsize=(14, 6))

            L = channel
            log = np.log(channel)
            # Plot LI (LOG) curve in dBm
            ax2.plot(I, log, marker='o', label='Power (dBm)')
            ax2.set_ylabel("Power (dBm)")
            ax2.set_title(f"Ch {ch_i}: Power (dBm) vs Current (mA)")
            #ax2.legend()
            ax2.grid(True)

            # Plot LI curve in mW
            ax3.plot(I, L, marker='o', label='Power (mW)')
            ax3.set_xlabel("Current (mA)")
            ax3.set_ylabel("Power (mW)")
            ax3.set_title(f"Ch {ch_i}: Power (mW) vs Current (mA)")
            #ax3.legend()
            ax3.grid(True)

            fig_combined.tight_layout()

            # Save the channel plot as an SVG file in the output folder
            svg_filename = self.base_name + f"_LI_ch{ch_i}.svg"
            save_path_svg = os.path.join(self.save_dir, svg_filename)
            fig_combined.savefig(save_path_svg, format="svg", bbox_inches="tight")
            print(f"Saved channel {ch_i} plot to {save_path_svg}")

            # Save the channel plot as an PNG file in the output folder
            png_filename = self.base_name + f"_LI_ch{ch_i}.png"
            save_path_png = os.path.join(self.save_dir, png_filename)
            fig_combined.savefig(save_path_png, format="png", bbox_inches="tight")
            print(f"Saved channel {ch_i} plot to {save_path_png}")

        return

    def extract_data(self, output_folder=None):
        df = pd.read_csv(self.path, header=None, on_bad_lines="skip", engine="python", skiprows=24)

        # Define search terms for each target row
        search_terms = {
            "current": "Current",
            "voltage": "Voltage",
            "temperature": "Temperature",
            "wavelength": "Wavelength",
            "channel 0": "0",
            "channel 1": "1",
            "channel 2": "2",
            "channel 3": "3"
        }

        # Find indices where these terms occur
        indices = {}
        for key, term in search_terms.items():
            matches = df[0].str.contains(term, case=False, na=False)
            if matches.any():
                indices[key] = matches.idxmax()
            else:
                indices[key] = None
        print("Indices found:", indices)
        # Remove the first column (used for matching)
        del df[0]

        # Extract data rows from the DataFrame
        current = df.loc[indices["current"]] if indices["current"] is not None else None
        if indices["current"] is not None:
            self.current = pd.to_numeric(df.loc[indices["current"]], errors='coerce') 
            #print(current)
        else:
            print("No current data found, aborting file...")
            return

        # Extract wavelength data - optional, not required
        wavelength = df.loc[indices["wavelength"]] if indices["wavelength"] is not None else None
        if wavelength is not None:
            self.wavelength = pd.to_numeric(df.loc[indices["wavelength"]], errors='coerce')
            print("Wavelength data extracted")
            self.has_wavelength = True
        else:
            print("Info: No Wavelength data found - will skip wavelength plots")
            self.wavelength = None
            self.has_wavelength = False
        
        # Extract voltage and temperature data - make None if not found to handle errors
        # Extract voltage data
        voltage = df.loc[indices["voltage"]] if indices["voltage"] is not None else None
        if voltage is not None:
            self.voltage = pd.to_numeric(df.loc[indices["voltage"]], errors='coerce')
            print("Voltage data extracted")
        else:
            print("No Voltage data found. Invalid File.")
            return

        # Extract temperature data
        temperature = df.loc[indices["temperature"]] if indices["temperature"] is not None else None
        if temperature is not None:
            self.temperature = pd.to_numeric(df.loc[indices["temperature"]], errors='coerce')
            print("Temperature data extracted")
        else:
            print("No Temperature data found. Invalid File.")
            return

        # Check if voltage and temperature are swapped (voltage > 20 indicates it's actually temperature)
        # CSV files sometimes have these columns swapped
        if (self.voltage > 20).any():
            print(f"Info: Detected swapped voltage/temperature - swapping them back")
            self.voltage, self.temperature = self.temperature, self.voltage
            voltage, temperature = self.temperature, self.voltage  # Also swap local variables

        ch0 = pd.to_numeric(df.loc[indices["channel 0"]],errors='coerce') if indices["channel 0"] is not None else None
        ch1 = pd.to_numeric(df.loc[indices["channel 1"]],errors='coerce') if indices["channel 1"] is not None else None
        ch2 = pd.to_numeric(df.loc[indices["channel 2"]],errors='coerce')  if indices["channel 2"] is not None else None
        ch3 = pd.to_numeric(df.loc[indices["channel 3"]],errors='coerce')  if indices["channel 3"] is not None else None

        ch0_log = np.log(ch0) if ch0 is not None else None
        ch1_log = np.log(ch1) if ch1 is not None else None
        ch2_log = np.log(ch2) if ch2 is not None else None
        ch3_log = np.log(ch3) if ch3 is not None else None

        if ch0 is not None:
            ch1_idx = 1
        else:
            ch1_idx = 0

        channels = []
        channels = [ch for ch in [ch0, ch1, ch2, ch3] if ch is not None]
        print("Channels found:", len(channels))
        #print(channels)


        # Formulate comparison data (Max power of data channel and assoc current)
        if ch1_idx is not None:
            self.peak_power = channels[ch1_idx].max()
            self.peak_power_I = current[channels[ch1_idx].idxmax()]
            self.peak_power_V = voltage[channels[ch1_idx].idxmax()]
            # Only set peak_power_wl if wavelength data exists
            if wavelength is not None:
                self.peak_power_wl = wavelength[channels[ch1_idx].idxmax()]
            else:
                self.peak_power_wl = None
        else:
            print("No valid data channel found for peak power calculation.")


        # Determine the output directory
        if output_folder is not None:
            self.save_dir = str(output_folder)  # Ensure it's a string, not Path
        else:
            self.save_dir = str(self.path.parent / "WLM_Results")
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        # # Get thresholds
        # # PLOT differential resistance (dV/dI vs I)   
        # thresh.fit_idvdi(self.current, self.voltage, self.base_name, self.save_dir)


        # #plotting LI curves + finding threshold
        # ch1_threshold = 0
        # ch_thresholds = []

        # print("plotting LI curve and finding threshold for each channel")
        # num_valid = len(channels)
        # if num_valid == 0:
        #     print("No valid channels to plot.")
        # else:
        #     for (i, ch) in enumerate(channels):
        #         print(f"Processing Channel {i} with {len(ch)} data points.")
                
        #         # Plot all LIV curves (+derivative) and find threshold
        #         ch_threshold = thresh.run_liv(self.current, ch, self.base_name, self.save_dir, i)
        #         ch_thresholds.append(ch_threshold)
        #         if ch1_idx == i:
        #             ch1_threshold = ch_threshold
        #             print(f"Channel 1 threshold: {ch1_threshold} mA")

        self.ch0 = ch0
        self.ch1 = ch1
        self.ch2 = ch2
        self.ch3 = ch3
        self.ch0_log = ch0_log
        self.ch1_log = ch1_log
        self.ch2_log = ch2_log
        self.ch3_log = ch3_log

        # Replace None values with NaN arrays for .mat file compatibility
        # scipy.io.savemat cannot save None values or pandas Series directly
        # Convert all pandas Series to numpy arrays
        nan_array = np.full_like(self.current, np.nan)
        
        data_dict = {
            "current": np.array(self.current),
            "voltage": np.array(self.voltage),
            "temperature": np.array(self.temperature),
            "wavelength": np.array(self.wavelength) if self.wavelength is not None else nan_array,
            "channel_0": np.array(ch0) if ch0 is not None else nan_array,
            "channel_1": np.array(ch1) if ch1 is not None else nan_array,
            "channel_2": np.array(ch2) if ch2 is not None else nan_array,
            "channel_3": np.array(ch3) if ch3 is not None else nan_array,
            "channel_0_log": np.array(ch0_log) if ch0_log is not None else nan_array,
            "channel_1_log": np.array(ch1_log) if ch1_log is not None else nan_array,
            "channel_2_log": np.array(ch2_log) if ch2_log is not None else nan_array,
            "channel_3_log": np.array(ch3_log) if ch3_log is not None else nan_array,
            "peak_power": self.peak_power,
            "peak_power_I": self.peak_power_I,
            "peak_power_V": self.peak_power_V,
            "peak_power_wl": self.peak_power_wl if self.peak_power_wl is not None else np.nan
        }


        # Save the data dictionary to a .mat file in the output folder
        mat_filename = self.base_name + ".mat"
        save_path_mat = os.path.join(self.save_dir, mat_filename)
        scipy.io.savemat(save_path_mat, data_dict)
        print(f"Data dictionary saved to {save_path_mat}")
        
        # Debug: Print summary of what was saved
        num_ch = sum([1 for ch in [ch0, ch1, ch2, ch3] if ch is not None])
        print(f"  - Saved {len(self.current)} data points")
        print(f"  - Saved {num_ch} channels with power data")
        for i, ch in enumerate([ch0, ch1, ch2, ch3]):
            if ch is not None:
                print(f"    Channel {i}: {len(ch)} points, range [{np.nanmin(ch):.6f}, {np.nanmax(ch):.6f}] mW")
        if self.wavelength is not None:
            print(f"  - Wavelength data included")
        else:
            print(f"  - No wavelength data")
            

if __name__ == "__main__":
    csv_file = Path(r"C:\Users\OWNER\Downloads\LIV (4)\LIV\2025_06_27_13_49_37_wlmLIV_1310nm_ChipC32_R4_clad\2025_06_27_13_49_37_wlmLIV_1310nm_ChipC32_R4_clad.csv")
    if not csv_file.exists():
        raise FileNotFoundError(f"Cannot find input CSV: {csv_file}")
    WLMclass(str(csv_file))