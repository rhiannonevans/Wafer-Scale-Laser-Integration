import csv
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import viscm
import scipy.io as sio
import scipy as scp
import matplotlib as mpl

def sweep_osa(file_path_str, output_folder=None):
    # Expand the file path
    file_path = os.path.expanduser(file_path_str)
    print(f"Looking for the file at: {file_path}")
    
    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist. Please check the file path.")
    
    # Load the file as a CSV (the file should be a CSV)
    df = pd.read_csv(file_path, header=None, skiprows=24, on_bad_lines="skip", engine="python")
    
    # Organize into sweeps (by groups of 2 - assuming two data points per sweep)
    df["Sweep"] = df.index // 2

    # Calculate number of sweeps
    num_sweeps = df["Sweep"].count() / 2
    print(num_sweeps)

    # Re-read file for longer data rows
    df2 = pd.read_csv(file_path, header=None, skiprows=26, on_bad_lines="skip", engine="python")
    
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
    
    OSA_df = df2_merged
    print(OSA_df)
    
    """
    PLOT SORTED DATA
    """
    cmap = mpl.colormaps['inferno']
    colors = cmap(np.linspace(0.2, 0.9, int(num_sweeps)))  # Adjust range to exclude very light colors
    
    fig1, ax1 = plt.subplots()  # Spectrum figure
    fig2, ax2 = plt.subplots()  # Peak power vs wavelength
    fig3, ax3 = plt.subplots()  # Peak power vs current
    fig4, ax4 = plt.subplots()  # Peak power vs wavelength

    peak_pows = [None] * len(curr)
    peak_wls = [None] * len(curr)


    for sweep in OSA_df.index:
        # Get the data for the current sweep
        wavelength_values = pivot_df.loc[sweep, "Wavelength (nm)"]
        power_values = pivot_df.loc[sweep, "Optical power (dBm)"]

        temperature = OSA_df.loc[sweep, 'Temperature (C)']
        current = OSA_df.loc[sweep, 'Current (mA)']

        max_power = max(power_values)
        peak_pows[sweep] = max_power
        max_wl = wavelength_values[power_values.index(max_power)]
        peak_wls[sweep] = max_wl
        
        ax1.plot(wavelength_values, power_values, label=f"{sweep} / {current} / {temperature}", color=colors[sweep])
        ax2.scatter(current, max_wl, label=f"{sweep}", color=colors[sweep])
        ax3.scatter(current, max_power, label=f"{sweep}", color=colors[sweep])
        ax4.scatter(current, max_wl, label=f"{sweep}", color=colors[sweep])
    
    print(peak_pows)
    print(peak_wls)
    
    # Polynomial fit: 2nd degree fit for peak wavelength vs current
    fit_x = curr[1].to_numpy()                  # current in mA
    fit_y = np.array(peak_wls)                  # peak wavelengths
    poly_coeffs = np.polyfit(fit_x, fit_y, 2)   # 2nd-degree fit
    poly_func = np.poly1d(poly_coeffs)

       # Polynomial fit: 3rd degree fit for peak wavelength vs current
    fit_x2 = curr[1].to_numpy()                  # current in mA
    fit_y2 = np.array(peak_wls)                  # peak wavelengths
    poly_coeffs2 = np.polyfit(fit_x2, fit_y2, 3)   # 3rd-degree fit
    poly_func2 = np.poly1d(poly_coeffs2)

    # Generate fit line
    fit_x_vals = np.linspace(fit_x.min(), fit_x.max(), 300)
    fit_y_vals = poly_func(fit_x_vals)
    ax2.plot(fit_x_vals, fit_y_vals, 'k--', linewidth=2, label="2nd Deg. Fit")

     # Generate fit line
    fit_x_vals2 = np.linspace(fit_x2.min(), fit_x2.max(), 300)
    fit_y_vals2 = poly_func2(fit_x_vals2)
    ax4.plot(fit_x_vals2, fit_y_vals2, 'k--', linewidth=2, label="3rd Deg. Fit")

    # Annotate polynomial equation on the plot
    eq_text2 = (f"Fit: y = {poly_coeffs2[0]:.3e}x³ + {poly_coeffs2[1]:.3e}x² + "f"{poly_coeffs2[2]:.3e}x + {poly_coeffs2[3]:.3f}")
    eq_text = f"Fit: y = {poly_coeffs[0]:.3e}x² + {poly_coeffs[1]:.3e}x + {poly_coeffs[2]:.3f}"

    ax2.text(0.05, 0.95, eq_text, transform=ax2.transAxes, fontsize=9, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.6))
    
    ax4.text(0.05, 0.95, eq_text2, transform=ax4.transAxes, fontsize=9, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.6))  

    # Customize plots
    ax1.set_title("Wavelength vs Optical Power by Sweep")
    ax1.set_xlabel("Wavelength (nm)")
    ax1.set_ylabel("Optical Power (dBm)")
    ax1.legend(title="Sweep / Current (mA) / Temperature (C)", loc='center right', bbox_to_anchor=(1, 0.3))
    ax1.grid(True)
    fig1.tight_layout()
    
    ax2.set_title("Associated Wavelength at Peak Power by Sweep")
    ax2.set_xlabel("Current (mA)")
    ax2.set_ylabel("Wavelength (nm)")
    ax2.legend(title="Sweep", loc='center right', bbox_to_anchor=(1, 0.3))
    fig2.tight_layout()
    
    
    ax3.set_title("Peak Power and Assoc. Current by Sweep")
    ax3.set_xlabel("Current (mA)")
    ax3.set_ylabel("Power (dBm)")
    ax3.legend(title="Sweep", loc='center right', bbox_to_anchor=(1, 0.3))
    fig3.tight_layout()

    
    ax4.set_title("Peak Power and Assoc. Wavelength by Sweep")
    ax4.set_xlabel("Current (mA)")
    ax4.set_ylabel("Wavelength (nm)")
    ax4.legend(title="Sweep", loc='center right', bbox_to_anchor=(1, 0.3))
    fig4.tight_layout()

    # Save figures and processed data
    file_loc, file_name = os.path.split(file_path_str)
    base_name = file_name.split('.')[0]
    nameMat = base_name + ".mat"
    nameSVG1 = base_name + "_spectrum.svg"
    nameSVG2 = base_name + "_WLpeaks.svg"
    nameSVG3 = base_name + "_Ipeaks.svg"
    nameSVG4 = base_name + "_WLpeaks2.svg"

    namePNG1 = base_name + "_spectrum.png"
    namePNG2 = base_name + "_WLpeaks.png"
    namePNG3 = base_name + "_Ipeaks.png"
    namePNG4 = base_name + "_WLpeaks2.png"

    # Use the provided output_folder if available; otherwise, default to the file's directory
    if output_folder is not None:
        save_dir = output_folder
    else:
        save_dir = file_loc

    # Create the output folder if it doesn't exist
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    save_path_svg1 = os.path.join(save_dir, nameSVG1)
    save_path_svg2 = os.path.join(save_dir, nameSVG2)
    save_path_svg3 = os.path.join(save_dir, nameSVG3)
    save_path_svg4 = os.path.join(save_dir, nameSVG4)
    save_path_mat = os.path.join(save_dir, nameMat)
    save_path_png1 = os.path.join(save_dir, namePNG1)
    save_path_png2 = os.path.join(save_dir, namePNG2)
    save_path_png3 = os.path.join(save_dir, namePNG3)
    save_path_png4 = os.path.join(save_dir, namePNG4)

    fig1.savefig(save_path_svg1, bbox_inches="tight")
    fig2.savefig(save_path_svg2, bbox_inches="tight")
    fig3.savefig(save_path_svg3, bbox_inches="tight")
    fig4.savefig(save_path_svg4, bbox_inches="tight")

    fig1.savefig(save_path_png1, bbox_inches="tight")
    fig2.savefig(save_path_png2, bbox_inches="tight")
    fig3.savefig(save_path_png3, bbox_inches="tight")
    fig4.savefig(save_path_png4, bbox_inches="tight")

    d_OSA = {
        "peak_power": peak_pows,
        "peak_wavelength": peak_wls,
        "current_mA": curr[1].tolist(),
        "temperature_C": temp[1].tolist(),
        "optical_power_dBm": OSA_df["Optical Power (dBm)"].tolist(),
        "wavelength_nm": OSA_df["Wavelength (nm)"].tolist(),
        "polyfit_peakWL_vs_I_deg2_coeffs": poly_coeffs.tolist(),
        "polyfit_peakWL_vs_I_deg3_coeffs": poly_coeffs2.tolist()
    }
    
    sio.savemat(save_path_mat, d_OSA, appendmat=True)
    
    print(f"Outputs saved in: {save_dir}")
