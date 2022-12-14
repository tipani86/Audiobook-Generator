# Translate text from one language to another using Azure Cognitive Services

import os
import uuid
import argparse
import requests
from glob import glob

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate text from one language to another using Azure Cognitive Services")
    parser.add_argument("input", help="The input file or directory to translate")
    parser.add_argument("-o", "--output", help="The output directory to write to", default="_output")
    parser.add_argument("-s", "--source", help="The source language to translate from", default="en")
    parser.add_argument("-t", "--target", nargs="*", help="The target language(s) to translate to", default=["zh-Hans"])
    parser.add_argument("--azure_region", help="The Azure region to use", default="northeurope")
    parser.add_argument("--azure_endpoint", help="The Azure endpoint to use", default="https://api.cognitive.microsofttranslator.com")
    args = parser.parse_args()

    # Get Azure credentials from environment variables
    
    if "RESOURCE_KEY" not in os.environ:
        print("Please set the RESOURCE_KEY environment variable to use this script.")
        exit(2)

    azure_key = os.getenv("RESOURCE_KEY")

    azure_endpoint = args.azure_endpoint
    call_url = os.path.join(azure_endpoint, "translate")

    params = {
        "api-version": "3.0",
        "from": args.source,
        "to": args.target
    }

    headers = {
        "Ocp-Apim-Subscription-Key": azure_key,
        "Ocp-Apim-Subscription-Region": args.azure_region,
        "Content-type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4())
    }

    # Read the input file/directory

    if os.path.isfile(args.input):
        files = [args.input]
    elif os.path.isdir(args.input):
        files = glob(os.path.join(args.input, "*.txt"))
    else:
        print(f"The input {args.input} does not exist.")
        exit(2)

    for file in files:
        with open(file, "r") as f:
            input_text = f.read()

        body = [{
            "text": input_text
        }]

        # Call the Azure API

        request = requests.post(call_url, params=params, headers=headers, json=body)
        response = request.json()
        
        if "error" in response:
            print(f"Code: {response['error']['code']}, message: {response['error']['message']}")
            exit(2)

        # Ready for output

        if not os.path.isdir(args.output):
            os.makedirs(args.output)
        base, ext = os.path.splitext(os.path.basename(file))

        # Write the output per language

        for translation in response[0]["translations"]:
            lang = translation["to"]
            translated_text = translation["text"]

            out_fn = os.path.join(args.output, f"{base}_{lang}{ext}")

            with open(out_fn, "w") as f:
                f.write(translated_text)

            print(f"Successfully written {out_fn}")
    
    exit(0)