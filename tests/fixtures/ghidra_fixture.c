/* Original test fixture; never executed by the analysis smoke test. */
__declspec(dllexport) __declspec(noinline) double smooth(double state,double target,double alpha) {
    return state+(target-state)*alpha;
}
__declspec(dllexport) __declspec(noinline) double apply_gain(double sample,double state,double target) {
    return sample*smooth(state,target,.125);
}
int _fltused=0;
volatile double result;
void entry(void){result=apply_gain(.5,.1,.9);}
