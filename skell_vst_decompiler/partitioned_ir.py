"""Independent offline stereo partitioned convolution research, not a vendor model."""
import numpy as np
from scipy.fft import rfft, irfft
from scipy.signal import sosfilt, butter, fftconvolve


def shape_ir(h, fs, *, decay_db_per_second=0., damping_hz=None,
             early_ms=50., early_gain=1., late_gain=1., resonance_hz=None):
    """Shape original IRs offline; no fitting or normalization."""
    h = np.asarray(h, dtype=float)
    if h.ndim != 3 or h.shape[1:] != (2, 2) or not len(h) or not np.isfinite(h).all():
        raise ValueError('expected finite [time, output, input] matrix')
    if not 8000 <= fs <= 192000 or not 0 <= decay_db_per_second <= 120 or not 0 <= early_ms <= 1000 or not 0 <= early_gain <= 4 or not 0 <= late_gain <= 4:
        raise ValueError('invalid shaping settings')
    t = np.arange(len(h)) / fs
    mix = np.clip((t - early_ms / 1000) / .01, 0, 1)
    y = h * ((early_gain * (1 - mix) + late_gain * mix) * 10**(-decay_db_per_second * t / 20))[:, None, None]
    if damping_hz is not None:
        if not 20 <= damping_hz < .49 * fs: raise ValueError('invalid damping')
        low = sosfilt(butter(2, damping_hz, fs=fs, output='sos'), y, axis=0)
        y = y * (1-mix[:, None, None]) + low * mix[:, None, None]
    if resonance_hz is not None:
        if not 40 <= resonance_hz < .45 * fs: raise ValueError('invalid resonance')
        band = sosfilt(butter(1, [resonance_hz*.8, resonance_hz*1.2], btype='bandpass', fs=fs, output='sos'), y, axis=0)
        y -= .5 * band * mix[:, None, None]
    return y


class PartitionedIR:
    """Uniform overlap-add with fixed B-frame calls; offline prototype.

    Output is aligned to input block start; a sample-at-a-time host adapter
    would require buffering or a separate zero-latency head. No RT claim.
    """
    def __init__(self, h, block=256):
        h = np.asarray(h, dtype=float)
        if type(block) is not int or block < 16 or block > 8192 or block & (block-1): raise ValueError('invalid block')
        if h.ndim != 3 or h.shape[1:] != (2, 2) or not 1 <= len(h) <= 1920000 or not np.isfinite(h).all(): raise ValueError('invalid IR')
        self.block, self.length = block, len(h)
        self.parts = (len(h)+block-1)//block
        padded = np.zeros((self.parts, 2*block, 2, 2))
        for i in range(self.parts):
            p = h[i*block:(i+1)*block]; padded[i,:len(p)] = p
        self.H = rfft(padded, axis=1)
        self.X = np.zeros((self.parts, block+1, 2), complex)
        self.overlap = np.zeros((block,2)); self.cursor = 0

    def process(self, x):
        x = np.asarray(x,dtype=float); b = self.block
        if x.shape != (b,2) or not np.isfinite(x).all(): raise ValueError('invalid block input')
        self.X[self.cursor] = rfft(x,n=2*b,axis=0)
        # Split ring in two contiguous slices: no full history gather.
        n = self.cursor+1
        y = np.einsum('pfoi,pfi->fo',self.H[:n],self.X[:n][::-1], optimize=False)
        if n < self.parts:
            y += np.einsum('pfoi,pfi->fo',self.H[n:],self.X[n:][::-1], optimize=False)
        t = irfft(y,n=2*b,axis=0)
        out = t[:b]+self.overlap; self.overlap = t[b:].copy()
        self.cursor = (self.cursor+1)%self.parts
        return out


def render(h,x,block=256):
    engine=PartitionedIR(h,block); x=np.asarray(x,float)
    if x.ndim!=2 or x.shape[1]!=2 or not len(x) or not np.isfinite(x).all(): raise ValueError('invalid signal')
    n=len(x)+len(h)-1; frames=((n+block-1)//block)*block
    padded=np.zeros((frames,2)); padded[:len(x)]=x
    return np.concatenate([engine.process(padded[i:i+block]) for i in range(0,frames,block)])[:n]


def render_two_tier(h,x,head_block=128,tail_block=2048):
    """Offline nonuniform partition reference; late response starts at tail_block.

    The late tier may be scheduled ahead of its output deadline by a native
    adapter; this offline implementation does not establish deadline safety.
    """
    if type(head_block) is not int or type(tail_block) is not int or head_block<16 or tail_block<head_block or tail_block%head_block:
        raise ValueError('invalid tier geometry')
    if len(h)<=tail_block: return render(h,x,head_block)
    a=render(h[:tail_block],x,head_block)
    b=render(h[tail_block:],x,tail_block)
    y=np.zeros((len(x)+len(h)-1,2)); y[:len(a)]+=a; y[tail_block:]+=b
    return y


def switch_render(h1,h2,x,transition,fade,block=256):
    """Two-bank input crossfade; old bank receives no new input after fade.
    Full old and new tails retained, no output crossfade or tail normalization.
    Offline reference; bounded native scheduling remains a future gate.
    """
    x=np.asarray(x,float)
    if type(transition) is not int or type(fade) is not int or not 0<=transition<len(x) or fade<1: raise ValueError('invalid transition')
    w=np.clip((np.arange(len(x))-transition)/fade,0,1)[:,None]
    a=render(h1,x*(1-w),block); b=render(h2,x*w,block)
    y=np.zeros((max(len(a),len(b)),2)); y[:len(a)]+=a; y[:len(b)]+=b
    return y


def oracle(h,x):
    y=np.zeros((len(h)+len(x)-1,2))
    for o in range(2):
        for i in range(2): y[:,o]+=fftconvolve(x[:,i],h[:,o,i])
    return y


def selftest():
    rng=np.random.default_rng(8371); errors=[]; count=0
    for fs in (44100,48000,88200,96000,176400,192000):
        h=rng.normal(0,.005,(int(fs*.017)+3,2,2)); h[0]=[[.3,.1],[-.08,.2]]
        x=rng.normal(0,.12,(2317,2)); ref=oracle(h,x)
        for block in (32,128,256,1024):
            y=render(h,x,block); err=float(np.max(abs(y-ref))); assert err<1e-11; errors.append(err); count+=1
        assert np.max(abs(render_two_tier(h,x,32,256)-ref))<1e-11
        s=shape_ir(h,fs,decay_db_per_second=30,damping_hz=3000,early_ms=2,early_gain=1,late_gain=.7,resonance_hz=800)
        assert np.array_equal(shape_ir(h,fs),h); assert np.isfinite(s).all(); assert np.linalg.norm(s)<np.linalg.norm(h)
        # An impulse before switching must keep the entire old response.
        p=np.zeros((1300,2)); p[0,0]=1; a=switch_render(h,s,p,80,100)
        assert np.max(abs(a-oracle(h,p)))<1e-11
        w=np.clip((np.arange(len(x))-77)/83,0,1)[:,None]
        a=switch_render(h,s,x,77,83); ref=oracle(h,x*(1-w))+oracle(s,x*w)
        assert np.max(abs(a-ref))<1e-11
    return {'sample_rates':6,'convolution_cases':count,'two_tier_cases':6,'max_error':max(errors),'shaping_cases':6,'transition_cases':12}


if __name__=='__main__': print(selftest())
