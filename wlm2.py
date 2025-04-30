def process_other(file_path_str, LDC, output_folder=None):
    import os
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import scipy.io

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
    df = pd.read_csv(file_path, header=None, on_bad_lines="skip", engine="python", skiprows=24)

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

    ch0 = df.loc[indices["channel 0"]] if indices["channel 0"] is not None else None
    ch1 = df.loc[indices["channel 1"]] if indices["channel 1"] is not None else None
    ch2 = df.loc[indices["channel 2"]] if indices["channel 2"] is not None else None
    ch3 = df.loc[indices["channel 3"]] if indices["channel 3"] is not None else None
    ch4 = df.loc[indices["channel 4"]] if indices["channel 4"] is not None else None

    # Optionally, convert power data if provided in mW (0: already in dBm, 1: in mW)
    is_mW = 0
    convert_const = 10 * np.log(10)
    if is_mW:
        if ch0 is not None: ch0 = ch0.mul(convert_const)
        if ch1 is not None: ch1 = ch1.mul(convert_const)
        if ch2 is not None: ch2 = ch2.mul(convert_const)
        if ch3 is not None: ch3 = ch3.mul(convert_const)
        if ch4 is not None: ch4 = ch4.mul(convert_const)

    # Build a dictionary with the core data for saving to a .mat file
    data_dict = {
        "temperature": temperature,
        "voltage": voltage,
        "current": current,
        "wavelength": wavelength
    }
    channels = [ch0, ch1, ch2, ch3, ch4]
    for i, ch in enumerate(channels):
        if ch is not None:
            data_dict[f"channel{i}"] = ch
            tidx = next(idx for idx, value in enumerate(ch) if value > 10**(-20))+1
    
    print("Threshold current:", current[tidx])
    data_dict["threhold_current"] = current[tidx]

    # Determine the output directory
    if output_folder is not None:
        save_dir = output_folder
    else:
        save_dir = file_loc
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Save the data dictionary to a .mat file in the output folder
    mat_filename = base_name + "_data.mat"
    save_path_mat = os.path.join(save_dir, mat_filename)
    scipy.io.savemat(save_path_mat, data_dict)
    print(f"Data dictionary saved to {save_path_mat}")

    # Determine the current data to use (filter by wavelength if not LDC)
    if LDC:
        fcurrent = current
    else:
        fcurrent = current[wavelength > 1000]

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
            if LDC:
                proc_ch = ch
            else:
                proc_ch = ch[wavelength > 1000]

            # Generate axis ticks
            ch_ticks = get_ticks(proc_ch, 5, 4)
            i_ticks = get_ticks(fcurrent, 4, 3)

            fig, ax = plt.subplots()
            ax.plot(fcurrent, proc_ch, color='black', marker='o', label=f"Channel {i}")
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

    # Create and save the current vs voltage (IV) plot
    if current is not None and voltage is not None:
        if LDC:
            fcurrent_IV = current
            fvoltage_IV = voltage
        else:
            fcurrent_IV = current[wavelength > 1000]
            fvoltage_IV = voltage[wavelength > 1000]

        i_ticks_IV = get_ticks(fcurrent_IV, 4, 3)
        v_ticks_IV = get_ticks(fvoltage_IV, 4, 2)

        ivfig, ivax = plt.subplots()
        ivax.plot(fcurrent_IV, fvoltage_IV, color='black', marker='o')
        ivax.set_title("IV Curve")
        ivax.set_xlabel("Current (mA)")
        ivax.set_ylabel("Voltage (V)")
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

    # Create and save the current vs wavelength plot with polynomial fits
    if current is not None and wavelength is not None:
        # Filter valid data (remove NaN or invalid values)
        valid_idx = ~np.isnan(current) & ~np.isnan(wavelength)
        fcurrent = current[valid_idx]
        fwavelength = wavelength[valid_idx]

        # Fit polynomials of orders 2 and 3
        poly2_coeffs = np.polyfit(fcurrent, fwavelength, 2)
        poly3_coeffs = np.polyfit(fcurrent, fwavelength, 3)

        # Generate best-fit lines
        poly2_fit = np.polyval(poly2_coeffs, fcurrent)
        poly3_fit = np.polyval(poly3_coeffs, fcurrent)

        # Plot original data and best-fit lines
        plt.figure(figsize=(10, 6))
        plt.plot(fcurrent, fwavelength, 'o', label='Original Data', color='blue')  # Original data
        plt.plot(fcurrent, poly2_fit, '-', label='2nd Order Fit', color='red')     # 2nd order fit
        plt.plot(fcurrent, poly3_fit, '--', label='3rd Order Fit', color='green')  # 3rd order fit

        # Generate polynomial equations as strings
        poly2_eq = f"2nd Order: {poly2_coeffs[0]:.3e}x² + {poly2_coeffs[1]:.3e}x + {poly2_coeffs[2]:.3e}"
        poly3_eq = f"3rd Order: {poly3_coeffs[0]:.3e}x³ + {poly3_coeffs[1]:.3e}x² + {poly3_coeffs[2]:.3e}x + {poly3_coeffs[3]:.3e}"

        # Annotate the equations on the plot
        plt.text(0.05, 0.95, poly2_eq, transform=plt.gca().transAxes, fontsize=12,color='red', verticalalignment='top')
        plt.text(0.05, 0.90, poly3_eq, transform=plt.gca().transAxes, fontsize=12, color='green', verticalalignment='top')

        # Add labels, title, and legend
        plt.xlabel("Current (mA)", fontsize=14)
        plt.ylabel("Wavelength (nm)", fontsize=14)
        plt.title("Current vs Wavelength with Best-Fit Lines", fontsize=16)
        plt.legend(loc='lower right', fontsize=12)
        plt.grid(True)

        # Save the plot as PNG and SVG
        fit_plot_filename_png = base_name + "_Current_vs_Wavelength_Fit.png"
        fit_plot_filename_svg = base_name + "_Current_vs_Wavelength_Fit.svg"
        save_path_png = os.path.join(save_dir, fit_plot_filename_png)
        save_path_svg = os.path.join(save_dir, fit_plot_filename_svg)
        plt.savefig(save_path_png, format="png", bbox_inches="tight")
        plt.savefig(save_path_svg, format="svg", bbox_inches="tight")
        print(f"Saved Current vs Wavelength plot with fits to {save_path_png} and {save_path_svg}")

        # Show the plot
       #plt.show()
               

    # Save all processed data to a .mat file
    matlab_data = {
        "current": fcurrent if current is not None else None,
        "wavelength": fwavelength if wavelength is not None else None,
        "voltage": voltage if voltage is not None else None,
        "temperature": temperature if temperature is not None else None,
        "channels": {f"channel_{i}": ch.tolist() for i, ch in enumerate(channels) if ch is not None},
        "threshold_current": current[tidx] if "tidx" in locals() else None,
    }

    # Add polynomial fit data for current vs wavelength
    if current is not None and wavelength is not None:
        matlab_data["poly2_coeffs"] = poly2_coeffs.tolist()
        matlab_data["poly3_coeffs"] = poly3_coeffs.tolist()
        matlab_data["poly2_fit"] = poly2_fit.tolist()
        matlab_data["poly3_fit"] = poly3_fit.tolist()

    # Save the MATLAB data
    mat_filename = base_name + "_processed_data.mat"
    save_path_mat = os.path.join(save_dir, mat_filename)
    scipy.io.savemat(save_path_mat, matlab_data)
    print(f"All processed data saved to {save_path_mat}")

