# Peak Finding

[scipy.signal.find_peaks](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html#scipy.signal.find_peaks)

```python
peaks, properties = find_peaks(x, height=0)
```

The important entries in returned properties that can help decide the curve fitting range are:

> - ‘prominences’, ‘right_bases’, ‘left_bases’
>
>   If prominence is given, these keys are accessible. See [peak_prominences](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.peak_prominences.html#scipy.signal.peak_prominences) for a description of their content.

## Preprocessing

In practice, we find out some smoothing on the raw data before `find_peaks` can reduce the chance of finding noises as peaks.

## Bases and Prominence

Visualization of prominence from [MATLAB documentation](https://www.mathworks.com/help/signal/ug/prominence.html):

![prominence](https://www.mathworks.com/help/signal/ug/peaksnolines.png)

The bases of a peak with large prominence may fully contain some other small peaks. Take care when using this information in specifying the fitting range in later steps.
