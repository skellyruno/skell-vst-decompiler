// Owned headless research fixture; not a production plugin or commercial reference.
#include <juce_audio_processors/juce_audio_processors.h>
#include "../ir/FastStereoIR.h"
#include <memory>
using namespace skell::research::fast_ir;
class IRFixture final : public juce::AudioProcessor {
public:
    IRFixture():AudioProcessor(BusesProperties().withInput("Input",juce::AudioChannelSet::stereo(),true).withOutput("Output",juce::AudioChannelSet::stereo(),true)){}
    const juce::String getName() const override {return "Skell IR Host Fixture";}
    void prepareToPlay(double fs,int) override {
        engine.reset();setLatencySamples(0);
        if(!std::isfinite(fs)||fs<8000||fs>192000)return;
        const auto n=static_cast<std::size_t>(std::round(fs*10));
        std::vector<Tap> h(n);
        // Bounded original dense four-route impulse, reproducible independently in Python.
        for(std::size_t i=0;i<n;++i)for(std::size_t c=0;c<4;++c)
            h[i][c]=1e-5*double(static_cast<int>((i*17+c*13)%31)-15)/15.;
        h[0][0]+=.5;h[0][3]+=.5;
        engine=std::make_unique<NativeStereoIR>(h);
    }
    void releaseResources() override {engine.reset();}
    bool isBusesLayoutSupported(const BusesLayout& l) const override {return l.getMainInputChannelSet()==juce::AudioChannelSet::stereo()&&l.getMainOutputChannelSet()==juce::AudioChannelSet::stereo();}
    void processBlock(juce::AudioBuffer<float>& audio,juce::MidiBuffer&) override {
        juce::ScopedNoDenormals guard;
        if(!engine||audio.getNumChannels()!=2){audio.clear();return;}
        auto* l=audio.getWritePointer(0);auto* r=audio.getWritePointer(1);
        for(int i=0;i<audio.getNumSamples();++i){auto y=engine->tick({l[i],r[i]});l[i]=static_cast<float>(y[0]);r[i]=static_cast<float>(y[1]);}
    }
    // One fresh instance per capture; no live IR replacement or same-instance reset test.
    double getTailLengthSeconds() const override {return 10.;}
    bool acceptsMidi() const override {return false;} bool producesMidi() const override {return false;} bool isMidiEffect() const override {return false;}
    bool hasEditor() const override {return false;} juce::AudioProcessorEditor* createEditor() override {return nullptr;}
    int getNumPrograms() override {return 1;} int getCurrentProgram() override {return 0;} void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override {return "Fixture";} void changeProgramName(int,const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock& dest) override {dest.reset();}
    void setStateInformation(const void*,int) override {}
private: std::unique_ptr<NativeStereoIR> engine;
};
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter(){return new IRFixture();}
