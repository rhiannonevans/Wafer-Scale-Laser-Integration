
import os
import pandas as pd
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import threshold as thresh

""" 
    WLM class for processing Wavelength Meter measurement files (LIV-type files with additional wavelength data). Processes raw measurement csvs, 
    organizes data and computed values of interest, then saves to a '_loss_data.csv' file and generates plots.
    Plots (for each readable channel):
            - LI curve (mW)
            - LI curve (dBm)
            - VI curve
            - Wavelength vs Temperature
            - Wavelength vs Current
            - I * dV/dI curve (differential resistance) - with fit
            - Second and third derivatives of LI curve

    Computed Values:
            - Threshold current for each channel
            - Peak Power in channel 1
            - Voltage at peak power in channel 1
            - Current at peak power in channel 1
            - Wavelength at peak power in channel 1
"""

class WLMclass:
    def __init__(self, path, output_folder=None):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Cannot find input CSV: {self.path}")
        
        self.base_name = self.path.stem
        
        # Extract and process data and plot LI curve
        self.extract_data(output_folder=output_folder)

        #Plot IV curve and rest of WLM plots
        self.plot_iv()
        self.plot_wl_vs_temp()
        self.plot_wl_vs_current()
        #plt.show()
        return

    def plot_iv(self):
        fig2, ax2 = plt.subplots()
        ax2.plot(self.current, self.voltage, color='black', marker='o', label="IV Curve")
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
        fig, ax = plt.subplots()
        mask = self.wavelength > 1000
        ax.scatter(self.current[mask], self.wavelength[mask], color='black', marker='o')
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
            self.current = pd.to_numeric(df.loc[indices["current"]], errors='coerce') * 1000
            print(current)
        else:
            print("No current data found, aborting file...")
            return

        wavelength = df.loc[indices["wavelength"]] if indices["wavelength"] is not None else None
        if wavelength is not None:
            self.wavelength = pd.to_numeric(df.loc[indices["wavelength"]], errors='coerce')
            print("Wavelength data extracted")
        else:
            print("No Wavelength data found. Invalid File.")
            return
        
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
        print(channels)


        # Formulate comparison data (Max power of data channel and assoc current)
        if ch1_idx is not None:
            self.peak_power = channels[ch1_idx].max()
            self.peak_power_I = current[channels[ch1_idx].idxmax()]
            self.peak_power_V = voltage[channels[ch1_idx].idxmax()]
            self.peak_power_wl = wavelength[channels[ch1_idx].idxmax()]
        else:
            print("No valid data channel found for peak power calculation.")


        # Determine the output directory
        if output_folder is not None:
            self.save_dir = output_folder
        else:
            self.save_dir = self.path.parent / "WLM_Results"
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        # Get thresholds
        # PLOT differential resistance (dV/dI vs I)   
        thresh.fit_idvdi(self.current, self.voltage, self.base_name, self.save_dir)


        #plotting LI curves + finding threshold
        ch1_threshold = 0
        ch_thresholds = []

        print("plotting LI curve and finding threshold for each channel")
        num_valid = len(channels)
        if num_valid == 0:
            print("No valid channels to plot.")
        else:
            for (i, ch) in enumerate(channels):
                print(f"Processing Channel {i} with {len(ch)} data points.")
                
                # Plot all LIV curves (+derivative) and find threshold
                ch_threshold = thresh.run_liv(self.current, ch, self.base_name, self.save_dir, i)
                ch_thresholds.append(ch_threshold)
                if ch1_idx == i:
                    ch1_threshold = ch_threshold
                    print(f"Channel 1 threshold: {ch1_threshold} mA")


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
            csv_out["threshold_currents"] = str(ch_thresholds) if ch_thresholds else None
            csv_out["threshold_ch1"] = ch1_threshold
            csv_filename = self.base_name + "_loss_data.csv"
            csv_save_path = os.path.join(self.save_dir, csv_filename)
            csv_out.to_csv(csv_save_path, index=False)
            print(f"Saved all extracted data to {csv_save_path}")
        else:
            print("No valid data found to save to CSV.")

        #plt.close('all')  # Close all plots to free up memory

                        # Save all extracted data to a CSV, save computed values (peaks and thresholds) as comments
        # csv_data = {}
        # for key, idx in indices.items():
        #     if idx is not None:
        #         csv_data[key] = df.loc[idx].values
        # csv_out = pd.DataFrame(csv_data)

        # # add dBm (log) channel data if present
        # if ch0_log  is not None: csv_out["channel 0 (dBm)"] = ch0_log
        # if ch1_log  is not None: csv_out["channel 1 (dBm)"] = ch1_log
        # if ch2_log  is not None: csv_out["channel 2 (dBm)"] = ch2_log
        # if ch3_log  is not None: csv_out["channel 3 (dBm)"] = ch3_log

        # # --- prepare your computed metrics --- #
        # metrics = {
        #     "peak_power":         getattr(self, "peak_power", None),
        #     "peak_power_I":       getattr(self, "peak_power_I", None),
        #     "peak_power_V":       getattr(self, "peak_power_V", None),
        #     "threshold_currents": ch_thresholds if ch_thresholds else None,
        #     "threshold_ch1":      ch1_threshold
        # }

        # # --- write to one CSV: first the metadata, then the table --- #
        # csv_filename   = self.base_name + "_loss_data.csv"
        # csv_save_path  = Path(self.save_dir) / csv_filename

        # with open(csv_save_path, "w") as f:
        #     # write each metric as a commented line
        #     for k, v in metrics.items():
        #         if v is None:
        #             continue
        #         # pop arrays or lists straight into the header
        #         f.write(f"# {k}: {v}\n")
        #     # now dump the DataFrame
        #     csv_out.to_csv(f, index=False)

        # print(f"Saved all extracted data + metrics to {csv_save_path}")



            

if __name__ == "__main__":
    csv_file = Path(r"C:\Users\OWNER\Desktop\LIV_0604\LIV\2025_05_29_19_22_31_bothLIVwlm_1330nm_channel2_ChipD30_R0_clad\2025_05_29_19_22_31_bothLIVwlm_1330nm_channel2_ChipD30_R0_clad.csv")
    if not csv_file.exists():
        raise FileNotFoundError(f"Cannot find input CSV: {csv_file}")
    WLMclass(str(csv_file))