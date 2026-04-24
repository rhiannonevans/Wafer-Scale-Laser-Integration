# Temperature Analysis Guide

## Overview

The `plot_spectrograms.py` script now generates **temperature drift analysis plots** for all three measurement systems (Benchtop, On-Chip, and Eval System) when temperature data is available.

## Two Types of Temperature Plots

For each system with temperature data, you get **TWO plots**:

### 1. Absolute Temperature Plot
**Filename**: `{system}_temperature_drift.png`

Shows the **absolute temperature** values over time with statistics:
- All measured temperature points
- Mean temperature (blue dashed line)
- Min temperature (green dotted line)
- Max temperature (orange dotted line)
- Statistics box showing mean, std dev, min, max, range, and number of points

**Use this to:**
- See the absolute operating temperature
- Identify the temperature range during measurement
- Spot temperature trends or cycling
- Check thermal stability

### 2. Delta Temperature Plot (ΔT from Initial) ⭐ NEW
**Filename**: `{system}_temperature_delta.png`

Shows the **temperature change from the initial value** in °C:
- ΔT = T(t) - T(initial)
- Zero line at ΔT = 0 (the reference point)
- Shaded ±1σ band showing typical fluctuation
- Statistics box with initial T, std dev, max |ΔT|, and final ΔT

**Use this to:**
- See thermal drift from the starting point
- Quantify how much temperature changed during measurement
- Identify thermal settling or runaway
- Correlate with wavelength drift (thermal effects)

## Temperature Delta (ΔT) Explained

### What Is It?

```
ΔT(t) = Temperature(t) - Temperature(initial)
```

- **At t=0**: ΔT = 0°C (by definition - this is your reference)
- **Positive ΔT**: Temperature increased (heating)
- **Negative ΔT**: Temperature decreased (cooling)
- **Near zero**: Temperature stable throughout measurement

### Example Interpretation

```
Initial T:     25.123°C
Std Dev:       0.045°C
Max |ΔT|:      0.234°C
Final ΔT:      +0.180°C
```

**Analysis:**
- Started at 25.123°C
- Typical fluctuation: ±0.045°C
- Maximum excursion: 0.234°C from initial
- Ended 0.180°C warmer than start
- **Conclusion**: Gradual heating trend, likely thermal settling after power-on

## Statistics Provided

### Absolute Temperature Statistics:
- **Mean**: Average temperature across all measurements
- **Std Dev**: Temperature stability indicator
- **Min/Max**: Temperature range bounds
- **Range**: Total temperature swing (Max - Min)
- **Points**: Number of temperature measurements

### Delta Temperature Statistics:
- **Initial T**: Your starting reference temperature
- **Std Dev**: RMS fluctuation from initial value
- **Max |ΔT|**: Largest temperature deviation (positive or negative)
- **Final ΔT**: Where you ended relative to where you started
  - Close to 0 → good thermal stability
  - Large positive → heating trend
  - Large negative → cooling trend

## Temperature Quality Guidelines

| Stability Level | Std Dev (°C) | Max |\u0394T| (°C) | Quality |
|----------------|--------------|----------------|---------|
| Excellent | < 0.05 | < 0.1 | Very stable, controlled environment |
| Good | 0.05-0.15 | 0.1-0.3 | Typical for lab measurements |
| Moderate | 0.15-0.5 | 0.3-1.0 | Some thermal drift, acceptable for many apps |
| Poor | > 0.5 | > 1.0 | Significant thermal instability |

## Correlation with Wavelength Drift

Temperature changes directly affect laser wavelength through:
1. **Refractive index changes**: dn/dT
2. **Cavity length changes**: Thermal expansion
3. **Gain peak shifts**: In active materials

### Typical Relationships:
- **1°C temperature change** ≈ **80-100 pm wavelength shift** (for typical semiconductor lasers at 1330 nm)
- **0.1°C change** ≈ **8-10 pm shift**
- **0.01°C change** ≈ **0.8-1 pm shift**

**Example Analysis:**
```
From delta_temperature plot:
  Final ΔT = +0.18°C (heating)

From wavelength_drift_pm plot:
  Final Δλ = +15.2 pm (red shift)

Expected shift: 0.18°C × 85 pm/°C ≈ 15.3 pm ✓
Conclusion: Wavelength drift fully explained by temperature change
```

## File Naming Convention

### Benchtop System:
- `benchtop_temperature_drift.png` - Absolute temperature
- `benchtop_temperature_delta.png` - ΔT from initial ⭐ NEW

### On-Chip System:
- `onchip_temperature_drift.png` - Absolute temperature
- `onchip_temperature_delta.png` - ΔT from initial ⭐ NEW

### Eval System:
- `evalsys_temperature_drift.png` - Absolute temperature
- `evalsys_temperature_delta.png` - ΔT from initial ⭐ NEW

## When Temperature Data is Available

### Benchtop:
- Extracted from CSV files
- Looks for "temperature" or "temp" rows in CSV
- Filters out zero values
- Multiple temperature readings per file are collected

### On-Chip (LIV):
- Looks for temperature fields in .mat files
- Searches for keys: 'temperature', 'Temperature', 'temp', 'Temp'
- Filters zeros and applies same filtering as current/power data

### Eval System:
- Extracts 'srs_temps' from .mat files
- Interpolates to match current/power data resolution
- Temperature typically sampled at 10× lower rate than current

## Plot Features

### Visual Elements:
1. **Scatter points**: Individual temperature measurements
2. **Zero line** (ΔT plot): Horizontal black line at ΔT = 0
3. **Shaded band** (ΔT plot): ±1σ region (red, 20% opacity)
4. **Statistics box**: Light blue background (positioned top-left)
5. **Grid**: Light dotted lines for easier reading
6. **Legend**: Shows what each element represents

### Color Coding:
- **Dark red points**: Temperature measurements
- **Black zero line**: Reference (ΔT = 0)
- **Red shaded band**: ±1σ typical fluctuation
- **Light blue stats box**: Easy to distinguish from wavelength plots

## Common Patterns and What They Mean

### Pattern 1: Monotonic Increase (Heating)
```
ΔT plot: Steady upward trend
Final ΔT: Positive (e.g., +0.5°C)
```
**Causes**: Thermal settling after power-on, insufficient cooling, ambient temperature rise
**Impact**: Red shift in wavelength

### Pattern 2: Monotonic Decrease (Cooling)
```
ΔT plot: Steady downward trend
Final ΔT: Negative (e.g., -0.3°C)
```
**Causes**: Over-active cooling, ambient temperature drop
**Impact**: Blue shift in wavelength

### Pattern 3: Oscillating
```
ΔT plot: Sinusoidal or random fluctuations
Std Dev: Relatively high
```
**Causes**: HVAC cycling, PID controller oscillation, external disturbances
**Impact**: Wavelength jitter

### Pattern 4: Stable
```
ΔT plot: Flat around ΔT ≈ 0
Std Dev: < 0.05°C
Final ΔT: Close to 0
```
**Causes**: Excellent thermal control, stable environment
**Impact**: Minimal wavelength drift

## Integration with Other Analyses

The temperature delta plots complement:

1. **Wavelength drift plots** (`*_wavelength_drift_pm.png`)
   - Compare ΔT with Δλ to verify thermal origin of drift
   - Expected correlation: ~85 pm/°C

2. **Power fluctuation plots** (`*_fluctuation_analysis.png`)
   - Temperature changes can affect laser output power
   - Check if power drops correlate with temperature spikes

3. **Spectrograms** (`*_spectrogram.png`)
   - Diagonal features in spectrograms often indicate thermal drift
   - ΔT plot confirms thermal origin

## Example Combined Analysis

**Scenario**: High wavelength instability observed

**Step 1**: Check `wavelength_drift_pm.png`
```
Δλ Std Dev: 35 pm (high!)
Δλ Range: 120 pm
```

**Step 2**: Check `temperature_delta.png`
```
ΔT Std Dev: 0.35°C
ΔT Range: 1.2°C
```

**Step 3**: Calculate expected wavelength shift
```
Expected Δλ from ΔT = 1.2°C × 85 pm/°C = 102 pm
Observed Δλ range = 120 pm
```

**Conclusion**: Most of the wavelength drift (85%) is explained by temperature changes. Improve thermal control to stabilize wavelength.

## Tips for Using Temperature Delta Plots

1. **Compare with wavelength plots** - Should show strong correlation
2. **Look for thermal settling** - Initial rapid drift followed by stabilization
3. **Check Final ΔT** - Large values indicate poor thermal equilibrium
4. **Monitor Std Dev** - Lower is better for stability
5. **Note the time scale** - Fast changes vs. slow drift have different causes

## Summary

Temperature delta plots provide:
- ✅ Clear reference to initial conditions (ΔT = 0 at start)
- ✅ Easy identification of heating/cooling trends
- ✅ Quantification of thermal stability
- ✅ Direct correlation with wavelength drift
- ✅ Better insight than absolute temperature alone

Use these plots alongside wavelength drift analysis for complete thermal characterization of your laser system!
