from scipy.signal import savgol_filter
import numpy as np

def find_elbow_smoothed(data, window=7, polyorder=2):
    """
    Like find_elbow, but first smooths the data via Savitzky–Golay.
    window must be odd and >= 3; if data is shorter, it auto‐adjusts.
    """
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
    
    # Then exactly the same logic as before, but on 'smooth'
    max_delta = -np.inf
    elbow_idx = None
    for i in range(N - 1):
        delta = smooth[i+1] - smooth[i]
        if delta > max_delta:
            max_delta = delta
            elbow_idx = i + 1

    return elbow_idx

# Example with a bit of noise:
if __name__ == "__main__":
    np.random.seed(0)
    flat = np.random.normal(loc=0.0, scale=0.02, size=50)
    ramp = np.linspace(0, 5, 50) + np.random.normal(scale=0.1, size=50)
    data = np.concatenate([flat, ramp])

    idx = find_elbow_smoothed(data, window=9, polyorder=2)
    print("Smoothed elbow at index:", idx)