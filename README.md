# Wafer-Scale-Laser-Integration
The scripts here are used for data analysis for on-chip laser measurements with the following primary functionality:
- extract different kinds of data (OSA, LIV, benchtop, etc) in csv files and save in .mat with certain plots
- analyze multiple OSA data
- analyze multiple LIV and wavelength meter data
- compare between benchtop and on-chip laser measurements


# USER INFO

For producing data plots from wavelength metre [LIV (+ Wavelength)] and OSA from CSV. Capable of processing files individually and producing comparison plots for multiple files.


## FILE NAME FORMAT:
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

## USE GUIDE:
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
## OSA:
### Individual Files:

### Comparison:

## LIV
### Individual Files:

### Comparison:

## WLM:
### Individual Files:

### Comparison:


