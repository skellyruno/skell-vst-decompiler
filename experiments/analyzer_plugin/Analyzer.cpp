// Original read-only report viewer and transparent signal observer.
// Heavy analysis stays in the isolated offline worker, never in processBlock.
#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_basics/juce_gui_basics.h>
#include <atomic>
#include <cmath>
#include <memory>

class AnalyzerEditor;
class Analyzer final : public juce::AudioProcessor {
public:
    Analyzer() : AudioProcessor(BusesProperties().withInput("Input",juce::AudioChannelSet::stereo(),true)
                                                  .withOutput("Output",juce::AudioChannelSet::stereo(),true)) {}
    const juce::String getName() const override { return "Skell Analyzer"; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0; }
    bool isBusesLayoutSupported(const BusesLayout& layouts) const override {
        auto in=layouts.getMainInputChannelSet();auto out=layouts.getMainOutputChannelSet();
        return in==out && (in==juce::AudioChannelSet::mono() || in==juce::AudioChannelSet::stereo());
    }
    void prepareToPlay(double,int) override { peak.store(0,std::memory_order_relaxed); }
    void releaseResources() override {}
    void processBlock(juce::AudioBuffer<float>& b,juce::MidiBuffer&) override {
        float p=0;
        for(int c=0;c<getTotalNumInputChannels() && c<b.getNumChannels();++c){
            auto* x=b.getReadPointer(c);
            for(int i=0;i<b.getNumSamples();++i)if(std::isfinite(x[i]))p=juce::jmax(p,std::abs(x[i]));
        }
        for(int c=getTotalNumInputChannels();c<b.getNumChannels();++c)b.clear(c,0,b.getNumSamples());
        peak.store(p,std::memory_order_relaxed);
    }
    bool hasEditor() const override { return true; }
    juce::AudioProcessorEditor* createEditor() override;
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return "Default"; }
    void changeProgramName(int,const juce::String&) override {}
    void getStateInformation(juce::MemoryBlock& dest) override { dest.reset(); }
    void setStateInformation(const void*,int) override {}
    static_assert(std::atomic<float>::is_always_lock_free,"Meter must be lock free");
    std::atomic<float> peak{0};
};

class AnalyzerEditor final : public juce::AudioProcessorEditor, private juce::Timer {
public:
    explicit AnalyzerEditor(Analyzer& owner) : AudioProcessorEditor(owner),processor(owner) {
        setSize(740,500);
        title.setText("SKELL ANALYZER",juce::dontSendNotification);
        title.setFont(juce::Font(juce::FontOptions(23.f,juce::Font::bold)));
        title.setColour(juce::Label::textColourId,juce::Colour(0xffa9eecc));
        addAndMakeVisible(title);addAndMakeVisible(meter);addAndMakeVisible(open);addAndMakeVisible(report);
        report.setMultiLine(true);report.setReadOnly(true);report.setScrollbarsShown(true);
        report.setColour(juce::TextEditor::backgroundColourId,juce::Colour(0xff151a1c));
        report.setColour(juce::TextEditor::textColourId,juce::Colour(0xffe7e9e9));
        report.setText("Use the offline Skell analyzer_worker inventory or sweep command on a trusted, licensed installation. Then open its JSON report here.\n\nThis VST3 passes audio through unchanged. It never loads or analyzes a target binary inside the DAW process.",false);
        open.onClick=[this]{chooseReport();};startTimerHz(12);
    }
    void paint(juce::Graphics& g) override {g.fillAll(juce::Colour(0xff101416));}
    void resized() override {
        auto r=getLocalBounds().reduced(18);title.setBounds(r.removeFromTop(35));
        auto row=r.removeFromTop(38);open.setBounds(row.removeFromLeft(182).reduced(0,3));meter.setBounds(row.reduced(10,0));
        r.removeFromTop(8);report.setBounds(r);
    }
private:
    void timerCallback() override {
        const float p=processor.peak.load(std::memory_order_relaxed);
        const float db=juce::Decibels::gainToDecibels(p,-120.f);
        meter.setText("Live block peak: "+juce::String(db,1)+" dBFS",juce::dontSendNotification);
    }
    void chooseReport() {
        chooser=std::make_unique<juce::FileChooser>("Open private analyzer report",juce::File{},"*.json");
        chooser->launchAsync(juce::FileBrowserComponent::openMode|juce::FileBrowserComponent::canSelectFiles,
            [safe=juce::Component::SafePointer<AnalyzerEditor>(this)](const juce::FileChooser& fc){
                if(safe==nullptr)return;
                auto file=fc.getResult();if(!file.existsAsFile())return;
                if(file.getSize()<=0 || file.getSize()>512*1024){safe->report.setText("Report size is unsupported.",false);return;}
                auto parsed=juce::JSON::parse(file.loadFileAsString());
                if(!parsed.isObject()){safe->report.setText("Expected a JSON object.",false);return;}
                safe->report.setText(juce::JSON::toString(parsed),false);
            });
    }
    Analyzer& processor;
    juce::Label title,meter;
    juce::TextButton open{"Open worker report"};
    juce::TextEditor report;
    std::unique_ptr<juce::FileChooser> chooser;
};

juce::AudioProcessorEditor* Analyzer::createEditor(){return new AnalyzerEditor(*this);}
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter(){return new Analyzer();}
