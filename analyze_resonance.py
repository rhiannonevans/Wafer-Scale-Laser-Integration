"""
Python port of MATLAB analyze_resonance function
Adapted for wafer-scale laser integration analysis
Author: Sheri & Copilot
Date: 2025-10-17
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from scipy.signal import find_peaks, medfilt
from lorentzfit import lorentzfit


def analyze_resonance(wavelength, power, 
                      noiseLevel=-60,
                      minProminence=1.5,
                      minDistance=2,
                      useEqualFitWidth=True,
                      fitWidthMult=4,
                      baselineWidthMult=0.5,
                      resampleFactor=50,
                      RsqThresh=0.7,
                      linearizeFit=True,
                      dBThresh=[5, 1.5],
                      useThreshForER=True,
                      use_medFilter=0,
                      correct_powerData=None,
                      dbg=False,
                      width_scale=1):
    """
    Analyze resonance peaks in optical spectrum data.
    
    Parameters:
        wavelength : array_like
            Wavelength data (will be converted to nm)
        power : array_like
            Power data in dBm
        noiseLevel : float
            Threshold for noise in dBm (default: -60)
        minProminence : float
            Minimum ER/peak prominence in dBm (default: 1.5)
        minDistance : float
            Minimum FSR/peak spacing in nm (default: 2)
        useEqualFitWidth : bool
            Use equal fit window based on widest peak (default: True)
        fitWidthMult : float
            Multiplier for fit window width (default: 4)
        baselineWidthMult : float
            Proportion of peak window for baseline fitting (default: 0.5)
        resampleFactor : int
            Resampling factor for wavelength (default: 50)
        RsqThresh : float
            R-squared threshold for good fit (default: 0.7)
        linearizeFit : bool
            Linearize power before fitting (default: True)
        dBThresh : list
            ER thresholds [dB_scale, linear_scale] (default: [5, 1.5])
        useThreshForER : bool
            Use Rsq threshold for ER calculation (default: True)
        use_medFilter : int
            Median filter width, 0 to disable (default: 0)
        correct_powerData : dict or None
            Power correction parameters (default: None)
        dbg : bool
            Plot debug figures (default: False)
        width_scale : float
            Scaling for Lorentzian width parameter (default: 1)
    
    Returns:
        dict with keys:
            numPeaks, avg_ER, avg_ER_fit, avg_Q, FSR, FSR_err, finesse,
            resLocs, ERs, ERs_fit, FWHMs, Qs, fitParams, gofs
    """
    
    # Default power correction settings
    if correct_powerData is None:
        correct_powerData = {
            'flag': True,
            'badData': -100,
            'repData': -80,
            'removeClipping': False,
            'clipVal': -80
        }
    
    # Ensure arrays
    wavelength = np.asarray(wavelength, dtype=float).flatten()
    power = np.asarray(power, dtype=float).flatten()
    
    # Correct power data for anomalous readings
    power_pkFind = power.copy()
    if correct_powerData['flag']:
        power[power == correct_powerData['badData']] = correct_powerData['repData']
        power_pkFind = power.copy()
        
        if correct_powerData['removeClipping']:
            # Remove consecutive clipping values
            for i in range(1, len(power)-1):
                if (power[i] == correct_powerData['clipVal'] and
                    power[i-1] == correct_powerData['clipVal'] and
                    power[i+1] == correct_powerData['clipVal']):
                    power[i] = np.nan
    
    # Convert wavelength to nm if needed (assume input is in meters if max < 100)
    if np.max(wavelength) < 100:
        wavelength = wavelength * 1e9
    
    # Apply median filter for peak finding if requested
    if use_medFilter > 0:
        power_for_peaks = medfilt(-power_pkFind, kernel_size=use_medFilter)
    else:
        power_for_peaks = -power_pkFind
    
    # Find peaks
    peaks_dict = find_peaks(power_for_peaks, 
                           prominence=minProminence,
                           distance=int(minDistance / np.mean(np.diff(wavelength))))
    
    locs_idx = peaks_dict[0]
    if len(locs_idx) == 0:
        print("***Warning: No peaks found in spectrum. Skipping analysis.")
        return _return_empty_results()
    
    # Check noise level
    noise_count = np.sum(power < noiseLevel) + np.sum(np.isnan(power))
    if noise_count > len(power) / 2 or np.sum(np.isnan(power)) > len(power) / 5:
        print("***Warning: Spectrum found to be mostly noise. Skipping analysis.")
        return _return_empty_results()
    
    locs = wavelength[locs_idx]
    pks = power_for_peaks[locs_idx]
    
    # Estimate widths
    widths = peaks_dict[1]['widths'] if 'widths' in peaks_dict[1] else np.ones(len(locs)) * minDistance
    widths = widths * np.mean(np.diff(wavelength))  # Convert to nm
    
    ERs = peaks_dict[1]['prominences'] if 'prominences' in peaks_dict[1] else np.ones(len(locs)) * minProminence
    
    numPeaks = len(locs)
    print(f"Found {numPeaks} peaks")
    
    # --- Baseline correction ---
    baseline = power.copy()
    xdiff = np.mean(np.diff(wavelength))
    
    # Remove peaks from baseline
    for pkIdx in range(numPeaks):
        pkCentreIdx = locs_idx[pkIdx]
        if useEqualFitWidth:
            fitWidth = int(np.ceil(np.max(widths) * baselineWidthMult * fitWidthMult / xdiff))
        else:
            fitWidth = int(np.ceil(widths[pkIdx] * baselineWidthMult * fitWidthMult / xdiff))
        
        startIdx = max(0, pkCentreIdx - fitWidth)
        endIdx = min(len(wavelength), pkCentreIdx + fitWidth)
        baseline[startIdx:endIdx] = np.nan
    
    excludeIdx = np.isnan(baseline)
    
    if np.sum(~excludeIdx) < 5:
        print("***Warning: Not enough non-peak points for baseline correction.")
        baselineCorrected = False
    else:
        # Polynomial fit to baseline
        p = np.polyfit(wavelength[~excludeIdx], baseline[~excludeIdx], 3)
        
        # Plot baseline fit
        fig_baseline = plt.figure(figsize=(10, 6))
        plt.plot(wavelength, baseline, '.k', label='Baseline data')
        plt.plot(wavelength, np.polyval(p, wavelength), 'c', label='Polynomial fit')
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Baseline Power (dB)')
        plt.legend()
        plt.grid(True)
        
        # Subtract baseline
        power = power - np.polyval(p, wavelength)
        baselineCorrected = True
    
    # --- Plot baseline-corrected data ---
    fig_main = plt.figure(figsize=(12, 8))
    gs = GridSpec(5, 1, figure=fig_main, hspace=0.3)
    ax_main = fig_main.add_subplot(gs[0:3, 0])  # Rows 0-2 (first 3 rows)
    
    if linearizeFit:
        ax_main.plot(wavelength, 10**(power/10), '.k', label='Data')
        ax_main.set_ylabel('Baseline-Subtracted Power (mW)')
        
        # Also plot dB-scale for troubleshooting
        fig_log = plt.figure(figsize=(12, 6))
        plt.plot(wavelength, power, '.k')
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Power (dBm)')
        plt.grid(True)
    else:
        ax_main.plot(wavelength, power, '.k', label='Data')
        ax_main.set_ylabel('Power (dBm)')
    
    # Overlay found peaks
    pks_plot = -pks
    if baselineCorrected:
        pks_plot = pks_plot - np.polyval(p, locs)
    
    if linearizeFit:
        ax_main.plot(locs, 10**(pks_plot/10), 'm^', markersize=8, label='Found peaks')
        if 'fig_log' in locals():
            plt.figure(fig_log.number)
            plt.plot(locs, pks_plot, 'm^', markersize=8)
            plt.figure(fig_main.number)
    else:
        ax_main.plot(locs, pks_plot, 'm^', markersize=8, label='Found peaks')
    
    ax_main.set_xlabel('Wavelength (nm)')
    ax_main.legend()
    ax_main.grid(True)
    
    # --- Lorentzian fit each peak ---
    FWHMs = np.full(numPeaks, np.nan)
    Qs = np.full(numPeaks, np.nan)
    ERs_fit = np.full(numPeaks, np.nan)
    resLocs = np.full(numPeaks, np.nan)
    fitParams = [None] * numPeaks
    gofs = [None] * numPeaks
    
    ax_residual = fig_main.add_subplot(gs[4, 0])  # Row 4 (last row)
    
    for pkIdx in range(numPeaks):
        pkCentreIdx = locs_idx[pkIdx]
        
        if useEqualFitWidth:
            fitWidth = int(np.ceil(np.max(widths) * 0.5 * fitWidthMult / xdiff))
        else:
            fitWidth = int(np.ceil(widths[pkIdx] * 0.5 * fitWidthMult / xdiff))
        
        startIdx = max(0, pkCentreIdx - fitWidth)
        endIdx = min(len(wavelength), pkCentreIdx + fitWidth)
        
        x = wavelength[startIdx:endIdx]
        y = -power[startIdx:endIdx]
        
        if linearizeFit:
            # Linearize and normalize
            y = 10**(-y/10)
            ymax = np.max(y)
            y = 1 - y/ymax
        
        # Remove NaNs
        mask = ~np.isnan(y)
        x_nonan = x[mask]
        y_nonan = y[mask]
        
        if len(y_nonan) < 5:
            print(f"***Peak {pkIdx+1} warning: insufficient non-NaN datapoints.")
            gofs[pkIdx] = {'rsq': np.nan, 'rsq_peak': np.nan}
            if useThreshForER:
                ERs[pkIdx] = np.nan
            continue
        
        # Set up fit parameters
        if linearizeFit:
            p0 = [(np.max(y_nonan)-np.min(y_nonan))*widths[pkIdx]/width_scale,
                  locs[pkIdx], widths[pkIdx]/width_scale, np.min(y_nonan)]
            bounds = ([0, np.min(x), 0, 0],
                     [np.inf, np.max(x), 10*widths[pkIdx], max(5*np.max(y_nonan), 10)])
        else:
            p0 = [-ERs[pkIdx], locs[pkIdx], widths[pkIdx], np.max(y_nonan)]
            bounds = ([0, np.min(x), 0, 0],
                     [np.inf, np.max(x), 10*widths[pkIdx], max(5*np.max(y), 10)])
        
        # Perform fit
        try:
            yfit, fitpar, resnorm, res = lorentzfit(x_nonan, y_nonan, p0=p0, bounds=bounds)
            fitParams[pkIdx] = fitpar
            
            # Calculate R²
            rsq = 1 - np.sum(res**2) / np.sum((y_nonan - np.mean(y_nonan))**2)
            
            # Get higher-res fit for plotting
            xfit = np.arange(np.min(x), np.max(x), xdiff/resampleFactor)
            yfit_plot = fitpar[0] / ((xfit - fitpar[1])**2 + fitpar[2]) + fitpar[3]
            
            # Plot fit
            if linearizeFit:
                yfit_plot = (1 - yfit_plot) * ymax
                ax_main.plot(xfit, yfit_plot, 'm', linewidth=1.5)
                
                # Calculate ER from fit
                ERs_fit[pkIdx] = 10*(np.log10(ymax*(1 - fitpar[0]/fitpar[2] - fitpar[3]))) - 10*np.log10(ymax*(1 - fitpar[4]))
                
                if 'fig_log' in locals():
                    plt.figure(fig_log.number)
                    yfit_log = 10*np.log10(yfit_plot)
                    plt.plot(xfit, yfit_log, 'm')
                    plt.figure(fig_main.number)
            else:
                yfit_plot = -yfit_plot
                ax_main.plot(xfit, yfit_plot, 'm', linewidth=1.5)
                ERs_fit[pkIdx] = np.abs(np.min(yfit_plot) - np.max(yfit_plot))
            
            # Plot residuals
            ax_residual.plot(x_nonan, res, '.k', markersize=3)
            
            # Store goodness of fit
            gofs[pkIdx] = {
                'res': res,
                'resnorm': resnorm,
                'rsq': rsq,
                'rsq_peak': np.nan
            }
            
            # --- Calculate resonator properties ---
            if rsq > RsqThresh:
                # Resonance wavelength
                resLocs[pkIdx] = fitpar[1]
                
                # FWHM and Q
                if ERs[pkIdx] > dBThresh[int(linearizeFit)]:
                    if linearizeFit:
                        half_max = np.mean([np.max(yfit_plot), np.min(yfit_plot)])
                        temp_idx = np.where(yfit_plot < half_max)[0]
                    else:
                        temp_idx = np.where(yfit_plot < -(fitpar[3] + 3))[0]
                    
                    if len(temp_idx) > 1:
                        FWHMs[pkIdx] = np.abs(xfit[temp_idx[0]] - xfit[temp_idx[-1]])
                        Qs[pkIdx] = resLocs[pkIdx] / FWHMs[pkIdx]
                        
                        # Draw FWHM line
                        if linearizeFit:
                            ax_main.plot([xfit[temp_idx[0]], xfit[temp_idx[-1]]],
                                       [half_max, half_max], 'm:', linewidth=2)
                        else:
                            y_fwhm = -(fitpar[3] + 3)
                            ax_main.plot([xfit[temp_idx[0]], xfit[temp_idx[-1]]],
                                       [y_fwhm, y_fwhm], 'm:', linewidth=2)
                        
                        # Calculate peak region R²
                        FWHM_mask = (x_nonan > resLocs[pkIdx] - FWHMs[pkIdx]) & (x_nonan < resLocs[pkIdx] + FWHMs[pkIdx])
                        if np.sum(FWHM_mask) > 0:
                            res_peak = res[FWHM_mask]
                            y_peak = y_nonan[FWHM_mask]
                            rsq_peak = 1 - np.sum(res_peak**2) / np.sum((y_peak - np.mean(y_peak))**2)
                            gofs[pkIdx]['rsq_peak'] = rsq_peak
                            
                            # Plot peak region points in blue
                            ax_residual.plot(x_nonan[FWHM_mask], res[FWHM_mask], '.b', markersize=4)
                            if linearizeFit:
                                ax_main.plot(x_nonan[FWHM_mask], ymax*(1-y_nonan[FWHM_mask]), '.b', markersize=4)
                            else:
                                ax_main.plot(x_nonan[FWHM_mask], -y_nonan[FWHM_mask], '.b', markersize=4)
                    else:
                        print(f"***Peak {pkIdx+1} warning: could not calculate FWHM and Q due to low ER.")
                else:
                    print(f"***Peak {pkIdx+1} warning: could not calculate FWHM and Q due to low ER.")
            else:
                print(f"***Peak {pkIdx+1} warning: using raw peak location due to low R² of fit.")
                resLocs[pkIdx] = locs[pkIdx]
                if useThreshForER:
                    ERs[pkIdx] = np.nan
                    ERs_fit[pkIdx] = np.nan
                
        except Exception as e:
            print(f"***Peak {pkIdx+1} fit failed: {e}")
            gofs[pkIdx] = {'rsq': np.nan, 'rsq_peak': np.nan}
            resLocs[pkIdx] = locs[pkIdx]
            if useThreshForER:
                ERs[pkIdx] = np.nan
    
    # Set residual plot labels
    ax_residual.axhline(0, color='k', linewidth=0.5)
    ax_residual.set_xlabel('Wavelength (nm)')
    if linearizeFit:
        ax_residual.set_ylabel('Residuals\n(mW)')
    else:
        ax_residual.set_ylabel('Residuals\n(dBm)')
    ax_residual.grid(True)
    
    # Match x-limits
    xlims = ax_main.get_xlim()
    ax_residual.set_xlim(xlims)
    
    plt.tight_layout()
    plt.show()
    
    # --- Calculate averages ---
    # Q
    avg_Q = np.nanmean(Qs) if np.any(~np.isnan(Qs)) else np.nan
    
    # FSR
    resSpacings = np.diff(resLocs[~np.isnan(resLocs)])
    if len(resSpacings) > 0:
        # Remove outliers
        q1, q3 = np.percentile(resSpacings, [25, 75])
        iqr = q3 - q1
        lower = q1 - 1.5*iqr
        upper = q3 + 1.5*iqr
        resSpacingsTrunc = resSpacings[(resSpacings >= lower) & (resSpacings <= upper)]
        
        FSR = np.mean(resSpacingsTrunc) if len(resSpacingsTrunc) > 0 else np.nan
        FSR_err = np.std(resSpacingsTrunc) if len(resSpacingsTrunc) > 0 else np.nan
    else:
        FSR = np.nan
        FSR_err = np.nan
    
    # Finesse
    if np.any(~np.isnan(Qs)) and np.any(~np.isnan(FWHMs)):
        finesse = FSR / np.nanmean(FWHMs)
    else:
        finesse = np.nan
    
    # ER
    avg_ER = np.nanmean(ERs) if np.any(~np.isnan(ERs)) else np.nan
    avg_ER_fit = np.nanmean(ERs_fit) if np.any(~np.isnan(ERs_fit)) else np.nan
    
    return {
        'numPeaks': numPeaks,
        'avg_ER': avg_ER,
        'avg_ER_fit': avg_ER_fit,
        'avg_Q': avg_Q,
        'FSR': FSR,
        'FSR_err': FSR_err,
        'finesse': finesse,
        'resLocs': resLocs,
        'ERs': ERs,
        'ERs_fit': ERs_fit,
        'FWHMs': FWHMs,
        'Qs': Qs,
        'fitParams': fitParams,
        'gofs': gofs
    }


def _return_empty_results():
    """Return empty results dictionary when no peaks found."""
    return {
        'numPeaks': 0,
        'avg_ER': np.nan,
        'avg_ER_fit': np.nan,
        'avg_Q': np.nan,
        'FSR': np.nan,
        'FSR_err': np.nan,
        'finesse': np.nan,
        'resLocs': np.nan,
        'ERs': np.nan,
        'ERs_fit': np.nan,
        'FWHMs': np.nan,
        'Qs': np.nan,
        'fitParams': np.nan,
        'gofs': np.nan
    }


# Example usage
if __name__ == "__main__":
    # Test with synthetic data
    wl = np.linspace(1549, 1551, 1000)
    
    # Create synthetic resonances
    p1 = 0.5 / ((wl - 1549.5)**2 + 0.001)
    p2 = 0.5 / ((wl - 1550.0)**2 + 0.001)
    p3 = 0.5 / ((wl - 1550.5)**2 + 0.001)
    power_lin = p1 + p2 + p3 + 0.05
    power_dbm = 10*np.log10(power_lin) + np.random.randn(len(wl))*0.5
    
    results = analyze_resonance(wl/1e9, power_dbm)
    
    print(f"\nResults:")
    print(f"  Number of peaks: {results['numPeaks']}")
    print(f"  Average Q: {results['avg_Q']:.0f}")
    print(f"  FSR: {results['FSR']*1e3:.2f} pm")
    print(f"  Average ER: {results['avg_ER']:.2f} dB")