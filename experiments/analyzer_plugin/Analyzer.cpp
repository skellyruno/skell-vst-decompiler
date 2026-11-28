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
        setSize(800,530);
        title.setText("SKELL ANALYZER",juce::dontSendNotification);
        title.setFont(juce::Font(juce::FontOptions(23.f,juce::Font::bold)));
        title.setColour(juce::Label::textColourId,juce::Colour(0xffa9eecc));
        addAndMakeVisible(title);addAndMakeVisible(meter);addAndMakeVisible(open);addAndMakeVisible(report);
        addAndMakeVisible(pythonButton);addAndMakeVisible(findButton);addAndMakeVisible(stopButton);
        stopButton.setEnabled(false);
        report.setMultiLine(true);report.setReadOnly(true);report.setScrollbarsShown(true);
        report.setColour(juce::TextEditor::backgroundColourId,juce::Colour(0xff151a1c));
        report.setColour(juce::TextEditor::textColourId,juce::Colour(0xffe7e9e9));
        report.setText("DSP discovery: select a trusted Python interpreter with the Skell worker installed and GNU or LLVM objdump on PATH. Then choose an inner Windows x64 VST3/DLL/EPL module. The separate worker ranks likely DSP regions without loading the target. Candidate scores are not recovered algorithms.\n\nThe audio path remains transparent. Existing parameter-sweep reports can also be opened here.",false);
        open.onClick=[this]{chooseReport();};
        pythonButton.onClick=[this]{choosePython();};
        findButton.onClick=[this]{chooseTarget();};
        stopButton.onClick=[this]{cancelDiscovery();};
        startTimerHz(12);
    }
    ~AnalyzerEditor() override {
        stopTimer();
        chooser.reset();
        if(worker&&worker->isRunning())worker->kill();
        if(outputFile.existsAsFile())outputFile.deleteFile();
    }
    void paint(juce::Graphics& g) override {g.fillAll(juce::Colour(0xff101416));}
    void resized() override {
        auto r=getLocalBounds().reduced(18);title.setBounds(r.removeFromTop(35));
        auto row=r.removeFromTop(38);open.setBounds(row.removeFromLeft(182).reduced(0,3));meter.setBounds(row.reduced(10,0));
        auto actions=r.removeFromTop(38);
        pythonButton.setBounds(actions.removeFromLeft(225).reduced(0,3));
        actions.removeFromLeft(8);findButton.setBounds(actions.removeFromLeft(180).reduced(0,3));
        actions.removeFromLeft(8);stopButton.setBounds(actions.removeFromLeft(90).reduced(0,3));
        r.removeFromTop(8);report.setBounds(r);
    }
private:
    void timerCallback() override {
        const float p=processor.peak.load(std::memory_order_relaxed);
        const float db=juce::Decibels::gainToDecibels(p,-120.f);
        meter.setText("Live block peak: "+juce::String(db,1)+" dBFS",juce::dontSendNotification);
        if(worker){
            if(worker->isRunning()){
                if(juce::Time::getMillisecondCounterHiRes()-startedAt>180000.0)cancelDiscovery();
            }else{
                const auto exit=worker->getExitCode();
                worker.reset();
                if(outputFile.existsAsFile())showReport(outputFile);
                else report.setText("Worker returned no report (exit "+juce::String(static_cast<int>(exit))+"). Check the installed Python package and objdump PATH.",false);
                if(outputFile.existsAsFile())outputFile.deleteFile();
                outputFile=juce::File{};
                setBusy(false);
            }
        }
    }
    void setBusy(bool busy){
        pythonButton.setEnabled(!busy);findButton.setEnabled(!busy);
        open.setEnabled(!busy);stopButton.setEnabled(busy);
    }
    void showReport(const juce::File& file){
        if(!file.existsAsFile()||file.getSize()<=0||file.getSize()>512*1024){
            report.setText("Report size is unsupported.",false);return;
        }
        auto parsed=juce::JSON::parse(file.loadFileAsString());
        if(!parsed.isObject()){report.setText("Expected a JSON object.",false);return;}
        report.setText(juce::JSON::toString(parsed),false);
    }
    void choosePython(){
        if(worker)return;
        chooser=std::make_unique<juce::FileChooser>("Choose your trusted Python executable",juce::File{},"*.exe");
        chooser->launchAsync(juce::FileBrowserComponent::openMode|juce::FileBrowserComponent::canSelectFiles,
            [safe=juce::Component::SafePointer<AnalyzerEditor>(this)](const juce::FileChooser& fc){
                if(safe==nullptr)return;
                const auto file=fc.getResult();if(!file.existsAsFile())return;
                safe->pythonExecutable=file;
                safe->report.setText("Python selected. Choose Find DSP to analyze a module. Only use an interpreter you trust with the Skell package installed.",false);
            });
    }
    void chooseTarget(){
        if(worker)return;
        if(!pythonExecutable.existsAsFile()){report.setText("Select your trusted Python executable first.",false);return;}
        chooser=std::make_unique<juce::FileChooser>("Choose an inner Windows x64 plugin module",juce::File{},"*.vst3;*.dll;*.epl");
        chooser->launchAsync(juce::FileBrowserComponent::openMode|juce::FileBrowserComponent::canSelectFiles,
            [safe=juce::Component::SafePointer<AnalyzerEditor>(this)](const juce::FileChooser& fc){
                if(safe==nullptr)return;
                const auto file=fc.getResult();if(!file.existsAsFile())return;
                safe->startDiscovery(file);
            });
    }
    void startDiscovery(const juce::File& file){
        if(worker||!pythonExecutable.existsAsFile()||!file.existsAsFile())return;
        outputFile=juce::File::getSpecialLocation(juce::File::tempDirectory)
            .getChildFile("skell-dsp-"+juce::Uuid().toString()+".json");
        if(outputFile.exists()){report.setText("Temporary report collision; retry.",false);return;}
        juce::StringArray args{pythonExecutable.getFullPathName(),"-I","-m","skell_vst_decompiler.dsp_job",
            "--binary",file.getFullPathName(),"--output",outputFile.getFullPathName()};
        worker=std::make_unique<juce::ChildProcess>();
        if(!worker->start(args,0)){
            worker.reset();outputFile=juce::File{};
            report.setText("Could not launch the selected interpreter.",false);return;
        }
        startedAt=juce::Time::getMillisecondCounterHiRes();setBusy(true);
        report.setText("Finding candidate DSP regions in "+file.getFileName()+"...\nThe target is not executed. You can stop the scan.",false);
    }
    void cancelDiscovery(){
        if(!worker)return;
        if(worker->isRunning()&&!worker->kill()){
            report.setText("Worker could not be stopped. It is still being monitored.",false);return;
        }
        worker.reset();
        if(outputFile.existsAsFile())outputFile.deleteFile();
        outputFile=juce::File{};setBusy(false);
        report.setText("Discovery cancelled or timed out.",false);
    }
    void chooseReport() {
        chooser=std::make_unique<juce::FileChooser>("Open private analyzer report",juce::File{},"*.json");
        chooser->launchAsync(juce::FileBrowserComponent::openMode|juce::FileBrowserComponent::canSelectFiles,
            [safe=juce::Component::SafePointer<AnalyzerEditor>(this)](const juce::FileChooser& fc){
                if(safe==nullptr)return;
                auto file=fc.getResult();if(!file.existsAsFile())return;
                safe->showReport(file);
            });
    }
    Analyzer& processor;
    juce::Label title,meter;
    juce::TextButton open{"Open worker report"},pythonButton{"Select Python worker"},findButton{"Find DSP"},stopButton{"Stop"};
    juce::TextEditor report;
    std::unique_ptr<juce::FileChooser> chooser;
    std::unique_ptr<juce::ChildProcess> worker;
    juce::File pythonExecutable,outputFile;
    double startedAt=0.0;
};

juce::AudioProcessorEditor* Analyzer::createEditor(){return new AnalyzerEditor(*this);}
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter(){return new Analyzer();}
