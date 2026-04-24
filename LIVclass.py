import os
import pandas as pd
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import threshold as thresh
import scipy.io

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
    # Font size and figure defaults for consistent plotting
    FONT_AXIS_LABEL = 14
    FONT_AXIS_TICKS = 12
    FONT_LEGEND = 12
    FONT_TITLE = 14
    DEFAULT_FIGSIZE = (8, 8)

    def __init__(self, path, output_folder=None):
        plt.close('all')  # Close all plots to free up memory
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Cannot find input CSV: {self.path}")
        
        self.base_name = self.path.stem
        
        # Load the CSV file
        self.extract_data(output_folder=output_folder) # also computed thresholds, max power, and plots ALL LI curves and differential resistance
        self.plot_iv()
        # Create LIV+Voltage overlay plots for files in the same data folder
        try:
            self.plot_liv_voltage_overlay()
        except Exception as e:
            print(f"Warning: plot_liv_voltage_overlay failed: {e}")
        #plt.show()
        return

    def plot_iv(self):
        fig2, ax2 = plt.subplots(figsize=self.DEFAULT_FIGSIZE)
        ax2.plot(self.current, self.voltage, color='black', marker='o', label="IV Curve")
        ax2.set_title(f"Current vs Voltage", fontsize=self.FONT_TITLE)
        ax2.set_xlabel("Current (mA)", fontsize=self.FONT_AXIS_LABEL)
        ax2.set_ylabel("Voltage (V)", fontsize=self.FONT_AXIS_LABEL)
        ax2.grid(True)
        ax2.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)

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
        #print("Indices found:", indices)
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
        #print(channels)


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
        ch0_threshold = np.nan
        ch1_threshold = np.nan
        ch2_threshold = np.nan
        ch3_threshold = np.nan
        
        # Initialize slope efficiency variables for each channel
        ch0_slope_efficiency = np.nan
        ch1_slope_efficiency = np.nan
        ch2_slope_efficiency = np.nan
        ch3_slope_efficiency = np.nan
        
        # Initialize voltage parameter variables for each channel
        ch0_voltage_param = np.nan
        ch1_voltage_param = np.nan
        ch2_voltage_param = np.nan
        ch3_voltage_param = np.nan

        print("plotting LI curve and finding threshold for each channel")
        num_valid = len(channels)
        if num_valid == 0:
            print("No valid channels to plot.")
        else:
            for (i, ch) in enumerate(channels):
                print(f"Processing Channel {i} with {len(ch)} data points.")

                # Plot all LIV curves (+derivative) and find threshold, slope efficiency, and voltage
                ch_threshold, ch_slope_eff, ch_voltage = thresh.run_liv(
                    self.current, ch, self.base_name, self.save_dir, i, self.voltage
                )
                
                if ch_threshold is None:
                    ch_threshold = np.nan
                if ch_slope_eff is None:
                    ch_slope_eff = np.nan
                if ch_voltage is None:
                    ch_voltage = np.nan

                # Save values to the corresponding variables
                if i == 0:
                    ch0_threshold = ch_threshold
                    ch0_slope_efficiency = ch_slope_eff
                    ch0_voltage_param = ch_voltage
                elif i == 1:
                    ch1_threshold = ch_threshold
                    ch1_slope_efficiency = ch_slope_eff
                    ch1_voltage_param = ch_voltage
                elif i == 2:
                    ch2_threshold = ch_threshold
                    ch2_slope_efficiency = ch_slope_eff
                    ch2_voltage_param = ch_voltage
                elif i == 3:
                    ch3_threshold = ch_threshold
                    ch3_slope_efficiency = ch_slope_eff
                    ch3_voltage_param = ch_voltage

                print(f"Channel {i} threshold: {ch_threshold} mA")
                if not np.isnan(ch_slope_eff):
                    print(f"Channel {i} slope efficiency: {ch_slope_eff:.4f} mW/mA")
                if not np.isnan(ch_voltage):
                    print(f"Channel {i} voltage parameter: {ch_voltage:.3f} V")

        data_dict = {
            "current": self.current,
            "voltage": self.voltage,
            "temperature": self.temperature,
            "channel_0": ch0,
            "channel_1": ch1,
            "channel_2": ch2,
            "channel_3": ch3,
            "channel_0_log": ch0_log,
            "channel_1_log": ch1_log,
            "channel_2_log": ch2_log,
            "channel_3_log": ch3_log,
            "ch0_threshold": ch0_threshold,
            "ch1_threshold": ch1_threshold,
            "ch2_threshold": ch2_threshold,
            "ch3_threshold": ch3_threshold,
            "ch0_slope_efficiency": ch0_slope_efficiency,
            "ch1_slope_efficiency": ch1_slope_efficiency,
            "ch2_slope_efficiency": ch2_slope_efficiency,
            "ch3_slope_efficiency": ch3_slope_efficiency,
            "ch0_voltage_param": ch0_voltage_param,
            "ch1_voltage_param": ch1_voltage_param,
            "ch2_voltage_param": ch2_voltage_param,
            "ch3_voltage_param": ch3_voltage_param,
            "peak_power": self.peak_power,
            "peak_power_I": self.peak_power_I,
            "peak_power_V": self.peak_power_V
        }


        # Save the data dictionary to a .mat file in the output folder
        mat_filename = self.base_name + ".mat"
        self.save_path_mat = os.path.join(self.save_dir, mat_filename)
        scipy.io.savemat(self.save_path_mat, data_dict)
        print(f"Data dictionary saved to {self.save_path_mat}")


    def plot_liv_voltage_overlay(self):
        """
        Scan the current data folder for .mat files and create overlay LIV plots
        grouped by wavelength substring in filenames.

        - 1310nm & 1330nm: use `channel_2` (left axis) and `voltage` (right axis)
        - 1550nm: use `channel_3` (left axis) and `voltage` (right axis)

        Saves PNG files into `self.save_dir`.
        """
        import scipy.io as sio
        from matplotlib.lines import Line2D

        parent = self.path.parent
        # search for .mat files in the parent folder (include subfolders)
        mat_files = [p for p in parent.rglob('*.mat') if p.is_file()]
        if not mat_files:
            # also check the save_dir for mat files
            mat_files = [p for p in Path(self.save_dir).rglob('*.mat') if p.is_file()]

        # Group files by wavelength keyword
        groups = {'1310nm': [], '1330nm': [], '1550nm': []}
        for mf in mat_files:
            name = mf.name.lower()
            if '1310' in name:
                groups['1310nm'].append(mf)
            elif '1330' in name:
                groups['1330nm'].append(mf)
            elif '1550' in name:
                groups['1550nm'].append(mf)

        cmap = plt.get_cmap('inferno')
        colors = cmap(np.linspace(0.25, 0.75, 3))
        color_map = {'1310nm': colors[0], '1330nm': colors[1], '1550nm': colors[2]}

        # Helper to load arrays from .mat safely
        def load_array(mdict, key):
            try:
                arr = np.array(mdict[key]).flatten()
                return arr
            except Exception:
                return None

        # Plot 1310 & 1330 together (channel_2)
        if groups['1310nm'] or groups['1330nm']:
            fig, ax = plt.subplots(figsize=(10, 7))
            ax_r = ax.twinx()
            for wl in ('1310nm', '1330nm'):
                for mf in groups[wl]:
                    try:
                        mat = sio.loadmat(str(mf))
                    except Exception:
                        print(f"Skipping unreadable mat file: {mf}")
                        continue
                    current = load_array(mat, 'current')
                    ch2 = load_array(mat, 'channel_2')
                    voltage = load_array(mat, 'voltage')
                    if current is None or ch2 is None:
                        continue
                    ax.plot(current, ch2, color=color_map[wl], linewidth=1.8, alpha=0.85)
                    if voltage is not None:
                        ax_r.plot(current, voltage, color=color_map[wl], linestyle='--', linewidth=1.2, alpha=0.7)

            ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
            ax.set_ylabel('Power (a.u.) - channel_2', fontsize=self.FONT_AXIS_LABEL)
            ax_r.set_ylabel('Voltage (V)', fontsize=self.FONT_AXIS_LABEL)
            ax.set_title('LIV (channel_2) and Voltage — 1310nm vs 1330nm', fontsize=self.FONT_TITLE)
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
            ax_r.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)
            legend_lines = [Line2D([0], [0], color=color_map['1310nm'], lw=3), Line2D([0], [0], color=color_map['1330nm'], lw=3)]
            ax.legend(legend_lines, ['1310nm', '1330nm'], fontsize=self.FONT_LEGEND, loc='best')
            save_path = Path(self.save_dir) / f"{self.base_name}_LIV_channel2_voltage_1310_1330.png"
            fig.tight_layout()
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            print(f"Saved LIV+Voltage overlay (1310/1330) to {save_path}")

        # Plot 1550 (channel_3)
        if groups['1550nm']:
            fig2, ax2 = plt.subplots(figsize=(10, 7))
            ax2_r = ax2.twinx()
            for mf in groups['1550nm']:
                try:
                    mat = sio.loadmat(str(mf))
                except Exception:
                    print(f"Skipping unreadable mat file: {mf}")
                    continue
                current = load_array(mat, 'current')
                ch3 = load_array(mat, 'channel_3')
                voltage = load_array(mat, 'voltage')
                if current is None or ch3 is None:
                    continue
                ax2.plot(current, ch3, color=color_map['1550nm'], linewidth=1.8, alpha=0.85)
                if voltage is not None:
                    ax2_r.plot(current, voltage, color=color_map['1550nm'], linestyle='--', linewidth=1.2, alpha=0.7)

            ax2.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
            ax2.set_ylabel('Power (a.u.) - channel_3', fontsize=self.FONT_AXIS_LABEL)
            ax2_r.set_ylabel('Voltage (V)', fontsize=self.FONT_AXIS_LABEL)
            ax2.set_title('LIV (channel_3) and Voltage — 1550nm', fontsize=self.FONT_TITLE)
            ax2.grid(True, alpha=0.3)
            ax2.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
            ax2_r.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)
            legend_line = Line2D([0], [0], color=color_map['1550nm'], lw=3)
            ax2.legend([legend_line], ['1550nm'], fontsize=self.FONT_LEGEND, loc='best')
            save_path2 = Path(self.save_dir) / f"{self.base_name}_LIV_channel3_voltage_1550.png"
            fig2.tight_layout()
            fig2.savefig(save_path2, dpi=300, bbox_inches='tight')
            plt.close(fig2)
            print(f"Saved LIV+Voltage overlay (1550) to {save_path2}")



            

if __name__ == "__main__":
    csv_file = Path(r"C:\Users\OWNER\Downloads\LIV (4)\LIV\2025_06_27_13_53_34_LIV_1310nm_ChipC32_R4_clad\2025_06_27_13_53_34_LIV_1310nm_ChipC32_R4_clad.csv")
    if not csv_file.exists():
        raise FileNotFoundError(f"Cannot find input CSV: {csv_file}")
    liv = LIVclass(str(csv_file))

    matdata = scipy.io.loadmat(liv.save_path_mat)
    print(matdata['channel_1'])
    print("Loaded data from .mat file:")
    # for key, value in matdata.items():
    #     print(f"  {key}: {value}")