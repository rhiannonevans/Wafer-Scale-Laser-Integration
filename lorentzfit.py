"""
LORENTZFIT fits a single- or multi-parameter Lorentzian function to data

Python port of the MATLAB lorentzfit function by Jered R Wells
Original: v1.7 (2020/06/15)
Python port: 2025

Usage:
    yprime, params, resnorm, residual = lorentzfit(x, y, p0=None, bounds=None, nparams='3c')

Parameters:
    x : array_like
        Independent variable data
    y : array_like
        Dependent variable data (same size as x)
    p0 : array_like, optional
        Initial parameter guesses. If None, defaults are computed.
    bounds : tuple of array_like, optional
        Lower and upper bounds for parameters: (lb, ub)
    nparams : str, optional
        Model selection:
            '1'   - Single parameter Lorentzian (no constant)
            '1c'  - Single parameter Lorentzian (with constant)
            '2'   - Two parameter Lorentzian (no constant)
            '2c'  - Two parameter Lorentzian (with constant)
            '3'   - Three parameter Lorentzian (no constant)
            '3c'  - Three parameter Lorentzian (with constant) [DEFAULT]

Returns:
    yprime : ndarray
        Fitted y values
    params : ndarray
        Optimized parameters
    resnorm : float
        Sum of squared residuals
    residual : ndarray
        Residuals (y - yprime)

Reference: http://www.home.uos.de/kbetzler/notes/fitp.pdf
"""

import numpy as np
from scipy.optimize import curve_fit
import warnings


def lorentzfit(x, y, p0=None, bounds=None, nparams='3c'):
    """
    Fit Lorentzian function to data using least-squares optimization.
    """
    # Input validation
    x = np.asarray(x, dtype=float).flatten()
    y = np.asarray(y, dtype=float).flatten()
    
    if x.size != y.size:
        raise ValueError("x and y must have the same size")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("x and y must contain only finite values")
    
    # Compute default initial guesses
    p3_default = ((x.max() - x.min()) / 10.0) ** 2
    p2_default = (x.max() + x.min()) / 2.0
    p1_default = y.max() * p3_default
    c_default = y.min()
    
    # Model selection
    nparams = nparams.lower()
    
    if nparams == '1':
        # L(x) = 1 / (p1 * (x^2 + 1))
        def model(x, p1):
            return 1.0 / (p1 * (x**2 + 1))
        
        p0_default = [y.max()]
        lb_default = [-np.inf]
        ub_default = [np.inf]
        
    elif nparams == '1c':
        # L(x) = 1 / (p1 * (x^2 + 1)) + c
        def model(x, p1, c):
            return 1.0 / (p1 * (x**2 + 1)) + c
        
        p0_default = [y.max(), c_default]
        lb_default = [-np.inf, -np.inf]
        ub_default = [np.inf, np.inf]
        
    elif nparams == '2':
        # L(x) = p1 / (x^2 + p2)
        def model(x, p1, p2):
            return p1 / (x**2 + p2)
        
        p2_init = ((x.max() - x.min()) / 10.0) ** 2
        p1_init = y.max() * p2_init
        p0_default = [p1_init, p2_init]
        lb_default = [-np.inf, -np.inf]
        ub_default = [np.inf, np.inf]
        
    elif nparams == '2c':
        # L(x) = p1 / (x^2 + p2) + c
        def model(x, p1, p2, c):
            return p1 / (x**2 + p2) + c
        
        p2_init = ((x.max() - x.min()) / 10.0) ** 2
        p1_init = y.max() * p2_init
        p0_default = [p1_init, p2_init, c_default]
        lb_default = [-np.inf, -np.inf, -np.inf]
        ub_default = [np.inf, np.inf, np.inf]
        
    elif nparams == '3':
        # L(x) = p1 / ((x - p2)^2 + p3)
        def model(x, p1, p2, p3):
            return p1 / ((x - p2)**2 + p3)
        
        p0_default = [p1_default, p2_default, p3_default]
        lb_default = [-np.inf, -np.inf, -np.inf]
        ub_default = [np.inf, np.inf, np.inf]
        
    elif nparams == '3c':
        # L(x) = p1 / ((x - p2)^2 + p3) + c
        def model(x, p1, p2, p3, c):
            return p1 / ((x - p2)**2 + p3) + c
        
        p0_default = [p1_default, p2_default, p3_default, c_default]
        lb_default = [-np.inf, -np.inf, -np.inf, -np.inf]
        ub_default = [np.inf, np.inf, np.inf, np.inf]
        
    else:
        warnings.warn(f"Unknown nparams '{nparams}', using default '3c'")
        return lorentzfit(x, y, p0, bounds, '3c')
    
    # Handle p0 and bounds
    if p0 is None:
        p0 = p0_default
    else:
        p0 = np.asarray(p0, dtype=float).flatten()
        if p0.size != len(p0_default):
            raise ValueError(f"p0 must have {len(p0_default)} elements for nparams='{nparams}'")
    
    if bounds is None:
        lb = lb_default
        ub = ub_default
    else:
        if len(bounds) != 2:
            raise ValueError("bounds must be a tuple (lower_bounds, upper_bounds)")
        lb = np.asarray(bounds[0], dtype=float).flatten()
        ub = np.asarray(bounds[1], dtype=float).flatten()
        if lb.size != len(lb_default) or ub.size != len(ub_default):
            raise ValueError(f"bounds must have {len(lb_default)} elements for nparams='{nparams}'")
        if np.any(lb >= ub):
            raise ValueError("Lower bounds must be less than upper bounds")
    
    # Perform curve fitting
    try:
        params, pcov = curve_fit(model, x, y, p0=p0, bounds=(lb, ub), maxfev=10000)
        yprime = model(x, *params)
        residual = y - yprime
        resnorm = np.sum(residual**2)
        
        return yprime, params, resnorm, residual
        
    except RuntimeError as e:
        raise RuntimeError(f"Curve fitting failed: {e}")


# Example usage (equivalent to MATLAB examples)
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    
    # Generate test data
    x = np.arange(-16, 35.1, 0.1)
    y_true = 19.4 / ((x - 7)**2 + 15.8)
    y = y_true + np.random.randn(len(x)) / 10.0
    
    # Fit with initial guesses
    yprime1, params1, resnorm1, residual1 = lorentzfit(x, y, p0=[20, 10, 15, 0])
    
    print(f"Fitted parameters (3c): {params1}")
    print(f"Residual norm: {resnorm1:.4f}")
    
    # Plot results
    plt.figure(figsize=(10, 6))
    plt.plot(x, y, 'b.', linewidth=2, label='Data')
    plt.plot(x, yprime1, 'r-', linewidth=2, label='Fit')
    plt.xlabel('x')
    plt.ylabel('y')
    plt.title('Lorentzian Fit Example')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    # Fit without constant term
    yprime2, params2, resnorm2, residual2 = lorentzfit(x, y, nparams='3')
    print(f"\nFitted parameters (3): {params2}")
    print(f"Residual norm: {resnorm2:.4f}")
