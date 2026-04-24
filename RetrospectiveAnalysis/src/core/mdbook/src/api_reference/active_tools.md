# active_tools.py

## `ConverterConfig`

The abstract data type representation of the active converter CSV config file. It has helper functions to convert from/to CSV.

## `CSVData`

A data class representing the ramp column and power columns of a CSV data file. The ramp channel can be at any column.

## `SimpleRampCSVReaderBase`

Essentially an iterator return all the data in an active experiment by sweep. The sweeps are sliced from the reference signal (ramp channel). The slicing algorithm should be simple and quick. This is for raw data spectrogram plotting.

## `AdvancedRampCSVReaderBase`

Like `SimpleRampCSVReaderBase`, but slices the sweeps more accurately, using the LTI simulation method.

## `generate_sawtooth_from_data()`

Guess the period and phase of a ramp signal, in terms of sample point, assuming the ramp signal is evenly sampled in time. This is used because there is missing data between CSV files, and CSV files may start from a random place of a period.
