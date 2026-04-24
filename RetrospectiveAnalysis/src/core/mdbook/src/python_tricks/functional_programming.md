# Functional Programming

Prerequisite: [**Functional Programming HOWTO**](https://docs.python.org/3/howto/functional.html)

## Multiprocessing

Using functional programming style, it's extremely easy to parallelize your code. Just replace the normal `map()` by `Pool.map()` from [multiprocessing.pool.Pool](https://docs.python.org/3/library/multiprocessing.html#multiprocessing.pool.Pool.map) package.

There is not a lazy version of `starmap()`. Mimic this by using [`functools.partial()`](https://docs.python.org/3/library/functools.html#functools.partial) in `imap()`.
