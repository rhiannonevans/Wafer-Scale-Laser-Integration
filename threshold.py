
import pandas as pd
import extract as ex
import numpy as np
import matplotlib.pyplot as plt

#Call only if power > -20 dBm
def detect_trend(data):
    df = pd.DataFrame(data)
    pois = []
    # Calculate moving averages once for efficiency
    shortMA = df.rolling(window=2).mean()
    longMA = df.rolling(window=5).mean()  # Use a longer window for trend
    # Detect significant positive crossover: shortMA crosses above longMA
    cross = (shortMA[0] > longMA[0]) & (shortMA[0].shift(1) <= longMA[0].shift(1))
    # Only consider points where power > -40 dBm
    for idx in cross[cross].index:
        if -10 > np.log(df[0][idx]) > -40:
            pois.append(idx)
    return pois

def main():
    print("Starting trend detection...")
    import scipy.io

    path = "C:/Users/OWNER/Desktop/smaller_LIV/2025_03_16_16_15_12_loopTEST_1310nm_ChipA1_R0/2025_03_16_16_15_12_loopTEST_1310nm_ChipA1_R0.mat"
    #path = "C:/Users/OWNER/Desktop/smaller_LIV/2025_03_16_16_56_11_hangzouTEST_1310nm_ChipA1_R1/2025_03_16_16_56_11_hangzouTEST_1310nm_ChipA1_R1.mat"
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
    points0 = detect_trend(channel_0)
    print("Channel 1 Data:")
    points1 = detect_trend(channel_1)
    print(f"Thresholds (ch0) detected at {len(points0)} points:")
    fig0, ax0 = plt.subplots()
    ax0.scatter(current, channel_0, color='red', label='Threshold Point (ch0)')
    for point in points0:
        print(f"Current: {current[point]}, Power: {channel_0[point]} mW")
        ax0.axvline(x=current[point], color='red', linestyle='--', label='Threshold Current')

    fig1, ax1 = plt.subplots()
    ax1.scatter(current, channel_1, color='red', label='Threshold Point (ch0)')
    print(f"Thresholds (ch1) detected at {len(points1)} points:")
    for point in points1:
        print(f"Current: {current[point]}, Power: {channel_1[point]} mW")
        ax1.axvline(x=current[point], color='red', linestyle='--', label='Threshold Current')
    plt.show()

if __name__ == '__main__':
    main()
