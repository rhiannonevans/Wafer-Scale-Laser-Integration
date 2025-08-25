# Wafer-Scale-Laser-Integration
The scripts here are used for data analysis for on-chip laser measurements with the following primary functionality:
- extract different kinds of data (OSA, LIV, benchtop, etc) in csv files and save in .mat with certain plots
- analyze multiple OSA data
- analyze multiple LIV and wavelength meter data
- compare between benchtop and on-chip laser measurements


# USER INFO

For producing data plots from wavelength metre [LIV (+ Wavelength)] and OSA from CSV. Capable of processing files individually and producing comparison plots for multiple files.


## FILE NAME FORMAT:
Starred items (*) are required, the rest are recommended.
(item = example)

*custom = "anything123"
*datatype = "LIV" (or "OSA")
wavelength = "1310nm" 
*chipID = "Chip27"
deviceID = "R5" 
cladding = "clad" (or "unclad") 
iteration = "iter90

filename = custom_datatype_wavelength_chipID_deviceID_cladding_iteration.csv

Example: "anything123_LIV_1310nm_Chip27_R5_clad_iter90.csv"

Note: Format is case insensitive.



## USE GUIDE:
1. Run main.py

2. You will be prompted to select a folder. Select the parent folder containing the file(s) to be processed and submit.

3. You will shown a clickable list of all files in the parent folder. Select the file(s) you wish to process.

4. You will be asked to overwrite or skip existing files - these are files which have previously been processed (meaning a .mat file has been generated and can be found within the parent folder). 

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;y: all files will be processed from scratch, existing .mat and any plots will be replaced.<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;n: files will be processed unless an appropriate .mat can be found, in which case relevent data will be extracted &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;from the .mat.

5. On submission, the program will attempt to process the selected files as LIV, then as WLM, and finally as OSA.
Attempts to process a given file as any type (LIV, WLM, OSA) will skip any files not containing the type in their name ('liv', 'wlm', 'osa'). NOTE: A file will only be processed as LIV if the file name contains 'liv' and does NOT contain 'wlm' - all file names containing 'wlm' will be processed as WLM.

Data is organized and saved to .mat, characteristic plots are generated and saved both as .png and as .svg. In the terminal, you can monitor progress and/or terminate early using the CTRL+C command.

6. As the program processes each file, it will store a unique IDtag and certain data points depending on the file type. Once all files have been processed, these data points will be used to compare all selected files within a certain type. Thus, even if you select files of multiple types, they will be processed and compaired seperately (WLM is processed only as WLM, and compaired only to other WLM, and so on). 

Comparison plots are generated and saved as both .png and as .svg.




### For OSA:
"filename_Ipeaks"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/2025_04_27_20_04_58_OSA_1310nm_Chip27_R5_clad_Ipeaks.png)<br>
"filename_spectrum"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/2025_04_27_20_04_58_OSA_1310nm_Chip27_R5_clad_spectrum.png)<br>
"filename_WLpeaks"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/2025_04_27_20_04_58_OSA_1310nm_Chip27_R5_clad_WLPeaks.png)<br>

### For LIV/WLM:
"filename_LI_ch#" *** # replaced with 1, 2, 3..., one is produced for each channel in the csv <br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/main/Documentation/2025_04_04_18_35_48_LIV_1310nm_ChipC32_R4_LI_ch2.png)<br>
"filename_derivatives_ch#"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/main/Documentation/2025_04_04_18_35_48_LIV_1310nm_ChipC32_R4_derivatives_ch2.png)<br>
"filename_I_dVdIcurve"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/main/Documentation/2025_04_05_23_28_24_LIV_1310nm_ChipC31_R2_I_dVdIcurve.png)<br>

(The last two are omitted if there is no useful wavelength data in the csv)<br>
"filename_WL_vs_Current"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/main/Documentation/2025_05_29_19_51_09_bothLIVwlm_1330nm_channel4_ChipD30_R0_clad_WL_vs_Current.png)<br>
"filename_Temp_vs_WL"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/main/Documentation/2025_05_29_19_51_09_bothLIVwlm_1330nm_channel4_ChipD30_R0_clad_Temp_vs_WL.png)<br>




## MULTI-File / Comparison Processing:
Run base_multi.py

Opt to (1) run all files in a parent folder or (2) run only select files from a parent folder.

(1) Select parent folder (script will process all files in the parent folder, it will search through subfolders as well)
(3) Select parent folder from first window, submit and from the next window select (check boxes for) desired files.

Choose what to do for files which have been processed already and for which a .mat file exists. Either "y" to overwrite (re-process) or "n" to skip these files (use previously processed data).

Choose to process files of type (1) "OSA", (2) "LIV", or (3) "WLM". 

The following plots and characteristic data (for comparison), and a .mat file containing the organized data, will be saved to the parent folder.

### FOR OSA COMPARISONS
"current_wl"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/current_wl.png)<br>
"osa_current_peakL"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/osa_current_peakL.jpg)<br>
"singlePT_osa"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/1ec14481114dfe28c4617163fcd4c9d644a5fca5/Documentation/singlePT_osa.png)<br>

### FOR LIV COMPARISONS
"peak_power_current_comparison_liv"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/main/Documentation/peak_power_current_comparison_liv.png)<br>
"peak_power_current_comparison_filtered_liv"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/main/Documentation/peak_power_current_comparison_filtered_liv.png)<br>
"threshI_comparison_liv"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/main/Documentation/threshI_comparison_liv.png)<br>

### FOR WLM COMPARISONS
The same as the outputs for LIV Comparisons, with the file names:
"peak_power_current_comparison_wlm"<br>
"peak_power_current_comparison_filtered_wlm"<br>
"threshI_comparison_wlm"<br>
<!-- "wavelength_power_comparison"<br>
![](https://github.com/rhiannonevans/Wafer-Scale-Laser-Integration/blob/main/Documentation/wavelength_power_comparison.png) -->
