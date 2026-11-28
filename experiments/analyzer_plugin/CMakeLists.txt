cmake_minimum_required(VERSION 3.22)
project(SkellAnalyzer VERSION 0.2.0 LANGUAGES C CXX)
if(NOT TARGET juce::juce_audio_processors)
    if(NOT DEFINED JUCE_DIR)
        message(FATAL_ERROR "Pass -DJUCE_DIR=<checked-out JUCE source>")
    endif()
    add_subdirectory("${JUCE_DIR}" juce)
endif()
juce_add_plugin(SkellAnalyzer
    COMPANY_NAME "Skell Research"
    PLUGIN_MANUFACTURER_CODE Skll
    PLUGIN_CODE SAnl
    PRODUCT_NAME "Skell Analyzer"
    VERSION 0.2.0
    FORMATS VST3
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
    COPY_PLUGIN_AFTER_BUILD FALSE)
target_sources(SkellAnalyzer PRIVATE Analyzer.cpp)
target_compile_features(SkellAnalyzer PRIVATE cxx_std_17)
target_compile_definitions(SkellAnalyzer PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries(SkellAnalyzer PRIVATE juce::juce_audio_processors juce::juce_gui_basics juce::juce_recommended_config_flags)
