# lib.py

Basic shared tools for Lorentzian peak fitting, cosine similarity peak tracking and hough transform peak mapping.

## Peak Finding

`find_peak_and_properties` was refactored from the curve fitting section. It applies a Gaussian filter as a preprocessor of the data.

## Curve Fitting

### `LorentzianPeakFitResult`

Stores the results from fitting a single peak.

### `SweepFitResult`

Essentially a list of `LorentzianPeakFitResult`, with constructor from raw data, and helper functions to report results.

## Peak Tracking

`peak_to_traces()` takes all the peaks in an experiment in ragged array from, and returns a list of trace sections, with one single roughly estimated FSR.

## Find Parallel Peaks

`group_peaks()` takes all the peak central wavelengths in ragged array from, with one full-size overall peak-shift trace. It returns a list of traces, where each trace is a list of ragged array indices.
