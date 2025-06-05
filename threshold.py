
import pandas as pd
import extract as ex
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d

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

def detect_trend_gradient(data, current, slope_threshold=0.00001, window=10):
    data = np.array(data)
    current = np.array(current)
    
    # Smooth the data
    #smoothed = gaussian_filter1d(data, sigma=2)
    alpha = 0.2  # Smoothing factor between 0 and 1
    ema = [data[0]]
    for d in data[1:]:
        ema.append(alpha * d + (1 - alpha) * ema[-1])
    smoothed = np.array(ema)
    
    # Compute the gradient (dy/dx)
    dy = np.gradient(smoothed)
    dx = np.gradient(current)
    gradient = dy / dx
    pois = []
    
    # Find first point where slope exceeds threshold and stays high
    for i in range(1, len(gradient)):
        # Only consider if current (in mA) at i is less than 25 (30 to be generous) and greater than 5 
        if 5 < current[i] < 20:
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

    return pois, smoothed


def detect_trend_elbow(data, current,slope_threshold = 0.00001, window=10):
    data = np.array(data)
    current = np.array(current)
    
    # Smooth data
    smoothed = gaussian_filter1d(data, sigma=2)
    
    # Compute first and second derivative
    grad1 = np.gradient(data, current)
    grad2 = np.gradient(grad1, current)

    pois = []
    # for i in range(1, len(grad2)):
    #     if grad2[i] > slope_threshold and all(grad2[i:i+3] > slope_threshold):
    #         pois.append(i)

    for i in range(1, len(grad2)):
        # Only consider if current (in mA) at i is less than 25 (30 to be generous) and greater than 5 
        if 5 < current[i] < 20:
            # Calculate average (2nd) gradient before i (all previous points) and after i (all following points)
            before = grad2[:i]
            after = grad2[i+1:]
            before1 = grad1[:i]
            after1 = grad1[i+1:]
            integral_before = np.trapz(data[:i], current[:i]) if i > 1 else 0
            integral_after = np.trapz(data[i:], current[i:]) if i < len(data) - 1 else 0
            integral = integral_before + integral_after
            if len(before) > 0 and len(after) > 0:
                if np.mean(before) < np.mean(after) and np.mean(before1) < np.mean(after1) and grad1[i] > np.mean(before1) and integral_before/integral <= 0.001:
                    pois.append(i)
    return pois


def main():
    print("Starting trend detection...")
    import scipy.io

    path0 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_03_16_16_15_12_loopTEST_1310nm_ChipA1_R0/2025_03_16_16_15_12_loopTEST_1310nm_ChipA1_R0.mat"
    path1 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_03_16_16_56_11_hangzouTEST_1310nm_ChipA1_R1/2025_03_16_16_56_11_hangzouTEST_1310nm_ChipA1_R1.mat"
    path2 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_07_21_39_43_LIV_wlm_1310nm_ChipC31_R1__iter22/2025_05_07_21_39_43_LIV_wlm_1310nm_ChipC31_R1__iter22.mat"
    path3 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6/2025_05_06_07_52_37_LIV_1310nm_Chip31_R5__iter6.mat"
    #path4 = "C:/Users/OWNER/Desktop/smaller_LIV/2025_05_08_20_43_18_LIV_1310nm_ChipC31_R1__iter25/2025_05_08_20_43_18_LIV_1310nm_ChipC31_R1__iter25.mat"
    path5 = "C:/Users/OWNER/Desktop/LIV_0604_2/LIV/2025_05_01_19_55_58_LIV_1310nm_Chip27_R5_clad__iter16/2025_05_01_19_55_58_LIV_1310nm_Chip27_R5_clad__iter16.mat"
    paths = [path1,path2, path5]
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
            if channel.size == 0 or np.log(channel.mean()) <= -15:
                print(f"Channel {i} is empty or not found in the file.")
                channels[i] = None
                continue
            print(f"Channel {i} numpy array:", channel)

        #print(channel_0)
        for i, channel in enumerate(channels):
            if channel is None:
                continue
            print(f"Channel {i} Data:")
            points, smoothed = detect_trend_gradient(channel, current)
            epoints = detect_trend_elbow(channel, current)
            print(f"Thresholds (ch{i}) detected at {len(points)} points:")
            fig, ax = plt.subplots()
            ax.scatter(current, smoothed, color='green', label=f'Smooth Data (ch{i})', alpha=0.5)
            ax.scatter(current, channel, color='black', label=f'Raw Data (ch{i})')
            for point in points:
                print(f"GRAD - Current: {current[point]}, Power: {channel[point]} mW")
                ax.axvline(x=current[point], color='red', linestyle='--', label='Threshold Current')
            for point in epoints:
                print(f"ELBOW - Current: {current[point]}, Power: {channel[point]} mW")
                ax.axvline(x=current[point], color='blue', linestyle='dotted', label='Threshold Current')
    plt.show()

if __name__ == '__main__':
    main()
