#include "OriginalSpace.h"
#include <SkellCore/ResearchWetDuck.h>
#include <array>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <stdexcept>
#include <string>

using skell_lab::Frame;
int main(int argc,char** argv) {
    if(argc!=4) throw std::runtime_error("usage: compare rate input.raw output.raw");
    double fs=std::stod(argv[1]);
    std::ifstream input(argv[2],std::ios::binary);
    std::ofstream output(argv[3],std::ios::binary);
    if(!input||!output) throw std::runtime_error("file open");
    skell_lab::OriginalSpace reference(fs), raw(fs,1.8,4200.,0.);
    using skellcore::research::WetDuck;
    std::array<WetDuck,4> cs{{WetDuck(fs),WetDuck(fs,9.,14.,260.,1.),WetDuck(fs,9.,14.,260.,2.),WetDuck(fs,9.,14.,260.,3.)}};
    Frame x;
    while(input.read(reinterpret_cast<char*>(x.data()),sizeof(x))) {
        const auto a=reference.wet(x), b=raw.wet(x);
        std::array<double,17> row{b[0],b[1],a[0],a[1],reference.wetGain()};
        for(size_t i=0;i<cs.size();++i){const double g=cs[i].process(x[0],x[1]);row[5+3*i]=b[0]*g;row[6+3*i]=b[1]*g;row[7+3*i]=g;}
        output.write(reinterpret_cast<const char*>(row.data()),sizeof(row));
    }
    if(input.gcount()!=0||!input.eof()||!output)throw std::runtime_error("IO failure");
}
