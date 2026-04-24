#!/usr/bin/env python3"""================================================================================Script: AllQ_fsr.pyAuthor: sheri and co-pilotDate: 2025-10-28PURPOSE:--------This script creates a dual y-axis comparison plot of laser performance metricsacross multiple chip IDs. It analyzes Q-factor and FSR (Free Spectral Range)measurements from both benchtop and on-chip laser configurations.WORKFLOW:---------1. DIRECTORY SELECTION:   - Prompts user to select a parent directory containing chip subfolders   - Each subfolder represents a unique chip ID (subfolder name = chip ID)2. DATA EXTRACTION:   - Searches each subfolder for .mat files (saved by Benchtop_vs_OnChip script)   - Extracts 8 key metrics per chip:     * benchtop_avg_Q      (average Q-factor from benchtop measurement)     * benchtop_std_Q      (standard deviation of benchtop Q)     * benchtop_avg_FSR    (average FSR from benchtop, in pm)     * benchtop_std_FSR    (standard deviation of benchtop FSR)     * onchip_avg_Q        (average Q-factor from on-chip measurement)     * onchip_std_Q        (standard deviation of on-chip Q)     * onchip_avg_FSR      (average FSR from on-chip, in pm)     * onchip_std_FSR      (standard deviation of on-chip FSR)3. VISUALIZATION:   - Creates a dual y-axis plot:     LEFT Y-AXIS:  FSR values with error bars (benchtop vs on-chip)     RIGHT Y-AXIS: Average Q values with error bars (benchtop vs on-chip)     X-AXIS:       Chip IDs (subfolder names)      - Uses different markers for clarity:     * Circle (o):    FSR benchtop     * Square (s):    FSR on-chip     * Triangle up (^):   Q benchtop     * Triangle down (v): Q on-chip4. ERROR HANDLING:   - Skips subfolders without .mat files   - Skips .mat files that fail to load   - Skips chips missing required variables   - Uses np.nan for missing data pointsOUTPUT:-------Interactive matplotlib plot showing comparative performance across all chips.REQUIREMENTS:-------------- Parent directory structure:  Parent_Folder/  ├── ChipID_1/  │   └── results.mat (containing benchtop_avg_Q, onchip_avg_Q, etc.)  ├── ChipID_2/  │   └── results.mat  └── ...- Each .mat file must contain variables saved by Benchtop_vs_OnChip_Resonance_Analysis.py================================================================================"""import osimport sysfrom pathlib import Pathimport numpy as npimport scipy.ioimport matplotlib.pyplot as pltimport tkinter as tkfrom tkinter import filedialog# =============================================================================# HELPER FUNCTIONS# =============================================================================def ask_directory():    """    Prompt user to select directory using GUI file dialog.    Falls back to text input if GUI fails.        Returns:    --------    str : Path to selected directory    """    try:        root = tk.Tk()        root.withdraw()        d = filedialog.askdirectory(            title="Select parent directory containing chip subfolders"        )        root.destroy()        if d:            return d    except Exception:        pass    # Fallback to command-line input    return input("Enter parent directory path containing chip subfolders: ").strip()def squeeze_val(v):    """    Convert MATLAB arrays to Python scalars/arrays.    Handles nested arrays and single-element arrays.        Parameters:    -----------    v : any        Value from scipy.io.loadmat (typically numpy array)        Returns:    --------    float or numpy.ndarray : Squeezed value    """    v = np.array(v)    v = np.squeeze(v)  # Remove single-dimensional entries    # Convert 0-D arrays (scalars) to float    if v.shape == ():        return float(v)    return vdef extract_values_from_mat(mat):    """    Extract benchtop and on-chip Q and FSR values from .mat file.        Searches for EXPLICIT variable names:    - benchtop_avg_Q, benchtop_std_Q, benchtop_avg_FSR, benchtop_std_FSR    - onchip_avg_Q, onchip_std_Q, onchip_avg_FSR, onchip_std_FSR        Parameters:    -----------    mat : dict        Dictionary returned by scipy.io.loadmat()        Returns:    --------    dict or None:        Dictionary with keys:        - 'FSR_bench', 'FSR_bench_dev', 'FSR_onchip', 'FSR_onchip_dev'        - 'Q_bench', 'Q_bench_dev', 'Q_onchip', 'Q_onchip_dev'        Returns None if required variables not found.    """    out = {}        # EXPLICIT SEARCH for benchtop variables    out['FSR_bench'] = mat.get('benchtop_avg_FSR')    out['FSR_bench_dev'] = mat.get('benchtop_std_FSR')    out['Q_bench'] = mat.get('benchtop_avg_Q')    out['Q_bench_dev'] = mat.get('benchtop_std_Q')        # EXPLICIT SEARCH for on-chip variables    out['FSR_onchip'] = mat.get('onchip_avg_FSR')    out['FSR_onchip_dev'] = mat.get('onchip_std_FSR')    out['Q_onchip'] = mat.get('onchip_avg_Q')    out['Q_onchip_dev'] = mat.get('onchip_std_Q')        # Convert all values to scalars using squeeze_val    for k, v in list(out.items()):        if v is not None:            try:                out[k] = squeeze_val(v)            except Exception as e:                print(f"Warning: Could not convert {k}: {e}")                out[k] = None        # Check if minimum required data is present    required_keys = ['FSR_bench', 'FSR_onchip', 'Q_bench', 'Q_onchip']    if all(out.get(k) is None for k in required_keys):        return None        # Replace None with np.nan for missing optional values (std deviations)    for k in ['FSR_bench_dev', 'FSR_onchip_dev', 'Q_bench_dev', 'Q_onchip_dev']:        if out.get(k) is None:            out[k] = 0.0  # Zero error bar if std not available        return outdef find_mat_file_in_folder(folder):    """    Find the most recent .mat file in a folder.        Parameters:    -----------    folder : Path        Directory to search        Returns:    --------    Path or None : Path to .mat file, or None if not found    """    mats = sorted(Path(folder).glob('*.mat'))    if not mats:        return None    # Return most recent file (last in sorted list)    return mats[-1]# =============================================================================# MAIN EXECUTION# =============================================================================def main():    """    Main function to:    1. Prompt for parent directory    2. Loop through chip subfolders    3. Extract Q and FSR data from .mat files    4. Generate dual y-axis comparison plot    """        # Step 1: Get parent directory from user    parent = ask_directory()    if not parent:        print("No directory provided. Exiting.")        return    parent = Path(parent)    if not parent.is_dir():        print("Provided path is not a directory. Exiting.")        return    print(f"\nScanning directory: {parent}")    print("=" * 80)        # Initialize data storage lists    chip_names = []    fsr_bench = []    fsr_bench_dev = []    fsr_on = []    fsr_on_dev = []    q_bench = []    q_bench_dev = []    q_on = []    q_on_dev = []    # Step 2: Loop through all subfolders (each = one chip)    for sub in sorted(parent.iterdir()):        if not sub.is_dir():            continue                # Find .mat file in this chip's folder        matpath = find_mat_file_in_folder(sub)        if matpath is None:            print(f"⚠ Skipping {sub.name}: no .mat file found")            continue                # Try to load .mat file        try:            mat = scipy.io.loadmat(str(matpath))        except Exception as e:            print(f"⚠ Skipping {sub.name}: failed to load {matpath.name} ({e})")            continue        # Extract Q and FSR values        vals = extract_values_from_mat(mat)        if vals is None:            print(f"⚠ Skipping {sub.name}: required variables not found in {matpath.name}")            print(f"  Available keys: {', '.join([k for k in mat.keys() if not k.startswith('__')])}")            continue        # Store extracted values        chip_names.append(sub.name)        fsr_bench.append(vals.get('FSR_bench', np.nan))        fsr_bench_dev.append(vals.get('FSR_bench_dev', 0.0))        fsr_on.append(vals.get('FSR_onchip', np.nan))        fsr_on_dev.append(vals.get('FSR_onchip_dev', 0.0))        q_bench.append(vals.get('Q_bench', np.nan))        q_bench_dev.append(vals.get('Q_bench_dev', 0.0))        q_on.append(vals.get('Q_onchip', np.nan))        q_on_dev.append(vals.get('Q_onchip_dev', 0.0))                print(f"✓ Loaded {sub.name}: Q_bench={vals.get('Q_bench', 'N/A'):.0f}, "              f"Q_onchip={vals.get('Q_onchip', 'N/A'):.0f}, "              f"FSR_bench={vals.get('FSR_bench', 'N/A'):.1f}pm, "              f"FSR_onchip={vals.get('FSR_onchip', 'N/A'):.1f}pm")    # Check if any valid data was found    if not chip_names:        print("\n❌ No valid chip data found. Exiting.")        return    print(f"\n✓ Successfully loaded {len(chip_names)} chips")    print("=" * 80)        # Step 3: Create dual y-axis plot    x = np.arange(len(chip_names))    width = 0.2  # Spacing between markers        fig, ax_left = plt.subplots(figsize=(max(10, len(chip_names)*0.8), 7))    ax_right = ax_left.twinx()    # Plot FSR on LEFT y-axis    eb1 = ax_left.errorbar(x - width*1.5, fsr_bench, yerr=fsr_bench_dev,                            fmt='o', color='#1f77b4', markersize=8, capsize=5,                           label='FSR (benchtop)', linewidth=2)    eb2 = ax_left.errorbar(x - width*0.5, fsr_on, yerr=fsr_on_dev,                            fmt='s', color='#ff7f0e', markersize=8, capsize=5,                           label='FSR (on-chip)', linewidth=2)    # Plot Q on RIGHT y-axis    eb3 = ax_right.errorbar(x + width*0.5, q_bench, yerr=q_bench_dev,                            fmt='^', color='#2ca02c', markersize=10, capsize=5,                           label='avgQ (benchtop)', linewidth=2)    eb4 = ax_right.errorbar(x + width*1.5, q_on, yerr=q_on_dev,                            fmt='v', color='#d62728', markersize=10, capsize=5,                           label='avgQ (on-chip)', linewidth=2)    # Configure axes    ax_left.set_xlabel('Chip ID', fontsize=14, fontweight='bold')    ax_left.set_ylabel('FSR (pm)', fontsize=14, fontweight='bold', color='#1f77b4')    ax_right.set_ylabel('Average Q-Factor', fontsize=14, fontweight='bold', color='#2ca02c')        ax_left.tick_params(axis='y', labelcolor='#1f77b4', labelsize=12)    ax_right.tick_params(axis='y', labelcolor='#2ca02c', labelsize=12)    ax_left.set_xticks(x)    ax_left.set_xticklabels(chip_names, rotation=45, ha='right', fontsize=11)    ax_left.grid(True, alpha=0.3, linestyle='--')    # Combined legend    lines = [eb1, eb2, eb3, eb4]    labels = ['FSR (benchtop)', 'FSR (on-chip)', 'avgQ (benchtop)', 'avgQ (on-chip)']    ax_left.legend(lines, labels, loc='upper left', fontsize=11, framealpha=0.9)    plt.suptitle('Laser Performance Comparison: FSR and Q-Factor\n(Benchtop vs On-Chip)',                  fontsize=16, fontweight='bold', y=0.98)    plt.tight_layout()    plt.subplots_adjust(top=0.93)        # Save plot    output_file = parent / "Chip_Comparison_FSR_Q.png"    plt.savefig(output_file, dpi=300, bbox_inches='tight')    print(f"\n✓ Plot saved to: {output_file}")        # =============================================================================    # CREATE HISTOGRAM PLOTS - Q-FACTORS AND FSR COMPARISON    # =============================================================================    print("\n--- Creating Histogram Comparison Plots ---")    
    # Convert lists to numpy arrays for easier handling
    fsr_bench_arr = np.array(fsr_bench)
    fsr_bench_dev_arr = np.array(fsr_bench_dev)
    fsr_on_arr = np.array(fsr_on)
    fsr_on_dev_arr = np.array(fsr_on_dev)
    q_bench_arr = np.array(q_bench)
    q_bench_dev_arr = np.array(q_bench_dev)
    q_on_arr = np.array(q_on)
    q_on_dev_arr = np.array(q_on_dev)
    
    # Inferno colormap colors
    import matplotlib.cm as cm
    inferno_cmap = cm.get_cmap('inferno')
    benchtop_color = inferno_cmap(0.2)  # Dark purple/blue from inferno
    onchip_color = inferno_cmap(0.8)    # Bright yellow/orange from inferno
    
    # Create figure with subplots for histograms
    fig_hist, (ax_q, ax_fsr) = plt.subplots(1, 2, figsize=(16, 7))
    
    # --- Q-Factor Histogram ---
    x_pos = np.arange(len(chip_names))
    width = 0.35  # Width of bars
    
    # Plot Q-factor bars (separate bar() and errorbar() calls)
    bars1 = ax_q.bar(x_pos - width/2, q_bench_arr, width, 
                     color=benchtop_color, alpha=0.8, 
                     label='Benchtop Laser',
                     edgecolor='black', linewidth=1.5)
    
    # Add error bars separately
    ax_q.errorbar(x_pos - width/2, q_bench_arr, yerr=q_bench_dev_arr, 
                  fmt='none', capsize=8, capthick=2, color='black')
    
    bars2 = ax_q.bar(x_pos + width/2, q_on_arr, width,
                     color=onchip_color, alpha=0.8,
                     label='On-Chip Laser',
                     edgecolor='black', linewidth=1.5)
    
    # Add error bars separately
    ax_q.errorbar(x_pos + width/2, q_on_arr, yerr=q_on_dev_arr, 
                  fmt='none', capsize=8, capthick=2, color='black')
    
    # Customize Q-factor plot
    ax_q.set_xlabel('Chip ID', fontsize=14, fontweight='bold')
    ax_q.set_ylabel('Average Q-Factor', fontsize=14, fontweight='bold')
    ax_q.set_title('Q-Factor Comparison by Chip', fontsize=16, fontweight='bold', pad=20)
    ax_q.set_xticks(x_pos)
    ax_q.set_xticklabels(chip_names, rotation=45, ha='right', fontsize=11)
    ax_q.legend(fontsize=12, loc='upper right')
    ax_q.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax_q.tick_params(axis='both', which='major', labelsize=12)
    
    # Add value labels on Q-factor bars
    for i, (bar, value, std) in enumerate(zip(bars1, q_bench_arr, q_bench_dev_arr)):
        if not np.isnan(value) and value > 0:
            height = bar.get_height()
            ax_q.text(bar.get_x() + bar.get_width()/2., height + std + height*0.02,
                     f'{value:.0f}±{std:.0f}',
                     ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    for i, (bar, value, std) in enumerate(zip(bars2, q_on_arr, q_on_dev_arr)):
        if not np.isnan(value) and value > 0:
            height = bar.get_height()
            ax_q.text(bar.get_x() + bar.get_width()/2., height + std + height*0.02,
                     f'{value:.0f}±{std:.0f}',
                     ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # --- FSR Histogram ---
    # Plot FSR bars (separate bar() and errorbar() calls)
    bars3 = ax_fsr.bar(x_pos - width/2, fsr_bench_arr, width,
                       color=benchtop_color, alpha=0.8,
                       label='Benchtop Laser',
                       edgecolor='black', linewidth=1.5)
    
    # Add error bars separately
    ax_fsr.errorbar(x_pos - width/2, fsr_bench_arr, yerr=fsr_bench_dev_arr, 
                    fmt='none', capsize=8, capthick=2, color='black')
    
    bars4 = ax_fsr.bar(x_pos + width/2, fsr_on_arr, width,
                       color=onchip_color, alpha=0.8,
                       label='On-Chip Laser',
                       edgecolor='black', linewidth=1.5)
    
    # Add error bars separately
    ax_fsr.errorbar(x_pos + width/2, fsr_on_arr, yerr=fsr_on_dev_arr, 
                    fmt='none', capsize=8, capthick=2, color='black')
    
    # Customize FSR plot
    ax_fsr.set_xlabel('Chip ID', fontsize=14, fontweight='bold')
    ax_fsr.set_ylabel('Average FSR (pm)', fontsize=14, fontweight='bold')
    ax_fsr.set_title('FSR Comparison by Chip', fontsize=16, fontweight='bold', pad=20)
    ax_fsr.set_xticks(x_pos)
    ax_fsr.set_xticklabels(chip_names, rotation=45, ha='right', fontsize=11)
    ax_fsr.legend(fontsize=12, loc='upper right')
    ax_fsr.grid(True, alpha=0.3,