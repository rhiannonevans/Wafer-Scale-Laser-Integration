import pytest
import numpy as np
from lorentzfit import lorentzfit, compute_Q_factor


def test_lorentzfit_basic():
    """Test basic Lorentzian fit with synthetic data."""
    x = np.linspace(-10, 10, 100)
    # Generate synthetic Lorentzian data: L(x) = A / ((x - x0)^2 + gamma) + c
    A_true, x0_true, gamma_true, c_true = 10, 0, 1, 0.5
    y_true = A_true / ((x - x0_true)**2 + gamma_true) + c_true
    y_noisy = y_true + np.random.randn(len(x)) * 0.05
    
    yprime, params, resnorm, residual = lorentzfit(x, y_noisy, nparams='3c')
    
    # Check that fit converged (parameters should be close to true values)
    assert len(params) == 4
    assert abs(params[1] - x0_true) < 0.5  # center wavelength
    assert resnorm < 1.0  # residual norm should be small
    assert len(yprime) == len(x)


def test_lorentzfit_returns_correct_shape():
    """Test that lorentzfit returns 4 outputs (not 5)."""
    x = np.linspace(1540, 1560, 50)
    y = 1.0 / ((x - 1550)**2 + 0.1) + 0.2
    
    result = lorentzfit(x, y, nparams='3c')
    
    assert len(result) == 4  # yprime, params, resnorm, residual
    yprime, params, resnorm, residual = result
    assert isinstance(params, np.ndarray)
    assert len(params) == 4


def test_compute_Q_factor():
    """Test Q-factor calculation from fit parameters."""
    # params = [A, x0, gamma, c] for '3c' model
    # Q = x0 / FWHM, FWHM = 2*sqrt(gamma)
    params = np.array([10, 1550, 0.25, 0.1])  # gamma=0.25 -> FWHM=1.0
    
    Q, lambda0, FWHM = compute_Q_factor(params, nparams='3c')
    
    assert lambda0 == 1550
    assert abs(FWHM - 1.0) < 0.01
    assert abs(Q - 1550) < 1.0


def test_lorentzfit_invalid_input():
    """Test that invalid inputs raise appropriate errors."""
    x = np.linspace(0, 10, 50)
    y = np.linspace(0, 10, 40)  # mismatched length
    
    with pytest.raises(ValueError):
        lorentzfit(x, y, nparams='3c')