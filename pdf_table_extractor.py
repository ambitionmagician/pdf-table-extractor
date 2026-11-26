#!/usr/bin/env python3
"""Extract tables from a PDF into separate UTF-8 CSV files."""

import argparse
import csv
import importlib
import re
import sys
from pathlib import Path


def parse_pages(value):
    """Parse a one-based page selection without expanding large ranges."""
    ranges = []
    for item in value.split(","):
        match = re.fullmatch(r"([0-9]+)(?:\s*-\s*([0-9]+))?", item.strip())
        if not match:
            raise argparse.ArgumentTypeError("expected page numbers or ranges, e.g. 1-3,5")
        start = int(match[1])
        end = int(match[2]) if match[2] is not None else start
        if not 1 <= start <= end:
            raise argparse.ArgumentTypeError("pages start at 1 and ranges must be ascending")
        ranges.append((start, end))

    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def positive_int(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return number


def write_table(path, rows, width):
    """Write rows to *path* with exclusive creation; remove partial output on failure."""
    created = False
    try:
        with path.open("x", encoding="utf-8", newline="") as stream:
            created = True
            writer = csv.writer(stream)
            for row in rows:
                writer.writerow(list(row) + [""] * (width - len(row)))
    except BaseException:
        if created:
            try:
                path.unlink()
            except OSError:
                pass
        raise


def extract(pdfplumber, args):
    if not args.pdf.is_file():
        raise FileNotFoundError(f"not a file: {args.pdf}")

    if args.out_dir.exists() and not args.out_dir.is_dir():
        raise NotADirectoryError(f"output destination is not a directory: {args.out_dir}")

    written = 0
    with pdfplumber.open(str(args.pdf)) as pdf:
        count = len(pdf.pages)
        ranges = args.pages or [(1, count)]
        if ranges[-1][1] > count:
            raise ValueError(f"requested page {ranges[-1][1]}, but the PDF has {count} pages")

        for start, end in ranges:
            for number in range(start, end + 1):
                page = pdf.pages[number - 1]
                try:
                    tables = page.extract_tables() or []
                    for index, rows in enumerate(tables, start=1):
                        if len(rows) < args.min_rows:
                            continue
                        width = max(map(len, rows))
                        if not written:
                            args.out_dir.mkdir(parents=True, exist_ok=True)
                        path = args.out_dir / f"{args.pdf.stem}-p{number}-t{index}.csv"
                        write_table(path, rows, width)
                        written += 1
                        print(f"{path}: {len(rows)} rows, {width} columns")
                except Exception as exc:
                    raise RuntimeError(f"page {number}: {exc}") from exc
                finally:
                    # Recent pdfplumber releases can release per-page caches.
                    close = getattr(page, "close", None)
                    if close is not None:
                        close()

    if not written:
        print("No tables matched the selection.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="input PDF (opened read-only)")
    parser.add_argument("--pages", type=parse_pages, metavar="LIST",
                        help="one-based pages and inclusive ranges, e.g. 1-3,5 (default: all)")
    parser.add_argument("--out-dir", type=Path, default=Path("."),
                        help="CSV destination directory (default: current directory)")
    parser.add_argument("--min-rows", type=positive_int, default=1, metavar="N",
                        help="skip tables with fewer than N rows (default: 1)")
    args = parser.parse_args(argv)

    try:
        pdfplumber = importlib.import_module("pdfplumber")
    except ImportError as exc:
        print(f"Cannot import pdfplumber: {exc}\n"
              "Install it in this Python environment: python -m pip install pdfplumber",
              file=sys.stderr)
        return 1

    try:
        extract(pdfplumber, args)
    except KeyboardInterrupt:
        print("Extraction interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        # Parser backends raise several different errors for malformed PDFs.
        print(f"Extraction failed for {args.pdf}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
