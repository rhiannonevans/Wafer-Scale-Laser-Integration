"""
    Processes "WLM-type" files - LIV files containing useful WL data.
    Produces .mat files and plots of data.
    Expects a CSV with Current, Wavelength, Voltage, Temperature, and multiple channels (optional channels 0 through 10) of Optical Power data.
    For comparison plots: Extracts threshold current, peak power, and associated current, wavelength, and voltage.

    Extracts peak power w associated current.
    Estimates threshold current for each channel.
    Generates LIV curves, and a differential resistance curve.
    Saves original mW power data and computed values of interest to a .mat file.

    [Author: Rhiannon H Evans]
    [Date: 2025-06-12]
"""

def process_wlm(file_path_str, output_folder=None):
    import os
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import scipy.io
    import threshold as thresh
    from scipy.optimize import curve_fit

    # Helper function to generate nicely spaced tick values
    def get_ticks(data, num_ticks, decimal_places):
        ticks = np.linspace(data.min(), data.max(), num_ticks)
        return np.round(ticks, decimals=decimal_places)

    # Expand the file path and determine the base name and location
    file_path = os.path.expanduser(file_path_str)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    file_loc = os.path.dirname(file_path)
    print(f"Looking for the file at: {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist. Please check the file path.")
    


    # Load the CSV file
    # f = open(file_path, 'r')
    # print(f"Reading file: {file_path}")
    # df = pd.read_csv(f, header=None, on_bad_lines="skip", engine="python", skiprows=23)
    # f.close()
    # print(df)
    with open(file_path, 'r') as file:
        df = pd.read_csv(file, header=None, on_bad_lines="skip", engine="python", skiprows=24)
        file.close()

    # Define search terms for each target row
    search_terms = {
        "current": "Current",
        "voltage": "Voltage",
        "temperature": "Temperature",
        "wavelength": "Wavelength",
        "channel 0": "0",
        "channel 1": "1",
        "channel 2": "2",
        "channel 3": "3",
        "channel 4": "4",
        "channel 5": "5",
        "channel 6": "6",
        "channel 7": "7",
        "channel 8": "8",
        "channel 9": "9",
        "channel 10": "10"
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
    print(df)

    # Extract data rows from the DataFrame
    current = df.loc[indices["current"]] if indices["current"] is not None else None
    if indices["current"] is not None:
        current = pd.to_numeric(df.loc[indices["current"]], errors='coerce') * 1000
        print(current)
    else:
        current = None
        print("No current data found, aborting file...")
        return

    print("Current data extracted")
    # Extract voltage and temperature data - make None if not found to handle errors
    # Extract voltage data
    voltage = df.loc[indices["voltage"]] if indices["voltage"] is not None else None
    if voltage is not None:
        voltage = pd.to_numeric(df.loc[indices["voltage"]], errors='coerce')
        print("Voltage data extracted")
    else:
        print("No Voltage data found. Invalid File.")
        return

    # Extract temperature data
    temperature = df.loc[indices["temperature"]] if indices["temperature"] is not None else None
    if temperature is not None:
        temperature = pd.to_numeric(df.loc[indices["temperature"]], errors='coerce')
        print("Temperature data extracted")
    else:
        print("No Temperature data found. Invalid File.")
        return

    wavelength = df.loc[indices["wavelength"]] if indices["wavelength"] is not None else None
    if wavelength is not None:
        wavelength = pd.to_numeric(df.loc[indices["wavelength"]], errors='coerce')
        print("Wavelength data extracted")
    else:
        print("No Wavelength data found. Invalid File.")
        return

    ch0 = pd.to_numeric(df.loc[indices["channel 0"]],errors='coerce') if indices["channel 0"] is not None else None
    ch1 = pd.to_numeric(df.loc[indices["channel 1"]],errors='coerce') if indices["channel 1"] is not None else None
    ch2 = pd.to_numeric(df.loc[indices["channel 2"]],errors='coerce')  if indices["channel 2"] is not None else None
    ch3 = pd.to_numeric(df.loc[indices["channel 3"]],errors='coerce')  if indices["channel 3"] is not None else None
    ch4 = pd.to_numeric(df.loc[indices["channel 4"]],errors='coerce')  if indices["channel 4"] is not None else None
    ch5 = pd.to_numeric(df.loc[indices["channel 5"]],errors='coerce')  if indices["channel 5"] is not None else None
    ch6 = pd.to_numeric(df.loc[indices["channel 6"]],errors='coerce')  if indices["channel 6"] is not None else None
    ch7 = pd.to_numeric(df.loc[indices["channel 7"]],errors='coerce')  if indices["channel 7"] is not None else None
    ch8 = pd.to_numeric(df.loc[indices["channel 8"]],errors='coerce')  if indices["channel 8"] is not None else None
    ch9 = pd.to_numeric(df.loc[indices["channel 9"]],errors='coerce')  if indices["channel 9"] is not None else None
    ch10 = pd.to_numeric(df.loc[indices["channel 10"]],errors='coerce')  if indices["channel 10"] is not None else None

    print("Extrated channel (power) data")

    
    channels = []
    channels = [ch for ch in [ch0, ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8, ch9, ch10] if ch is not None]
    print("Channels found:", len(channels))
    print(channels)

    if ch0 is not None:
        ch1_idx = 1
    else:
        ch1_idx = 0

    data_channel_index = ch1_idx  # Default to channel 1 (main signal)

    # # Determine the "data" channel based on the largest average value
    # data_channel_index = None
    # max_average = -np.inf
    # for i, ch in enumerate(channels):
    #     if ch is not None:
    #         avg_value = ch.mean()
    #         if avg_value > max_average:
    #             max_average = avg_value
    #             data_channel_index = i

    # if data_channel_index is not None:
    #     print(f"Data channel determined: Channel {data_channel_index} with average value {max_average}")
    # else:
    #     print("No valid data channel found.")

    # Build a dictionary with the core data for saving to a .mat file
    data_dict = {
        "current": current,
        "temperature": temperature,
        "voltage": voltage,
        "wavelength": wavelength
    }

    print("Data dictionary initialized")


    threshold_Is = []
    for i, ch in enumerate(channels):
        if ch is not None:
            data_dict[f"channel_{i}"] = ch
            print(f"Saved channel {i}:")
            
            # Assumes there is no threshold if data starts above 20mA - implies threshold has been passed
            if current[1] >= 20:
                print(f"Initial current is above 0.2A, skipping threshold detection for all channels.")
                threshold_Is.append(0.2)
            else:
                threshold = thresh.fit_guess(current, ch, show=False)
                if threshold is None or threshold == 0:
                    print(f"No threshold found for channel {i}. Setting to 0.")
                    threshold_Is.append(0)
                else:
                    threshold_Is.append(threshold)
                    print(f"Threshold current for channel {i}: {threshold}mA")

    

    print("Threshold currents:", threshold_Is)
    data_dict["threhold_currents"] = threshold_Is
    data_dict["threshold_ch1"] = threshold_Is[ch1_idx]

    # Formulate comparison data (Max power of data channel and assoc current)
    if data_channel_index is not None:
        peak_power = channels[data_channel_index].max()
        peak_power_I = current[channels[data_channel_index].idxmax()]
        peak_power_V = voltage[channels[data_channel_index].idxmax()]
        peak_power_wl = wavelength[channels[data_channel_index].idxmax()]
        data_dict["peak_power_V"] = peak_power_V
        data_dict["peak_power"] = peak_power
        data_dict["peak_power_I"] = peak_power_I
        data_dict["peak_power_WL"] = peak_power_wl
        print(f"Peak power: {data_dict['peak_power']}")
        print(f"Assoc Current: {data_dict['peak_power_I']}")
        print(f"Assoc Voltage: {data_dict['peak_power_V']}")
    else:
        print("No valid data channel found for peak power calculation.")

    # Determine the output directory
    if output_folder is not None:
        save_dir = output_folder
    else:
        save_dir = file_loc
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Save the data dictionary to a .mat file in the output folder
    mat_filename = base_name + ".mat"
    save_path_mat = os.path.join(save_dir, mat_filename)
    scipy.io.savemat(save_path_mat, data_dict)
    print(f"Data dictionary saved to {save_path_mat}")
    print(data_dict)


    fcurrent = current
    # Dummy noise-check function (replace with your actual noise check if available)
    noise_threshold = 10 ** -30
    def noisy(val, threshold):
        return val < threshold

    # Loop through each channel and plot valid ones (not None and not classified as noise)
    valid_channels = []
    for i, ch in enumerate(channels):
        if ch is not None:

            print(f"Found power (mW) data for Channel {i}")
            if noisy(ch.mean(), noise_threshold):
                print(f"Channel {i} classified as noise, skipping.")
            else:
                valid_channels.append((i, ch))
        else:
            print(f"No match found for Channel {i}.")

    print("plotting IV curve")

    # Plot IV Curve
    fig2, ax2 = plt.subplots()
    ax2.plot(fcurrent, voltage, color='black', marker='o', label="IV Curve")
    #ax2.axvline(x=current[tidx], color='red', linestyle='--', label='Threshold Current') #vertical line at threshold current
    #ax2.axvline(x=peak_power_I, color='blue', linestyle='--', label='Current at Peak Power') #vertical line at threshold current
    ax2.set_title(f"Current vs Voltage")
    ax2.set_xlabel("Current (mA)")
    ax2.set_ylabel("Voltage (V)")
    ax2.grid(True)

    #save svg
    svg_filename2 = base_name + f"_IVcurve.svg"
    save_path_svg2 = os.path.join(save_dir, svg_filename2)
    fig2.savefig(save_path_svg2, format="svg", bbox_inches="tight")
    print(f"Saved IV curve svg to {save_path_svg2}")
     #save png
    png_filename2 = base_name + f"_IVcurve.png"
    save_path_png2 = os.path.join(save_dir, png_filename2)
    fig2.savefig(save_path_png2, format="png", bbox_inches="tight")
    print(f"Saved IV curve png to {save_path_png2}")     

    # PLOT differential resistance (dV/dI vs I)    
    # Calculate differential resistance (dV/dI) vs I
    dI = np.gradient(fcurrent)
    dV = np.gradient(voltage)
    R = dV / dI
    I=fcurrent
    IdVdI = I*R  # Convert to Ohms

    # Define model: power law with offset
    def model(I, a, b, c):
        return a * I**b + c

    # Initial guess for parameters
    p0 = [0.01, 1.0, 0.1]

    # Fit the model to data
    params, _ = curve_fit(model, I, IdVdI, p0=p0)
    a, b, c = params

    # Generate fitted curve
    I_fit = np.linspace(min(I), max(I), 200)
    fit_vals = model(I_fit, *params)

    # Plot
    fig3, ax3 = plt.subplots()
    ax3.scatter(I, IdVdI, label='I*dV/dI (data)', color='blue')
    ax3.plot(I_fit, fit_vals, label=f'Fit: {a:.4f} * I^{b:.4f} + {c:.4f}', color='red')

    # Labels and title
    ax3.set_title("Current * Differential Resistance (I*dV/dI) vs Current")
    ax3.set_xlabel("Current (mA)")
    ax3.set_ylabel("I*dV/dI (Ohm*mA)")
    ax3.grid(True)
    ax3.legend()


    # Save the differential resistance plot
    svg_filename3 = base_name + "_I_dVdIcurve.svg"
    save_path_svg3 = os.path.join(save_dir, svg_filename3)
    fig3.savefig(save_path_svg3, format="svg", bbox_inches="tight")
    print(f"Saved dV/dI curve svg to {save_path_svg3}")

    png_filename3 = base_name + "_I_dVdIcurve.png"
    save_path_png3 = os.path.join(save_dir, png_filename3)
    fig3.savefig(save_path_png3, format="png", bbox_inches="tight")
    print(f"Saved I*dV/dI curve png to {save_path_png3}")


    # PLOT LI curves
    print("plotting LI curve")
    num_valid = len(valid_channels)
    if num_valid == 0:
        print("No valid channels to plot.")
    else:
        cmap = mpl.colormaps['inferno']
        colours = cmap(np.linspace(0, 1, num_valid))
        for idx, (i, ch) in enumerate(valid_channels):
            print(f"Processing Channel {i} with {len(ch)} data points.")
            proc_ch = ch

            # Generate axis ticks
            ch_ticks = get_ticks(proc_ch, 5, 4)
            i_ticks = get_ticks(fcurrent, 4, 3)

            fig, ax = plt.subplots()
            ax.plot(fcurrent, proc_ch, color='black', marker='o', label=f"Channel {i}")
            #ax.set_xticks(i_ticks)
            #ax.set_xticklabels(i_ticks)
            #ax.set_yticks(ch_ticks)
            #ax.set_yticklabels(ch_ticks)
            if threshold_Is[i] > 0:
                ax.axvline(x=threshold_Is[i], color='red', linestyle='--', label='Threshold Current') #vertical line at threshold current
            ax.legend()
            ax.set_title(f"Current vs Power - Channel {i}")
            ax.set_xlabel("Current (mA)")
            ax.set_ylabel("Power (mW)")
            ax.grid(True)

            # LI Curves
            fig, ax = plt.subplots()
            ax.plot(fcurrent, proc_ch, color='black', marker='o')
            ax.axvline(x=threshold_Is[i], color='red', linestyle='--', label='Threshold Current') #vertical line at threshold current
            #ax.axvline(x=peak_power_I, color='blue', linestyle='--', label='Current at Peak Power') #vertical line at threshold current
            #ax.axhline(y=peak_power, color='blue', linestyle='--', label='Peak Power') #horizontal line at peak power

            #ax.set_xticks(i_ticks)
            #ax.set_xticklabels(i_ticks)
            #ax.set_yticks(ch_ticks)
            #ax.set_yticklabels(ch_ticks)
            ax.set_title(f"Current vs Power - Channel {i}")
            ax.set_xlabel("Current (mA)")
            ax.set_ylabel("Power (mW)")
            ax.legend()
            ax.grid(True)
            


            # Save the channel plot as an SVG file in the output folder
            svg_filename = base_name + f"_LI_channel{i}.svg"
            save_path_svg = os.path.join(save_dir, svg_filename)
            fig.savefig(save_path_svg, format="svg", bbox_inches="tight")
            print(f"Saved channel {i} plot to {save_path_svg}")
            # Optionally, close the figure: plt.close(fig)
            # Save the channel plot as an PNG file in the output folder
            png_filename = base_name + f"_LI_channel{i}.png"
            save_path_png = os.path.join(save_dir, png_filename)
            fig.savefig(save_path_png, format="png", bbox_inches="tight")
            print(f"Saved channel {i} plot to {save_path_png}")
    
    #Plot WL vs Temp and WL vs Current
    print("plotting WL vs Temp and WL vs Current")
        # WL vs Temp plot
    if wavelength is not None and temperature is not None:
        fig, ax = plt.subplots()
        mask = wavelength > 1000
        ax.scatter(wavelength[mask], temperature[mask], color='black', marker='o')
        ax.set_title("Temperature vs Wavelength")
        ax.set_ylabel("Temperature (C)")
        ax.set_xlabel("Wavelength (nm)")
        ax.grid(True)

        # Save the WL vs Temp plot as an SVG file in the output folder
        wl_temp_filename = base_name + "_Temp_vs_WL.svg"
        save_path_wl_temp = os.path.join(save_dir, wl_temp_filename)
        fig.savefig(save_path_wl_temp, format="svg", bbox_inches="tight")
        print(f"Saved Temperature vs Wavelength plot to {save_path_wl_temp}")
        
         # Save the WL vs Temp plot as an SVG file in the output folder
        wl_temp_filename1 = base_name + "_WL_vs_Temp.png"
        save_path_wl_temp1 = os.path.join(save_dir, wl_temp_filename1)
        fig.savefig(save_path_wl_temp1, format="png", bbox_inches="tight")
        print(f"Saved Temperature vs Wavelength plot to {save_path_wl_temp1}")

    # WL vs current plot
    if wavelength is not None and current is not None:
        fig, ax = plt.subplots()
        mask = wavelength > 1000
        ax.scatter(current[mask], wavelength[mask], color='black', marker='o')
        ax.set_title("Wavelength vs Current")
        ax.set_xlabel("Current (mA)")
        ax.set_ylabel("Wavelength (nm)")
        ax.grid(True)

        #ax.axvline(x=peak_power_I, color='blue', linestyle='--', label='Current at Peak Power') #vertical line at threshold current
        #ax.axhline(y=peak_power_WL, color='blue', linestyle='--', label='Peak Power') #horizontal line at peak power


        # Save the WL vs current plot as an SVG file in the output folder
        wl_current_filename = base_name + "_WL_vs_Current.svg"
        save_path_wl_current = os.path.join(save_dir, wl_current_filename)
        fig.savefig(save_path_wl_current, format="svg", bbox_inches="tight")
        print(f"Saved Wavelength vs Current plot to {save_path_wl_current}")

        wl_current_filename1 = base_name + "_WL_vs_Current.png"
        save_path_wl_current1 = os.path.join(save_dir, wl_current_filename1)
        fig.savefig(save_path_wl_current1, format="png", bbox_inches="tight")
        print(f"Saved  Wavelength vs Current plot to {save_path_wl_current1}")


def main():
    import sys
    from tkinter import Tk, simpledialog
    from tkinter.filedialog import askopenfilename
    from tkinter.filedialog import askdirectory

    # Hide the root window
    root = Tk()
    root.withdraw()

    # Ask for the file path
    file_path = askopenfilename(title="Select a LIV CSV File", filetypes=[("CSV files", "*.csv")])
    if not file_path:
        print("No file selected. Exiting.")
        sys.exit(0)

    # Ask for the output folder
    output_folder = askdirectory(title="Select Output Folder (Cancel for same location)")
    if not output_folder:
        output_folder = None

    # Process the LIV file
    process_wlm(file_path, output_folder)

if __name__ == "__main__":
    main()