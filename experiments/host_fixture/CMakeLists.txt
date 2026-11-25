cmake_minimum_required(VERSION 3.22)
project(SkellHostFixture VERSION 1.0.0 LANGUAGES C CXX)
if(NOT DEFINED JUCE_DIR)
    message(FATAL_ERROR "Pass -DJUCE_DIR=<checked-out JUCE source>")
endif()
add_subdirectory("${JUCE_DIR}" juce)
juce_add_plugin(SkellHostFixture
    COMPANY_NAME "Skell Research"
    PLUGIN_MANUFACTURER_CODE Skll
    PLUGIN_CODE HstF
    PRODUCT_NAME "Skell Host Fixture"
    VERSION 1.0.0
    FORMATS VST3
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
    COPY_PLUGIN_AFTER_BUILD FALSE)
target_sources(SkellHostFixture PRIVATE Fixture.cpp)
target_compile_features(SkellHostFixture PRIVATE cxx_std_17)
target_compile_definitions(SkellHostFixture PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries(SkellHostFixture PRIVATE juce::juce_audio_processors juce::juce_recommended_config_flags)

# Share the pinned JUCE checkout with the original analyzer target.
add_subdirectory(../analyzer_plugin analyzer)

# Public numeric ParamID inventory, isolated executable; no hosting inside analyzer.
juce_add_console_app(SkellParamIds PRODUCT_NAME "SkellParamIds")
target_sources(SkellParamIds PRIVATE ParamIds.cpp)
target_compile_features(SkellParamIds PRIVATE cxx_std_17)
target_compile_definitions(SkellParamIds PRIVATE JUCE_PLUGINHOST_VST3=1 JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries(SkellParamIds PRIVATE juce::juce_audio_processors juce::juce_gui_basics juce::juce_cryptography juce::juce_recommended_config_flags)
