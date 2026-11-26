# PDF Table Extractor

Save the script as `pdf_table_extractor.py`. It reads a local PDF without modifying it and writes one UTF-8 CSV per detected table. Each successful write is reported on stdout with its row and column counts.

## Install

    python -m pip install pdfplumber

Help works without pdfplumber. If the dependency is missing, extraction exits non-zero before creating any output.

## Usage

    python pdf_table_extractor.py --help
    python pdf_table_extractor.py report.pdf
    python pdf_table_extractor.py "annual report.pdf" --pages 1-3,5 --out-dir tables --min-rows 3

By default, the tool checks every page, keeps tables with at least one row, and writes to the current directory. Page selections are one-based and inclusive; overlapping selections are processed only once. An out-of-range page is an error.

For `report.pdf`, the second detected table on page 5 is `report-p5-t2.csv`. Table numbers restart on each page and do not change when earlier tables are filtered out. Row counts include any detected header rows. Missing cells are empty, and shorter rows are padded to the table's widest row.

## Limits

- Detection uses pdfplumber's default table settings, not OCR. Image-only pages, borderless tables, and complex layouts may yield no tables or inaccurate boundaries. Tables spanning pages are not joined.
- No matching tables is a successful result. Existing files are never overwritten; if a later table fails, previously completed CSVs remain.
- CSV fields preserve extracted text, including embedded line breaks. When opening untrusted results in a spreadsheet, import columns as text to avoid evaluating formula-like cells.
