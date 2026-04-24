import scipy.io
import numpy as np
import glob
import os

def save_power_values(input_mat_path_pattern, output_mat_path):
    # Find all .mat files matching the pattern
    mat_files = glob.glob(input_mat_path_pattern)
    if not mat_files:
        print(f"No .mat files found matching the pattern: {input_mat_path_pattern}")
        return

    for mat_file in mat_files:
        print(f"Processing file: {mat_file}")
        data = scipy.io.loadmat(mat_file)

        # Extract power values (assuming keys are 'channel_1', 'channel_2', 'channel_3')
        power_keys = ['channel_3'] #['channel_1', 'channel_2', 'channel_3']
        power_values = []

        for key in power_keys:
            if key in data:
                power_values.append(data[key])
            else:
                print(f"Warning: Key '{key}' not found in the file {mat_file}.")

        # Combine all power values into a single array (similar to 'power' in 1(1).mat)
        combined_power = np.vstack(power_values) if power_values else None

        # Transpose the combined power array to save it vertically
        if combined_power is not None:
            combined_power = combined_power.T

        # Generate wavelength values based on the equation: wavelength = 2*current^2 + 3*current + 1310
        if 'current' in data:
            current = data['current']
            wavelength = 2 * np.square(current) + 3 * current + 1310
        else:
            print(f"Warning: Key 'current' not found in the file {mat_file}.")
            wavelength = None

        # Convert power values from mW to dBm
        if combined_power is not None:
            combined_power = (-1) * 10 * np.log10(combined_power)

        # Save the combined power and wavelength values in the desired format
        base_name = os.path.splitext(os.path.basename(mat_file))[0]
        output_file = os.path.join(output_mat_path, f"{base_name}_formatted.mat")
        if combined_power is not None and wavelength is not None:
            scipy.io.savemat(output_file, {'power': combined_power, 'wavelength': wavelength})
            print(f"Power and wavelength values saved to {output_file}")
        elif combined_power is not None:
            scipy.io.savemat(output_file, {'power': combined_power})
            print(f"Power values saved to {output_file}")
        else:
            print(f"No power values found to save for file {mat_file}.")

# Example usage
input_file_pattern = r'C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\A_July_updatedscript_DataAnalysis\20250623_Shuksan_ANT_Light2025_WaferScaleMeasurements\LIV\2025_06_25_17_10_02_LIV_1330nm_ChipD30_R4_clad\*.mat'
output_folder = r'c:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\Obsolete'
save_power_values(input_file_pattern, output_folder)
