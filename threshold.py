"""
    Filters and detects trends in LIV data using gradient and elbow methods. 
    The code identifies significant points in the data that indicate a trend, specifically the threshold current point, then guesses
    the true threshold point based on the intersection of multiple detection methods.

    If run as a script, it processes LIV data from specified .mat files, detects trends, and plots the results. This is ideal for troubleshooting
    new ways of detecting threshold currents - will show you a plot of all detected points (gradient, elbow, and weighted threshold) for each channel in the LIV data
"""


import pandas as pd
import extract as ex
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from scipy.signal import savgol_filter
from collections import Counter


#Call only if power > -20 dBm
def detect_trend(data):
    df = pd.DataFrame(data)
    pois = []
    # Calculate moving averages once for efficiency
    shortMA = df.rolling(window=3).mean()
    longMA = df.rolling(window=5).mean()  # Use a longer window for trend
    # Detect significant positive crossover: shortMA crosses above longMA
    cross = (shortMA[0] > longMA[0]) & (shortMA[0].shift(1) <= longMA[0].shift(1))
    # Only consider points where power > -40 dBm
    for idx in cross[cross].index:
        pois.append(idx)
        # if -10 > np.log(df[0][idx]) > -40:
        #     pois.append(idx)
    return pois

def detect_trend_gradient(data, current):
    data = np.array(data)
    current = np.array(current)
    
    # Smooth the data
    #smoothed = gaussian_filter1d(data, sigma=2)
    # alpha = 0.2  # Smoothing factor between 0 and 1
    # ema = [data[0]]
    # for d in data[1:]:
    #     ema.append(alpha * d + (1 - alpha) * ema[-1])
    # smoothed = np.array(ema)

    # from scipy.signal import butter, filtfilt
    # b, a = butter(N=2, Wn=0.1)  # N=order, Wn=normalized cutoff frequency
    # smoothed = filtfilt(b, a, data)

    smoothed = smooth_data(data)
    
    # Compute the gradient (dy/dx)
    dy = np.gradient(smoothed)
    dx = np.gradient(current)
    gradient = dy / dx
    pois = []
    
    # Find first point where slope exceeds threshold and stays high
    for i in range(1, len(gradient)):
        # Only consider if current (in mA) at i is less than 25 (30 to be generous) and greater than 8
        if 8 < current[i] < 20:
            # Calculate average gradient before i (all previous points) and after i (all following points)
            before = gradient[:i]
            after = gradient[i+1:]
            integral_before = np.trapz(data[:i], current[:i]) if i > 1 else 0
            integral_after = np.trapz(data[i:], current[i:]) if i < len(data) - 1 else 0
            integral = integral_before + integral_after
            if len(before) > 0 and len(after) > 0:
                if np.mean(before) < np.mean(after) and integral_before/integral <= 0.001:
                    pois.append(i)
    # if not pois or all(p == 0 for p in pois):
    #     # If no points found, decrease slope threshold and try again
    #     step_size =  0.000005
    #     new_slope = slope_threshold - step_size
    #     if new_slope <= 0: # Avoid negative slope threshold, give up if data is not suitable
    #         return [0] * len(pois)
    #     print(f"No points found with slope threshold {slope_threshold}. Trying with {new_slope}...")

    #     #recursively call the function with a lower slope threshold
    #     detect_trend_gradient(data, current, new_slope)

    return pois


def detect_trend_elbow(data, current):
    data = np.array(data)
    current = np.array(current)
    
    # Smooth data
    smoothed = gaussian_filter1d(data, sigma=2)
    
    # Compute first and second derivative
    grad1 = np.gradient(smoothed, current)
    grad2 = np.gradient(grad1, current)

    pois = []
    # for i in range(1, len(grad2)):
    #     if grad2[i] > slope_threshold and all(grad2[i:i+3] > slope_threshold):
    #         pois.append(i)

    for i in range(1, len(grad2)):
        # Only consider if current (in mA) at i is less than 25 (30 to be generous) and greater than 8 
        if 8 < current[i] < 20:
            # Calculate average (2nd) gradient before i (all previous points) and after i (all following points)
            before = grad2[:i]
            after = grad2[i+1:]
            before1 = grad1[:i]
            after1 = grad1[i+1:]
            integral_before = np.trapz(data[:i], current[:i]) if i > 1 else 0
            integral_after = np.trapz(data[i:], current[i:]) if i < len(data) - 1 else 0
            integral = integral_before + integral_after
            if len(before) > 0 and len(after) > 0:
                if np.mean(before) < np.mean(after) and np.mean(before1) < np.mean(after1): #and grad1[i] > np.mean(before1) and integral_before/integral <= 0.001:
                    pois.append(i)
    return pois

def find_elbow_smoothed(data,current, window=7, polyorder=2):
    """
    Like find_elbow, but first smooths the data via Savitzky–Golay.
    window must be odd and >= 3; if data is shorter, it auto‐adjusts.
    """

    data = data[:50]
    arr = np.asarray(data, dtype=float)
    N = arr.size
    if N < 2:
        return None

    # Adjust window to be at most N (and odd & ≥3)
    w = min(window, N if N % 2 == 1 else N - 1)
    if w < 3:
        w = 3
    if w % 2 == 0:
        w += 1

    smooth = savgol_filter(arr, window_length=w, polyorder=polyorder)
    # from scipy.signal import butter, filtfilt
    # b, a = butter(N=2, Wn=0.1)  # N=order, Wn=normalized cutoff frequency
    # smooth = filtfilt(b, a, data)
    
    # Then exactly the same logic as before, but on 'smooth'
    max_delta = -np.inf
    elbow_idx = []
    for i in range(N - 1):
        if 8 < current[i] < 20:
            delta = smooth[i+1] - smooth[i]
            if delta > max_delta:
                max_delta = delta
                elbow_idx.append(i + 1)

    return elbow_idx

''' Determine true threshold point from many possible points by weighing candidates. Candidates refer to 
    points common to at least two trend detection methods. Candidates common to three methods are weighed 
    higher than those common to two, points detected by only one method have no weight (zero).    
'''

def find_weighted_threshold(gradient, elbow):
    # Combine all values with source tracking
    all_points = gradient + elbow

    # Count occurrences
    count = Counter(all_points)

    # Assign weights: only keep those with count >= 2
    weighted_points = {pt: count for pt, count in count.items() if count >= 2}

    if not weighted_points:
        print("No common threshold candidates found.")
        return None

    # Find point(s) with max weight
    max_weight = max(weighted_points.values())
    candidates = [pt for pt, w in weighted_points.items() if w == max_weight]

    # Choose the smallest index among top candidates (or customize selection here)
    best_point = min(candidates)

    return best_point

def find_threshold(data, current):
    """
    Find the threshold point in the data based on gradient and elbow detection.
    Returns the index of the threshold point.
    """
    # Detect trend gradient points
    gradpts, smoothed = detect_trend_gradient(data, current)
    print(f"Gradient points detected: {gradpts}")
    
    # Detect trend elbow points
    elbowpts = find_elbow_smoothed(data, current)
    print(f"Elbow points detected: {elbowpts}")

    # Find weighted threshold point
    guess = find_weighted_threshold(gradpts, elbowpts)
    print(f"Weighted threshold guess: {guess}")

    return guess

def smooth_data(data):
    alpha = 0.2  # Smoothing factor between 0 and 1
    ema = [data[0]]
    for d in data[1:]:
        ema.append(alpha * d + (1 - alpha) * ema[-1])
    smooth = np.array(ema)
    return smooth

from scipy.optimize import curve_fit

def piecewise_linear(I, Ith, a, b):
    """
    I   : array of currents
    Ith : threshold current
    a   : slope above threshold
    b   : baseline output below threshold
    """
    return np.where(I < Ith,
                    b,
                    a * (I - Ith) + b)

def fit_guess(I_data, L_data, show=True):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    # initial guesses: 
    #   Ith ~ the midpoint of your current range,
    #   a   ~ (max(L)-min(L)) / (max(I)-min(I)),
    #   b   ~ min(L)
    p0 = [I_data.mean(), 
        (L_data.max() - L_data.min())/(I_data.max() - I_data.min()), 
        L_data.min()]

    # optionally constrain Ith to lie within [min(I), max(I)]
    bounds = ([I_data.min(),    0,       -np.inf],
            [I_data.max(),  np.inf,    np.inf])

    popt, pcov = curve_fit(piecewise_linear,
                        I_data, L_data,
                        p0=p0, bounds=bounds)

    Ith_fit, a_fit, b_fit = popt
    print(f"Threshold current Ith = {Ith_fit:.3f} mA")
    
    if show:
        I_fine = np.linspace(I_data.min(), I_data.max(), 200)
        L_fine = piecewise_linear(I_fine, *popt)

        ax.plot(I_data, L_data,   'o', label="data")
        ax.plot(I_fine, L_fine,  '-', label="piecewise fit")
        ax.axvline(Ith_fit, color='k', ls='--', label=f"Ith = {Ith_fit:.3f}")
        ax.set_xlabel("Current (mA)")
        ax.set_ylabel("Power")
        #plt.legend()
        plt.show()
        
    return Ith_fit

def main():
    print("Starting trend detection...")
    import scipy.io

    path0 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_03_16_16_15_12_loopTEST_liv_1310nm_ChipA1_R0/2025_03_16_16_15_12_loopTEST_liv_1310nm_ChipA1_R0.mat"
    path1 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_03_16_16_56_11_hangzouTEST_liv_1310nm_ChipA1_R1/2025_03_16_16_56_11_hangzouTEST_liv_1310nm_ChipA1_R1.mat"
    path2 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_07_21_39_43_LIV_wlm_1310nm_ChipC31_R1__iter22/2025_05_07_21_39_43_LIV_wlm_1310nm_ChipC31_R1__iter22.mat"
    #path3 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6.mat"
    #path4 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_08_20_43_18_LIV_1310nm_ChipC31_R1__iter25/2025_05_08_20_43_18_LIV_1310nm_ChipC31_R1__iter25.mat"
    #path5 = "C:/Users/OWNER/Desktop/LIV_0604_2/LIV/2025_05_01_19_55_58_LIV_1310nm_Chip27_R5_clad__iter16/2025_05_01_19_55_58_LIV_1310nm_Chip27_R5_clad__iter16.mat"
    #path6 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6.mat"
    #path7 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_08_20_43_18_LIV_1310nm_ChipC31_R1__iter25/2025_05_08_20_43_18_LIV_1310nm_ChipC31_R1__iter25.mat"
    paths = [path0, path1, path2]
    for path in paths:
        print(f"Processing file: {path}")
        mat_data = scipy.io.loadmat(path)

        current = np.squeeze(mat_data.get("current", np.array([])))

        # Extract specific variables from the MATLAB workspace and save as numpy arrays
        channel_0 = np.squeeze(mat_data.get("channel_0", np.array([]))) if "channel_0" in mat_data else np.array([])
        channel_1 = np.squeeze(mat_data.get("channel_1", np.array([]))) if "channel_1" in mat_data else np.array([])
        channel_2 = np.squeeze(mat_data.get("channel_2", np.array([]))) if "channel_2" in mat_data else np.array([])
        channel_3 = np.squeeze(mat_data.get("channel_3", np.array([]))) if "channel_3" in mat_data else np.array([])
        channel_4 = np.squeeze(mat_data.get("channel_4", np.array([]))) if "channel_4" in mat_data else np.array([])
        channel_5 = np.squeeze(mat_data.get("channel_5", np.array([]))) if "channel_5" in mat_data else np.array([])
        
        channels = [channel_0, channel_1, channel_2, channel_3, channel_4, channel_5]
        for i, channel in enumerate(channels):
            if channel.size == 0 or np.log(channel.mean()) <= -10:
                print(f"Channel {i} is empty or not found in the file.")
                channels[i] = None
                continue
            print(f"Channel {i} numpy array:", channel)

        #print(channel_0)
        for i, channel in enumerate(channels):
            if channel is None:
                continue
            print(f"Channel {i} Data:")

            thresh_I = fit_guess(current, channel)

            # smoothed = smooth_data(channel)
            # gradpts = detect_trend_gradient(channel, current)

            # fig, ax = plt.subplots()
            # ax.scatter(current, smoothed, color='magenta', label=f'Smooth Data (ch{i})', alpha=0.5)
            # ax.scatter(current, channel, color='black', label=f'Raw Data (ch{i})', alpha=0.5)
            
            # for point in gradpts:
            #     print(f"GRAD - Current: {current[point]}, Power: {channel[point]} mW")
            #     ax.axvline(x=current[point], color='red', linestyle='--', label='Threshold Current', alpha=0.5)
            # # epoints = detect_trend_elbow(channel, current)
            # # for point in epoints:
            # #     print(f"ELBOW - Current: {current[point]}, Power: {channel[point]} mW")
            # #     ax.axvline(x=current[point], color='blue', linestyle='dotted', label='Threshold Current', alpha=0.5)
            # elbowpts = find_elbow_smoothed(channel,current)
            # for point in elbowpts:
            #     print(f"ELBOW SMOOTHED - Current: {current[point]}, Power: {channel[point]} mW")
            #     ax.axvline(x=current[point], color='green', linestyle='dashdot', label='Threshold Current', alpha=0.5)
            
            # guess = find_weighted_threshold(gradpts, elbowpts)
            # if guess is not None:
            #     print(f"Weighted Threshold Current: {current[guess]}, Power: {channel[guess]} mW")
            #     ax.axvline(x=current[guess], color='magenta', label='Weighted Threshold Current', alpha=0.5)
            # else:
            #     print("No common threshold candidates found.")
    plt.show()

if __name__ == '__main__':
    main()
