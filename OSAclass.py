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
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Cannot find input CSV: {self.path}")
        
        self.base_name = self.path.stem
        self.cmap = plt.get_cmap('inferno')
        
        # Load the CSV file data
        self.extract_data(output_folder=output_folder)

        self.peak_pows = []
        self.peak_wls = []

        self.plot_WL_L()
        self.plot_current_vs_peak_power()
        self.plot_wl_vs_peak_power()
        self.plot_current_vs_peak_wavelength()

        self.save_to_csv(outpath=output_folder)
        print(self.data)

        #plt.show()
        return
    
    
    def extract_data(self, output_folder=None):
        df = pd.read_csv(self.path, header=None, on_bad_lines="skip", engine="python", skiprows=24)
        
        # Organize into sweeps (by groups of 2 - assuming two data points per sweep)
        df["Sweep"] = df.index // 2

        # Calculate number of sweeps
        num_sweeps = df["Sweep"].count() / 2
        print(num_sweeps)

        # Re-read file for longer data rows
        df2 = pd.read_csv(self.path, header=None, skiprows=26, on_bad_lines="skip", engine="python")
        
        # Filter rows to extract the desired titles
        extract = ["Wavelength (nm)", "Optical power (dBm)"]
        df2 = df2[df2[0].isin(extract)]
        
        # Group rows in sequential pairs
        df2["Sweep"] = df2.index // 2
        
        # Adjust the "Sweep" column in df2 to match df
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
        # Convert current from A to mA
        curr[1] = curr[1].astype(float) * 1000 

        self.temperature = temp
        self.current = curr
        
        # Ensure that the lengths match
        if len(curr) != len(temp):
            raise ValueError("Mismatch between Current and Temperature data lengths.")
        
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
        
        self.data = df2_merged
        return

    def save_to_csv(self, outpath=None):
        if outpath is None:
            outpath = self.path.parent / self.path.name.replace('.csv', '_loss_data.csv')
        # 1) compute your metrics
        metrics = {
            "max_peak_power_dBm":   max(self.peak_pows),
            "mean_peak_power_dBm":  np.mean(self.peak_pows),
            "max_peak_wavelength_nm":   max(self.peak_wls),
            "mean_peak_wavelength_nm":  np.mean(self.peak_wls),
            "degree_2_fit_coeffs": self.d2coeffs,
            "degree_3_fit_coeffs": self.d3coeffs
        }

        # 2) open file, write metrics as commented key: value
        with open(outpath, "w") as f:
            for k, v in metrics.items():
                f.write(f"# {k}: {v}\n")
            # 3) now dump your raw data
            self.data.to_csv(f, index=True)

        print(f"Wrote CSV with metrics header to {outpath}")

    
    def plot_WL_L(self):
        """
        Plot Wavelength vs Optical Power for each sweep.
        """
        sweeps = list(self.data.index)
        n = len(sweeps)
        # generate n evenly spaced values in [0,1]
        normed = np.linspace(0, 1, n)

        plt.figure(figsize=(10, 6))
        for t, sweep in enumerate(sweeps):
            c = self.cmap(normed[t])  # now evenly samples the cmap
            wavelength = self.data.at[sweep, "Wavelength (nm)"]
            power     = self.data.at[sweep, "Optical Power (dBm)"]
            plt.plot(wavelength, power,
                        label=f"Sweep {sweep}",
                        color=c)
             
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Optical Power (dBm)')
        plt.title('Wavelength vs Optical Power')
        plt.legend()
        plt.grid()
        plt.savefig(self.path.parent / self.path.name.replace('.csv', '_wl_v_pow.png'))

        #plt.show()
        return
    
    def plot_current_vs_peak_power(self):
        """
        Plot Current vs Peak Optical Power for each sweep.
        """
        sweeps = list(self.data.index)
        n = len(sweeps)
        # generate n evenly spaced values in [0,1]
        normed = np.linspace(0, 1, n)

        plt.figure(figsize=(10, 6))
        for t, sweep in enumerate(sweeps):
            color = self.cmap(normed[t])

            # --- pull out the lists from the DataFrame cell ---
            power_list = self.data.at[sweep, "Optical Power (dBm)"]
            current  = self.data.at[sweep, "Current (mA)"]

            # convert to numpy arrays and find the index of the max power
            power_arr = np.array(power_list, dtype=float)

            idx_max   = int(np.argmax(power_arr))
            peak_pow  = power_arr[idx_max]
            self.peak_pows.append(peak_pow)

            plt.scatter(
                current,
                peak_pow,
                color=color,
                label=f"Sweep {sweep}"
            )
        
        plt.xlabel('Current (mA)')
        plt.ylabel('Peak Optical Power (dBm)')
        plt.title('Current vs Peak Optical Power')
        plt.grid()
        plt.legend(title='Sweep')
        plt.tight_layout()
        plt.savefig(self.path.parent / self.path.name.replace('.csv', '_I_v_peakpow.png'))
        #plt.show()
        return
    
    def plot_current_vs_peak_wavelength(self):
        """
        Plot Current vs Peak Wavelength for each sweep.
        """

        d2fig, d2ax = plt.subplots(figsize=(10, 6))
        d3fig, d3ax = plt.subplots(figsize=(10, 6))

        sweeps = list(self.data.index)
        n = len(sweeps)
        normed = np.linspace(0, 1, n)


        for t, sweep in enumerate(sweeps):
            color = self.cmap(normed[t])

            # --- pull out the lists from the DataFrame cell ---
            wavelength_list = self.data.at[sweep, "Wavelength (nm)"]
            current  = self.data.at[sweep, "Current (mA)"]

            # convert to numpy arrays and find the index of the max wavelength
            wavelength_arr = np.array(wavelength_list, dtype=float)

            idx_max   = int(np.argmax(wavelength_arr))
            peak_wl  = wavelength_arr[idx_max]
            self.peak_wls.append(peak_wl)

            d2ax.scatter(
                current,
                peak_wl,
                color=color,
                label=f"Sweep {sweep}"
            )
            d3ax.scatter(
                current,
                peak_wl,
                color=color,
                label=f"Sweep {sweep}"
            )
        
        
        fit_peaks = np.array(self.peak_wls)
        fit_curr = self.data["Current (mA)"].values  # current in mA

        d2_fit = np.polyfit(fit_curr, fit_peaks, 2)  # 2nd-degree polynomial fit
        d2_func = np.poly1d(d2_fit)

        d3_fit = np.polyfit(fit_curr, fit_peaks, 3)  # 3rd-degree polynomial fit
        d3_func = np.poly1d(d3_fit)

        # Generate fit line
        fit_x_vals2 = np.linspace(fit_curr.min(), fit_curr.max(), 300)
        fit_y_vals2 = d2_func(fit_x_vals2)
        d2ax.plot(fit_x_vals2, fit_y_vals2, 'k--', linewidth=2, label="2nd Deg. Fit")

        # Generate fit line
        fit_x_vals3 = np.linspace(fit_curr.min(), fit_curr.max(), 300)
        fit_y_vals3 = d3_func(fit_x_vals3)
        d3ax.plot(fit_x_vals3, fit_y_vals3, 'k--', linewidth=2, label="3rd Deg. Fit")

        d2ax.set_xlabel('Current (mA)')
        d2ax.set_ylabel('Peak Wavelength (nm)') 
        d2ax.set_title('Current vs Peak Wavelength (2nd Degree Fit)')
        d2ax.grid()
        d2ax.legend(title='Sweep')

        d3ax.set_xlabel('Current (mA)')
        d3ax.set_ylabel('Peak Wavelength (nm)')
        d3ax.set_title('Current vs Peak Wavelength (3rd Degree Fit)')
        d3ax.grid()
        d3ax.legend(title='Sweep')

        self.d2coeffs = d2_func.coefficients
        self.d3coeffs = d3_func.coefficients

        # Annotate polynomial equation on the plot
        eq_text2 = (f"Fit: y = {d3_fit[0]:.3e}x³ + {d3_fit[1]:.3e}x² + {d3_fit[2]:.3e}x + {d3_fit[3]:.3f}")
        eq_text = f"Fit: y = {d2_fit[0]:.3e}x² + {d2_fit[1]:.3e}x + {d2_fit[2]:.3f}"

        d2ax.text(0.05, 0.95, eq_text, transform=d2ax.transAxes, fontsize=9, 
                  verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.6))
        
        d3ax.text(0.05, 0.95, eq_text2, transform=d3ax.transAxes, fontsize=9, 
                  verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.6))


        d2fig.savefig(self.path.parent / self.path.name.replace('.csv', '_d2fit_I_v_peakWL.png'))
        d3fig.savefig(self.path.parent / self.path.name.replace('.csv', '_d3fit_I_v_peakWL.png'))
        #plt.show()
        return
    
    def plot_wl_vs_peak_power(self):
        """
        Plot Wavelength vs Peak Optical Power for each sweep.
        """
        sweeps = list(self.data.index)
        n = len(sweeps)
        normed = np.linspace(0, 1, n)

        fig, ax = plt.subplots(figsize=(10, 6))
        for t, sweep in enumerate(sweeps):
            color = self.cmap(normed[t])

            # --- pull out the lists from the DataFrame cell ---
            power_list = self.data.at[sweep, "Optical Power (dBm)"]
            wl_list    = self.data.at[sweep, "Wavelength (nm)"]

            # convert to numpy arrays and find the index of the max power
            power_arr = np.array(power_list, dtype=float)
            wl_arr    = np.array(wl_list,    dtype=float)

            idx_max   = int(np.argmax(power_arr))
            peak_pow  = power_arr[idx_max]
            peak_wl   = wl_arr[idx_max]

            self.data.at[sweep, "Peak Power (dBm)"] = peak_pow
            self.data.at[sweep, "Peak Wavelength (nm)"] = peak_wl

            ax.scatter(
                peak_wl,
                peak_pow,
                color=color,
                label=f"Sweep {sweep}"
            )

        ax.set_xlabel('Wavelength (nm)')
        ax.set_ylabel('Peak Optical Power (dBm)')
        ax.set_title('Wavelength vs Peak Optical Power')
        ax.grid(True)
        ax.legend(title='Sweep')
        fig.tight_layout()

        fig.savefig(self.path.parent / self.path.name.replace('.csv', '_wl_v_peakpow.png'))
        #plt.show()
        return
    
    def read_data(self):
        import io

        data_file = self.path.parent / self.path.name.replace('.csv', '_loss_data.csv')

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
            # array‐like?
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
        # print(data_io)
        # print(df)

        # # now you have:
        # #   meta — a dict of { str → float or np.ndarray }
        # #   df   — your per‐sweep DataFrame
        # print("Metadata keys:", meta.keys())
        # for k,v in meta.items():
        #     print(f"  {k} →", v)
        # print("\nData head:")
        # print(df.head())
    



if __name__ == "__main__":
    csv_file = Path(r"C:\Users\OWNER\Desktop\osa_data\2025_04_04_17_36_58_OSA_1330nm_ChipC32_R2\2025_04_04_17_36_58_OSA_1330nm_ChipC32_R2.csv")
    if not csv_file.exists():
        raise FileNotFoundError(f"Cannot find input CSV: {csv_file}")
    osa = OSAclass(str(csv_file))
    meta, df = osa.read_data()
    print("Metadata:", meta)
    print("DataFrame head:")
    print(df.head())

    
