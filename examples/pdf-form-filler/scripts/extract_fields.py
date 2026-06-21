#!/usr/bin/env python3
"""提取 PDF 表单的所有字段信息"""

import sys
import json
from pathlib import Path


def extract_fields(pdf_path: str) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError:
        print(json.dumps(
            {"error": "pypdf not installed", "fix": "pip install pypdf"},
            ensure_ascii=False, indent=2
        ))
        sys.exit(1)

    if not Path(pdf_path).exists():
        print(json.dumps(
            {"error": f"File not found: {pdf_path}"},
            ensure_ascii=False, indent=2
        ))
        sys.exit(1)

    reader = PdfReader(pdf_path)

    if reader.is_encrypted:
        print(json.dumps(
            {"error": "PDF is encrypted", "fix": "Decrypt first or provide password"},
            ensure_ascii=False, indent=2
        ))
        sys.exit(1)

    fields = reader.get_fields() or {}

    result = {
        "file": pdf_path,
        "page_count": len(reader.pages),
        "field_count": len(fields),
        "fields": [
            {
                "name": name,
                "type": str(info.get("/FT", "unknown")).replace("/", ""),
                "required": bool(info.get("/Ff", 0) & 2),
                "value": info.get("/V", ""),
                "options": info.get("/Opt", None),
            }
            for name, info in fields.items()
        ]
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: extract_fields.py <pdf-path>")
        sys.exit(1)
    extract_fields(sys.argv[1])
