import numpy as np
from scipy.optimize import curve_fit

def lorentzfit(x, y, p0=None, bounds=None, nparams='3c', options=None, return_func=False):
    """
    Lorentzian curve fitting with flexible parameterization and diagnostics.

    Parameters
    ----------
    x, y : array_like
        Data arrays to fit.
    p0 : list or None
        Initial guess for parameters.
    bounds : tuple or None
        Bounds for parameters as ([lower_bounds], [upper_bounds]).
    nparams : str
        Lorentzian type: '1', '1c', '2', '2c', '3', '3c'.
    options : dict or None
        Options for scipy.optimize.curve_fit.
    return_func : bool
        If True, also return the fit function.

    Returns
    -------
    yfit : ndarray
        Fitted curve values.
    params : ndarray
        Optimized parameters.
    resnorm : float
        Sum of squared residuals.
    residual : ndarray
        Residuals (y - yfit).
    jacobian : ndarray
        Jacobian matrix from curve_fit.
    fitfunc : function, optional
        The fit function (if return_func is True).
    """
    x = np.asarray(x)
    y = np.asarray(y)
    if nparams == '1':
        fitfunc = lambda x, p1: 1.0 / (p1 * (x**2 + 1))
        npar = 1
    elif nparams == '1c':
        fitfunc = lambda x, p1, c: 1.0 / (p1 * (x**2 + 1)) + c
        npar = 2
    elif nparams == '2':
        fitfunc = lambda x, p1, p2: p1 / (x**2 + p2)
        npar = 2
    elif nparams == '2c':
        fitfunc = lambda x, p1, p2, c: p1 / (x**2 + p2) + c
        npar = 3
    elif nparams == '3':
        fitfunc = lambda x, p1, p2, p3: p1 / ((x - p2)**2 + p3)
        npar = 3
    elif nparams == '3c':
        fitfunc = lambda x, p1, p2, p3, c: p1 / ((x - p2)**2 + p3) + c
        npar = 4
    else:
        raise ValueError("Unknown nparams option.")

    # Set default initial guess if not provided
    if p0 is None:
        p3 = ((np.max(x) - np.min(x)) / 10.0) ** 2
        p2 = (np.max(x) + np.min(x)) / 2.0
        p1 = np.max(y) * p3
        c = np.min(y)
        if nparams == '1':
            p0 = [p1]
        elif nparams == '1c':
            p0 = [p1, c]
        elif nparams == '2':
            p0 = [p1, p3]
        elif nparams == '2c':
            p0 = [p1, p3, c]
        elif nparams == '3':
            p0 = [p1, p2, p3]
        elif nparams == '3c':
            p0 = [p1, p2, p3, c]
    if bounds is None:
        bounds = (-np.inf * np.ones(npar), np.inf * np.ones(npar))

    # Fit
    popt, pcov = curve_fit(fitfunc, x, y, p0=p0, bounds=bounds, **(options or {}))
    yfit = fitfunc(x, *popt)
    residual = y - yfit
    resnorm = np.sum(residual**2)

    # Numerical Jacobian (scipy returns pcov, not jacobian directly)
    # We'll estimate the Jacobian at the solution numerically
    eps = np.sqrt(np.finfo(float).eps)
    jacobian = np.empty((len(x), npar))
    for i in range(npar):
        dp = np.zeros_like(popt)
        dp[i] = eps * (abs(popt[i]) + 1)
        yfit1 = fitfunc(x, *(popt + dp))
        yfit2 = fitfunc(x, *(popt - dp))
        jacobian[:, i] = (yfit1 - yfit2) / (2 * dp[i])

    if return_func:
        return yfit, popt, resnorm, residual, jacobian, fitfunc
    return yfit, popt, resnorm, residual, jacobian

# Example usage for external scripts:
# from lorentzfit import lorentzfit
# yfit, params, resnorm, residual, jacobian = lorentzfit(x, y, nparams='3c')