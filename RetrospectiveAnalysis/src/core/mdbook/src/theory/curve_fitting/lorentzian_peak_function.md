# Lorentzian Peak Function Fitting

## Lorentzian Function

$$
f(x_0,y_0,I,\gamma) = y_0 + I \cdot \frac{\frac{\gamma}{2}^2}{\frac{\gamma}{2}^2 + (x-x_0)^2}
$$

[Desmos Playground](https://www.desmos.com/calculator/cysy3xftbw)

## Sloped Lorentzian Function

$$
f(x_0,y_0,I,\gamma,a) = y_0 + I \cdot \frac{\frac{\gamma}{2}^2}{\frac{\gamma}{2}^2 + (x-x_0)^2} + a(x-x_0)
$$

[Desmos Playground](https://www.desmos.com/calculator/bwk3fmqwdm)

## Curve Fitting

The use of [scipy.optimize.curve_fit](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html#scipy.optimize.curve_fit) is directly from the [legacy CLI RA script](https://github.com/SiEPIC/biosensors/blob/d89d08ba2ae25af1e3d65ec46948ad4c32c7085f/RetrospectiveAnalysis/MultiLorentzianFit.py#L90C4-L90C4).

Basically, just specify initial guesses and bounds.

Note that initial guesses will not only affect the executing time but may also cause fitting failure (will raise an error like "exceed maximum iteration").
