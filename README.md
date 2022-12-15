# Audiobook-Generator
Generate audiobooks from input text with optional translation in between. Using Azure Cognitive Services: Language and Speech.

## Setup

1. `pip3 install -r requirements.txt`
2. Set up an environment variable called `RESOURCE_KEY` which is your Azure Cognitive Services API authentication key

## Azure Free Tier Limits

* Translation: 2M chars of any combination of standard translation and custom training free per month
* Voice Synthesis: 0.5 million characters free per month
