# Construct Adjacency Matrix

How the adjacency matrix is constructed will directly affect the path finding result.

## A Simple Idea

One simple idea is to only build connections for a pair of peaks between two adjacent sweeps.

```python
# demo pseudo-code
from itertools import pairwise, product

for sweep1,sweep2 in pairwise(ragged_array):
    for peak1,peak2 in product(sweep1,sweep2):
        adjacency_matrix[index_of(peak1)][index_of(peak2)] = cost_function(peak1,peak2)
```

Notice that in the above example, if a sweep has no peak, there will be no connections between the sweep before the no-peak sweep and the sweep after the no-peak sweep.

## [`scipy.sparse`](https://docs.scipy.org/doc/scipy/reference/sparse.html)

`scipy` uses sparse a matrix to store an adjacency matrix. In such `scipy` sparse matrix, assigning a value of 0 (connection with cost of 0) to a matrix element is different than the uninitialized element (no connection).
