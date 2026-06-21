#!/usr/bin/env python3
"""填写 PDF 表单"""

import sys
import json
import argparse
from pathlib import Path


def parse_field_args(args):
    fields = {}
    for arg in args:
        if "=" not in arg:
            continue
        name, value = arg.split("=", 1)
        fields[name] = value
    return fields


def fill_pdf(input_path: str, output_path: str, fields: dict):
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print(json.dumps({"error": "pypdf not installed"}))
        sys.exit(1)

    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.update_page_form_field_values(writer.pages[0], fields)

    with open(output_path, "wb") as f:
        writer.write(f)

    print(json.dumps(
        {
            "status": "ok",
            "input": input_path,
            "output": output_path,
            "fields_filled": len(fields),
            "field_names": list(fields.keys()),
        },
        ensure_ascii=False, indent=2
    ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--field", action="append", default=[])
    args = parser.parse_args()

    fields = parse_field_args(args.field)
    fill_pdf(args.input, args.output, fields)
