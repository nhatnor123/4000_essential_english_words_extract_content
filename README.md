# 4000 Essential English Words - Passage Extractor

This project provides a robust, fully automated Python script (`extract_passages.py`) designed to extract reading passages and bold their target vocabulary words from the *"4000 Essential English Words"* PDF book series.

## Features

- **Automated ToC Parsing**: Scans the Table of Contents to automatically discover the target vocabulary words for all 30 units in the book.
- **Smart Keyword Bolding**: Uses case-insensitive regex with morphology support (plurals, past tense, irregular verbs, '-ing' forms, etc.) to accurately bold all target keywords in the extracted text.
- **Page-Based Extraction**: Uses a highly robust page-level parsing strategy (based on `pdftotext` form-feeds) to cleanly locate passages right before the exercise sections, completely eliminating the need for hardcoded line numbers.
- **Noise Filtering**: Automatically cleans out OCR artifacts, page numbers, and exercise headings from the extracted titles and text.
- **Markdown Output**: Generates clean, formatted Markdown (`.md`) files containing all 30 stories with their titles and bolded keywords.

## Prerequisites

- **Python 3.x**
- **poppler-utils**: The script relies on `pdftotext` to convert PDFs into parsable text.
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - macOS: `brew install poppler`

## Usage

Run the script by passing the PDF file as an argument. You can optionally specify an output Markdown file name.

```bash
python3 extract_passages.py "<path_to_pdf>" [output_file.md]
```

### Example:

```bash
python3 extract_passages.py "[PDF] 4000 english words volume 3.pdf"
```

If the output file is not specified, it will automatically detect the volume number from the PDF name and generate an output file like `reading_passages_v3.md` in the same directory.

## How it Works

1. **PDF Conversion**: Uses `pdftotext` to convert the book into a raw text file (`*_raw.txt`).
2. **Vocabulary Extraction**: Parses the first few pages (ToC) to find comma-separated lists of target words for all units.
3. **Passage Location**: Splits the text by form-feed (`\f`) characters into pages. It finds pages containing "Mark each statement" or "Answer the questions" (exercise pages) and grabs the immediately preceding page, which always contains the reading passage.
4. **Formatting**: Cleans the title and text, applies the keyword bolding regex, and writes to Markdown.
5. **Cleanup**: Automatically deletes the intermediate `*_raw.txt` file.

## Supported Books

The script is generically written and successfully tested on:
- 4000 Essential English Words Volume 2
- 4000 Essential English Words Volume 3
- 4000 Essential English Words Volume 4
- 4000 Essential English Words Volume 5
- 4000 Essential English Words Volume 6

It should work seamlessly on any other volumes in the series that follow the same layout.
