# Peak Power vs Average Power - Explanation

## What's the Difference?

### Peak Power
- **Definition**: The **maximum power value** in the spectrum at each time point
- **What it represents**: The brightness of the strongest resonance/peak
- **Measured from**: `max(spectrum)` at each time slice
- **Typical value**: 2-3 mW (for strong laser output)
- **Use case**: Monitor laser mode stability and output strength

**Example from synthetic data:**
```
Peak Power Statistics:
  Mean:     2.499 mW  ← The laser's peak output power
  Std Dev:  0.145 mW
  CV:       5.8%      ← 5.8% variation in peak brightness
```

### Average Power
- **Definition**: The **mean of all power values** across the wavelength range
- **What it represents**: Overall power distribution including background, noise, and side modes
- **Measured from**: `mean(spectrum)` at each time slice
- **Typical value**: Much lower than peak (e.g., 0.2-0.5 mW if spectrum is mostly background)
- **Use case**: Monitor total optical power and background drift

**Example from synthetic data:**
```
Average Power Statistics:
  Mean:     0.228 mW  ← Much lower! Includes all the background
  Std Dev:  0.048 mW
  CV:       21.1%     ← Higher CV! More sensitive to noise/baseline shifts
```

## Why Track Both?

| Metric | What It Tells You | What Changes Would Mean |
|--------|-------------------|-------------------------|
| **Peak Power CV** | Stability of laser's main resonance | High CV → mode hopping, pump instability, thermal issues |
| **Average Power CV** | Total power distribution stability | High CV → background drift, multi-mode behavior, alignment changes |

## Key Insights

1. **Different Sensitivities**
   - Peak power: Sensitive to changes in the laser's primary mode
   - Average power: Sensitive to background, side modes, and overall power distribution

2. **Typical Relationship**
   - Average power << Peak power (for well-confined resonances)
   - Peak power CV < Average power CV (peaks are usually more stable than background)

3. **What's Normal?**
   - **Good stability**: Peak power CV < 5%, Average power CV < 10%
   - **Moderate fluctuations**: Peak power CV 5-10%, Average power CV 10-20%
   - **Significant instability**: Peak power CV > 10%, Average power CV > 20%

## Visual Comparison in Plots

The fluctuation analysis creates **3 panels**:

1. **Top**: Peak wavelength vs time (where is the peak?)
2. **Middle**: Peak power vs time (how bright is it?)
3. **Bottom**: Average power vs time (what's the total power level?)

Comparing middle and bottom panels shows if instability is in the peak mode or the overall power distribution.

---

# New Feature: Delta Wavelength Plot (Δλ in pm)

## What Is It?

A **dedicated plot showing wavelength drift from the initial value** in **picometers (pm)**.

### Why Picometers?
- 1 nm = 1000 pm
- Typical laser drift: 0.001 - 0.050 nm = **1-50 pm**
- Picometers give better resolution for small drifts

## How It's Calculated

```python
# Reference: First measurement
initial_wavelength = peak_wavelengths[0]  # e.g., 1330.502513 nm

# For each time point:
Δλ(t) = [wavelength(t) - initial_wavelength] × 1000 pm/nm

# Example:
# t=0:  Δλ = 0 pm        (by definition)
# t=30: Δλ = +12.5 pm    (red shift - longer wavelength)
# t=60: Δλ = -5.0 pm     (blue shift - shorter than initial)
```

## What It Shows

### The Plot
- **X-axis**: Time (minutes)
- **Y-axis**: Δλ from initial (pm)
- **Zero line**: Horizontal black line at Δλ = 0
- **Shaded band**: ±1σ region showing typical drift
- **Points**: Measured drift at each time point

### Interpretation

| Sign | Meaning | Physical Cause |
|------|---------|----------------|
| **Positive Δλ** | Red shift (longer wavelength) | Heating, refractive index increase, cavity expansion |
| **Negative Δλ** | Blue shift (shorter wavelength) | Cooling, refractive index decrease, cavity contraction |
| **Near zero** | Stable wavelength | Good thermal control |
| **Monotonic trend** | Continuous drift | Thermal settling or degradation |
| **Oscillating** | Periodic drift | Temperature cycling, environmental changes |

## Statistics Included

The statistics file now includes:

```
WAVELENGTH DRIFT FROM INITIAL (Δλ):
  Initial λ:         1330.502513 nm   ← Reference wavelength
  Std Deviation:     7.334 pm         ← RMS drift magnitude
  Max |Δλ|:          15.075 pm        ← Maximum excursion from initial
  Final Δλ:          -5.025 pm        ← Net drift over entire measurement
  (Note: Positive = red shift, Negative = blue shift)
```

### What Each Metric Means

- **Initial λ**: Your starting wavelength (reference point)
- **Std Deviation**: How much the wavelength typically wanders (RMS)
- **Max |Δλ|**: Worst-case drift during the measurement
- **Final Δλ**: Where you ended up compared to where you started
  - Close to zero → good return to initial wavelength
  - Large → monotonic drift (thermal settling, aging)

## Example Interpretation

```
Std Deviation:     7.3 pm
Max |Δλ|:          15.1 pm
Final Δλ:          -5.0 pm
```

**Analysis:**
- Wavelength wanders by ±7.3 pm typically
- Maximum excursion was 15.1 pm
- Ended 5 pm blue-shifted from start
- **Conclusion**: Sub-20 pm stability, slight blue drift trend

## Typical Drift Levels

| Drift Level | Std Dev (pm) | Quality |
|-------------|--------------|---------|
| Excellent | < 5 pm | High-precision laser, stable thermal environment |
| Good | 5-20 pm | Well-controlled, suitable for most applications |
| Moderate | 20-50 pm | Some thermal drift, may need better control |
| Poor | > 50 pm | Significant drift, investigate thermal/mechanical issues |

## Files Generated

For each spectrogram analysis, you now get **4 files**:

1. `{prefix}_fluctuation_statistics.txt` - All statistics including Δλ
2. `{prefix}_fluctuation_analysis.png` - 3-panel plot (wavelength, peak power, avg power)
3. **`{prefix}_wavelength_drift_pm.png` - NEW! Delta wavelength plot**
4. Original spectrogram PNG

## Multi-Peak Mode

When using `peak_mode="all"`, the delta wavelength plot also shows **all detected peaks** as gray X markers, allowing you to see:
- Which peak you're tracking (blue line)
- Where other peaks are drifting (gray X's)
- Mode competition and hopping behavior

---

# Summary Table

| Analysis | What It Measures | Units | Output |
|----------|------------------|-------|--------|
| **Peak Wavelength** | Absolute wavelength of peak | nm | Mean, std, min, max, range |
| **Delta Wavelength** | Drift from initial value | pm | Std, max \|Δλ\|, final Δλ |
| **Peak Power** | Maximum spectral power | mW | Mean, std, CV% |
| **Average Power** | Mean spectral power | mW | Mean, std, CV% |

All four analyses help you understand different aspects of laser stability and performance!
