
import pandas as pd
import extract as ex
import numpy as np
import matplotlib.pyplot as plt

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

def detect_trend_gradient(data, current, slope_threshold=0.0001, window=3):
    data = np.array(data)
    current = np.array(current)
    
    # Smooth the data slightly
    smoothed = np.convolve(data, np.ones(window)/window, mode='same')
    
    # Compute the gradient (dy/dx)
    dy = np.gradient(smoothed)
    dx = np.gradient(current)
    gradient = dy / dx
    pois = []
    
    # Find first point where slope exceeds threshold and stays high
    for i in range(1, len(gradient)):
        if gradient[i] > slope_threshold and all(gradient[i:i+3] > slope_threshold):
            pois.append(i)
    
    return pois


def detect_trend_elbow(data, current,slope_threshold = 0.00001, window=30):
    data = np.array(data)
    current = np.array(current)
    
    # Smooth data
    #smoothed = np.convolve(data, np.ones(window)/window, mode='same')
    
    # Compute first and second derivative
    grad1 = np.gradient(data, current)
    grad2 = np.gradient(grad1, current)

    pois = []
    for i in range(1, len(grad2)):
        if grad2[i] > slope_threshold and all(grad2[i:i+3] > slope_threshold):
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
    paths = [path0, path1, path2, path3]
    for path in paths:
        print(f"Processing file: {path}")
        mat_data = scipy.io.loadmat(path)
        # Extract specific variables from the MATLAB workspace and save as numpy arrays
        channel_0 = np.squeeze(mat_data.get("channel_0", np.array([])))
        channel_1 = np.squeeze(mat_data.get("channel_1", np.array([])))

        current = np.squeeze(mat_data.get("current", np.array([])))
        print("channel_0 numpy array:", channel_0)
        print("channel_1 numpy array:", channel_1)
        # Optionally, create a DataFrame if needed for further processing

        #print(channel_0)
        print("Channel 0 Data:")
        points0 = detect_trend_gradient(channel_0, current)
        print("Channel 1 Data:")
        points1 = detect_trend_gradient(channel_1, current)
        epoints1 = detect_trend_elbow(channel_1, current)
        epoints0 = detect_trend_elbow(channel_0, current)
        print(f"Thresholds (ch0) detected at {len(points0)} points:")
        fig0, ax0 = plt.subplots()
        ax0.scatter(current, channel_0, color='red', label='Threshold Point (ch0)')
        for point in points0:
            print(f"GRAD - Current: {current[point]}, Power: {channel_0[point]} mW")
            ax0.axvline(x=current[point], color='red', linestyle='--', label='Threshold Current')
        for point in epoints0:
            print(f"ELBOW - Current: {current[point]}, Power: {channel_0[point]} mW")
            ax0.axvline(x=current[point], color='blue', linestyle='dotted', label='Threshold Current')
        fig1, ax1 = plt.subplots()
        ax1.scatter(current, channel_1, color='red', label='Threshold Point (ch0)')
        print(f"Thresholds (ch1) detected at {len(points1)} points:")
        for point in points1:
            print(f"Current: {current[point]}, Power: {channel_1[point]} mW")
            ax1.axvline(x=current[point], color='red', linestyle='--', label='Threshold Current')
        for point in epoints1:
            print(f"ELBOW - Current: {current[point]}, Power: {channel_1[point]} mW")
            ax1.axvline(x=current[point], color='blue', linestyle='dotted', label='Threshold Current')
        
    plt.show()

if __name__ == '__main__':
    main()
