// Standalone public VST3 host parameter inventory. Explicit trusted owned bundle only.
#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_cryptography/juce_cryptography.h>
#include <iostream>
#include <set>
#include <cmath>
#include <memory>

int main(int argc,char** argv){
    if(argc!=4||juce::String(argv[1])!="--authorized-owned"){
        std::cerr<<"Usage: SkellParamIds --authorized-owned <absolute VST3 bundle> <module SHA256>\n";
        return 2;
    }
    const juce::String path=juce::String::fromUTF8(argv[2]),expected=juce::String::fromUTF8(argv[3]).toLowerCase();
    if(!juce::File::isAbsolutePath(path)||expected.length()!=64||!expected.containsOnly("0123456789abcdef"))return 2;
    const juce::File bundle(path);
    if(!bundle.isDirectory()||!bundle.hasFileExtension("vst3"))return 2;
    const auto module=bundle.getChildFile("Contents/x86_64-win").getChildFile(bundle.getFileName());
    if(!module.existsAsFile()||module.getSize()<=0||module.getSize()>256LL*1024*1024||
       juce::SHA256(module).toHexString()!=expected)return 2;
    juce::ScopedJuceInitialiser_GUI init;
    juce::AudioPluginFormatManager manager;
    manager.addFormat(std::make_unique<juce::VST3PluginFormat>());
    juce::OwnedArray<juce::PluginDescription> descriptions;
    manager.getFormat(0)->findAllTypesForFile(descriptions,bundle.getFullPathName());
    if(descriptions.size()!=1||descriptions[0]->isInstrument)return 3;
    juce::String error;
    auto instance=manager.createPluginInstance(*descriptions[0],48000.,256,error);
    if(!instance){std::cerr<<error<<'\n';return 3;}
    const int count=instance->getParameters().size();
    if(count<1||count>2048)return 4;
    juce::Array<juce::var> rows;
    std::set<juce::int64> seen;
    for(int i=0;i<count;++i){
        const auto* param=instance->getHostedParameter(i);
        if(!param)return 4;
        const auto id=param->getParameterID();
        if(id.isEmpty()||id.length()>10||!id.containsOnly("0123456789"))return 4;
        const auto n=id.getLargeIntValue();
        if(n<0||n>0xffffffffLL||!seen.insert(n).second)return 4;
        const double value=param->getValue(),def=param->getDefaultValue();
        if(!std::isfinite(value)||value<0||value>1||!std::isfinite(def)||def<0||def>1)return 4;
        auto* row=new juce::DynamicObject();
        row->setProperty("param_id",juce::var(n));
        row->setProperty("name",param->getName(256));
        row->setProperty("normalized",value);row->setProperty("default_normalized",def);
        row->setProperty("steps",param->getNumSteps());row->setProperty("automatable",param->isAutomatable());
        rows.add(juce::var(row));
    }
    const auto name=instance->getName();
    instance.reset();
    if(juce::SHA256(module).toHexString()!=expected)return 5;
    auto* report=new juce::DynamicObject();
    report->setProperty("type","public_vst3_param_ids");
    report->setProperty("module_sha256",expected);
    report->setProperty("name",name);report->setProperty("parameters",juce::var(rows));
    std::cout<<juce::JSON::toString(juce::var(report)).toStdString()<<'\n';
    return 0;
}
