import os
import re
import csv
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import numpy as np
from matplotlib import cm
import scipy.io
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# --- User: set CSV path here (can include trailing space) ---
csv_path = r"C:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\RCA\RCA-GCLossMonitoring.csv"

# resolve folder containing the CSV (used for output)
folder = os.path.dirname(csv_path) if csv_path else os.getcwd()



# Read CSV and show preview
df = pd.read_csv(csv_path)
print("Columns found:", list(df.columns))
print("Preview (first 5 rows):")
print(df.head().to_string(index=False))

# Flexible column mapping: match common variants to required names
req_map = {
    'x (um)': ['x (um)', 'x_um', 'x', 'x (um)', 'xum', 'x_um', 'position_x', 'pos_x'],
    'y (um)': ['y (um)', 'y_um', 'y', 'y (um)', 'yum', 'y_um', 'position_y', 'pos_y'],
    'Power (dBm)': ['power (dbm)', 'power (dBm)', 'power_dbm', 'power', 'pwr_dbm', 'power(dbm)']
}

def normalize(name):
    return re.sub(r'[^0-9a-z]', '', str(name).lower())

col_norm = {normalize(c): c for c in df.columns}
mapped = {}
for target, variants in req_map.items():
    found_col = None
    for v in variants:
        nv = normalize(v)
        if nv in col_norm:
            found_col = col_norm[nv]; break
    if found_col is None:
        # try loose matching by substring
        for k, orig in col_norm.items():
            if any(sub in k for sub in [normalize(target).replace('power',''), normalize(target).replace(' (um)','')]):
                found_col = orig
                break
    if found_col:
        mapped[target] = found_col

missing = [t for t in req_map.keys() if t not in mapped]
if missing:
    print("CSV columns do not match exactly. Missing mappings for:", missing)
    print("Attempted mappings found:", mapped)
    raise ValueError(f"CSV file must contain or map to columns: {list(req_map.keys())}")

# Rename columns to canonical names
df = df.rename(columns={mapped['x (um)']: 'x (um)', mapped['y (um)']: 'y (um)', mapped['Power (dBm)']: 'Power (dBm)'})
print("Columns after mapping:", list(df.columns))

# Ignore sentinel power values (if present)
df = df[~(df['Power (dBm)'] == -90)]

if df.empty:
    raise ValueError("No valid data in CSV after filtering.")

# --- Fixed-area heatmap + darker colors (no bright yellows) ---
FIXED_RANGE = 33900   # um, map extent [-FIXED_RANGE, FIXED_RANGE]
STEP = 500            # <-- smaller bin size -> smaller plotted squares (was 1000)
CMAP_TOP_FRACTION = 0.90  # keep lower 90% of inferno to remove brightest yellows

# build fixed bin edges (ensures full square area is always present)
x_bins = np.arange(-FIXED_RANGE, FIXED_RANGE + STEP, STEP)
y_bins = np.arange(-FIXED_RANGE, FIXED_RANGE + STEP, STEP)

# compute weighted histogram and counts (fixed grid)
heatmap, xedges, yedges = np.histogram2d(
    df['x (um)'], df['y (um)'], bins=[x_bins, y_bins], weights=df['Power (dBm)']
)
counts, _, _ = np.histogram2d(
    df['x (um)'], df['y (um)'], bins=[x_bins, y_bins]
)

# average power (NaN where no samples)
avg_power = np.divide(heatmap, counts, out=np.full_like(heatmap, np.nan), where=counts!=0)

# compute robust vmin/vmax
valid = avg_power[~np.isnan(avg_power)]
if valid.size == 0:
    vmin, vmax = 0.0, 1.0
else:
    vmin = float(np.nanpercentile(valid, 5))
    vmax = float(np.nanpercentile(valid, 95))

# create a truncated inferno colormap to remove the bright yellow tip
base_cmap = plt.get_cmap('inferno')
colors = base_cmap(np.linspace(0.0, CMAP_TOP_FRACTION, 256))
trunc_inferno = LinearSegmentedColormap.from_list('inferno_trunc', colors)
trunc_inferno.set_bad((1.0, 1.0, 1.0, 0.0))

plt.figure(figsize=(8, 8), facecolor='none')
ax = plt.gca()
ax.set_facecolor('none')

im = ax.imshow(
    avg_power.T,
    origin='lower',
    extent=[-FIXED_RANGE, FIXED_RANGE, -FIXED_RANGE, FIXED_RANGE],
    cmap=trunc_inferno,
    vmin=vmin,
    vmax=vmax,
    interpolation='nearest',
    aspect='equal'
)

# OPTIONAL: overlay raw measurement points as small dots (use s to control dot size)
# set s to 1-4 for very small dots; alpha helps visibility without hiding heatmap
plt.scatter(
    df['x (um)'], df['y (um)'],
    c=df['Power (dBm)'],
    cmap=trunc_inferno,
    vmin=vmin, vmax=vmax,
    s=1, alpha=0.8, linewidths=0
)

plt.xlabel('x (um)')
plt.ylabel('y (um)')
plt.title(' Loss(dBm)')
cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
cbar.set_label('Power (dBm)')

# enforce fixed axis limits so full defined squares appear
plt.xlim(-FIXED_RANGE, FIXED_RANGE)
plt.ylim(-FIXED_RANGE, FIXED_RANGE)

# save PNG next to the selected CSV (use cleaned filename without trailing spaces)
clean_name = os.path.basename(csv_path).strip()
out_dir = os.path.dirname(csv_path)
out_png = os.path.join(out_dir, os.path.splitext(clean_name)[0] + '_heatmap.png')
# save PNG with transparent background
plt.savefig(out_png, dpi=300, bbox_inches='tight', transparent=True)
plt.close()
print(f"Heatmap PNG saved to '{out_png}'")