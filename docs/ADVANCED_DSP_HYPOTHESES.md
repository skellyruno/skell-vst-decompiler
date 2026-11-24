# Advanced independent DSP hypotheses

Evo public manual describes stochastic optimal linear estimation, not a specific published state model. New original causal four-state Kalman experiment separates pitch center, slope and a fixed-frequency harmonic oscillator. Joseph covariance update, explicit unvoiced reset, innovation-triggered note jump reset. Tests use synthetic pitch trajectories, not audio/F0 end-to-end. 5 Hz model matches 5 Hz vibrato best; 4/6 Hz mismatches remain. No vendor mapping or resynthesis.

VMR: replace grid-only descriptive recovery fitting with optional bounded multistart continuous least-squares. Fit first 65%, predict remaining 35%; known 47/483 ms noisy synthetic control. Fit is not a circuit identification or proof of two states; actual renders and competing models required.

TVB/VMR coloration: coherent 1700/2300 Hz two-tone projection for sum/difference and third-order products. Test known linear/quadratic/cubic controls. Not all distortion, not an alias metric; near -300 dB is numerical floor, not hardware performance.

Three local tests passed on NumPy 2.3.5/SciPy 1.17.0; report includes exact code blob and local metrics. New CI pending. No vendor file instruction analysis this batch. Production plugins unchanged.
