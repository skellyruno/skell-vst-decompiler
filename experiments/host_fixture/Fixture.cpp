// Original owned gain and creative-delay fixture for supported-host verification only.
#include <juce_audio_processors/juce_audio_processors.h>
#include <cmath>
#include "DelayFixture.h"

class Fixture final : public juce::AudioProcessor {
public:
    Fixture() : AudioProcessor(BusesProperties().withInput("Input",juce::AudioChannelSet::stereo(),true)
                                               .withOutput("Output",juce::AudioChannelSet::stereo(),true)) {
        gain = new juce::AudioParameterFloat(juce::ParameterID{"gain",1},"Gain",0.0f,1.0f,0.5f);
        addParameter(gain);
        delay = new juce::AudioParameterBool(juce::ParameterID{"creative_delay",1},"Creative Delay",false);
        addParameter(delay);
    }
    const juce::String getName() const override { return "Skell Host Fixture"; }
    void prepareToPlay(double,int) override { line.reset();setLatencySamples(0); }
    void releaseResources() override { line.reset(); }
    void reset() override { line.reset(); }
    bool isBusesLayoutSupported(const BusesLayout& l) const override {
        return l.getMainInputChannelSet()==juce::AudioChannelSet::stereo() && l.getMainOutputChannelSet()==juce::AudioChannelSet::stereo();
    }
    void processBlock(juce::AudioBuffer<float>& audio,juce::MidiBuffer&) override {
        juce::ScopedNoDenormals guard;
        if (audio.getNumChannels()!=2) return;
        auto* left=audio.getWritePointer(0);auto* right=audio.getWritePointer(1);
        const bool enabled=delay->get();
        for (int i=0;i<audio.getNumSamples();++i) line.process(left[i],right[i],enabled);
        audio.applyGain(gain->get());
    }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return delay->get() && getSampleRate()>0 ? static_cast<double>(DelayFixture::samples)/getSampleRate() : 0.; }
    bool hasEditor() const override { return false; }
    juce::AudioProcessorEditor* createEditor() override { return nullptr; }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return "Default"; }
    void changeProgramName(int,const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock& dest) override {
        juce::MemoryOutputStream stream(dest,false);stream.writeFloat(gain->get());stream.writeInt(delay->get()?1:0);
    }
    void setStateInformation(const void* data,int size) override {
        if (size==4 || size==8) { juce::MemoryInputStream stream(data,static_cast<size_t>(size),false);
            const float value=stream.readFloat();if (std::isfinite(value)) gain->setValueNotifyingHost(juce::jlimit(0.0f,1.0f,value));
            delay->setValueNotifyingHost(size==8 && stream.readInt()!=0 ? 1.f : 0.f); }
    }
private:
    juce::AudioParameterFloat* gain=nullptr;
    juce::AudioParameterBool* delay=nullptr;
    DelayFixture line;
};

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new Fixture(); }
