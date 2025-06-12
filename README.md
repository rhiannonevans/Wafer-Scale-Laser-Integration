# Wafer-Scale-Laser-Integration
The scripts here are used for data analysis for on-chip laser measurements with the following primary functionality:
- extract different kinds of data (OSA, LIV, benchtop, etc) in csv files and save in .mat with certain plots
- analyze multiple OSA data
- analyze multiple LIV and wavelength meter data
- compare between benchtop and on-chip laser measurements


# USER INFO

For producing data plots from wavelength metre [LIV (+ Wavelength)] and OSA from CSV. Capable of processing files individually and producing comparison plots for multiple files.


## REQUIRED FILE FORMAT:

custom = "anything123"
datatype = "LIV" (or "OSA")
wavelength = "1310nm" 
chipID = "Chip27"
rowID = "R5" 
cladding = "clad" (or "unclad")
iteration = "iter90

filename = custom_datatype_wavelength_chipID_rowID_cladding_iteration.csv

Example: "anything123_LIV_1310nm_Chip27_R5_clad__iter90.csv"



## INDIVIDUAL File Processing:
Run process_csv.py

Opt to (1) run an individual file, (2) run all files in a parent folder, or (3) run only select files from a parent folder.

(1) Select file from the popup window.
(2) Select parent folder (script will process all files in the parent folder, it will search through subfolders as well)
(3) Select parent folder from first window, then select (check boxes for) desired files.


Choose to process files of type (1) "OSA", (2) "LIV", or (3) to run all files (OSA and LIV). 

The following plots and characteristic data (for comparison), and a .mat file containing the organized data, will be saved to a subfolder of the same name as your file.


### For OSA:
"filename_Ipeaks"
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/2025_04_27_20_04_58_OSA_1310nm_Chip27_R5_clad_Ipeaks.png)
"filename_spectrum"
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/2025_04_27_20_04_58_OSA_1310nm_Chip27_R5_clad_spectrum.png)
"filename_WLpeaks"
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/2025_04_27_20_04_58_OSA_1310nm_Chip27_R5_clad_WLPeaks.png)

### For LIV:
"filename_LI_channel#" *** # replaced with 1, 2, 3..., one is produced for each channel in the csv
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/2025_05_07_21_39_43_LIV_wlm_1310nm_ChipC31_R1__iter22_LI_channel1.png)
"filename_IVcurve"
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6_IVcurve.png)
"filename_dVdIcurve"
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/2025_05_08_16_09_17_LIV_wlm_1310nm_ChipC31_R1__iter14_dVdIcurve.png)

(The last two are omitted if there is no useful wavelength data in the csv)
"filename_WL_vs_Current"
EXAMPLE IMAGE
"filename_WL_vs_Temp"
EXAMPLE IMAGE




## MULTI-File / Comparison Processing:
Run base_multi.py

Opt to (1) run all files in a parent folder or (2) run only select files from a parent folder.

(1) Select parent folder (script will process all files in the parent folder, it will search through subfolders as well)
(3) Select parent folder from first window, submit and from the next window select (check boxes for) desired files.


Choose to process files of type (1) "OSA" or (2) "LIV". 

The following plots and characteristic data (for comparison), and a .mat file containing the organized data, will be saved to the parent folder.
