import os
import pandas as pd
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import threshold as thresh

""" 
    LIV class for processing probe station measurement files with no wavelength data. Processes raw measurement csvs, organizes data 
    and computed values of interest, then saves to a '_loss_data.csv' file and generates plots.
    Plots (for each readable channel):
            - LI curve (mW)
            - LI curve (dBm)
            - Second and third derivatives of LI curve
            - VI curve
            - I * dV/dI curve (differential resistance) - with fit

    Computed Values:
            - Threshold current for each channel
            - Peak Power in channel 1
            - Voltage at peak power in channel 1
            - Current at peak power in channel 1
"""

class LIVclass:
    def __init__(self, path, output_folder=None):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Cannot find input CSV: {self.path}")
        
        self.base_name = self.path.stem
        
        # Load the CSV file
        self.extract_data(output_folder=output_folder) # also computed thresholds, max power, and plots ALL LI curves and differential resistance
        self.plot_iv()
        #plt.show()
        return

    def plot_iv(self):
        fig2, ax2 = plt.subplots()
        ax2.plot(self.current, self.voltage, color='black', marker='o', label="IV Curve")
        ax2.set_title(f"Current vs Voltage")
        ax2.set_xlabel("Current (mA)")
        ax2.set_ylabel("Voltage (V)")
        ax2.grid(True)

        base_name = self.base_name

        #save svg
        svg_filename2 = base_name + f"_IVcurve.svg"
        save_path_svg2 = os.path.join(self.save_dir, svg_filename2)
        fig2.savefig(save_path_svg2, format="svg", bbox_inches="tight")
        print(f"Saved IV curve svg to {save_path_svg2}")
        #save png
        png_filename2 = base_name + f"_IVcurve.png"
        save_path_png2 = os.path.join(self.save_dir, png_filename2)
        fig2.savefig(save_path_png2, format="png", bbox_inches="tight")
        print(f"Saved IV curve png to {save_path_png2}") 

        return

    def extract_data(self, output_folder=None):
        df = pd.read_csv(self.path, header=None, on_bad_lines="skip", engine="python", skiprows=24)

        # Define search terms for each target row
        search_terms = {
            "current": "Current",
            "voltage": "Voltage",
            "temperature": "Temperature",
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
            self.current = pd.to_numeric(df.loc[indices["current"]], errors='coerce') * 1000
        else:
            print("No current data found for LIV, aborting file...")
            return

        print("Current data extracted")
        # Extract voltage and temperature data - make None if not found to handle errors
        voltage = df.loc[indices["voltage"]] if indices["voltage"] is not None else None
        temperature = df.loc[indices["temperature"]] if indices["temperature"] is not None else None
        if voltage is not None and temperature is not None:
            self.voltage = pd.to_numeric(df.loc[indices["voltage"]], errors='coerce')
            self.temperature = pd.to_numeric(df.loc[indices["temperature"]], errors='coerce')
        else:
            print("No Voltage, and/or Temperature data found. Invalid File.")
            return
        print("Voltage and Temperature data extracted")


        ch0 = pd.to_numeric(df.loc[indices["channel 0"]],errors='coerce') if indices["channel 0"] is not None else None
        ch1 = pd.to_numeric(df.loc[indices["channel 1"]],errors='coerce') if indices["channel 1"] is not None else None
        ch2 = pd.to_numeric(df.loc[indices["channel 2"]],errors='coerce')  if indices["channel 2"] is not None else None
        ch3 = pd.to_numeric(df.loc[indices["channel 3"]],errors='coerce')  if indices["channel 3"] is not None else None

        ch0_log = 10 * np.log10(ch0) if ch0 is not None else None
        ch1_log = 10 * np.log10(ch1) if ch1 is not None else None
        ch2_log = 10 * np.log10(ch2) if ch2 is not None else None
        ch3_log = 10 * np.log10(ch3) if ch3 is not None else None

        if ch0 is not None:
            ch1_idx = 1
        else:
            ch1_idx = 0

        channels = []
        channels = [ch for ch in [ch0, ch1, ch2, ch3] if ch is not None]
        print("Channels found:", len(channels))
        print(channels)


        # Formulate comparison data (Max power of data channel and assoc current)
        if ch1_idx is not None:
            self.peak_power = channels[ch1_idx].max()
            self.peak_power_I = current[channels[ch1_idx].idxmax()]
            self.peak_power_V = voltage[channels[ch1_idx].idxmax()]
        else:
            print("No valid data channel found for peak power calculation.")


        # Determine the output directory
        if output_folder is not None:
            self.save_dir = output_folder
        else:
            self.save_dir = self.path.parent / "LIV_Results"
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        # Get thresholds
        # PLOT differential resistance (dV/dI vs I)   
        thresh.fit_idvdi(self.current, self.voltage, self.base_name, self.save_dir)


        #plotting LI curves + finding threshold
        # Initialize threshold variables for each channel
        ch0_threshold = None
        ch1_threshold = None
        ch2_threshold = None
        ch3_threshold = None

        print("plotting LI curve and finding threshold for each channel")
        num_valid = len(channels)
        if num_valid == 0:
            print("No valid channels to plot.")
        else:
            for (i, ch) in enumerate(channels):
                print(f"Processing Channel {i} with {len(ch)} data points.")

                # Plot all LIV curves (+derivative) and find threshold
                ch_threshold = thresh.run_liv(self.current, ch, self.base_name, self.save_dir, i)

                # Save threshold to the corresponding variable
                if i == 0:
                    ch0_threshold = ch_threshold
                elif i == 1:
                    ch1_threshold = ch_threshold
                elif i == 2:
                    ch2_threshold = ch_threshold
                elif i == 3:
                    ch3_threshold = ch_threshold

                print(f"Channel {i} threshold: {ch_threshold} mA")

        # Save all extracted data (search terms) to a CSV
        csv_data = {}
        for key, idx in indices.items():
            if idx is not None:
                csv_data[key] = df.loc[idx].values
            else:
                csv_data[key] = None

        # Build DataFrame for CSV (only include non-None)
        csv_columns = []
        csv_rows = []
        for key, values in csv_data.items():
            if values is not None:
                csv_columns.append(key)
                csv_rows.append(values)
        if csv_rows:
            csv_out = pd.DataFrame(csv_rows, index=csv_columns).transpose()

            # add dBm (log) channel data
            csv_out["channel 0 (dBm)"] = ch0_log if ch0_log is not None else None
            csv_out["channel 1 (dBm)"] = ch1_log if ch1_log is not None else None
            csv_out["channel 2 (dBm)"] = ch2_log if ch2_log is not None else None
            csv_out["channel 3 (dBm)"] = ch3_log if ch3_log is not None else None

            # Add peak_power and related variables as new columns to the DataFrame
            csv_out["peak_power"] = self.peak_power if hasattr(self, 'peak_power') else None
            csv_out["peak_power_I"] = self.peak_power_I if hasattr(self, 'peak_power_I') else None
            csv_out["peak_power_V"] = self.peak_power_V if hasattr(self, 'peak_power_V') else None
            csv_out["threshold_currents"] = str([ch0_threshold, ch1_threshold, ch2_threshold, ch3_threshold])
            csv_out["threshold_ch0"] = ch0_threshold
            csv_out["threshold_ch1"] = ch1_threshold
            csv_out["threshold_ch2"] = ch2_threshold
            csv_out["threshold_ch3"] = ch3_threshold

            csv_filename = self.base_name + "_loss_data.csv"
            csv_save_path = os.path.join(self.save_dir, csv_filename)
            csv_out.to_csv(csv_save_path, index=False)
            print(f"Saved all extracted data to {csv_save_path}")
        else:
            print("No valid data found to save to CSV.")

        #plt.close('all')  # Close all plots to free up memory



            

if __name__ == "__main__":
    csv_file = Path(r"C:\Users\OWNER\Downloads\LIV (2)\LIV\2025_04_06_10_59_27_LIV_1310nm_ChipD22_R11\2025_04_06_10_59_27_LIV_1310nm_ChipD22_R11.csv")
    if not csv_file.exists():
        raise FileNotFoundError(f"Cannot find input CSV: {csv_file}")
    LIVclass(str(csv_file))