"""Original offline frame-rate note selection and retune control.

Produces correction cents only: no resynthesis, no audio latency guarantee,
and no claim of reproducing a commercial pitch-correction engine.
"""
import math


class RetuneControl:
    def __init__(self, notes=range(36,85), retune_ms=20., hysteresis_cents=12.,
                 min_periodicity=.8, *, sustain_ms=0., sustain_after_ms=150., sustain_ramp_ms=250.):
        if not all(math.isfinite(v) for v in (sustain_ms,sustain_after_ms,sustain_ramp_ms)) or not 0<=sustain_ms<=1000 or not 0<=sustain_after_ms<=5000 or not 0<sustain_ramp_ms<=5000:
            raise ValueError('Invalid sustained-note settings')
        self.sustain_ms=sustain_ms
        self.sustain_after_ms=sustain_after_ms
        self.sustain_ramp_ms=sustain_ramp_ms
        notes=tuple(sorted(set(notes)))
        if not notes or any(type(n) is not int or not 0<=n<=127 for n in notes):
            raise ValueError('Expected MIDI note set')
        if not all(math.isfinite(v) for v in (retune_ms,hysteresis_cents,min_periodicity)) or not 0<=retune_ms<=1000 or not 0<=hysteresis_cents<50 or not 0<=min_periodicity<=1:
            raise ValueError('Invalid retune settings')
        self.notes=notes
        self.retune_ms=retune_ms
        self.hysteresis=hysteresis_cents
        self.minimum=min_periodicity
        self.reset()

    def reset(self):
        self.note=None
        self.cents=0.
        self.note_age_ms=0.

    def step(self, frequency, periodicity, elapsed_ms):
        if not math.isfinite(elapsed_ms) or elapsed_ms<=0:
            raise ValueError('Positive frame duration required')
        if not math.isfinite(periodicity) or not 0<=periodicity<=1:
            raise ValueError('Invalid periodicity')
        if frequency is None or periodicity<self.minimum:
            self.reset()
            return None,0.
        if not math.isfinite(frequency) or frequency<=0:
            raise ValueError('Invalid frequency')
        pitch=69.+12.*math.log2(frequency/440.)
        candidate=min(self.notes,key=lambda n:(abs(n-pitch),n))
        if self.note is None or abs(pitch-self.note)-abs(pitch-candidate)>2*self.hysteresis/100.:
            self.note=candidate
            self.note_age_ms=0.
        target=100.*(self.note-pitch)
        # Original duration-dependent smoothing, not a commercial control mapping.
        weight=min(1.,max(0.,(self.note_age_ms-self.sustain_after_ms)/self.sustain_ramp_ms))
        tau=self.retune_ms+self.sustain_ms*weight*weight*(3.-2.*weight)
        alpha=1. if tau==0 else -math.expm1(-elapsed_ms/tau)
        self.note_age_ms+=elapsed_ms
        self.cents+=alpha*(target-self.cents)
        return self.note,self.cents
