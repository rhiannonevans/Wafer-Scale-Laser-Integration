import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd
from pathlib import Path
import re
import ast
import scipy
import glob

from LIVclass import LIVclass

""" Class for processing multiple LIV (Power, current, voltage) files. Processes selected 'liv' files, creates the following comparison plots:
         - LI, VI, and TI curves for all devices (channel 1 - although this is changeable)
         - Threshold currents for each IDtag
         - Power at specified currents (default: 25mA and 50mA)

    CHANNEL NAMING CONVENTION:
    --------------------------
    Code uses zero-indexed naming (programmer convention):
        channel_0 / ch0_threshold = Physical Channel 1
        channel_1 / ch1_threshold = Physical Channel 2
        channel_2 / ch2_threshold = Physical Channel 3
        channel_3 / ch3_threshold = Physical Channel 4
"""

class multi_LIV:
    def plot_LI_VI_overlay_by_wavelength(self, interactive_li=False):
        """
        Overlay LI (Light-Current) and VI (Voltage-Current) plots grouped by wavelength:
        - 1310nm: inferno
        - 1330nm: viridis
        - 1550nm: cividis
        Uses same grouping as beeswarm plots.
        """
        import re
        # Use the same inferno-based color mapping as beeswarm
        cmap = plt.get_cmap('inferno')
        wavelength_order = ['1310nm', '1330nm', '1550nm']
        # Prepare data
        idtags = list(self.loss_data.keys())
        idtag_to_path = {}
        for fp in self.selected_files:
            fname = fp.name if hasattr(fp, 'name') else str(fp)
            idtag = self.get_IDtag(fname)
            idtag_to_path[idtag] = str(fp)
        # Group by wavelength
        group_dict = {wl: [] for wl in wavelength_order}
        for idtag in idtags:
            df = self.loss_data[idtag]
            file_path = idtag_to_path.get(idtag, idtag)
            wl = None
            for w in wavelength_order:
                if re.search(w[:4], file_path):
                    wl = w
                    break
            if wl is None:
                continue
            group_dict[wl].append((idtag, df))
        # build fixed color map for overlays (consistent with beeswarm)
        inferno_colors = cmap(np.linspace(0.2, 0.8, len(wavelength_order)))
        color_map = dict(zip(wavelength_order, inferno_colors))
        # LI overlay plot
        plt.figure(figsize=(10, 7))
        for wl in wavelength_order:
            group = group_dict[wl]
            color = color_map.get(wl, 'gray')
            for idtag, df in group:
                # Use channel_2 for 1310/1330, channel_3 for 1550 (consistency with beeswarm)
                if wl in ('1310nm', '1330nm') and 'channel_2' in df:
                    y = np.array(df['channel_2'])
                elif wl == '1550nm' and 'channel_3' in df:
                    y = np.array(df['channel_3'])
                else:
                    continue
                # Normalize LI curve by each device's max absolute value
                try:
                    denom = np.nanmax(np.abs(y)) if y.size else 0
                except Exception:
                    denom = 0
                if denom and denom != 0:
                    y_norm = y / denom
                else:
                    y_norm = y
                line, = plt.plot(df['current'], y_norm, label=f'{idtag}', color=color, linewidth=2, alpha=0.8)
                # Make lines pickable if interactive mode is enabled
                if interactive_li:
                    line.set_picker(5)  # 5 points tolerance
                    # store idtag attribute (in case we need it)
                    setattr(line, 'idtag', idtag)
        plt.xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        plt.ylabel('Normalized Power', fontsize=self.FONT_AXIS_LABEL)
        plt.title('Overlay LI: Power vs Current by Wavelength', fontsize=self.FONT_TITLE)
        plt.grid(True, alpha=0.3)
        plt.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        # Show legend only if user wants legends and total traces is small
        total_traces = sum(len(v) for v in group_dict.values())
        if self.show_legends and total_traces <= 6:
            plt.legend(fontsize=self.FONT_LEGEND, loc='best')
        plt.tight_layout()
        plt.savefig(Path(self.save_dir) / 'Overlay_LI_by_Wavelength.png')
        plt.close()
        # VI overlay plot (plot voltage vs current). No per-id tag legend — match VI_no_legend behaviour
        plt.figure(figsize=(10, 7))
        for wl in wavelength_order:
            group = group_dict[wl]
            color = color_map.get(wl, 'gray')
            for idtag, df in group:
                # Prefer the global 'voltage' field (same as VI_no_legend), fallback to per-channel voltage params
                if 'voltage' in df:
                    yv = np.array(df['voltage'])
                elif wl in ('1310nm', '1330nm') and 'ch2_voltage_param' in df:
                    yv = np.array(df['ch2_voltage_param'])
                elif wl == '1550nm' and 'ch3_voltage_param' in df:
                    yv = np.array(df['ch3_voltage_param'])
                else:
                    continue
                plt.plot(df['current'], yv, color=color, linewidth=1.5, alpha=0.7)
        plt.xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        plt.ylabel('Voltage (V)', fontsize=self.FONT_AXIS_LABEL)
        plt.title('Overlay VI: Voltage vs Current by Wavelength', fontsize=self.FONT_TITLE)
        plt.grid(True, alpha=0.3)
        plt.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        # Do not show legend for VI overlay to match VI_no_legend behaviour
        plt.tight_layout()
        plt.savefig(Path(self.save_dir) / 'Overlay_VI_by_Wavelength.png')
        plt.close()
        print("Overlay LI and VI plots saved: Overlay_LI_by_Wavelength.png, Overlay_VI_by_Wavelength.png")

        # If interactive is requested, launch an interactive figure for LI
        if interactive_li:
            try:
                import matplotlib.widgets as mw
                fig, ax = plt.subplots(figsize=(10, 7))
                lines = []
                for wl in wavelength_order:
                    group = group_dict[wl]
                    color = color_map.get(wl, 'gray')
                    for idtag, df in group:
                        # same channel mapping and normalization as above
                        if wl in ('1310nm', '1330nm') and 'channel_2' in df:
                            y = np.array(df['channel_2'])
                        elif wl == '1550nm' and 'channel_3' in df:
                            y = np.array(df['channel_3'])
                        else:
                            continue
                        try:
                            denom = np.nanmax(np.abs(y)) if y.size else 0
                        except Exception:
                            denom = 0
                        y_norm = y / denom if denom and denom != 0 else y
                        lobj, = ax.plot(df['current'], y_norm, label=f'{idtag}', color=color, linewidth=2, alpha=0.8)
                        lobj.set_picker(5)
                        setattr(lobj, 'idtag', idtag)
                        lines.append(lobj)

                ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
                ax.set_ylabel('Normalized Power', fontsize=self.FONT_AXIS_LABEL)
                ax.set_title('Interactive Overlay LI: Click a line to toggle visibility, Save to write visible lines', fontsize=self.FONT_TITLE)
                ax.grid(True, alpha=0.3)

                # pick event toggles visibility
                def on_pick(event):
                    line = event.artist
                    vis = line.get_visible()
                    line.set_visible(not vis)
                    line.set_alpha(0.8 if not vis else 0.15)
                    fig.canvas.draw()

                fig.canvas.mpl_connect('pick_event', on_pick)

                # Buttons: Reset and Save
                ax_reset = plt.axes([0.75, 0.01, 0.1, 0.05])
                ax_save = plt.axes([0.87, 0.01, 0.1, 0.05])
                btn_reset = mw.Button(ax_reset, 'Reset')
                btn_save = mw.Button(ax_save, 'Save')

                def on_reset(event):
                    for ln in lines:
                        ln.set_visible(True)
                        ln.set_alpha(0.8)
                    fig.canvas.draw()

                def on_save(event):
                    out_fig, out_ax = plt.subplots(figsize=(10, 7))
                    for ln in lines:
                        if ln.get_visible():
                            x, y = ln.get_data()
                            out_ax.plot(x, y, color=ln.get_color(), linewidth=ln.get_linewidth(), alpha=ln.get_alpha())
                    out_ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
                    out_ax.set_ylabel('Normalized Power', fontsize=self.FONT_AXIS_LABEL)
                    out_ax.set_title('Overlay LI (Selected Traces)', fontsize=self.FONT_TITLE)
                    out_ax.grid(True, alpha=0.3)
                    save_path = Path(self.save_dir) / 'Overlay_LI_by_Wavelength_selected.png'
                    out_fig.tight_layout()
                    out_fig.savefig(save_path, dpi=300, bbox_inches='tight')
                    plt.close(out_fig)
                    print(f"Saved interactive LI plot (selected traces) to {save_path}")

                btn_reset.on_clicked(on_reset)
                btn_save.on_clicked(on_save)
                plt.show()
            except Exception as e:
                print(f"Interactive LI plot not available (matplotlib widgets issue): {e}")
    # Font size constants - change these in one place to update all plots
    FONT_AXIS_LABEL = 25
    FONT_AXIS_TICKS = 25
    FONT_LEGEND = 22
    FONT_TITLE = 14
    FONT_ANNOTATION = 9
    
    def __init__(self, parent_path, selected_files=None, overwrite_existing=False, handle_duplicates: str = 'datetime', show_legends: bool = None):
        """Process multiple LIV files.

        Parameters
        ----------
        parent_path : str
            Root directory to search.
        selected_files : list[str] | None
            Optional list of user-selected folder / file stems.
        overwrite_existing : bool
            Recreate intermediate .mat outputs if True.
        handle_duplicates : {'datetime','suffix','overwrite','skip'}
            Strategy for handling multiple files producing same ID tag.
        """
        p = Path(parent_path)
        self.parent_path = parent_path
        self.cmap = plt.get_cmap('inferno')
        
        # Prompt user for legend preference if not specified
        if show_legends is None:
            response = input("\nShow legends on all plots? (y/n, default: y): ").strip().lower()
            self.show_legends = response != 'n'
        else:
            self.show_legends = show_legends
        
        self.handle_duplicates = handle_duplicates.lower()
        allowed_modes = {'datetime','suffix','overwrite','skip'}
        if self.handle_duplicates not in allowed_modes:
            print(f"Unknown handle_duplicates option '{handle_duplicates}', defaulting to 'datetime'.")
            self.handle_duplicates = 'datetime'
        if self.handle_duplicates == 'overwrite':
            print("Info: 'overwrite' mode disabled; using 'datetime' to ensure unique IDs.")
            self.handle_duplicates = 'datetime'

        print("Debug: Selected files (raw):", selected_files)
        # Normalize selected_files: allow a single string/Path or an iterable of strings/Paths
        if isinstance(selected_files, (str, Path)):
            # If user accidentally passed a Python-list-as-string (e.g. "['a','b']") try to parse it
            s = str(selected_files).strip()
            parsed = None
            if (s.startswith('[') or s.startswith('(')):
                try:
                    parsed = ast.literal_eval(s)
                    print("Debug: parsed selected_files string as sequence via ast.literal_eval")
                except Exception:
                    parsed = None

            if parsed is None and ',' in s:
                # Try simple comma split (handles "a, b, c" or "'a','b'")
                parts = [p.strip().strip('\"\'') for p in s.split(',') if p.strip()]
                if len(parts) > 1:
                    parsed = parts
                    print("Debug: split selected_files string on commas into list")

            if parsed is not None:
                selected_files = list(parsed)
            else:
                print("Debug: selected_files was a single string/Path — converting to one-item list")
                selected_files = [selected_files]

        selected_files = self.filter_liv(selected_files) if selected_files else None

        if not selected_files:
            all_files = [fp for fp in p.rglob('*.csv') if fp.is_file()]
            print("Debug: All files found by rglob:", [str(fp) for fp in all_files])
            self.selected_files = [
                fp for fp in all_files
                if 'loss' not in fp.name.lower()
                and 'liv'  in fp.name.lower()
                and 'wlm' not in fp.name.lower()
            ]
        else:
            # If user passed explicit file paths (absolute or relative), prefer those directly
            candidate_paths = [Path(name) for name in selected_files]
            explicit_files = [fp for fp in candidate_paths if fp.is_file()]
            if explicit_files:
                print("Debug: Using explicit selected file paths:", [str(fp) for fp in explicit_files])
                # Apply same name-based filtering as the rglob branch
                self.selected_files = [
                    fp for fp in explicit_files
                    if 'loss' not in fp.name.lower()
                    and 'liv' in fp.name.lower()
                    and 'wlm' not in fp.name.lower()
                ]
            else:
                # Fall back to searching within parent_path for stems matching requested names
                # Wanted may be stems, folder names, or partial names. Match against CSV stem
                # and the CSV's parent directory name so selections of folder names work.
                wanted = {Path(name).stem.lower() for name in selected_files}
                all_files = [fp for fp in p.rglob('*.csv') if fp.is_file()]
                print("Debug: All files found by rglob:", [str(fp) for fp in all_files])
                def matches_wanted(fp):
                    stem = fp.stem.lower()
                    parent = fp.parent.name.lower()
                    pathstr = str(fp).lower()
                    if stem in wanted or parent in wanted:
                        return True
                    # allow partial matching if user provided a shorter identifier
                    for w in wanted:
                        if w and w in pathstr:
                            return True
                    return False

                self.selected_files = [fp for fp in all_files if matches_wanted(fp)]

        print("Debug: Final selected files:", [str(fp) for fp in self.selected_files])
        if not self.selected_files:
            print("No LIV files found!")
            return

        self.save_dir = p / "LIV_Comparison"
        os.makedirs(self.save_dir, exist_ok=True)
        self.overwrite_existing = overwrite_existing

        self.loss_data = {}
        for csv_fp in self.selected_files:
            print(f"→ Processing base file: {csv_fp.name}")
            loss_path = csv_fp.with_name(csv_fp.stem + '.mat')
            
            # Try to process or reprocess if needed
            should_process = self.overwrite_existing or not loss_path.exists()
            
            if should_process:
                try:
                    LIVclass(csv_fp, output_folder=csv_fp.parent)
                except Exception as e:
                    print(f"Error processing {csv_fp}: {e}")
                    continue
            else:
                print(f"Loss data already exists: {loss_path}. Skipping processing.")

            # Try to read the mat file, regenerate if it's invalid
            try:
                df = self.read_mat(loss_path)
            except (KeyError, ValueError) as e:
                print(f"Warning: Existing .mat file is invalid or outdated: {e}")
                print(f"Regenerating .mat file from CSV...")
                try:
                    LIVclass(csv_fp, output_folder=csv_fp.parent)
                    df = self.read_mat(loss_path)
                except Exception as e:
                    print(f"Error regenerating {csv_fp}: {e}")
                    continue
            print(df)
            print(f"Processing file: {csv_fp.name}")
            idtag = self.get_IDtag(csv_fp.name)
            print(f"Extracted ID tag: {idtag}")
            if idtag in self.loss_data:
                print(f"Warning: Duplicate ID tag detected for {idtag} (file: {csv_fp.name}).")
                mode = self.handle_duplicates
                if mode == 'skip':
                    print("  → Skipping this duplicate (handle_duplicates='skip').")
                    continue
                base_stem = Path(csv_fp.name).stem
                datetime_match = re.search(r'(\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2})', base_stem)
                if mode == 'datetime' and datetime_match:
                    core_suffix = datetime_match.group(1)
                elif mode == 'datetime':
                    core_suffix = base_stem
                else:
                    core_suffix = base_stem
                candidate = f"{idtag}__{core_suffix}"
                counter = 2
                while candidate in self.loss_data:
                    candidate = f"{idtag}__{core_suffix}_{counter}"
                    counter += 1
                print(f"  → Renaming duplicate to {candidate} (handle_duplicates='{mode}').")
                idtag = candidate

            self.loss_data[idtag] = df
            print(f"   ✓ loaded loss_data for {idtag}  ({len(df)} rows)")

        plt.close('all')
        # quick sanity check: print columns / first rows to ensure 'voltage' exists
        try:
            self.check_data()
        except Exception:
            pass
        self.compPlots()
        self.plot_thresholds()
        self.plot_thresholds_ch2()  # ch2 = Physical Channel 3 boxplot
        self.plot_power_at_current()
        self.plot_chip_thresholds(channel='ch2')  # ch2 = Physical Channel 3
        self.plot_chip_thresholds(channel='ch3')  # ch3 = Physical Channel 4
        self.plot_threshold_histogram(channel='ch1')  # ch1 = Physical Channel 2
        self.plot_threshold_histogram(channel='ch2')  # ch2 = Physical Channel 3
        self.plot_threshold_histogram(channel='ch3')  # ch3 = Physical Channel 4
        self.plot_normalized_LIV()  # Normalized power curves without legends
        self.plot_channel_analysis_by_wavelength()  # Interactive channel-specific analysis
        self.plot_power_dBm_vs_current()  # Power in dBm vs current for all channels
        self.plot_VI_no_legend()  # Voltage vs current without legends
        self.plot_LIV_voltage_by_wavelength()
        # Figures are saved to disk, not shown interactively


    def read_mat(self, mat_file: Path) -> pd.DataFrame:
        mat = scipy.io.loadmat(mat_file)
        
        # Check if this is a valid LIV file by looking for required keys
        required_keys = ['ch0_threshold', 'ch1_threshold', 'ch2_threshold', 'ch3_threshold', 
                        'current', 'voltage', 'channel_0']
        
        # Get actual keys (excluding MATLAB metadata keys)
        actual_keys = [k for k in mat.keys() if not k.startswith('__')]
        missing_keys = [k for k in required_keys if k not in mat]
        
        if missing_keys:
            raise KeyError(
                f"Invalid LIV .mat file: {mat_file.name}\n"
                f"  Missing keys: {missing_keys}\n"
                f"  Found keys: {actual_keys}\n"
                f"  This file may be from an older version or corrupted."
            )

        # Manually extract each known variable
        # NOTE: ch0 = Physical Channel 1, ch1 = Physical Channel 2, etc. (zero-indexed)
        ch0_threshold = mat['ch0_threshold'].item()  # Physical Channel 1
        ch1_threshold = mat['ch1_threshold'].item()  # Physical Channel 2
        ch2_threshold = mat['ch2_threshold'].item()  # Physical Channel 3
        ch3_threshold = mat['ch3_threshold'].item()  # Physical Channel 4

        # Extract slope efficiency parameters (if they exist)
        ch0_slope_efficiency = mat.get('ch0_slope_efficiency', np.array([[np.nan]])).item()
        ch1_slope_efficiency = mat.get('ch1_slope_efficiency', np.array([[np.nan]])).item()
        ch2_slope_efficiency = mat.get('ch2_slope_efficiency', np.array([[np.nan]])).item()
        ch3_slope_efficiency = mat.get('ch3_slope_efficiency', np.array([[np.nan]])).item()
        
        # Extract voltage parameters (if they exist)
        ch0_voltage_param = mat.get('ch0_voltage_param', np.array([[np.nan]])).item()
        ch1_voltage_param = mat.get('ch1_voltage_param', np.array([[np.nan]])).item()
        ch2_voltage_param = mat.get('ch2_voltage_param', np.array([[np.nan]])).item()
        ch3_voltage_param = mat.get('ch3_voltage_param', np.array([[np.nan]])).item()

        channel_0 = mat['channel_0'].flatten()
        channel_0_log = mat['channel_0_log'].flatten()
        channel_1 = mat['channel_1'].flatten()
        channel_1_log = mat['channel_1_log'].flatten()
        channel_2 = mat['channel_2'].flatten()
        channel_2_log = mat['channel_2_log'].flatten()
        channel_3 = mat['channel_3'].flatten()
        channel_3_log = mat['channel_3_log'].flatten()

        current = mat['current'].flatten()
        voltage = mat['voltage'].flatten()
        temperature = mat['temperature'].flatten()

        peak_power = mat['peak_power'].item()
        peak_power_I = mat['peak_power_I'].item()
        peak_power_V = mat['peak_power_V'].item()

        # Combine into DataFrame (only variables with 1D array shape can go into DataFrame columns)
        df = pd.DataFrame({
            'current': current,
            'voltage': voltage,
            'temperature': temperature,
            'channel_0': channel_0,
            'channel_0_log': channel_0_log,
            'channel_1': channel_1,
            'channel_1_log': channel_1_log,
            'channel_2': channel_2,
            'channel_2_log': channel_2_log,
            'channel_3': channel_3,
            'channel_3_log': channel_3_log,
        })

        # Add scalar values as metadata or new columns (same value repeated)
        df['ch0_threshold'] = ch0_threshold
        df['ch1_threshold'] = ch1_threshold
        df['ch2_threshold'] = ch2_threshold
        df['ch3_threshold'] = ch3_threshold
        df['ch0_slope_efficiency'] = ch0_slope_efficiency
        df['ch1_slope_efficiency'] = ch1_slope_efficiency
        df['ch2_slope_efficiency'] = ch2_slope_efficiency
        df['ch3_slope_efficiency'] = ch3_slope_efficiency
        df['ch0_voltage_param'] = ch0_voltage_param
        df['ch1_voltage_param'] = ch1_voltage_param
        df['ch2_voltage_param'] = ch2_voltage_param
        df['ch3_voltage_param'] = ch3_voltage_param
        df['peak_power'] = peak_power
        df['peak_power_I'] = peak_power_I
        df['peak_power_V'] = peak_power_V
        return df


    def filter_liv(self, selected_files = []):
        # Log the initial list of selected files
        print("Debug: Initial selected files:", selected_files)
        filtered = []
        for entry in selected_files:
            entry_str = str(entry)
            # Expand glob patterns
            if any(ch in entry_str for ch in ('*', '?', '[')):
                matches = glob.glob(entry_str, recursive=True)
                for m in matches:
                    if os.path.isfile(m):
                        filtered.append(Path(m))
                continue

            p = Path(entry)
            # If it's an explicit file, accept it
            if p.is_file():
                filtered.append(p)
                continue

            # If it's a directory, collect CSVs inside
            if p.is_dir():
                for m in p.rglob('*.csv'):
                    filtered.append(m)
                continue

            # Otherwise assume it's a filename stem or pattern to match later
            # Keep as string for downstream stem-matching fallback
            filtered.append(entry_str)

        # Apply basic name-based filtering for explicit files
        explicit_files = [f for f in filtered if isinstance(f, Path)]
        final = []
        for f in explicit_files:
            # Include files with 'liv' in name, exclude 'loss', 'osa', and 'wlm'
            fname_lower = f.name.lower()
            if ('liv' in fname_lower and 
                'loss' not in fname_lower and 
                'osa' not in fname_lower and 
                'wlm' not in fname_lower):
                final.append(f)
            # Also check if it's in a directory path that indicates it's not an LIV file
            elif 'osa' in str(f.parent).lower() or 'wlm' in str(f.parent).lower():
                print(f"Skipping non-LIV file (in OSA/WLM folder): {f}")
                continue

        # Also include any non-file stems to be used by the fallback logic
        non_files = [f for f in filtered if not isinstance(f, Path)]
        final.extend(non_files)

        print("Debug: Filtered files (expanded):", [str(f) for f in final])
        return final
            
    def check_data(self):
        """Prints out the loaded IDtags and first few rows of each DataFrame."""
        print("All IDtags loaded:", list(self.loss_data.keys()))
        # To inspect the first few rows of each DataFrame in the dictionary:
        for idtag, df in self.loss_data.items():
            print(f"First rows for {idtag}:")
            print(df.head())

    def get_IDtag(self, filename: str) -> str:
        base = Path(filename).stem
        # Expanded regex to handle more variations, including '_clad' and other suffixes
        matchR = re.search(r"Chip\w+_R\d+(_clad)?(__iter\d+)?", base)
        matchL = re.search(r"Chip\w+_L\d+(_clad)?(__iter\d+)?", base)
        matchD = re.search(r"Chip\w+_D\d+(_clad)?(__iter\d+)?", base)
        if matchR:
            id_tag = matchR.group(0)  # Retain '_clad' if present
        elif matchL:
            id_tag = matchL.group(0)  # Retain '_clad' if present
        elif matchD:
            id_tag = matchD.group(0)  # Retain '_clad' if present
        else:
            id_tag = "Unknown_ID"

        # Detailed logging for debugging
        print(f"Debug: Filename: {filename}, Base: {base}, Extracted ID Tag: {id_tag}")
        return id_tag
        
    def compPlots(self):
        """Generates comparison plots for channels 0–3, voltage, and temperature.
        NOTE: CH0 = Physical Channel 1, CH1 = Physical Channel 2, etc."""
        CH0fig, CH0ax = plt.subplots(figsize=(8, 6))  # Physical Channel 1
        CH1fig, CH1ax = plt.subplots(figsize=(8, 6))  # Physical Channel 2
        CH2fig, CH2ax = plt.subplots(figsize=(8, 6))  # Physical Channel 3
        CH3fig, CH3ax = plt.subplots(figsize=(8, 6))  # Physical Channel 4
        VIfig, VIax = plt.subplots(figsize=(8, 6))
        TIfig, TIax = plt.subplots(figsize=(8, 6))

        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0.2, 0.8, len(idtags))) if idtags else []
        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]
            if 'channel_0' in df:
                CH0ax.plot(df['current'], df['channel_0'], label=idtag, color=color)
            if 'channel_1' in df:
                CH1ax.plot(df['current'], df['channel_1'], label=idtag, color=color)
            if 'channel_2' in df:
                CH2ax.plot(df['current'], df['channel_2'], label=idtag, color=color)
            if 'channel_3' in df:
                CH3ax.plot(df['current'], df['channel_3'], label=idtag, color=color)
            if 'voltage' in df:
                VIax.plot(df['current'], df['voltage'], label=idtag, color=color)
            if 'temperature' in df:
                TIax.plot(df['current'], df['temperature'], label=idtag, color=color)

        def _fmt(ax, ylab, title):
            ax.set_xlabel('Current', fontsize=self.FONT_AXIS_LABEL)
            ax.set_ylabel(ylab, fontsize=self.FONT_AXIS_LABEL)
            ax.set_title(title, fontsize=self.FONT_TITLE)
            if self.show_legends:
                ax.legend(fontsize=self.FONT_LEGEND)
            ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)

        _fmt(CH0ax, 'Channel 0', 'Channel 0 vs Current (all devices)')
        _fmt(CH1ax, 'Channel 1', 'Channel 1 vs Current (all devices)')
        _fmt(CH2ax, 'Channel 2', 'Channel 2 vs Current (all devices)')
        _fmt(CH3ax, 'Channel 3', 'Channel 3 vs Current (all devices)')
        _fmt(VIax, 'Voltage', 'Voltage vs Current (all devices)')
        _fmt(TIax, 'Temperature', 'Temperature vs Current (all devices)')

        for fig in (CH0fig, CH1fig, CH2fig, CH3fig, VIfig, TIfig):
            fig.tight_layout()

        CH0fig.savefig(Path(self.save_dir) / 'CH0_comparison.png')
        CH1fig.savefig(Path(self.save_dir) / 'CH1_comparison.png')
        CH2fig.savefig(Path(self.save_dir) / 'CH2_comparison.png')
        CH3fig.savefig(Path(self.save_dir) / 'CH3_comparison.png')
        VIfig.savefig(Path(self.save_dir) / 'VI_comparison.png')
        TIfig.savefig(Path(self.save_dir) / 'TI_comparison.png')
        print("Comparison plots saved: CH0/1/2/3_comparison.png, VI_comparison.png, TI_comparison.png")
        return

    def plot_thresholds(self):
        """Generates a boxplot of threshold currents for each IDtag.
        NOTE: Uses ch1_threshold (Physical Channel 2)."""
        idtags = list(self.loss_data.keys())
        threshold_list = [self.loss_data[id]['ch1_threshold'].values[0] for id in idtags]  # Physical Channel 2
        # Replace None values in threshold_list with np.nan
        threshold_list = [np.nan if v is None else v for v in threshold_list]
        print(threshold_list)


        

        Threshfig, Threshax = plt.subplots(figsize=(8, 6))
        Threshax.boxplot(
            threshold_list,
            notch=False,              # Show notch (median CI)
            vert=True,               # Vertical boxplot
            whis=1.5,                 # Whisker length in IQR multiples
            patch_artist=True,        # Enable fill color
            boxprops=dict(facecolor="lightblue", color="blue"),
            medianprops=dict(color="red", linewidth=2),
            whiskerprops=dict(color="black", linewidth=1.5),
            capprops=dict(color="black", linewidth=1.5),
            flierprops=dict(marker='o', color='green', markersize=6, alpha=0.5)
        )

        # positions = np.arange(1, len(idtags) + 1)
        # Threshax.set_xticks(positions)
        # Threshax.set_xticklabels(idtags, rotation=45, ha='right', fontsize=self.FONT_AXIS_TICKS)

        Threshax.set_xlabel('Device Channel 1', fontsize=self.FONT_AXIS_LABEL)
        Threshax.set_ylabel('Threshold Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        Threshax.set_title('Threshold Currents\n(box = IQR, whiskers = ±1σ, ♦ = mean)', fontsize=self.FONT_TITLE)
        Threshax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        Threshfig.tight_layout()

        Threshfig.savefig(Path(self.save_dir) / 'Thresholds_comparison.png')
        print("Thresholds comparison plot saved as Thresholds_comparison.png")
        return

    def plot_thresholds_ch2(self):
        """Generates a boxplot of threshold currents for each IDtag.
        NOTE: Uses ch2_threshold (Physical Channel 3)."""
        idtags = list(self.loss_data.keys())
        threshold_list = [self.loss_data[id]['ch2_threshold'].values[0] for id in idtags]  # Physical Channel 3
        # Replace None values in threshold_list with np.nan
        threshold_list = [np.nan if v is None else v for v in threshold_list]
        print(threshold_list)

        Threshfig, Threshax = plt.subplots(figsize=(8, 6))
        Threshax.boxplot(
            threshold_list,
            notch=False,              # Show notch (median CI)
            vert=True,               # Vertical boxplot
            whis=1.5,                 # Whisker length in IQR multiples
            patch_artist=True,        # Enable fill color
            boxprops=dict(facecolor="lightcoral", color="red"),
            medianprops=dict(color="darkred", linewidth=2),
            whiskerprops=dict(color="black", linewidth=1.5),
            capprops=dict(color="black", linewidth=1.5),
            flierprops=dict(marker='o', color='orange', markersize=6, alpha=0.5)
        )

        Threshax.set_xlabel('Device Channel 2 (Physical Ch3)', fontsize=self.FONT_AXIS_LABEL)
        Threshax.set_ylabel('Threshold Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        Threshax.set_title('Threshold Currents - CH2\n(box = IQR, whiskers = ±1σ, ♦ = mean)', fontsize=self.FONT_TITLE)
        Threshax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        Threshfig.tight_layout()

        Threshfig.savefig(Path(self.save_dir) / 'Thresholds_CH2_comparison.png')
        print("Thresholds CH2 comparison plot saved as Thresholds_CH2_comparison.png")
        return

    def plot_power_at_current(self, allowance= 0.01):

        # Generates two separate bar plots for power at 25mA and 50mA for each chip ID. Allowance is the tolerance for current matching (i.e. 24.5 ~ 25.5 for 25mA).
        idtags = list(self.loss_data.keys())
        power_25mA = []
        for idtag in idtags:
            df = self.loss_data[idtag]
            cur_mA = df['current'].astype(float)  # Convert current to mA
            power = df['channel_2'].astype(float) #Ensure to use the correct channel
            mask = np.isclose(cur_mA, 25, atol=allowance)
            if mask.any():
                power_25mA.append(power[mask].iloc[0])
            else:
                power_25mA.append(np.nan)

        fig_25, ax_25 = plt.subplots(figsize=(8, 6))
        ax_25.bar(idtags, power_25mA, color='skyblue')
        ax_25.set_xlabel('Chip ID', fontsize=self.FONT_AXIS_LABEL)
        ax_25.set_ylabel('Power (mW)', fontsize=self.FONT_AXIS_LABEL)
        ax_25.set_title('Power at 25mA for all devices', fontsize=self.FONT_TITLE)
        ax_25.set_xticks(range(len(idtags)))
        ax_25.set_xticklabels(idtags, rotation=45, ha='right', fontsize=self.FONT_AXIS_TICKS)
        ax_25.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)
        fig_25.tight_layout()
        fig_25.savefig(Path(self.save_dir) / 'Power_at_25mA.png')
        print("Power at 25mA plot saved as Power_at_25mA.png")
        

        # Power at 50mA
        power_50mA = []
        for idtag in idtags:
            df = self.loss_data[idtag]
            cur_mA = df['current'].astype(float) # Convert current to mA
            power = df['channel_1'].astype(float) #Ensure to use the correct channel
            mask = np.isclose(cur_mA, 50, atol=allowance)
            if mask.any():
                power_50mA.append(power[mask].iloc[0])
            else:
                power_50mA.append(np.nan)

        fig_50, ax_50 = plt.subplots(figsize=(8, 6))
        ax_50.bar(idtags, power_50mA, color='lightcoral')
        ax_50.set_xlabel('Chip ID', fontsize=self.FONT_AXIS_LABEL)
        ax_50.set_ylabel('Power (mW)', fontsize=self.FONT_AXIS_LABEL)
        ax_50.set_title('Power at 50mA for all devices', fontsize=self.FONT_TITLE)
        ax_50.set_xticks(range(len(idtags)))
        ax_50.set_xticklabels(idtags, rotation=45, ha='right', fontsize=self.FONT_AXIS_TICKS)
        ax_50.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)
        fig_50.tight_layout()
        fig_50.savefig(Path(self.save_dir) / 'Power_at_50mA.png')
        print("Power at 50mA plot saved as Power_at_50mA.png")

        # Power at 25mA (dBm)
        power_25mA_dBm = []
        for idtag in idtags:
            df = self.loss_data[idtag]
            cur_mA = df['current'].astype(float)  # Convert current to mA
            power_dBm = df['channel_2_log'].astype(float)  #
            mask = np.isclose(cur_mA, 25, atol=allowance)
            if mask.any():
                power_25mA_dBm.append(power_dBm[mask].iloc[0])
            else:
                power_25mA_dBm.append(np.nan)

        fig_25_dBm, ax_25_dBm = plt.subplots(figsize=(8, 6))
        ax_25_dBm.bar(idtags, power_25mA_dBm, color='skyblue')
        
        # TEMPORARY: Add dotted horizontal lines for dBm reference levels
        dbm_levels = [-4.8, -10, -16.8, -19.8]
        for dbm in dbm_levels:
            ax_25_dBm.axhline(y=dbm, color='red', linestyle=':', linewidth=1.5, alpha=0.7, label=f'{dbm} dBm')
        
        ax_25_dBm.set_xlabel('Chip ID', fontsize=self.FONT_AXIS_LABEL)
        ax_25_dBm.set_ylabel('Power (dBm)', fontsize=self.FONT_AXIS_LABEL)
        ax_25_dBm.set_title('Power at 25mA (dBm) for all devices', fontsize=self.FONT_TITLE)
        ax_25_dBm.set_xticks(range(len(idtags)))
        ax_25_dBm.set_xticklabels(idtags, rotation=45, ha='right', fontsize=self.FONT_AXIS_TICKS)
        ax_25_dBm.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)
        if self.show_legends:
            ax_25_dBm.legend(fontsize=self.FONT_LEGEND, loc='upper right')
        fig_25_dBm.tight_layout()
        fig_25_dBm.savefig(Path(self.save_dir) / 'Power_at_25mA_dBm.png')
        print("Power at 25mA (dBm) plot saved as Power_at_25mA_dBm.png")

        # Power at 50mA (dBm)
        power_50mA_dBm = []
        for idtag in idtags:
            df = self.loss_data[idtag]
            cur_mA = df['current'].astype(float)  # Convert current to mA
            power_dBm = df['channel_2_log'].astype(float)  # Assuming channel 2 contains dBm values
            mask = np.isclose(cur_mA, 50, atol=allowance)
            if mask.any():
                power_50mA_dBm.append(power_dBm[mask].iloc[0])
            else:
                power_50mA_dBm.append(np.nan)

        fig_50_dBm, ax_50_dBm = plt.subplots(figsize=(8, 6))
        ax_50_dBm.bar(idtags, power_50mA_dBm, color='lightcoral')
        
        # TEMPORARY: Add dotted horizontal lines for dBm reference levels
        dbm_levels = [-4.8, -10, -16.8, -19.8]
        for dbm in dbm_levels:
            ax_50_dBm.axhline(y=dbm, color='red', linestyle=':', linewidth=1.5, alpha=0.7, label=f'{dbm} dBm')
        
        ax_50_dBm.set_xlabel('Chip ID', fontsize=self.FONT_AXIS_LABEL)
        ax_50_dBm.set_ylabel('Power (dBm)', fontsize=self.FONT_AXIS_LABEL)
        ax_50_dBm.set_title('Power at 50mA (dBm) for all devices', fontsize=self.FONT_TITLE)
        ax_50_dBm.set_xticks(range(len(idtags)))
        ax_50_dBm.set_xticklabels(idtags, rotation=45, ha='right', fontsize=self.FONT_AXIS_TICKS)
        ax_50_dBm.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)
        if self.show_legends:
            ax_50_dBm.legend(fontsize=self.FONT_LEGEND, loc='upper right')
        fig_50_dBm.tight_layout()
        fig_50_dBm.savefig(Path(self.save_dir) / 'Power_at_50mA_dBm.png')
        print("Power at 50mA (dBm) plot saved as Power_at_50mA_dBm.png")
        return

    def plot_chip_thresholds(self, channel='ch2'):
        """
        Generates a simple plot of chip ID vs threshold data for specified channel.
        
        Parameters:
        -----------
        channel : str, optional
            The channel to plot ('ch0', 'ch1', 'ch2', 'ch3'). Default is 'ch2'.
            NOTE: ch0=Physical Ch1, ch1=Physical Ch2, ch2=Physical Ch3, ch3=Physical Ch4
        """
        idtags = list(self.loss_data.keys())
        threshold_key = f'{channel}_threshold'
        
        threshold_values = [
            self.loss_data[id][threshold_key].values[0]
            if threshold_key in self.loss_data[id]
            else None
            for id in idtags
        ]

        filtered_data = [(idtag, current) for idtag, current in zip(idtags, threshold_values) 
                         if current is not None and not np.isnan(current)]
        if not filtered_data:
            print(f"No valid {threshold_key} data found to plot.")
            return

        idtags_filtered, thresholds = zip(*filtered_data)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(idtags_filtered, thresholds, color='skyblue', edgecolor='black', alpha=0.7)

        ax.set_xlabel('Chip ID', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('Threshold Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title(f'Chip ID vs Threshold Current - {channel.upper()}', fontsize=self.FONT_TITLE)
        ax.set_xticks(range(len(idtags_filtered)))
        ax.set_xticklabels(idtags_filtered, rotation=45, ha='right', fontsize=self.FONT_AXIS_TICKS)
        
        # Set y-axis ticks every 2 units
        y_min = int(np.floor(min(thresholds)))
        y_max = int(np.ceil(max(thresholds)))
        ax.set_yticks(np.arange(y_min, y_max + 1, 2))
        ax.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

        fig.tight_layout()
        save_path = Path(self.save_dir) / f'Chip_Thresholds_{channel.upper()}.png'
        fig.savefig(save_path)
        print(f"Chip ID vs Threshold Current ({channel.upper()}) plot saved as {save_path.name}")
        return
    
    def plot_threshold_histogram(self, channel='ch1'):
        """
        Generates a histogram of threshold currents rounded to the nearest whole number.
        
        Parameters:
        -----------
        channel : str, optional
            The channel to use for threshold data ('ch0', 'ch1', 'ch2', 'ch3'). Default is 'ch1'.
            NOTE: ch0=Physical Ch1, ch1=Physical Ch2, ch2=Physical Ch3, ch3=Physical Ch4
        """
        idtags = list(self.loss_data.keys())
        threshold_key = f'{channel}_threshold'
        
        # Collect threshold values
        threshold_values = []
        for idtag in idtags:
            if threshold_key in self.loss_data[idtag]:
                val = self.loss_data[idtag][threshold_key].values[0]
                if val is not None and not np.isnan(val):
                    threshold_values.append(val)
        
        if not threshold_values:
            print(f"No valid {threshold_key} data found to plot.")
            return
        
        # Round to nearest whole number
        rounded_thresholds = np.round(threshold_values).astype(int)
        
        # Count occurrences
        unique_thresholds, counts = np.unique(rounded_thresholds, return_counts=True)
        
        # Create complete range from 0 to max threshold
        min_threshold = int(np.floor(min(threshold_values)))
        max_threshold = int(np.ceil(max(threshold_values)))
        all_thresholds = np.arange(min_threshold - 1, max_threshold + 1)
        
        # Map counts to the complete range (fill missing values with 0)
        count_dict = dict(zip(unique_thresholds, counts))
        all_counts = [count_dict.get(t, 0) for t in all_thresholds]
        
        # Create bar plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(all_thresholds, all_counts, color='steelblue', edgecolor='black', alpha=0.7)
        
        ax.set_xlabel('Threshold Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('Number of Chips', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title(f'Distribution of Threshold Currents - {channel.upper()}', fontsize=self.FONT_TITLE)
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Set x-axis to show all integer values from 0 to max
        ax.set_xticks(all_thresholds)
        ax.set_xlim(min_threshold - 0.5, max_threshold + 0.5)
        
        # Set y-axis ticks every 2 chips
        y_max = int(np.ceil(max(all_counts)))
        ax.set_yticks(np.arange(0, y_max + 1, 2))
        
        fig.tight_layout()
        save_path = Path(self.save_dir) / f'Threshold_Histogram_{channel.upper()}.png'
        fig.savefig(save_path)
        print(f"Threshold current histogram ({channel.upper()}) saved as {save_path.name}")
        
        # Print statistics
        print(f"\nThreshold Statistics for {channel.upper()}:")
        print(f"  Mean: {np.mean(threshold_values):.2f} mA")
        print(f"  Median: {np.median(threshold_values):.2f} mA")
        print(f"  Std Dev: {np.std(threshold_values):.2f} mA")
        print(f"  Min: {np.min(threshold_values):.2f} mA")
        print(f"  Max: {np.max(threshold_values):.2f} mA")
        print(f"  Total chips: {len(threshold_values)}")
        
        return
    
    def plot_normalized_LIV(self):
        """
        Generates normalized LI curves for all channels where each device's power is normalized 
        to 0-1 scale (min-max normalization). All devices are overlaid without legends.
        NOTE: CH0 = Physical Channel 1, CH1 = Physical Channel 2, etc.
        """
        CH0fig, CH0ax = plt.subplots(figsize=(8, 6))  # Physical Channel 1
        CH1fig, CH1ax = plt.subplots(figsize=(8, 6))  # Physical Channel 2
        CH2fig, CH2ax = plt.subplots(figsize=(8, 6))  # Physical Channel 3
        CH3fig, CH3ax = plt.subplots(figsize=(8, 6))  # Physical Channel 4

        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0.2, 0.8, len(idtags))) if idtags else []
        
        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]
            current = df['current'].values
            
            # Normalize each channel's power data (min-max normalization)
            if 'channel_0' in df:
                power = df['channel_0'].values
                power_min, power_max = power.min(), power.max()
                if power_max > power_min:  # Avoid division by zero
                    power_norm = (power - power_min) / (power_max - power_min)
                    CH0ax.plot(current, power_norm, label=idtag, color=color, alpha=0.7, linewidth=1.5)
            
            if 'channel_1' in df:
                power = df['channel_1'].values
                power_min, power_max = power.min(), power.max()
                if power_max > power_min:
                    power_norm = (power - power_min) / (power_max - power_min)
                    CH1ax.plot(current, power_norm, label=idtag, color=color, alpha=0.7, linewidth=1.5)
            
            if 'channel_2' in df:
                power = df['channel_2'].values
                power_min, power_max = power.min(), power.max()
                if power_max > power_min:
                    power_norm = (power - power_min) / (power_max - power_min)
                    CH2ax.plot(current, power_norm, label=idtag, color=color, alpha=0.7, linewidth=1.5)
            
            if 'channel_3' in df:
                power = df['channel_3'].values
                power_min, power_max = power.min(), power.max()
                if power_max > power_min:
                    power_norm = (power - power_min) / (power_max - power_min)
                    CH3ax.plot(current, power_norm, label=idtag, color=color, alpha=0.7, linewidth=1.5)

        def _fmt(ax, title):
            ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
            ax.set_ylabel('Normalized Power', fontsize=self.FONT_AXIS_LABEL)
            ax.set_title(title, fontsize=self.FONT_TITLE)
            ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
            ax.grid(True, alpha=0.3, linestyle='--')
            # Add legend only if number of items is reasonable and user wants legends
            if self.show_legends and len(idtags) <= 20:
                ax.legend(fontsize=self.FONT_LEGEND, loc='best')

        _fmt(CH0ax, 'Normalized LI Curve - Channel 0 (Physical Ch1)')
        _fmt(CH1ax, 'Normalized LI Curve - Channel 1 (Physical Ch2)')
        _fmt(CH2ax, 'Normalized LI Curve - Channel 2 (Physical Ch3)')
        _fmt(CH3ax, 'Normalized LI Curve - Channel 3 (Physical Ch4)')

        for fig in (CH0fig, CH1fig, CH2fig, CH3fig):
            fig.tight_layout()

        CH0fig.savefig(Path(self.save_dir) / 'CH0_normalized_LI.png')
        CH1fig.savefig(Path(self.save_dir) / 'CH1_normalized_LI.png')
        CH2fig.savefig(Path(self.save_dir) / 'CH2_normalized_LI.png')
        CH3fig.savefig(Path(self.save_dir) / 'CH3_normalized_LI.png')
        print("Normalized LI curves saved: CH0/1/2/3_normalized_LI.png")
        return
    
    def plot_channel_analysis_by_wavelength(self):
        """
        Prompts user to select a channel for analysis, then creates vertically stacked subplots
        for each chip showing normalized power vs current (25-50 mA) for that channel.
        Colors each chip using the same inferno gradient as used in the normalized_LI plots.
        """
        print("\n" + "="*60)
        print("Channel-Specific Analysis")
        print("="*60)
        print("Available channels:")
        print("  0 - Channel 0 (Physical Ch1)")
        print("  1 - Channel 1 (Physical Ch2)")
        print("  2 - Channel 2 (Physical Ch3)")
        print("  3 - Channel 3 (Physical Ch4)")
        print("  (or press Enter to skip)")
        
        try:
            choice = input("Enter channel number (0-3): ").strip()
            if not choice:
                print("Skipping channel-specific analysis.")
                return
            
            channel_num = int(choice)
            if channel_num not in [0, 1, 2, 3]:
                print(f"Invalid channel: {channel_num}. Skipping analysis.")
                return
        except (ValueError, EOFError):
            print("Invalid input. Skipping channel-specific analysis.")
            return
        
        channel_key = f'channel_{channel_num}'
        channel_name = f'Channel {channel_num} (Physical Ch{channel_num + 1})'
        
        # Get ordered list of idtags (same order as in other plots)
        idtags = list(self.loss_data.keys())
        
        # Use same inferno gradient coloring as normalized_LI plots
        colors = self.cmap(np.linspace(0.2, 0.8, len(idtags))) if idtags else []
        
        # Collect all chips with their colors (maintaining order)
        chip_data = []
        for idtag, color in zip(idtags, colors):
            df = self.loss_data[idtag]
            if channel_key in df:
                chip_data.append((idtag, df, color))
        
        if not chip_data:
            print(f"No data found for {channel_key}")
            return
        
        # Create vertically stacked subplots with reduced height
        n_chips = len(chip_data)
        fig, axes = plt.subplots(n_chips, 1, figsize=(10, 1.5*n_chips), sharex=True)
        if n_chips == 1:
            axes = [axes]
        
        # Plot each chip
        for idx, (idtag, df, color) in enumerate(chip_data):
            ax = axes[idx]
            
            current = df['current'].values
            power = df[channel_key].values
            
            # Filter to 25-50 mA range
            mask = (current >= 25) & (current <= 50)
            current_filtered = current[mask]
            power_filtered = power[mask]
            
            if len(power_filtered) > 0:
                # Normalize power within the filtered range
                power_min, power_max = power_filtered.min(), power_filtered.max()
                if power_max > power_min:
                    power_norm = (power_filtered - power_min) / (power_max - power_min)
                    ax.plot(current_filtered, power_norm, color=color, linewidth=2)
            
            # Only show y-label on the middle subplot
            if idx == n_chips // 2:
                ax.set_ylabel('Normalized Power', fontsize=self.FONT_AXIS_LABEL)
            
            ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_xlim(25, 50)
        
        # Only show x-label on bottom subplot
        axes[-1].set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        
        fig.tight_layout()
        
        save_name = f'normalized_LI_ch{channel_num}_25_50mA_stacked.png'
        fig.savefig(Path(self.save_dir) / save_name, dpi=150)
        print(f"\nChannel {channel_num} analysis saved: {save_name}")
        return
    
    def plot_power_dBm_vs_current(self):
        """
        Generates power (dBm) vs current plots for all channels.
        Uses the channel_X_log columns which contain power in dBm.
        NOTE: CH0 = Physical Channel 1, CH1 = Physical Channel 2, etc.
        """
        CH0fig, CH0ax = plt.subplots(figsize=(8, 6))  # Physical Channel 1
        CH1fig, CH1ax = plt.subplots(figsize=(8, 6))  # Physical Channel 2
        CH2fig, CH2ax = plt.subplots(figsize=(8, 6))  # Physical Channel 3
        CH3fig, CH3ax = plt.subplots(figsize=(8, 6))  # Physical Channel 4

        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0.2, 0.8, len(idtags))) if idtags else []
        
        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]
            
            if 'channel_0_log' in df:
                # Filter out -200 dBm values
                mask = df['channel_0_log'] > -200
                CH0ax.plot(df['current'][mask], df['channel_0_log'][mask], label=idtag, color=color)
            if 'channel_1_log' in df:
                mask = df['channel_1_log'] > -200
                CH1ax.plot(df['current'][mask], df['channel_1_log'][mask], label=idtag, color=color)
            if 'channel_2_log' in df:
                mask = df['channel_2_log'] > -200
                CH2ax.plot(df['current'][mask], df['channel_2_log'][mask], label=idtag, color=color)
            if 'channel_3_log' in df:
                mask = df['channel_3_log'] > -200
                CH3ax.plot(df['current'][mask], df['channel_3_log'][mask], label=idtag, color=color)

        def _fmt(ax, title):
            ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
            ax.set_ylabel('Power (dBm)', fontsize=self.FONT_AXIS_LABEL)
            ax.set_title(title, fontsize=self.FONT_TITLE)
            if self.show_legends:
                ax.legend(fontsize=self.FONT_LEGEND)
            ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
            ax.grid(True, alpha=0.3, linestyle='--')

        _fmt(CH0ax, 'Power (dBm) vs Current - Channel 0 (Physical Ch1)')
        _fmt(CH1ax, 'Power (dBm) vs Current - Channel 1 (Physical Ch2)')
        _fmt(CH2ax, 'Power (dBm) vs Current - Channel 2 (Physical Ch3)')
        _fmt(CH3ax, 'Power (dBm) vs Current - Channel 3 (Physical Ch4)')

        for fig in (CH0fig, CH1fig, CH2fig, CH3fig):
            fig.tight_layout()

        CH0fig.savefig(Path(self.save_dir) / 'CH0_power_dBm_vs_current.png')
        CH1fig.savefig(Path(self.save_dir) / 'CH1_power_dBm_vs_current.png')
        CH2fig.savefig(Path(self.save_dir) / 'CH2_power_dBm_vs_current.png')
        CH3fig.savefig(Path(self.save_dir) / 'CH3_power_dBm_vs_current.png')
        print("Power (dBm) vs Current plots saved: CH0/1/2/3_power_dBm_vs_current.png")
        return
    
    def plot_VI_no_legend(self):
        """
        Generates a voltage vs current plot for all devices without legends.
        """
        fig, ax = plt.subplots(figsize=(8, 6))
        
        idtags = list(self.loss_data.keys())
        colors = self.cmap(np.linspace(0.2, 0.8, len(idtags))) if idtags else []
        
        for color, idtag in zip(colors, idtags):
            df = self.loss_data[idtag]
            if 'voltage' in df:
                ax.plot(df['current'], df['voltage'], color=color, alpha=0.7, linewidth=1.5)
        
        ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('Voltage (V)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Voltage vs Current (All Devices)', fontsize=self.FONT_TITLE)
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        fig.tight_layout()
        fig.savefig(Path(self.save_dir) / 'VI_no_legend.png')
        print("Voltage vs Current plot (no legend) saved as VI_no_legend.png")
        return
    
    def plot_beeswarm_by_wavelength(self, interactive_li=False):
        """
        Creates two beeswarm plots:
        1. ch2_threshold values grouped by wavelength (from file path)
        2. ch2_voltage_param values grouped by wavelength (from file path)
        Also creates a summary .txt file listing processed and not-plotted chip IDs.
        """
        import seaborn as sns
        import re
        # Prepare data
        idtags = list(self.loss_data.keys())
        idtag_to_path = {}
        for fp in self.selected_files:
            fname = fp.name if hasattr(fp, 'name') else str(fp)
            idtag = self.get_IDtag(fname)
            idtag_to_path[idtag] = str(fp)
        data = []
        for idtag in idtags:
            df = self.loss_data[idtag]
            file_path = idtag_to_path.get(idtag, idtag)
            wl = 'other'
            if re.search(r'1310', file_path):
                wl = '1310nm'
            elif re.search(r'1330', file_path):
                wl = '1330nm'
            elif re.search(r'1550', file_path):
                wl = '1550nm'
            # Select channel based on wavelength
            if wl == '1550nm':
                thresh = df.get('ch3_threshold', pd.Series([np.nan])).values[0]
                voltage = df.get('ch3_voltage_param', pd.Series([np.nan])).values[0]
            else:
                thresh = df.get('ch2_threshold', pd.Series([np.nan])).values[0]
                # For 1310nm and 1330nm: extract voltage at 25mA
                if 'voltage' in df.columns and 'current' in df.columns:
                    current_vals = df['current'].values
                    voltage_vals = df['voltage'].values
                    # Find closest current value to 35mA
                    idx_35mA = np.abs(current_vals - 35.0).argmin()
                    if np.abs(current_vals[idx_35mA] - 35.0) <= 1.0:  # Within 1mA tolerance
                        voltage = voltage_vals[idx_35mA]
                    else:
                        voltage = np.nan
                else:
                    voltage = np.nan
            data.append({'idtag': idtag, 'filename': file_path, 'wavelength': wl, 'threshold': thresh, 'voltage': voltage})
        df_all = pd.DataFrame(data)
        print("Beeswarm plot data:")
        print(df_all)
        # Filter out NaN values for plotting
        df_thresh = df_all[np.isfinite(df_all['threshold'])]
        df_voltage = df_all[np.isfinite(df_all['voltage'])]
        # Set up wavelength categories and colors (original behavior: inferno colormap)
        wavelength_order = ['1310nm', '1330nm', '1550nm']
        cmap = plt.get_cmap('inferno')
        inferno_colors = cmap(np.linspace(0.2, 0.8, len(wavelength_order)))
        color_map = dict(zip(wavelength_order, inferno_colors))
        # Beeswarm plot for threshold
        fig_thresh, ax = plt.subplots(figsize=(8, 6))
        try:
                ax = sns.swarmplot(x='wavelength', y='threshold', data=df_thresh,
                                   order=wavelength_order, size=10, palette=color_map, ax=ax)
        except Exception as e:
            print("Swarmplot failed, using stripplot instead:", e)
            ax = sns.stripplot(x='wavelength', y='threshold', data=df_thresh,
                               order=wavelength_order, size=10, palette=color_map, ax=ax)
        
        # Overlay mean ± std for each wavelength
        thresh_stats = {}
        for i, wl in enumerate(wavelength_order):
            wl_data = df_thresh[df_thresh['wavelength'] == wl]['threshold'].values
            if len(wl_data) > 0:
                mean_val = np.mean(wl_data)
                std_val = np.std(wl_data, ddof=1)
                # Calculate outliers using IQR method
                q1 = np.percentile(wl_data, 25)
                q3 = np.percentile(wl_data, 75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = wl_data[(wl_data < lower_bound) | (wl_data > upper_bound)]
                n_outliers = len(outliers)
                thresh_stats[wl] = {'mean': mean_val, 'std': std_val, 'n': len(wl_data), 'n_outliers': n_outliers}
                
                # Plot error bar (mean ± std)
                ax.errorbar(i, mean_val, yerr=std_val,
                          fmt='D', color='black', markersize=10,
                          capsize=8, capthick=2, linewidth=2,
                          markeredgewidth=2.5, markerfacecolor='white', zorder=10)
        
        ax.set_xlabel('Wavelength (nm)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('$I_{\mathrm{th}}$ (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Beeswarm: Threshold by Wavelength', fontsize=self.FONT_TITLE)
        # Show only numerical values in x-axis ticks
        ax.set_xticklabels(['1310', '1330', '1550'], fontsize=self.FONT_AXIS_TICKS)
        ax.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)
        plt.tight_layout()
        plt.savefig(Path(self.save_dir) / 'Beeswarm_Threshold_by_Wavelength.png', dpi=300)
        plt.close()
        # Beeswarm plot for voltage
        fig_volt, ax = plt.subplots(figsize=(8, 6))
        try:
            ax = sns.swarmplot(x='wavelength', y='voltage', data=df_voltage,
                               order=wavelength_order, size=10, palette=color_map, ax=ax)
        except Exception as e:
            print("Swarmplot failed, using stripplot instead:", e)
            ax = sns.stripplot(x='wavelength', y='voltage', data=df_voltage,
                               order=wavelength_order, size=10, palette=color_map, ax=ax)
        
        # Overlay mean ± std for each wavelength
        voltage_stats = {}
        for i, wl in enumerate(wavelength_order):
            wl_data = df_voltage[df_voltage['wavelength'] == wl]['voltage'].values
            if len(wl_data) > 0:
                mean_val = np.mean(wl_data)
                std_val = np.std(wl_data, ddof=1)
                # Calculate outliers using IQR method
                q1 = np.percentile(wl_data, 25)
                q3 = np.percentile(wl_data, 75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = wl_data[(wl_data < lower_bound) | (wl_data > upper_bound)]
                n_outliers = len(outliers)
                voltage_stats[wl] = {'mean': mean_val, 'std': std_val, 'n': len(wl_data), 'n_outliers': n_outliers}
                
                # Plot error bar (mean ± std)
                ax.errorbar(i, mean_val, yerr=std_val,
                          fmt='D', color='black', markersize=10,
                          capsize=8, capthick=2, linewidth=2,
                          markeredgewidth=2.5, markerfacecolor='white', zorder=10)
        
        ax.set_xlabel('Wavelength (nm)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('$V_{\mathrm{op}}$ (V)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('Beeswarm: Voltage by Wavelength', fontsize=self.FONT_TITLE)
        # Show only numerical values in x-axis ticks
        ax.set_xticklabels(['1310', '1330', '1550'], fontsize=self.FONT_AXIS_TICKS)
        ax.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)
        plt.tight_layout()
        plt.savefig(Path(self.save_dir) / 'Beeswarm_Voltage_by_Wavelength.png', dpi=300)
        plt.close()
        print("Beeswarm plots saved: Beeswarm_Threshold_by_Wavelength.png, Beeswarm_Voltage_by_Wavelength.png")
        # --- Write summary file ---
        summary_path = Path(self.save_dir) / 'Beeswarm_Summary.txt'
        with open(summary_path, 'w') as f:
            f.write('Beeswarm Plot Summary\n')
            f.write('='*60 + '\n')
            
            # Statistics for Threshold
            f.write('\nTHRESHOLD STATISTICS (by Wavelength)\n')
            f.write('-'*60 + '\n')
            for wl in wavelength_order:
                if wl in thresh_stats:
                    stats = thresh_stats[wl]
                    f.write(f"{wl}:\n")
                    f.write(f"  Mean ± Std: {stats['mean']:.3f} ± {stats['std']:.3f} mA\n")
                    f.write(f"  Number of samples: {stats['n']}\n")
                    f.write(f"  Number of outliers (IQR method): {stats['n_outliers']}\n")
                else:
                    f.write(f"{wl}: No data\n")
            
            # Statistics for Voltage
            f.write('\nVOLTAGE STATISTICS (by Wavelength)\n')
            f.write('-'*60 + '\n')
            for wl in wavelength_order:
                if wl in voltage_stats:
                    stats = voltage_stats[wl]
                    f.write(f"{wl}:\n")
                    f.write(f"  Mean ± Std: {stats['mean']:.3f} ± {stats['std']:.3f} V\n")
                    f.write(f"  Number of samples: {stats['n']}\n")
                    f.write(f"  Number of outliers (IQR method): {stats['n_outliers']}\n")
                else:
                    f.write(f"{wl}: No data\n")
            
            f.write('\n' + '='*60 + '\n')
            f.write('Processed files for beeswarm plots:\n')
            for idx, row in df_all.iterrows():
                f.write(f"  Chip ID: {row['idtag']}, Wavelength: {row['wavelength']}, File: {row['filename']}\n")
            f.write('\nNumber of files processed for each wavelength:\n')
            for wl in ['1310nm', '1330nm', '1550nm', 'other']:
                count = (df_all['wavelength'] == wl).sum()
                f.write(f"  {wl}: {count}\n")
            f.write('\nPlotted chip IDs (threshold):\n')
            for idtag in df_thresh['idtag']:
                f.write(f"  {idtag}\n")
            f.write('\nPlotted chip IDs (voltage):\n')
            for idtag in df_voltage['idtag']:
                f.write(f"  {idtag}\n")
            f.write('\nNot plotted (missing/NaN values):\n')
            not_plotted = set(df_all['idtag']) - set(df_thresh['idtag']) - set(df_voltage['idtag'])
            for idtag in not_plotted:
                f.write(f"  {idtag}\n")
        # Also create LI/VI overlays grouped by wavelength to match beeswarm grouping
        try:
            self.plot_LI_VI_overlay_by_wavelength(interactive_li=interactive_li)
        except Exception as e:
            print(f"Warning: Failed to create LI/VI overlays: {e}")
        print(f"Beeswarm summary written to: {summary_path}")
        return

    def plot_LIV_voltage_by_wavelength(self):
        """
        Create LIV plots (power vs current) with voltage on a right y-axis grouped by wavelength.
        - For 1310nm and 1330nm: use `channel_2` as the power trace (left axis) and voltage on right axis.
        - For 1550nm: use `channel_3` as the power trace (left axis) and voltage on right axis.
        Colors: use the `inferno` colormap and pick distinct colors for each wavelength group.
        """
        cmap = plt.get_cmap('inferno')
        # Map wavelengths to channel keys
        groups = {
            '1310nm': {'channel': 'channel_2', 'files': []},
            '1330nm': {'channel': 'channel_2', 'files': []},
            '1550nm': {'channel': 'channel_3', 'files': []},
        }

        # Build filename mapping
        idtag_to_path = {}
        for fp in self.selected_files:
            fname = fp.name if hasattr(fp, 'name') else str(fp)
            idtag = self.get_IDtag(fname)
            idtag_to_path[idtag] = str(fp)

        # Assign idtags to groups based on filename
        for idtag, df in self.loss_data.items():
            path = idtag_to_path.get(idtag, idtag)
            pstr = str(path).lower()
            if '1310' in pstr:
                groups['1310nm']['files'].append((idtag, df))
            elif '1330' in pstr:
                groups['1330nm']['files'].append((idtag, df))
            elif '1550' in pstr:
                groups['1550nm']['files'].append((idtag, df))

        # Prepare colors (two distinct inferno colors for 1310/1330; one for 1550)
        inferno_colors = cmap(np.linspace(0.25, 0.75, 3))
        color_map = {
            '1310nm': inferno_colors[0],
            '1330nm': inferno_colors[1],
            '1550nm': inferno_colors[2],
        }

        # Plot 1310 & 1330 together (both use channel_2)
        fig, ax = plt.subplots(figsize=(10, 7))
        ax_right = ax.twinx()
        plotted = 0
        total_traces = sum(len(groups[wl]['files']) for wl in ('1310nm', '1330nm'))
        for wl in ('1310nm', '1330nm'):
            ch_key = groups[wl]['channel']
            color = color_map.get(wl, 'gray')
            for idtag, df in groups[wl]['files']:
                if ch_key not in df:
                    continue
                x = np.array(df['current'])
                y = np.array(df[ch_key])
                ax.plot(x, y, color=color, linewidth=1.8, alpha=0.8)
                # voltage: prefer global 'voltage' then channel-specific voltage param
                if 'voltage' in df:
                    v = np.array(df['voltage'])
                else:
                    v = np.array(df.get(f'ch{ch_key.split("_")[1]}_voltage_param', np.full_like(x, np.nan)))
                ax_right.plot(x, v, color=color, linestyle='--', linewidth=1.2, alpha=0.7)
                plotted += 1

        ax.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_ylabel('Power (a.u. / channel_2)', fontsize=self.FONT_AXIS_LABEL)
        ax_right.set_ylabel('Voltage (V)', fontsize=self.FONT_AXIS_LABEL)
        ax.set_title('LIV (channel_2) and Voltage — 1310nm vs 1330nm', fontsize=self.FONT_TITLE)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        ax_right.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)

        # Legend: show which color corresponds to which wavelength
        from matplotlib.lines import Line2D
        legend_lines = [Line2D([0], [0], color=color_map['1310nm'], lw=3), Line2D([0], [0], color=color_map['1330nm'], lw=3)]
        if self.show_legends:
            ax.legend(legend_lines, ['1310nm', '1330nm'], fontsize=self.FONT_LEGEND, loc='best')

        save_path = Path(self.save_dir) / 'LIV_channel2_vs_voltage_1310_1330.png'
        fig.tight_layout()
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved LIV+Voltage overlay (1310/1330) to {save_path}")

        # Plot 1550 (channel_3)
        fig2, ax2 = plt.subplots(figsize=(10, 7))
        ax2_right = ax2.twinx()
        for idtag, df in groups['1550nm']['files']:
            ch_key = groups['1550nm']['channel']
            if ch_key not in df:
                continue
            x = np.array(df['current'])
            y = np.array(df[ch_key])
            ax2.plot(x, y, color=color_map['1550nm'], linewidth=1.8, alpha=0.8)
            if 'voltage' in df:
                v = np.array(df['voltage'])
            else:
                v = np.array(df.get('ch3_voltage_param', np.full_like(x, np.nan)))
            ax2_right.plot(x, v, color=color_map['1550nm'], linestyle='--', linewidth=1.2, alpha=0.7)

        ax2.set_xlabel('Current (mA)', fontsize=self.FONT_AXIS_LABEL)
        ax2.set_ylabel('Power (a.u. / channel_3)', fontsize=self.FONT_AXIS_LABEL)
        ax2_right.set_ylabel('Voltage (V)', fontsize=self.FONT_AXIS_LABEL)
        ax2.set_title('LIV (channel_3) and Voltage — 1550nm', fontsize=self.FONT_TITLE)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='both', labelsize=self.FONT_AXIS_TICKS)
        ax2_right.tick_params(axis='y', labelsize=self.FONT_AXIS_TICKS)

        # Legend for 1550
        legend_line_1550 = Line2D([0], [0], color=color_map['1550nm'], lw=3)
        if self.show_legends:
            ax2.legend([legend_line_1550], ['1550nm'], fontsize=self.FONT_LEGEND, loc='best')

        save_path2 = Path(self.save_dir) / 'LIV_channel3_vs_voltage_1550.png'
        fig2.tight_layout()
        fig2.savefig(save_path2, dpi=300, bbox_inches='tight')
        plt.close(fig2)
        print(f"Saved LIV+Voltage overlay (1550) to {save_path2}")
    
if __name__ == "__main__":
    parent_path = r"C:\Users\OWNER\Desktop\liv_data"
    multi = multi_LIV(parent_path, overwrite_existing=False)
    #multi.plot_beeswarm_by_wavelength(interactive_li=True)
    plt.show()  # Show all plots at once

