#include "PairwiseRecoveryBound.h"
extern "C" double pair_cap(const double* w,const double* r,double c){std::array<double,17> a{},b{};std::copy_n(w,17,a.begin());std::copy_n(r,17,b.begin());return skell_lab::forwardPairCap<17>(a,b,c);}
