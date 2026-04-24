# run_this_debug.py
import numpy as np
import scipy.io
from pathlib import Path

mat_path = r"C:\Users\jsheri1\Desktop\20250403_Shuksan_ANT_Light2025_WaferscaleMeasurements\20251015_SiEPICfab_Shuksan_24_02_ELEC413_RemeasurementDelayTest\LIV\2025_10_15_18_51_03_LIV_1550nm_ChipD28_L3\2025_10_15_18_51_03_LIV_1550nm_ChipD28_L3.mat"   # <-- set this to one of the files that differs
m = scipy.io.loadmat(mat_path)

def info(key):
    v = m.get(key)
    if v is None:
        print(f"{key}: MISSING")
        return None
    a = np.asarray(v).flatten().astype(float)
    print(f"{key}: len={a.size}, min={np.nanmin(a):.6g}, max={np.nanmax(a):.6g}")
    print("  sample:", a[:8])
    return a

ch0 = info('channel_0')
ch0_log = info('channel_0_log')
ch2 = info('channel_1')
ch2_log = info('channel_1_log')

# Compare stored log to computed dBm (if raw present)
def mW_to_dBm(x):
    x = np.asarray(x, dtype=float)
    out = np.full_like(x, np.nan)
    mask = (x > 0) & np.isfinite(x)
    out[mask] = 10.0 * np.log10(x[mask])
    return out

if ch0 is not None and ch0_log is not None:
    computed = mW_to_dBm(ch0)
    # print stats where both finite
    mask = np.isfinite(ch0_log) & np.isfinite(computed)
    if mask.any():
        diff = ch0_log[mask] - computed[mask]
        print(f"channel_0_log - 10*log10(channel_0) : min={diff.min():.6g}, max={diff.max():.6g}, mean={diff.mean():.6g}")
    else:
        print("No overlapping finite points to compare for channel_0.")

if ch2 is not None and ch2_log is not None:
    computed = mW_to_dBm(ch2)
    mask = np.isfinite(ch2_log) & np.isfinite(computed)
    if mask.any():
        diff = ch2_log[mask] - computed[mask]
        print(f"channel_1_log - 10*log10(channel_1) : min={diff.min():.6g}, max={diff.max():.6g}, mean={diff.mean():.6g}")
    else:
        print("No overlapping finite points to compare for channel_1.")