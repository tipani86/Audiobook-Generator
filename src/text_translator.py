# Translate text from one language to another using Azure Cognitive Services

import os
import uuid
import argparse
import requests
from glob import glob
from tqdm import tqdm
from functools import partial
from multiprocessing.pool import ThreadPool as Pool

def process_single_file(
    input_fn: str,
    output_dir: str,
    call_url: str,
    params: dict,
    headers: dict,
    debug: bool=False
) -> dict:
    res = {'status': 0, 'message': "Success"}

    with open(input_fn, "r") as f:
        input_text = f.read()

    body = [{
        'text': input_text
    }]

    # Call the Azure API

    request = requests.post(call_url, params=params, headers=headers, json=body)
    response = request.json()
    
    if 'error' in response:
        res['status'] = response['error']['code']
        res['message'] = response['error']['message']
        raise Exception(f"Error processing {input_fn}: Code {res['status']}, {res['message']}")

    # Ready for output

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)  # To work with multiprocessing
    base, ext = os.path.splitext(os.path.basename(file))

    # Write the output per language

    for translation in response[0]["translations"]:
        lang = translation["to"]
        translated_text = translation["text"]

        out_fn = os.path.join(output_dir, f"{base}_{lang}{ext}")

        with open(out_fn, "w") as f:
            f.write(translated_text)

        if debug:
            print(f"Successfully written {out_fn}")

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate text from one language to another using Azure Cognitive Services")
    parser.add_argument("input", help="The input file or directory to translate")
    parser.add_argument("-o", "--output", help="The output directory to write to", default="_output")
    parser.add_argument("-s", "--source", help="The source language to translate from", default="en")
    parser.add_argument("-t", "--target", nargs="*", help="The target language(s) to translate to", default=["zh-Hans"])
    parser.add_argument("--azure_region", help="The Azure region to use", default="northeurope")
    parser.add_argument("--azure_endpoint", help="The Azure endpoint to use", default="https://api.cognitive.microsofttranslator.com")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()

    # Get Azure credentials from arguments and environment variables
    
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

    if args.debug:
        res = []
        for file in tqdm(files, ascii=True, desc="Processing files"):
            res.append(
                process_single_file(
                    file,
                    args.output,
                    call_url,
                    params,
                    headers,
                    args.debug
                )
            )
    else:
        with Pool() as p:
            res = list(tqdm(p.imap_unordered(
                partial(
                    process_single_file, 
                    output_dir=args.output,
                    call_url=call_url,
                    params=params,
                    headers=headers
                ), files), total=len(files), ascii=True, desc="Processing files"))
        p.join()

    # Check results

    for item in res:
        if res['status'] != 0:
            print(f"Error: {res['message']}")
            exit(2)
    
    print(f"Successfully translated {len(res)} files from '{args.input}', outputs in '{args.output}' directory.")
    exit(0)