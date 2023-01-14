# Audiobook Generator
Generate audiobooks from input text with optional translation in between. Using Azure Cognitive Services: Language and Speech.

## Setup

1. `pip3 install -r requirements.txt`
2. Set up two environment variables called `TRANSLATOR_KEY` and `SPEECH_KEY` which are your Azure authentication keys for the translator and speech cognitive services, respectively.

In addition to the Python package requirements, speech synthesis requires additional prerequisites as per the [Azure documentation](https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/get-started-text-to-speech?pivots=programming-language-python):

* You must install the [Microsoft Visual C++ Redistributable for Visual Studio 2015, 2017, 2019, and 2022](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) for your platform. Installing this package for the first time might require a restart.
* On Linux, you must use the x64 target architecture.


## Azure Free Tier Limits Notice

* Translation: 2M chars of any combination of standard translation and custom training free per month
* Voice Synthesis: 0.5 million characters free per month
