# Wafer-Scale-Laser-Integration
Intended for use with laser-characterization measurements (.cvs) of the following types and expected data:
- Optical Spectrum Analysis (OSA): Sorted in sweeps (number unlimited), for each we record a single temperature and current, and an array of input wavelengths (swept over) and associated optical power outputs.
- Power-Current-Voltage (LIV): Current, voltage, and temperature is all-inclusive, power is channel-specific (supports up to 4 channels).
- Wavelength Meter (WLM): Identical to LIV, with the addition of wavelength (all-inclusve).

    

The scripts here are used for data analysis for on-chip laser characterization with the following primary functionality:
- extract and organize data from the Scylla station in Lab 4060 (LC group)
- Visualize and save data for each measurement
- Use the extracted data of multiple devices to compare performance. 

The system is automated, once the beginning prompts are completed the program will process as many files as you give it with no further user input.

<b><em>User should only need to use main.py.</em></b>


# FILE NAME FORMAT:
Starred items (*) are required, the rest are recommended.<br><br>
(item = example)<br>

*custom = "anything123"<br>
*datatype = "LIV" (or "OSA")<br>
wavelength = "1310nm" <br>
*chipID = "Chip27"<br>
deviceID = "R5" <br>
cladding = "clad" (or "unclad") <br>
iteration = "iter90"

filename = custom_datatype_wavelength_chipID_deviceID_cladding_iteration.csv

Example: "anything123_LIV_1310nm_Chip27_R5_clad_iter90.csv"

Note: Format is case insensitive.

# USE GUIDE:
1. Run main.py

2. You will be prompted to select a folder. Select the parent folder containing the file(s) to be processed and submit.

3. You will shown a clickable list of all files in the parent folder. Select the file(s) you wish to process.

4. You will be asked to overwrite or skip existing files - these are files which have previously been processed (meaning a .mat file has been generated and can be found within the parent folder). 

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;y: all files will be processed from scratch, existing .mat and any plots will be replaced.<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;n: files will be processed unless an appropriate .mat can be found, in which case relevent data will be extracted &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;from the .mat.

5. On submission, the program will attempt to process the selected files as LIV, then as WLM, and finally as OSA.
Attempts to process a given file as any type (LIV, WLM, OSA) will skip any files not containing the type in their name ('liv', 'wlm', 'osa'). NOTE: A file will only be processed as LIV if the file name contains 'liv' and does NOT contain 'wlm' - all file names containing 'wlm' will be processed as WLM.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Data is organized and saved to .mat, characteristic plots are generated and saved both as .png and as .svg. In the &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;terminal, you can monitor progress and/or terminate early using the CTRL+C command.

6. As the program processes each file, it will store a unique IDtag and certain data points depending on the file type. Once all files have been processed, these data points will be used to compare all selected files within a certain type. Thus, even if you select files of multiple types, they will be processed and compaired seperately (WLM is processed only as WLM, and compaired only to other WLM, and so on). 

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Comparison plots are generated and saved as both .png and as .svg.



# Data Characterization

## OSA
### Individual Files:
Saved to .mat:

1. For each Sweep:
    - Current (single value) 
    - Temperature (single value)
    - Wavelength
    - Optical Power 
    - Peak Power in Sweep (single value)
    - Wavelength at peak power (single value)
2. 2nd Degree Polynomial fit parameters (Peak WL vs Current for each Sweep)
3. 3rd Degree Polynomial fit parameters (Peak WL vs Current for each Sweep)


Plots (One per type, containing all sweeps):
1. Peak Power vs Current
2. Optical Power vs Wavelength
3. Peak Wavelength vs Current - with 2nd degree fit
4. Peak Wavelength vs Current - with 3rd degree fit

### Comparison:
1. Peak Power vs Current
2. Peak Power at 25 mA
3. Peak power at 50 mA
4. Peak wavelength vs Current
5. Peak wavelength vs Current with polynomial fits (R-squared included)

## LIV
### Individual Files:
Saved to .mat:
1. Voltage 
2. Current
3. Temperature
4. Peak Power (single value)
5. Current at peak power (single value)
6. Voltage at peak power (single value)
7. For each channel:
    - Threshold Current (single value)
    - Power in mW
    - Power in dBm


Plots:
1. IV Curve
2. Differential Resistance vs Current
3. For each channel:
    - LI Curve in dBm and in mW
    - 1st and 2nd derivatives of LI curve

### Comparison Plots:
Note: Data channel set manually, by default it is often either ch1 or ch2, but it is recommended that the user checks ALL plotting functions in multi_LIV to ensure the correct channel is prioritized. 
1. Threshold of data channel (Bar)
2. Threshold of data channel (box)
3. Power at 25mA (in mW)
4. Power at 25mA (in dBm)
5. Power at 50mA (in mW)
6. Power at 50mA (in dBm)
7. Temperature vs Current
8. VI Curves
9. LI Curves


## WLM
### Individual Files:
Saved to .mat:
1. Voltage 
2. Current
3. Wavelength
4. Temperature 
5. Peak Power (single value)
6. Current at peak power (single value)
7. Voltage at peak power (single value)
8. Wavelength at peak power (single value)
9. For each channel:
    - Power in mW
    - Power in dBm


Plots:
1. IV Curve
2. Wavelength vs Current
3. Temperature vs Current
3. For each channel:
    - LI Curve in dBm and in mW

### Comparison:
1. Voltage vs Current (VI curves)
2. Wavelength vs Current 

