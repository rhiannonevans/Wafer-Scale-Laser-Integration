# Multi-Peak Detection Summary

## The Problem You Identified

You correctly pointed out that the original implementation used `np.argmax(spectrum)` which only finds the **global maximum** - the single highest peak. This is too simplistic for spectrograms with **multiple peaks**, which can lead to:

1. **Peak jumping**: If two peaks compete for dominance, the tracked "peak" jumps between them
2. **Lost information**: Other resonances are completely ignored
3. **Misleading statistics**: Wavelength drift appears large when it's actually just switching between peaks

## The Solution

I've implemented **three intelligent peak detection modes** to handle multi-peak scenarios:

### Mode Comparison Table

| Mode | Best For | How It Works | Wavelength Stability | Pros | Cons |
|------|----------|--------------|---------------------|------|------|
| **dominant** | Single peak or don't care which | Tracks global maximum at each time | Can be HIGH if peaks compete | Simple, always works | Jumps between peaks |
| **nearest** | Tracking a specific resonance | Finds peak nearest to target wavelength | LOW for single peak | Locks onto one peak | Need to know target wavelength |
| **all** | Understanding multi-mode behavior | Detects all prominent peaks | Varies (tracks most prominent) | Complete picture | More complex |

## Demo Results (Two Competing Peaks)

Using synthetic data with two peaks that alternate dominance:

```
MODE 1 (dominant):
  Peak wavelength std:   0.1964 nm  ← HIGH due to jumping between peaks
  Peak wavelength range: 0.4114 nm  ← Spans both peak positions
  
MODE 2 (nearest to 1330.3 nm):
  Peak wavelength std:   0.0045 nm  ← 44x LOWER! Smooth single-peak tracking
  Peak wavelength range: 0.0167 nm  ← Only the targeted peak's variation
  
MODE 3 (all peaks):
  Average # of peaks:    2.0        ← Correctly detects both resonances
  Peak wavelength std:   0.1964 nm  ← Similar to dominant (tracks most prominent)
  Shows ALL peaks as gray X markers in plots
```

## How to Choose the Right Mode

### Use **"dominant"** when:
- ✅ You have single-peak data
- ✅ You want the simplest analysis
- ✅ You don't care which resonance is tracked
- ❌ NOT recommended for multi-peak data where peaks compete

### Use **"nearest"** when:
- ✅ You have multiple peaks but want to track ONE specific resonance
- ✅ You know approximately where your peak of interest is located
- ✅ You want stable tracking even when peak power varies
- ✅ Example: "Track the fundamental mode at 1330.5 nm, ignore side modes"

### Use **"all"** when:
- ✅ You want to see ALL resonances in your data
- ✅ You're investigating mode hopping or multi-mode operation
- ✅ You want to understand how many peaks are present
- ✅ You want visual confirmation of peak detection quality
- ⚠️ Statistics still track ONE peak (most prominent), but plots show all

## Configuration Parameters

```python
quantify_fluctuations(
    spec, wavelength, times, output_dir,
    prefix="my_analysis",
    peak_mode="nearest",           # Choose: "dominant", "nearest", or "all"
    target_wavelength=1330.5,      # Required for "nearest" mode (nm)
    prominence_threshold=0.1        # For "nearest"/"all": min peak prominence 
                                   # (0.1 = 10% of max power)
)
```

### Tuning `prominence_threshold`:
- **Higher (0.2-0.3)**: Only finds very prominent peaks, ignores noise/side peaks
- **Lower (0.05-0.1)**: Finds weaker peaks, may detect noise
- **Default (0.1)**: Good starting point for most data

## Current Implementation in plot_spectrograms.py

All three processing functions now use **default "dominant" mode** for backward compatibility:

```python
# Benchtop, On-chip, Eval system all use:
quantify_fluctuations(spec, ref_wl, rel_minutes, output_dir, 
                     prefix="...", 
                     peak_mode="dominant")  # Default
```

### To Change to a Different Mode:

Edit the function calls in `plot_spectrograms.py`:

```python
# Example: Track peak near 1330.5 nm in benchtop data
benchtop_stats = quantify_fluctuations(spec, ref_wl, rel_minutes, output_dir, 
                                      prefix="benchtop_spectrogram", 
                                      wl_roi=wl_roi,
                                      peak_mode="nearest",
                                      target_wavelength=1330.5,
                                      prominence_threshold=0.1)
```

## Visual Differences in Output Plots

- **dominant/nearest**: Clean plots showing one tracked peak
- **all**: Same main plot PLUS gray X markers showing all other detected peaks at each time point

## Recommendations

1. **Start with "dominant"** to see if you have single or multi-peak behavior
2. **If wavelength std is unexpectedly high** (>0.05 nm), check if you have multiple peaks
3. **Use "all" mode to investigate** and see all peaks visually
4. **Switch to "nearest"** once you identify which peak you want to track
5. **Tune prominence_threshold** if peaks aren't being detected or too much noise is picked up

## Files Generated

All three modes produce the same file types:
- `{prefix}_fluctuation_statistics.txt` - Includes mode information
- `{prefix}_fluctuation_analysis.png` - Plots (with gray X for "all" mode)

The statistics file clearly indicates which mode was used and what parameters were set.
