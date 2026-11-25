// Original owned gain fixture for supported-host verification only.
#include <juce_audio_processors/juce_audio_processors.h>
#include <cmath>

class Fixture final : public juce::AudioProcessor {
public:
    Fixture() : AudioProcessor(BusesProperties().withInput("Input",juce::AudioChannelSet::stereo(),true)
                                               .withOutput("Output",juce::AudioChannelSet::stereo(),true)) {
        gain = new juce::AudioParameterFloat(juce::ParameterID{"gain",1},"Gain",0.0f,1.0f,0.5f);
        addParameter(gain);
    }
    const juce::String getName() const override { return "Skell Host Fixture"; }
    void prepareToPlay(double,int) override {}
    void releaseResources() override {}
    bool isBusesLayoutSupported(const BusesLayout& l) const override {
        return l.getMainInputChannelSet()==juce::AudioChannelSet::stereo() && l.getMainOutputChannelSet()==juce::AudioChannelSet::stereo();
    }
    void processBlock(juce::AudioBuffer<float>& audio,juce::MidiBuffer&) override {
        juce::ScopedNoDenormals guard;
        audio.applyGain(gain->get());
    }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.; }
    bool hasEditor() const override { return false; }
    juce::AudioProcessorEditor* createEditor() override { return nullptr; }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return "Default"; }
    void changeProgramName(int,const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock& dest) override {
        juce::MemoryOutputStream stream(dest,false);stream.writeFloat(gain->get());
    }
    void setStateInformation(const void* data,int size) override {
        if (size==4) { juce::MemoryInputStream stream(data,static_cast<size_t>(size),false);
            const float value=stream.readFloat();if (std::isfinite(value)) gain->setValueNotifyingHost(juce::jlimit(0.0f,1.0f,value)); }
    }
private:
    juce::AudioParameterFloat* gain=nullptr;
};

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new Fixture(); }
