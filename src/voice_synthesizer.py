# Create long-form text-to-speech synthesis from text chapters using Azure Cognitive Services

import os
import json
import time
import requests
import argparse
from glob import glob
from tqdm import tqdm
from functools import partial
from multiprocessing.pool import ThreadPool as Pool
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_EXCEPTION

# From https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/rest-text-to-speech?tabs=streaming#audio-outputs
OUTPUT_AUDIO_FORMAT = "audio-48khz-192kbitrate-mono-mp3"

# Default to 15 minute limit for long-running downloads (4 simultaneous)
THREADPOOL_TIMEOUT = 900
N_DOWNLOAD_THREADS = 4


def submit_single_file(
    input_fn: str,
    call_url: str,
    config: dict,
    headers: dict,
    debug: bool = False
) -> dict:
    res = {'status': 0, 'message': "Success", 'job_id': None}

    with open(input_fn, "r") as f:
        input_text = f.read()

    payload = {
        'displayName': "Text to Voice Synthesis Batch Job",
        'description': input_fn,
        'textType': "PlainText",
        'synthesisConfig': config,
        'inputs': [{
            'text': input_text
        }],
        'properties': {
            'outputFormat': OUTPUT_AUDIO_FORMAT
        },
    }

    # Call the Azure API

    request = requests.post(call_url, headers=headers, json=payload)
    response = request.json()

    if request.status_code < 400:
        res['job_id'] = response['id']
        if debug:
            print(f"Successfully submitted {input_fn}, job_id: {res['job_id']}")
        return res

    res['status'] = request.status_code
    res['message'] = f"Error submitting {input_fn} to batch synthesis: {request.text}"
    raise Exception(f"Error processing {input_fn}: Code {res['status']}, {res['message']}")


def check_job_status(
    job_id: str,
    call_url: str,
    headers: dict,
    debug: bool = False
) -> dict:
    res = {'status': "", 'uri': None, 'input_fn': None}

    # Call the Azure API

    request = requests.get(f"{call_url}/{job_id}", headers=headers)
    response = request.json()

    if request.status_code < 400:
        res['status'] = response['status']
        if res['status'] == "Succeeded":
            res['uri'] = response['outputs']['result']
            res['input_fn'] = response['description']
        if debug:
            print(f"Status for {job_id}: {res['status']}, uri: {res['uri']}, input_fn: {res['input_fn']}")
        return res

    res['status'] = f"Error checking the status of job_id: {job_id}: {request.text}"
    return res


def download_file(
    job_id: str,
    uri: str,
    input_fn: str,
    output_dir: str,
    debug: bool = False
) -> dict:
    res = {'status': 0, 'message': "Success"}

    # Parse the output file extension from uri and form the output filename

    base, ext = os.path.splitext(os.path.basename(input_fn))
    out_ext = os.path.splitext(uri.split("?", 1)[0])[1]
    out_fn = os.path.join(output_dir, f"{base}_voice_synthesis{out_ext}")

    print(f"Downloading job {job_id} from {uri} to {out_fn}...")

    # Call the Azure API

    request = requests.get(uri)
    response = request.content

    if request.status_code < 400:

        # Save the file

        if not os.path.isdir(output_dir):
            os.makedirs(output_dir, exist_ok=True)  # To work with multiprocessing

        with open(out_fn, "wb") as f:
            f.write(response)

        if debug:
            print(f"Successfully downloaded job {job_id} to {out_fn}")

        return res

    res['status'] = request.status_code
    res['message'] = f"Error downloading job {job_id} from {uri} to {out_fn}: {request.text}"
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create text-to-speech synthesis from text chapters using Azure Cognitive Services")
    parser.add_argument("input", help="The input file or directory to synthesize")
    parser.add_argument("-o", "--output", help="The output directory to write to (default: _output)", default="_output")
    parser.add_argument("--config", help="The path to voice configuration json (default: cfg/bingbing.json", default="cfg/bingbing.json")
    parser.add_argument("--azure_region", help="The Azure region to use (default: northeurope)", default="northeurope")
    parser.add_argument("--azure_endpoint", help="The Azure endpoint to use (default: customvoice.api.speech.microsoft.com)", default="customvoice.api.speech.microsoft.com")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--list_only", action="store_true", help="Go straight to jobs listing and download mode")
    args = parser.parse_args()

    # Get Azure credentials from arguments and environment variables

    if "RESOURCE_KEY" not in os.environ:
        print("Please set the RESOURCE_KEY environment variable to use this script.")
        exit(2)

    azure_key = os.getenv("RESOURCE_KEY")

    azure_endpoint = f"https://{args.azure_region}.{args.azure_endpoint}"
    call_url = os.path.join(azure_endpoint, "api/texttospeech/3.1-preview1/batchsynthesis")

    headers = {
        "Ocp-Apim-Subscription-Key": azure_key,
        "Content-type": "application/json",
    }

    if args.list_only:
        print("Listing jobs...")
        request = requests.get(call_url, headers=headers)
        response = request.json()

        if request.status_code < 400:
            print(f"List batch synthesis jobs successfully, got {len(response['values'])} jobs:")
            print(json.dumps(response['values'], indent=4))
            exit(0)
        else:
            print(f"Error listing batch synthesis jobs: {request.text}")
            exit(2)

    # Read the input file/directory

    if os.path.isfile(args.input):
        files = [args.input]
    elif os.path.isdir(args.input):
        files = glob(os.path.join(args.input, "*.txt"))
    else:
        print(f"The input {args.input} does not exist.")
        exit(2)

    # Read the voice configuration file

    if not os.path.isfile(args.config):
        print(f"The voice configuration file {args.config} does not exist.")
        exit(2)

    with open(args.config, "r") as f:
        config = json.load(f)

    # Submit the input files to Azure for voice synthesis

    if args.debug:
        res = []
        for file in tqdm(files, ascii=True, desc="Submitting files"):
            res.append(
                submit_single_file(
                    file,
                    call_url,
                    config,
                    headers,
                    args.debug
                )
            )
    else:
        with Pool() as p:
            res = list(tqdm(p.imap_unordered(
                partial(
                    submit_single_file,
                    call_url=call_url,
                    config=config,
                    headers=headers
                ), files), total=len(files), ascii=True, desc="Submitting files"))
        p.join()

    # Collect both successful and failed submissions

    successful_submissions = {}
    failed_submissions = []

    for item in res:
        if item['status'] != 0:
            failed_submissions.append(res['message'])
        else:
            successful_submissions[item['job_id']] = check_job_status(item['job_id'], call_url, headers)

    # Display failed submissions, if any

    if len(failed_submissions) > 0:
        print(f"Warning! {len(failed_submissions)} failed submissions detected:")
        for item in failed_submissions:
            print(item)

    # Start a loop to check the status of the successful submissions and download via the threadpool executor

    executor = ThreadPoolExecutor(N_DOWNLOAD_THREADS)

    if len(successful_submissions) > 0:
        while True:
            n_success_jobs = 0
            if args.debug:
                print("Checking voice synthesis job status...")

            for job_id in successful_submissions:
                if args.debug:
                    print(f"{job_id}: {successful_submissions[job_id]['status']}")
                if successful_submissions[job_id]['status'] == "Succeeded":
                    if 'download_task' in successful_submissions[job_id]:
                        n_success_jobs += 1
                        continue
                    else:
                        successful_submissions[job_id]['download_task'] = executor.submit(
                            download_file,
                            job_id,
                            successful_submissions[job_id]['uri'],
                            successful_submissions[job_id]['input_fn'],
                            args.output,
                            args.debug
                        )
                        n_success_jobs += 1
                        continue
                else:
                    time.sleep(1)   # To avoid throttling
                    successful_submissions[job_id] = check_job_status(job_id, call_url, headers)

            # Break the loop if all jobs are successful
            if n_success_jobs == len(successful_submissions):
                break

            if args.debug:
                print("")

            time.sleep(10)  # The overall cycle doesn't need to be checked too often, every 10s is more than enough.

    # Collect all the download tasks and wait for them to finish

    download_tasks = []
    for job_id in successful_submissions:
        download_tasks.append(successful_submissions[job_id]['download_task'])

    download_task_res = wait(download_tasks, timeout=THREADPOOL_TIMEOUT, return_when=FIRST_EXCEPTION)

    if len(download_task_res.not_done) > 0:
        print(f"Download task timed out after {THREADPOOL_TIMEOUT} seconds.")
        exit(2)

    for task_res in download_task_res.done:
        res = task_res.result()
        if res['status'] != 0:
            print(res['message'])
            exit(res['status'])

    print(f"Successfully generated and downloaded {len(download_tasks)} voice syntheses from '{args.input}', outputs in '{args.output}' directory.")
    exit(0)
