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
EXAMPLE IMAGE
"filename_spectrum"
EXAMPLE IMAGE
"filename_WLpeaks"
EXAMPLE IMAGE
"filename_WLpeaks"
EXAMPLE IMAGE

### For LIV:
"filename_LI_channel#" *** # replaced with 1, 2, 3..., one is produced for each channel in the csv
EXAMPLE IMAGE
"filename_LI_channel#_log" *** # replaced with 1, 2, 3..., one is produced for each channel in the csv
EXAMPLE IMAGE
"filename_IV"
EXAMPLE IMAGE

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
