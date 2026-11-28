"""Analytical controls for the owned spectral metric (NumPy optional in CI)."""
import unittest
try:
    import numpy as np
    from benchmarks.owned_extended_audio import spectrum
except ModuleNotFoundError:
    np=None


@unittest.skipUnless(np is not None, 'requires NumPy')
class SpectrumTests(unittest.TestCase):
    def test_known_harmonic_and_residual_even_odd(self):
        for n in (1000,1001):
            t=np.arange(n)/n
            x=.5*np.sin(2*np.pi*11*t)+.05*np.sin(2*np.pi*22*t)+.005*np.sin(2*np.pi*37*t)+.1
            r=spectrum(x,n,11)
            self.assertAlmostEqual(r['fundamental_amplitude'],.5,places=12)
            self.assertAlmostEqual(r['harmonic_distortion_dbc'],-20,places=9)
            self.assertAlmostEqual(r['nonharmonic_dbc'],-40,places=9)

    def test_even_nyquist_and_odd_last_bin(self):
        for n in (1000,1001):
            t=np.arange(n)/n
            x=.5*np.sin(2*np.pi*11*t)+.005*np.cos(2*np.pi*(n//2)*t)
            r=spectrum(x,n,11)
            self.assertAlmostEqual(r['nonharmonic_dbc'],-40+(10*np.log10(2) if n%2==0 else 0),places=8)

    def test_noncoherent_rejected(self):
        with self.assertRaises(ValueError):spectrum(np.ones(100),1000,11)
