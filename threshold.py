"""
    Filters and detects trends in LIV data using first and second derivatives of the log power.

    If run as a script, it processes LIV data from specified .mat files, detects trends, and plots the results. This is ideal for troubleshooting
    new ways of detecting threshold currents 

    [Author: Rhiannon H Evans]
"""


import pandas as pd
import extract as ex
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
import os



def fit_idvdi(I,V, base_name=None, save_dir=None):
    from scipy.interpolate import UnivariateSpline
    from scipy.signal import argrelextrema

    # Calculate dV/dI
    dV_dI = np.gradient(V, I)
    I_dVdI = I*dV_dI 

    # Fit a smooth curve
    spline = UnivariateSpline(I, I_dVdI, s=0.001)  # s is smoothing factor
    I_fit = np.linspace(I.min(), I.max(), 2000)
    I_dVdI_fit = spline(I_fit)


    # Plot
    fig = plt.figure(figsize=(8, 5))
    plt.plot(I, I_dVdI, label='I*dV/dI', alpha=0.6)
    plt.plot(I_fit, I_dVdI_fit, 'r--', label='Spline Fit')
    plt.xlabel('Current (mA)')
    plt.ylabel('I*dV/dI (V)')
    plt.title('Differential vs Current')
    plt.legend()
    #plt.xlim(0,15)
    plt.grid(True)
    plt.tight_layout()
    #plt.show()

    if base_name is not None and save_dir is not None:
        # Save the differential resistance plot
        svg_filename3 = base_name + "_I_dVdIcurve.svg"
        save_path_svg3 = os.path.join(save_dir, svg_filename3)
        fig.savefig(save_path_svg3, format="svg", bbox_inches="tight")
        print(f"Saved dV/dI curve svg to {save_path_svg3}")

        png_filename3 = base_name + "_I_dVdIcurve.png"
        save_path_png3 = os.path.join(save_dir, png_filename3)
        fig.savefig(save_path_png3, format="png", bbox_inches="tight")
        print(f"Saved I*dV/dI curve png to {save_path_png3}")

    return

def run_liv(I,channel, base_name=None, save_dir=None, ch_i = 1):

    L=np.log(channel)
    print(I)

    # Mask for 4 < I < 20 mA
    mask = (I > 4) & (I < 20)
    I_sub = I[mask]
    L_sub = L[mask]
    print(f"Subtracted I: {I_sub}")
    # Compute first and second derivatives
    d1 = np.diff(L_sub)
    d2 = np.diff(d1)
    # The x-axis for the first and second derivatives
    I_d1 = I_sub[1:]
    I_d2 = I_sub[2:]
    # Find the index of the maximum second derivative (threshold) and/or first derivative (maximum jump)
    if I.iloc[0] >= 20:
        print("Warning: Current starts at or above 20mA, skipping threshold analysis.")
        threshold_current_1st = None
        threshold_current_2nd = None
    else:
        threshold_idx_2nd = np.argmax(d2)
        threshold_current_2nd = I_d2.iloc[threshold_idx_2nd]
        print(f"Threshold (second derivative max) at I = {threshold_current_2nd:.3f} mA")
        threshold_idx_1st = np.argmax(np.abs(d1))
        threshold_current_1st = I_d1.iloc[threshold_idx_1st]
        print(f"Maximum jump (first derivative max) at I = {threshold_current_1st:.3f} mA")
    


    #PLOT second and first derivatives

    if base_name is not None and save_dir is not None and threshold_current_2nd is not None:
        # Create a new figure with two subplots side by side for fig2 and fig3
        fig_combined, (ax2, ax3) = plt.subplots(1, 2, figsize=(14, 6))

        # Plot second derivative on the left
        ax2.plot(I_d2, d2, marker='o', label='Second derivative')
        if threshold_current_2nd is not None:
            ax2.axvline(threshold_current_2nd, color='red', linestyle='--', label=f'Second Deriv. Max at {threshold_current_2nd:.2f} mA')
        ax2.set_xlabel("Current (mA)")
        ax2.set_ylabel("Second derivative of log(Power)")
        ax2.set_title(f"Ch {ch_i}: Second Derivative of log(Power) vs Current")
        ax2.legend()
        ax2.grid(True)

        # Plot first derivative on the right
        ax3.plot(I_d1, d1, marker='o', label='First derivative')
        if threshold_current_1st is not None:
            ax3.axvline(threshold_current_1st, color='blue', linestyle='--', label=f'First Deriv. Max at {threshold_current_1st:.2f} mA')
        ax3.set_xlabel("Current (mA)")
        ax3.set_ylabel("First derivative of log(Power)")
        ax3.set_title(f"Ch {ch_i}: First Derivative of log(Power) vs Current")
        ax3.legend()
        ax3.grid(True)

        fig_combined.tight_layout()

        # Save the combined figure as SVG and PNG
        svg_filename_combined = base_name + f"_derivatives_ch{ch_i}.svg"
        save_path_svg_combined = os.path.join(save_dir, svg_filename_combined)
        fig_combined.savefig(save_path_svg_combined, format="svg", bbox_inches="tight")
        print(f"Saved combined derivatives plot to {save_path_svg_combined}")

        png_filename_combined = base_name + f"_derivatives_ch{ch_i}.png"
        save_path_png_combined = os.path.join(save_dir, png_filename_combined)
        fig_combined.savefig(save_path_png_combined, format="png", bbox_inches="tight")
        print(f"Saved combined derivatives plot to {save_path_png_combined}")
    else:
        # Plot the second derivative
        fig2 = plt.figure(figsize=(8, 6))
        plt.plot(I_d2, d2, marker='o', label='Second derivative')
        if threshold_current_2nd is not None:
            plt.axvline(threshold_current_2nd, color='red', linestyle='--', label=f'Second Deriv. Max at {threshold_current_2nd:.2f} mA')
        plt.xlabel("Current (mA)")
        plt.ylabel("Second derivative of log(Power)")
        plt.title("Second Derivative of log(Power) vs Current")
        plt.legend()
        plt.grid(True)

        # Plot the first derivative
        fig3 = plt.figure(figsize=(8, 6))
        plt.plot(I_d1, d1, marker='o', label='First derivative')
        if threshold_current_1st is not None:
            plt.axvline(threshold_current_1st, color='blue', linestyle='--', label=f'First Deriv. Max at {threshold_current_1st:.2f} mA')
        plt.xlabel("Current (mA)")
        plt.ylabel("First derivative of log(Power)")
        plt.title("First Derivative of log(Power) vs Current")
        plt.legend()
        plt.grid(True)

    

    if base_name is not None and save_dir is not None:
        fig_combined, (ax2, ax3) = plt.subplots(1, 2, figsize=(14, 6))

        # Plot LI (LOG) curve in dBm
        ax2.plot(I, L, marker='o', label='Power (dBm)')
        if threshold_current_2nd is not None:
            ax2.axvline(threshold_current_2nd, color='red', linestyle='--', label=f'Second Deriv. Max at {threshold_current_2nd:.2f} mA')
        ax2.set_xlabel("Current (mA)")
        ax2.set_ylabel("Power (dBm)")
        ax2.set_title(f"Ch {ch_i}: Power (dBm) vs Current (mA)")
        ax2.legend()
        ax2.grid(True)

        # Plot LI curve in mW
        ax3.plot(I, channel, marker='o', label='Power (mW)')
        if threshold_current_2nd is not None:
            ax3.axvline(threshold_current_2nd, color='red', linestyle='--', label=f'Second Deriv. Max at {threshold_current_2nd:.2f} mA')
        ax3.set_xlabel("Current (mA)")
        ax3.set_ylabel("Power (mW)")
        ax3.set_title(f"Ch {ch_i}: Power (mW) vs Current (mA)")
        ax3.legend()
        ax3.grid(True)

        fig_combined.tight_layout()

        # Save the channel plot as an SVG file in the output folder
        svg_filename = base_name + f"_LI_ch{ch_i}.svg"
        save_path_svg = os.path.join(save_dir, svg_filename)
        fig_combined.savefig(save_path_svg, format="svg", bbox_inches="tight")
        print(f"Saved channel {ch_i} plot to {save_path_svg}")

        # Save the channel plot as an PNG file in the output folder
        png_filename = base_name + f"_LI_ch{ch_i}.png"
        save_path_png = os.path.join(save_dir, png_filename)
        fig_combined.savefig(save_path_png, format="png", bbox_inches="tight")
        print(f"Saved channel {ch_i} plot to {save_path_png}")
    else:

        fig1 = plt.figure(figsize=(8, 6))
        plt.plot(I, L, marker='o', label='Power (dBm)')
        if threshold_current_2nd is not None:
            plt.axvline(threshold_current_2nd, color='red', linestyle='--', label=f'Second Deriv. Max at {threshold_current_2nd:.2f} mA')
        if threshold_current_1st is not None:
            plt.axvline(threshold_current_1st, color='blue', linestyle='--', label=f'First Deriv. Max at {threshold_current_1st:.2f} mA')
        plt.xlabel("Current (mA)")
        plt.ylabel("Power (dBm)")
        plt.title("LIV (dBm)")
        plt.legend()
        plt.grid(True)

        # Plot Power (mW) vs Current with both thresholds
        L1 = channel
        fig4 = plt.figure(figsize=(8, 6))
        plt.plot(I, L1, marker='o', label='Power (mW)')
        if threshold_current_2nd is not None:
            plt.axvline(threshold_current_2nd, color='red', linestyle='--', label=f'Second Deriv. Max at {threshold_current_2nd:.2f} mA')
        if threshold_current_1st is not None:
            plt.axvline(threshold_current_1st, color='blue', linestyle='--', label=f'First Deriv. Max at {threshold_current_1st:.2f} mA')
        plt.xlabel("Current (mA)")
        plt.ylabel("Power (mW)")
        plt.title("LIV (mW)")
        plt.legend()
        plt.grid(True)

    return threshold_current_2nd

def main():
    print("Starting trend detection...")
    import scipy.io

    path0 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_03_16_16_15_12_loopTEST_liv_1310nm_ChipA1_R0/2025_03_16_16_15_12_loopTEST_liv_1310nm_ChipA1_R0.mat"
    path1 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_03_16_16_56_11_hangzouTEST_liv_1310nm_ChipA1_R1/2025_03_16_16_56_11_hangzouTEST_liv_1310nm_ChipA1_R1.mat"
    path2 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_07_21_39_43_LIV_wlm_1310nm_ChipC31_R1__iter22/2025_05_07_21_39_43_LIV_wlm_1310nm_ChipC31_R1__iter22.mat"
    #path3 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6.mat"
    #path4 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_08_20_43_18_LIV_1310nm_ChipC31_R1__iter25/2025_05_08_20_43_18_LIV_1310nm_ChipC31_R1__iter25.mat"
    #path5 = "C:/Users/OWNER/Desktop/LIV_0604_2/LIV/2025_05_01_19_55_58_LIV_1310nm_Chip27_R5_clad__iter16/2025_05_01_19_55_58_LIV_1310nm_Chip27_R5_clad__iter16.mat"
    #path6 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6.mat"
    #path7 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_08_20_43_18_LIV_1310nm_ChipC31_R1__iter25/2025_05_08_20_43_18_LIV_1310nm_ChipC31_R1__iter25.mat"
    path8 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_06_07_01_18_LIV_1330nm_ChipD34_R3/2025_04_06_07_01_18_LIV_1330nm_ChipD34_R3.mat"
    path9 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_08_01_26_31_LIV_1330nm_ChipD24_R5/2025_04_08_01_26_31_LIV_1330nm_ChipD24_R5.mat"
    path10 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_08_03_47_53_LIV_1330nm_ChipD24_R14/2025_04_08_03_47_53_LIV_1330nm_ChipD24_R14.mat"
    path11 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_06_10_42_01_LIV_1310nm_ChipD22_R10/2025_04_06_10_42_01_LIV_1310nm_ChipD22_R10.mat"
    path12 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_08_04_07_19_LIV_1330nm_ChipD24_R7/2025_04_08_04_07_19_LIV_1330nm_ChipD24_R7.mat"
    path13 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_08_03_47_53_LIV_1330nm_ChipD24_R14/2025_04_08_03_47_53_LIV_1330nm_ChipD24_R14.mat"
    path14 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_09_14_55_57_LIV_1550nm_ChipD24_L1/2025_04_09_14_55_57_LIV_1550nm_ChipD24_L1.mat"
    path15 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_08_01_47_08_LIV_1330nm_ChipD24_R6/2025_04_08_01_47_08_LIV_1330nm_ChipD24_R6.mat"
    path16 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_06_04_15_45_LIV_1330nm_ChipD36_R0/2025_04_06_04_15_45_LIV_1330nm_ChipD36_R0.mat"
    path17 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_09_15_23_03_LIV_1550nm_ChipD24_L0/2025_04_09_15_23_03_LIV_1550nm_ChipD24_L0.mat"
    path18 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_08_02_50_38_LIV_1330nm_ChipD24_R10/2025_04_08_02_50_38_LIV_1330nm_ChipD24_R10.mat"
    path19 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_09_15_23_03_LIV_1550nm_ChipD24_L0/2025_04_09_15_23_03_LIV_1550nm_ChipD24_L0.mat"
    path20 = "C:/Users/OWNER/Downloads/LIV (2)/LIV/2025_04_08_04_19_12_LIV_1330nm_ChipD24_R4/2025_04_08_04_19_12_LIV_1330nm_ChipD24_R4.mat"
    
    IV = True
    

    paths = [path19,path20,path18]
    for path in paths:
        print(f"Processing file: {path}")
        mat_data = scipy.io.loadmat(path)

        current = np.squeeze(mat_data.get("current", np.array([])))
        voltage = np.squeeze(mat_data.get("voltage", np.array([])))

        #fit_iv(current, voltage)

        # Extract specific variables from the MATLAB workspace and save as numpy arrays
        channel_0 = np.squeeze(mat_data.get("channel_0", np.array([]))) if "channel_0" in mat_data else np.array([])
        channel_1 = np.squeeze(mat_data.get("channel_1", np.array([]))) if "channel_1" in mat_data else np.array([])
        channel_2 = np.squeeze(mat_data.get("channel_2", np.array([]))) if "channel_2" in mat_data else np.array([])
        channel_3 = np.squeeze(mat_data.get("channel_3", np.array([]))) if "channel_3" in mat_data else np.array([])
        channel_4 = np.squeeze(mat_data.get("channel_4", np.array([]))) if "channel_4" in mat_data else np.array([])
        channel_5 = np.squeeze(mat_data.get("channel_5", np.array([]))) if "channel_5" in mat_data else np.array([])
        
        channels = [channel_0, channel_1, channel_2, channel_3, channel_4, channel_5]
        # for i, channel in enumerate(channels):
        #     # if channel.size == 0 or np.log(channel.mean()) <= -10:
        #     #     print(f"Channel {i} is empty or not found in the file.")
        #     #     channels[i] = None
        #     #     continue
        #     # print(f"Channel {i} numpy array:", channel)

        #print(channel_0)
        for i, channel in enumerate(channels):
            if channel is None:
                continue
            print(f"Channel {i} Data:")

            threshold = run_liv(current, voltage, channel)

            #thresh_I = fit_guess(current, channel)

            # smoothed = smooth_data(channel)
            # gradpts = detect_trend_gradient(channel, current)

            # fig, ax = plt.subplots()
            # ax.scatter(current, smoothed, color='magenta', label=f'Smooth Data (ch{i})', alpha=0.5)
            # ax.scatter(current, channel, color='black', label=f'Raw Data (ch{i})', alpha=0.5)
            
            # for point in gradpts:
            #     print(f"GRAD - Current: {current[point]}, Power: {channel[point]} mW")
            #     ax.axvline(x=current[point], color='red', linestyle='--', label='Threshold Current', alpha=0.5)
            # # epoints = detect_trend_elbow(channel, current)
            # # for point in epoints:
            # #     print(f"ELBOW - Current: {current[point]}, Power: {channel[point]} mW")
            # #     ax.axvline(x=current[point], color='blue', linestyle='dotted', label='Threshold Current', alpha=0.5)
            # elbowpts = find_elbow_smoothed(channel,current)
            # for point in elbowpts:
            #     print(f"ELBOW SMOOTHED - Current: {current[point]}, Power: {channel[point]} mW")
            #     ax.axvline(x=current[point], color='green', linestyle='dashdot', label='Threshold Current', alpha=0.5)
            
            # guess = find_weighted_threshold(gradpts, elbowpts)
            # if guess is not None:
            #     print(f"Weighted Threshold Current: {current[guess]}, Power: {channel[guess]} mW")
            #     ax.axvline(x=current[guess], color='magenta', label='Weighted Threshold Current', alpha=0.5)
            # else:
            #     print("No common threshold candidates found.")
        plt.show()

if __name__ == '__main__':
    main()
