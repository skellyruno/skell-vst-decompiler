/* Owned ground truth: identical arithmetic can serve different host roles. */
#if defined(_WIN32)
#define API __declspec(dllexport) __declspec(noinline)
int _fltused = 0;
#else
#define API __attribute__((visibility("default"),noinline))
#endif
#define SCALE(name) API void name(float *p, unsigned n, float gain) { \
    for(unsigned i=0;i<n;++i) p[i] *= gain; \
}
SCALE(audio_gain)
SCALE(geometry_scale)
API void audio_clip(float *p,unsigned n,float limit) {
    for(unsigned i=0;i<n;++i) { float x=p[i]; p[i]=x>limit?limit:x< -limit?-limit:x; }
}
API void copy_control(float *p,unsigned n,float ignored) {
    (void)ignored; for(unsigned i=0;i<n;++i) p[i]=0.0f;
}
typedef void (*callback)(float*,unsigned,float);
API void dispatch(callback cb,float *p,unsigned n,float control) { cb(p,n,control); }
API void audio_route(float *p,unsigned n,float control) { dispatch(audio_gain,p,n,control); }
API void ui_route(float *p,unsigned n,float control) { dispatch(geometry_scale,p,n,control); }
API void clip_route(float *p,unsigned n,float control) { dispatch(audio_clip,p,n,control); }
API void clear_route(float *p,unsigned n,float control) { dispatch(copy_control,p,n,control); }
