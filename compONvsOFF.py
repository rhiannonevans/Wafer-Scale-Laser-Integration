import os
from tkinter import Tk, filedialog
import scipy.io
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# Initialize the Tkinter root window
root = Tk()
root.withdraw()  # Hide the root window but keep it active for dialogs

# Prompt user to select the OSA folder
osaFolder = filedialog.askdirectory(
    title="Select the folder containing OSA .mat files",
    initialdir=r"C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\20250403_Shuksan_ANT_Light2025_WaferscaleMeasurements\OSA"
)
if not osaFolder:
    raise FileNotFoundError("No OSA folder selected.")

# Prompt user to select the LIV folder
livFolder = filedialog.askdirectory(
    title="Select the folder containing LIV .mat files",
    initialdir=r"C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\20250403_Shuksan_ANT_Light2025_WaferscaleMeasurements\LIV"
)
if not livFolder:
    raise FileNotFoundError("No LIV folder selected.")

# Prompt user to select the Benchtop .mat file
benchtopFile = filedialog.askopenfilename(
    title="Select the Benchtop .mat file",
    filetypes=[("MAT files", "*.mat")],
    initialdir=r"C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\20250403_Shuksan_ANT_Light2025_WaferscaleMeasurements\Benchtop"
)
if not benchtopFile:
    raise FileNotFoundError("No Benchtop .mat file selected.")

# Process OSA files
osaFiles = [f for f in os.listdir(osaFolder) if f.endswith('.mat')]
if not osaFiles:
    raise FileNotFoundError("No .mat files found in the selected OSA folder.")

osaData = scipy.io.loadmat(os.path.join(osaFolder, osaFiles[0]))  # Load the first file
if 'polyfit_peakWL_vs_I_deg2_coeffs' not in osaData:
    raise KeyError("FitParams not found in the selected OSA file.")

# Process LIV files
livFiles = [f for f in os.listdir(livFolder) if f.endswith('.mat')]
if not livFiles:
    raise FileNotFoundError("No .mat files found in the selected LIV folder.")

livData = scipy.io.loadmat(os.path.join(livFolder, livFiles[0]))  # Load the first file
if 'current' not in livData or 'channel3' not in livData:
    raise KeyError("'current' or 'channel3' data not found in the selected LIV file.")

current = np.array(livData['current']).flatten()  # Current data
channel3 = np.array(livData['channel3']).flatten()  # Power data

# Filter current data between 20 mA and 50 mA
validIdx = (current >= 20) & (current <= 50)
currentFiltered = current[validIdx]
powerFiltered = channel3[validIdx]

# Debugging: Print the filtered data
print("Current array (scaled):", current)
print("Valid indices:", validIdx)
print("Filtered current values:", currentFiltered)

# Ensure currentFiltered is not empty
if len(currentFiltered) == 0:
    raise ValueError("No valid current values found in the range 20 mA to 50 mA. Please check the data or adjust the range.")

# Calculate wavelength using the polynomial coefficients
polyfit_peakWL_vs_I_deg2_coeffs = osaData['polyfit_peakWL_vs_I_deg2_coeffs'].flatten()
wavelengthOnChip = (
    polyfit_peakWL_vs_I_deg2_coeffs[0] * currentFiltered**2 +
    polyfit_peakWL_vs_I_deg2_coeffs[1] * currentFiltered +
    polyfit_peakWL_vs_I_deg2_coeffs[2]
)

# Ensure wavelengthOnChip is not empty
if len(wavelengthOnChip) == 0:
    raise ValueError("No valid wavelengths calculated for the on-chip data.")

# Process Benchtop file
benchtopData = scipy.io.loadmat(benchtopFile)  # Load the selected file
if 'wavelength' not in benchtopData or 'channel_4_mW' not in benchtopData:
    raise KeyError("'wavelength' or 'channel_4_mW' data not found in the selected Benchtop file.")

wavelengthBenchtop = np.array(benchtopData['wavelength']).flatten()
powerBenchtop = np.array(benchtopData['channel_4_mW']).flatten()

# Limit Benchtop data to the nearest 0.1 nm range of the on-chip wavelength
minWavelength = np.floor(min(wavelengthOnChip) * 10) / 10  # Round down to nearest 0.1 nm
maxWavelength = np.ceil(max(wavelengthOnChip) * 10) / 10   # Round up to nearest 0.1 nm

benchtopIdx = (wavelengthBenchtop >= minWavelength) & (wavelengthBenchtop <= maxWavelength)
wavelengthBenchtopLimited = wavelengthBenchtop[benchtopIdx]
powerBenchtopLimited = powerBenchtop[benchtopIdx]

# Ensure Benchtop data is valid
if len(wavelengthBenchtopLimited) == 0 or len(powerBenchtopLimited) == 0:
    raise ValueError("No Benchtop data found within the specified wavelength range.")

# Normalize the power values
powerBenchtopNormalized = powerBenchtopLimited / np.max(powerBenchtopLimited)
powerFilteredNormalized = powerFiltered / np.max(powerFiltered)

# Find peaks for Benchtop data
benchtopPeaks, _ = find_peaks(powerBenchtopNormalized, height=0.4)
benchtopPeakWavelengths = wavelengthBenchtopLimited[benchtopPeaks]  # Extract peak wavelengths
benchtopPeakWavelengths = np.sort(benchtopPeakWavelengths)  # Ensure sorted order
benchtopPeakDistances = np.diff(benchtopPeakWavelengths) * 1e3  # Convert to picometers (pm)

# Find peaks for On-Chip data
onChipPeaks, _ = find_peaks(powerFilteredNormalized,  height=0.2)
onChipPeakWavelengths = wavelengthOnChip[onChipPeaks]  # Extract peak wavelengths
onChipPeakWavelengths = np.sort(onChipPeakWavelengths)  # Ensure sorted order
onChipPeakDistances = np.diff(onChipPeakWavelengths) * 1e3  # Convert to picometers (pm)

# Save plot data to a .mat file
comparisonFolder = r"C:\Users\jsheri1\Documents\A_Research\2024-02_Wafer-Scale\20250403_Shuksan_ANT_Light2025_WaferscaleMeasurements\Comparison"
if not os.path.exists(comparisonFolder):
    os.makedirs(comparisonFolder)

benchtopFileName = os.path.basename(benchtopFile)
comparisonFileName = f"Comparison2_{benchtopFileName}"
outputFile = os.path.join(comparisonFolder, comparisonFileName)

scipy.io.savemat(outputFile, {
    'wavelengthBenchtopLimited': wavelengthBenchtopLimited,
    'powerBenchtopNormalized': powerBenchtopNormalized,
    'benchtopPeakWavelengths': benchtopPeakWavelengths,
    'benchtopPeakDistances': benchtopPeakDistances,
    'wavelengthOnChip': wavelengthOnChip,
    'powerFilteredNormalized': powerFilteredNormalized,
    'onChipPeakWavelengths': onChipPeakWavelengths,
    'onChipPeakDistances': onChipPeakDistances
})
print(f"Plot data saved to {outputFile}")

# Plotting
plt.figure(figsize=(12, 8))
plt.tick_params(axis='both', which='major', labelsize=16)  # Set axis tick label font size
plt.plot(wavelengthBenchtopLimited, powerBenchtopNormalized, color='red', linestyle='--', linewidth=1.5, label='Benchtop Laser')
plt.plot(wavelengthOnChip, powerFilteredNormalized, color='purple', linestyle='-', linewidth=1.5, label='On-Chip Laser')

# Annotate Benchtop peak distances
for i in range(len(benchtopPeakDistances)):
    x = (benchtopPeakWavelengths[i] + benchtopPeakWavelengths[i + 1]) / 2
    y = max(powerBenchtopNormalized) * (0.9 if i % 2 == 0 else 0.85)  # Alternate y position
    y_offset = 0.05 * (i % 2)  # Add a small vertical offset to alternate positions
    plt.annotate(f"{benchtopPeakDistances[i]:.1f} pm", (x, y + y_offset), fontsize=10, color='red', ha='center')

# Annotate On-Chip peak distances
for i in range(len(onChipPeakDistances)):
    x = (onChipPeakWavelengths[i] + onChipPeakWavelengths[i + 1]) / 2
    y = max(powerFilteredNormalized) * (0.5 if i % 2 == 0 else 0.75)  # Alternate y position
    y_offset = 0.05 * (i % 2)  # Add a small vertical offset to alternate positions
    plt.annotate(f"{onChipPeakDistances[i]:.1f} pm", (x, y + y_offset), fontsize=10, color='purple', ha='center')

plt.xlim([minWavelength, maxWavelength])  # Set x-axis limits to match the adjusted wavelength range
plt.xlabel('Wavelength (nm)', fontsize=16)
plt.ylabel('Normalized Power', fontsize=16)
plt.legend(loc='upper right', fontsize=13)  # Place the legend in the top-right corner

# Remove "_data" and ".mat" from the benchtop file name for the title
benchtopFileNameCleaned = os.path.splitext(benchtopFileName.replace("_data", ""))[0]

# Set the plot title with the cleaned file name
plt.title(f'Wavelength vs Normalized Power ({benchtopFileNameCleaned})', fontsize=14)

plt.grid(True)

# Save the figure as a PNG file
figureFileName = os.path.splitext(comparisonFileName)[0] + ".png"
figureFilePath = os.path.join(comparisonFolder, figureFileName)
plt.savefig(figureFilePath, format='png', dpi=300)
print(f"Figure saved to {figureFilePath}")

# Show the plot
plt.show()