# Test script: create a dummy .mat for a given CSV and run multi_LIV using that CSV path
import sys
from pathlib import Path
import numpy as np
from scipy.io import savemat

# Use non-interactive backend before matplotlib is imported by multi_LIV
import matplotlib
matplotlib.use('Agg')

if len(sys.argv) > 1:
    csv_path = Path(sys.argv[1])
else:
    # Default to the attached test CSV in the repo
    csv_path = Path(r"c:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration\2025_10_30_23_50_59_cycle01_run01_LIV\2025_10_30_23_50_59_C01_R01_LIV_1330nm_ChipD30_R4\2025_10_30_23_50_59_C01_R01_LIV_1330nm_ChipD30_R4.csv")

if not csv_path.exists():
    print('CSV not found at', csv_path)
    sys.exit(2)

matfile = csv_path.with_suffix('.mat')
print('Creating dummy mat file at', matfile)

# Minimal variables expected by multi_LIV.read_mat
data = {
    'ch0_threshold': np.array(1.0),
    'ch1_threshold': np.array(2.0),
    'ch2_threshold': np.array(3.0),
    'ch3_threshold': np.array(4.0),
    'channel_0': np.array([0.0, 1.0]),
    'channel_0_log': np.array([0.0, 1.0]),
    'channel_1': np.array([0.0, 1.0]),
    'channel_1_log': np.array([0.0, 1.0]),
    'channel_2': np.array([0.0, 1.0]),
    'channel_2_log': np.array([0.0, 1.0]),
    'channel_3': np.array([0.0, 1.0]),
    'channel_3_log': np.array([0.0, 1.0]),
    'current': np.array([0.0, 1.0]),
    'voltage': np.array([0.0, 1.0]),
    'temperature': np.array([25.0, 25.0]),
    'peak_power': np.array(0.5),
    'peak_power_I': np.array(1.0),
    'peak_power_V': np.array(2.0)
}

savemat(str(matfile), data)
print('Wrote dummy .mat')

# Now run the multi_LIV constructor pointing to this CSV
# Ensure the repository root is on sys.path so local modules can be imported
repo_root = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(repo_root))
print('Repo root:', repo_root)

from multi_LIV import multi_LIV

m = multi_LIV(str(repo_root), selected_files=[str(csv_path)], overwrite_existing=False)
print('multi_LIV run completed; selected files:', getattr(m, 'selected_files', None))
