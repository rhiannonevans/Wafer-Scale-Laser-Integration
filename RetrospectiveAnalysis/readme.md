# Retrospective Analysis GUI

## Setup

Python version >= 3.11

### Windows 10/11

#### Install Python

```shell
winget install --id Python.Python.3.11
```

#### Install Dependencies

- Right-click `install-dependencies.ps1`, and select `Run with PowerShell`. Answer `Y` if prompted.
- Right-click and run `retrospective-analysis.ps1` in the same method to start the GUI.

### macOS 12 

```shell
brew install python@3.11
```

And follow the brew output (if there is one) to set Python 3.11 into your path.

#### Virtual Environment (Recommended, Optional)

1. Clone this repo and navigate to this folder.
2. Find out the correct command to call Python 3.11. On \*nix platforms, use `which python`. It's usually `python3` for python.
3. Create a virtual environment by:
   ```shell
   python3 -m venv .venv
   ```

Then activate the virtual environment, by running `source .venv/bin/activate`.`

Official tutorial for the [virtual environment](https://docs.python.org/3/tutorial/venv.html).

#### Dependencies

If using a virtual environment, activate it. Double-check that the commands are calling the right binaries. i.e. both `pip` and `python` should be calling the ones in the virtual environment.

```shell
pip install -r requirements.txt
```

## Deployment

[Qt for Python Deployment](https://doc.qt.io/qtforpython-6/deployment.html#deployment-guides)

We tried Nuitka in 2022 summer. The compiled executable is somewhat unstable and crashes frequently. We deprecated it in 202208.

## Usage

```shell
python retrospective_analysis_gui.pyw
```

1. In the menubar, click `File`->`Open Folder` or `ctrl/⌘+O`
2. Select the folder containing the data files
3. Specify analyzer parameters and click `Load`
4. (Optional) In `(Optional) Plot Spectrograms`, select power channels and proper parameters, then click `Spectrogram`
5. Select power channels and click `Start Track`
6. Once the results show up, use the tab to navigate through power channels
7. If necessary, manually adjust the traces:
   1. Left-mouse-button dragging: free range adjustment
   2. Right-mouse-button dragging: trace will be anchored by a roughly estimated FSR
8. In the `Plot` block, push buttons for various kinds of plots **for this channel only**. Check `Auto-Save` to save the plots in the selected folder when clicking those buttons
9. Click `Save Results` to save all the fitted peaks in `peaks.mat`, all traces in `peak_shifts.mat`, and the overlaid and grouped traces will be popped up (This figure will always be automatically saved)

## Result Format

### `peak_shifts.mat`

Variables in this file:

- `power_*_peakWL_list`: a vector of peak wavelengths for each power channel
- `t_array`: a vector of time stamps for each peak

These variables should have the same size.

### `peaks.mat`

Variables in this file:

- `channel*`: a cell array containing all the fitted peaks for each power channel
  There are two cases for the shape of this cell array:

  1. If all the sweeps have the same number of peaks, the shape will be `#sweeps x #peaks x 5`
  2. If the sweeps have different number of peaks, the shape will be `1 x #sweeps`. And each element will be a matrix of shape `#peaks x 5`.

  The fitted peaks are represented by a 5-element vector: $\left[x_0, y_0, I, \gamma, a\right]$, where $x_0$ is the peak position, $y_0$ is the baseline, $I$ is the peak height (ER if in dB scale), $\gamma$ is the peak width (FWHM), and $a$ is a first-order compensate term for baseline drift.

  **One can always take it as a 2D array of vector and use`channel*[sweep_index][peak_index]` to find such 5-parameter vector for one specific peak.**

  The corresponding sloped Lorentzian function is: $f(x) = y_0 + {I}\frac{(\frac{\gamma}{2})^2}{(x-x_0)^2+(\frac{\gamma}{2})^2} + a(x-x_0)$. One can use this function to restore the spectrum around the fitted peaks.

- `channel*_peak_trace_indices`: a cell array containing the indices of the peaks in each trace. The shape is `1 x #traces`. Each element is a #length $\times 2$ matrix representing a trace, where each row is `(sweep_index,peak_index)`. One can use `[sweep_index][peak_index]` to index the `channel*`, `channel_er*` and `channel_q*` to get the corresponding peak information.
- `t_array`: a vector of time stamps for each sweep

### `fsr_er_q.mat`

Variables in this file:

- `channel*_er`, `channel*_q`: a cell array containing the extinction ratio / quality factor for all the fitted peaks in each power channel. The shape will be similar to `channel*` in `peaks.mat`. One can use `er[sweep_index][peak_index]` to find the data for one specific peak.
- `channel*_fsr`: a cell array containing the free spectral range for each power channel. The shape and indexing are similar to `channel*_er` and `channel*_q`, except that each sweep will have one less element.

## FAQ

- Peak tracking raises an error / never stops
  - Please first check the spectrograms in each channel. And only track the channels with resonance peaks.
  - If that doesn't solve the problem, check the first sweep in each channel. If there is no peak in the first sweep, the peak tracking will fail. Either not to include this channel, or select a different starting file number, or manually remove that sweep `.mat` file.
- What are the dots in peak tracking results?
  - This is usually because the trace section contains only a single data point. These points are invisible in all other output plots but will exist in the result matrix. Try manually aligning these points to have a better data result.

## Contribute

If you find (or believe that it is) a critical bug in this project, please submit an [issue](https://github.com/SiEPIC/biosensors/issues).

If you are not sure about how to use a feature or have any suggestions or ideas for the project, feel free to start a [discussion](https://github.com/SiEPIC/biosensors/discussions).
