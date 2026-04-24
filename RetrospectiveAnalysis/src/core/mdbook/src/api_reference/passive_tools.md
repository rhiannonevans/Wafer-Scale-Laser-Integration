# passive_tools.py

## `DataReaderBase`

The abstract class of passive data IO layer. Behaves like a list, where each item is of type `tuple[timestamp,wavelength_array,power_2d_array]`. It also has an interface to get `power_2d_array` only, for spectrogram plotting.
