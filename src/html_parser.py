# Parses an e-book or other kind of HTML input to various elements

import os
import argparse
from bs4 import BeautifulSoup

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse an HTML file")
    parser.add_argument("input", help="The HTML file to parse")
    parser.add_argument("-c", "--chapter-tag", help="The anchor/tag to identify chapters with", default="chapter")
    parser.add_argument("-t", "--title-tag", help="The anchor/tag to identify titles with", default="h1")
    parser.add_argument("-o", "--output", help="The output directory to write to", default="_output")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"The input file {args.input} does not exist.")
        exit(2)

    with open(args.input, "r") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Parse title

    title = list(soup.find(args.title_tag).strings)
    title = "\n".join(title)

    # Parsing chapters is slightly more difficult, we need to find a match of the chapter tag within the anchor name

    chapters = []

    divs = soup.find_all("div")
    for div in divs:
        if "id" in div.attrs and args.chapter_tag in div.attrs["id"]:
            lines = list(div.strings)
            chapters.append("".join(lines))

    if not os.path.isdir(args.output):
        os.makedirs(args.output)

    # Generate text outputs

    for i, chapter in enumerate(chapters):
        out_fn = os.path.join(args.output, f"chapter_{i+1}.txt")

        output = "\n".join([title, chapter])

        with open(out_fn, "w") as f:
            f.write(output)

    print(f"Successfully parsed {len(chapters)} chapters for '{args.input}', output in '{args.output}' directory.")
    exit(0)