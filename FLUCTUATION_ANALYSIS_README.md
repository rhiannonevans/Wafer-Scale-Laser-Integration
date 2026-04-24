# Fluctuation Analysis Feature

## Overview
The `plot_spectrograms.py` script has been enhanced to automatically quantify power and wavelength fluctuations over time for all spectrogram plots, with **intelligent multi-peak detection and tracking**.

## New Features

### 1. Automated Fluctuation Analysis
For each spectrogram (benchtop, on-chip, eval system), the script now automatically:

- **Tracks peak wavelength over time** - Identifies the wavelength of maximum power at each time point
- **Tracks peak power over time** - Records the maximum power value at each time point  
- **Calculates average power over time** - Computes the mean power across all wavelengths at each time point
- **Handles multiple peaks intelligently** - Can track dominant peak, specific peak by wavelength, or all peaks

### 2. Peak Detection Modes

The analysis supports **three different peak detection modes** to handle spectrograms with multiple peaks:

#### **Mode 1: "dominant" (Default)**
- Tracks the **global maximum** (single highest peak) at each time point
- Use when: You have a single dominant peak or want to track whatever is brightest
- **Pros**: Simple, always finds something, works for single-peak data
- **Cons**: Can jump between different physical peaks if their relative heights change

#### **Mode 2: "nearest"**
- Tracks the peak **nearest to a specified wavelength**
- Use when: You have multiple peaks but want to track one specific resonance
- **Pros**: Stays locked to the same physical peak even if its power varies
- **Cons**: Requires you to specify the target wavelength
- **Example**: Track the peak near 1330.5 nm even if there are peaks at 1330.3 and 1330.7 nm

#### **Mode 3: "all"**
- Detects **all significant peaks** at each time point
- Tracks the most prominent peak for statistics, but shows all peaks in plots
- Use when: You want to see all resonances and understand multi-peak behavior
- **Pros**: Complete picture of all peaks, can see mode-hopping
- **Cons**: More complex analysis, requires prominence threshold tuning

### 3. Configurable Parameters

You can customize the peak detection behavior:

- **`peak_mode`**: Choose "dominant", "nearest", or "all"
- **`target_wavelength`**: For "nearest" mode, specify which peak to track (in nm)
- **`prominence_threshold`**: For "nearest"/"all" modes, minimum peak prominence (as fraction of max power, default 0.1 = 10%)

### 4. Statistical Metrics Calculated

#### For "all" mode - Multi-Peak Detection Summary:
- **Number of peaks detected**: Average, std dev, min, max across all time points
- Shows how many resonances are present and how stable the mode structure is

#### Peak Wavelength Statistics:
- **Mean**: Average peak wavelength across all time points
- **Std Deviation**: Standard deviation showing wavelength stability
- **Min/Max**: Minimum and maximum peak wavelengths observed
- **Range**: Total wavelength variation (max - min)
- **Total Drift**: Net wavelength shift from start to end (last - first)

#### Peak Power Statistics:
- **Mean**: Average peak power
- **Std Deviation**: Power stability indicator
- **Min/Max**: Power extremes
- **Range**: Total power variation
- **CV (Coefficient of Variation)**: Relative variability as percentage (std/mean × 100%)

#### Average Power Statistics:
- Same metrics as peak power, but calculated on the average power across the spectrum

### 5. Output Files Generated

For each spectrogram, you will now get **3 additional files**:

1. **`{prefix}_fluctuation_statistics.txt`**
   - Text file with all calculated statistics
   - Includes analysis settings (peak mode, target wavelength, prominence threshold)
   - For "all" mode: includes multi-peak detection summary
   - Easy to read and include in reports
   - Example: `benchtop_spectrogram_fluctuation_statistics.txt`

2. **`{prefix}_fluctuation_analysis.png`**
   - Multi-panel plot showing:
     - Top panel: Peak wavelength vs. time with mean and ±1σ bands
       - In "all" mode: shows all detected peaks as gray X markers
     - Middle panel: Peak power vs. time with mean and ±1σ bands
       - In "all" mode: shows all detected peak powers as gray X markers
     - Bottom panel: Average power vs. time with mean and ±1σ bands
   - Plot titles indicate which peak mode was used
   - Example: `benchtop_spectrogram_fluctuation_analysis.png`

### 6. Analysis Applied To

The fluctuation analysis is automatically run for:

- **Benchtop spectrograms** - Using the wavelength ROI specified (wl_min to wl_max)
- **On-chip spectrograms** - Using the full wavelength range
- **Eval system spectrograms** - Separate analysis for power2, power3, and power4 channels

## Example Statistics Output

### Dominant Peak Mode (Default)
```
FLUCTUATION ANALYSIS STATISTICS
============================================================

ANALYSIS SETTINGS:
  Peak Detection Mode: dominant
  Analysis Region:     1330.280 - 1330.920 nm

PEAK WAVELENGTH STATISTICS:
  Mean:              1330.547123 nm
  Std Deviation:     0.012456 nm
  Min:               1330.521000 nm
  Max:               1330.573000 nm
  Range:             0.052000 nm
  Total Drift:       0.015000 nm
...
```

### Multi-Peak "All" Mode
```
FLUCTUATION ANALYSIS STATISTICS
============================================================

ANALYSIS SETTINGS:
  Peak Detection Mode: all
  Prominence Threshold: 10.0% of max power
  Analysis Region:     1330.280 - 1330.920 nm

MULTI-PEAK DETECTION SUMMARY:
  Average # of peaks:  2.3
  Std Dev # of peaks:  0.58
  Min # of peaks:      1
  Max # of peaks:      3
  (Statistics below are for most prominent peak at each time)

PEAK WAVELENGTH STATISTICS:
  Mean:              1330.547123 nm
  Std Deviation:     0.012456 nm
  Min:               1330.521000 nm
  Max:               1330.573000 nm
  Range:             0.052000 nm
  Total Drift:       0.015000 nm
...
```

### "Nearest" Target Peak Mode
```
FLUCTUATION ANALYSIS STATISTICS
============================================================

ANALYSIS SETTINGS:
  Peak Detection Mode: nearest
  Target Wavelength:   1330.500 nm
  Prominence Threshold: 10.0% of max power
  Analysis Region:     1330.280 - 1330.920 nm

PEAK WAVELENGTH STATISTICS:
  Mean:              1330.502456 nm
  Std Deviation:     0.008123 nm
  ...
```

## Interpretation Guide

### Wavelength Stability
- **Low Std Deviation** (< 0.01 nm): Excellent wavelength stability
- **Low Range** (< 0.05 nm): Minimal wavelength drift
- **Small Total Drift**: Laser frequency is stable over time

### Power Stability  
- **Low CV** (< 5%): Excellent power stability
- **High CV** (> 10%): Significant power fluctuations, may need investigation
- **Monotonic trend**: May indicate thermal drift or degradation

## Usage

No changes to usage - fluctuation analysis is automatic!

```bash
# Benchtop analysis (interactive)
python plot_spectrograms.py --benchtop

# On-chip analysis  
python plot_spectrograms.py --onchip --osa-file path/to/osa.mat --liv-dir path/to/liv

# Eval system analysis (via GUI selection)
python plot_spectrograms.py
```

The fluctuation analysis plots and statistics files will be automatically generated in the output directory alongside the spectrogram plots.

## Technical Notes

- Peak detection uses `np.argmax()` - finds global maximum at each time point
- Statistics are calculated over the region of interest (ROI) if specified
- Coefficient of variation (CV) provides a normalized measure of variability
- Analysis handles NaN values gracefully for incomplete datasets
