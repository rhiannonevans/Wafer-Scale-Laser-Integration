## OBSOLETE 

# Processes "WLM-type" files - non-OSA files containing current and channel (power) data, as well as wavelength, temperature, and voltage data.
#          Checks for the presence of useful wavelength data (mean > 1000 nm). If not present, it switches to LIV processing.
# Produces .mat files and plots of data.
# Expects a CSV with Current, Wavelength, Voltage, Temperature, and Channel (optional channels 0 through 4) data.
# For comparison plots: Extracts threshold current, peak power, and associated current, wavelength, and voltage.
# Generates LIV curves and other WLM data plots (like wl vs temp, wl vs current).
# Saves original mW power data

def process_wlm(file_path_str, output_folder=None):
    import os
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import scipy.io
    import Obsolete.liv as liv
    import re
    import threshold

    if output_folder is None:
        output_folder = os.path.dirname(os.path.abspath(file_path_str))

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
    #df = pd.read_csv(file_path, header=None, on_bad_lines="skip", engine="python", skiprows=24)
    # f = open(file_path, 'r')
    # df = pd.read_csv(f, header=None, on_bad_lines="skip", engine="python", skiprows=24)
    # f.close()

    with open(file_path, 'r') as file:
        df = pd.read_csv(file, header=None, on_bad_lines="skip", engine="python", skiprows=24)
        file.close()

    print(df)
    # Define search terms for each target row
    search_terms = {
        "current": "Current",
        "wavelength": "Wavelength",
        "voltage": "Voltage",
        "temperature": "Temperature",
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

    # Remove the first column (used for matching)
    del df[0]

    # Extract data rows from the DataFrame
    current = df.loc[indices["current"]] if indices["current"] is not None else None
    if indices["current"] is not None:
     current = pd.to_numeric(df.loc[indices["current"]], errors='coerce') * 1000
    else:
     current = None

    wavelength = df.loc[indices["wavelength"]] if indices["wavelength"] is not None else None
    voltage = df.loc[indices["voltage"]] if indices["voltage"] is not None else None
    temperature = df.loc[indices["temperature"]] if indices["temperature"] is not None else None

    #print("Current:", current)
    #print("Wavelength:", wavelength)
    #print("Voltage:", voltage)  
    #print("Temperature:", temperature)

    if voltage is not None and temperature is not None:
        voltage = pd.to_numeric(df.loc[indices["voltage"]], errors='coerce')
        temperature = pd.to_numeric(df.loc[indices["temperature"]], errors='coerce')
    else:
        print("No Voltage, and/or Temperature data found. Invalid File.")
        return
    
    liv = re.search(r"^liv", base_name, re.IGNORECASE)


    if wavelength is None or liv:
        print("No useful Wavelength data found. Processing as LIV.")
        liv.process_liv(file_path_str, output_folder=output_folder) 
    else:
        wavelength = pd.to_numeric(df.loc[indices["wavelength"]], errors='coerce')

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

        # Build a dictionary with the core data for saving to a .mat file
    data_dict = {
        "temperature": temperature,
        "voltage": voltage,
        "current": current,
        "wavelength": wavelength,
    }
    print("Data dictionary initialized")

    # Determine the "data" channel based on the largest average value
    data_channel_index = None
    max_average = -np.inf
    for i, ch in enumerate(channels):
        if ch is not None:
            avg_value = ch.mean()
            if avg_value > max_average:
                max_average = avg_value
                data_channel_index = i

    if data_channel_index is not None:
        print(f"Data channel determined: Channel {data_channel_index} with average value {max_average}")
    else:
        print("No valid data channel found.")


    threshold_Is = []
    for i, ch in enumerate(channels):
        data_dict[f"channel_{i}"] = ch
        print(f"Saved channel {i}:")

        # Assumes there is no threshold if data starts above 0.2A - implies threshold has been passed
        if current[0] >= 0.2:
            print(f"Initial current is above 0.2A, skipping threshold detection for all channels.")
            threshold_Is.append(0)
        else:
            tidx = threshold.detect_trend_gradient(ch, current)[0] if threshold.detect_trend_gradient(ch, current) else None
            print(f"Threshold index for channel {i}: {tidx} with current {current[tidx] if tidx is not None else 'N/A'}")
            if tidx is None:
                print(f"No threshold index found for channel {i}. Setting to 0.")
                threshold_Is.append(0)
            else:
                threshold_Is.append(current[tidx])
                print(f"Threshold current index is {tidx} for channel {i}: {current[tidx]}mA")
    
    
    print("Threshold currents:", threshold_Is)
    data_dict["threshold_currents"] = threshold_Is

    # Formulate comparison data (Max power of data channel and assoc current and wl)

    if data_channel_index is not None:
        peak_power = channels[data_channel_index].max()
        data_dict["peak_power"] = peak_power
        peak_power_I = current[channels[data_channel_index].idxmax()]
        data_dict["peak_power_I"] = peak_power_I
        peak_power_WL = wavelength[channels[data_channel_index].idxmax()]
        data_dict["peak_power_WL"] = peak_power_WL
        peak_power_V = voltage[channels[data_channel_index].idxmax()]
        data_dict["peak_power_V"] = peak_power_V

        print(f"Peak power: {data_dict['peak_power']}")
        print(f"Assoc Current: {data_dict['peak_power_I']}")
        print(f"Assoc Wavelength: {data_dict['peak_power_WL']}")
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

    # Determine the current data to use (filter noise by wavelength)
    if current.max() > 1000:
        fcurrent = current[wavelength > 1000]
    else:
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

    num_valid = len(valid_channels)
    if num_valid == 0:
        print("No valid channels to plot.")
    else:
        cmap = mpl.colormaps['inferno']
        colours = cmap(np.linspace(0, 1, num_valid))
        for idx, (i, ch) in enumerate(valid_channels):
            #if wavelength.max() > 1000:
            #    proc_ch = ch[wavelength > 1000]
            #else:
            #    proc_ch = ch

            proc_ch = ch
            # Generate axis ticks
            ch_ticks = get_ticks(proc_ch, 5, 4)
            i_ticks = get_ticks(fcurrent, 4, 3)

            fig, ax = plt.subplots()
            ax.plot(fcurrent, proc_ch, color='black', marker='o', label=f"Channel {i}")
            ax.axvline(x=current[tidx], color='red', linestyle='--', label='Threshold Current') #vertical line at threshold current
            #ax.axvline(x=peak_power_I, color='blue', linestyle='--', label='Current at Peak Power') #vertical line at threshold current
            #ax.axhline(y=peak_power, color='blue', linestyle='--', label='Peak Power') #horizontal line at peak power

            
            #ax.set_xticks(i_ticks)
            #ax.set_xticklabels(i_ticks)
            #ax.set_yticks(ch_ticks)
            #ax.set_yticklabels(ch_ticks)
            ax.set_title(f"Current vs Power - Channel {i}")
            ax.set_xlabel("Current (mA)")
            ax.set_ylabel("Power (mW)")
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
            plt.close(fig)  # Close the figure to free memory

    # Create and save the current vs voltage (IV) plot
    if current is not None and voltage is not None:
        if current.max() > 1000:
            fcurrent_IV = current[wavelength > 1000]
            fvoltage_IV = voltage[wavelength > 1000]
        else:
            fcurrent_IV = current
            fvoltage_IV = voltage

        i_ticks_IV = get_ticks(fcurrent_IV, 4, 3)
        v_ticks_IV = get_ticks(fvoltage_IV, 4, 2)

        ivfig, ivax = plt.subplots()
        ivax.plot(fcurrent_IV, fvoltage_IV, color='black', marker='o')
        ivax.set_title("IV Curve")
        ivax.set_xlabel("Current (mA)")
        ivax.set_ylabel("Voltage (V)")
        ivax.axvline(x=current[tidx], color='red', linestyle='--', label='Threshold Current') #vertical line at threshold current
        #ivax.axvline(x=peak_power_I, color='blue', linestyle='--', label='Current at Peak Power') #vertical line at threshold current
        #ivax.axhline(y=peak_power_V, color='blue', linestyle='--', label='Peak Power') #horizontal line at peak power


       # ivax.set_xticks(i_ticks_IV)
        #ivax.set_xticklabels(i_ticks_IV)
        #ivax.set_yticks(v_ticks_IV)
        #ivax.set_yticklabels(v_ticks_IV)
        #ivax.grid(True)

        # Save the IV plot as an SVG file in the output folder
        iv_filename = base_name + "_IV.svg"
        save_path_iv = os.path.join(save_dir, iv_filename)
        ivfig.savefig(save_path_iv, format="svg", bbox_inches="tight")
        print(f"Saved IV plot to {save_path_iv}")
        # Optionally, close the figure: plt.close(ivfig)

        
        # Save the IV plot as an SVG file in the output folder
        iv_filename1 = base_name + "_IV.png"
        save_path_iv = os.path.join(save_dir, iv_filename1)
        ivfig.savefig(save_path_iv, format="png", bbox_inches="tight")
        print(f"Saved IV plot to {save_path_iv}")
        # Optionally, close the figure: plt.close(ivfig)

    # WL vs Temp plot
    if wavelength is not None and temperature is not None:
        fig, ax = plt.subplots()
        ax.plot(temperature, wavelength, color='black', marker='o')
        ax.set_title("Wavelength vs Temperature")
        ax.set_xlabel("Temperature (C)")
        ax.set_ylabel("Wavelength (nm)")
        ax.grid(True)

        # Save the WL vs Temp plot as an SVG file in the output folder
        wl_temp_filename = base_name + "_WL_vs_Temp.svg"
        save_path_wl_temp = os.path.join(save_dir, wl_temp_filename)
        fig.savefig(save_path_wl_temp, format="svg", bbox_inches="tight")
        print(f"Saved Wavelength vs Temperature plot to {save_path_wl_temp}")
        
         # Save the WL vs Temp plot as an SVG file in the output folder
        wl_temp_filename1 = base_name + "_WL_vs_Temp.png"
        save_path_wl_temp1 = os.path.join(save_dir, wl_temp_filename1)
        fig.savefig(save_path_wl_temp1, format="png", bbox_inches="tight")
        print(f"Saved IV plot to {save_path_wl_temp1}")

    # WL vs current plot
    if wavelength is not None and current is not None:
        fig, ax = plt.subplots()
        ax.plot(current, wavelength, color='black', marker='o')
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
        print(f"Saved IV plot to {save_path_wl_current1}")

