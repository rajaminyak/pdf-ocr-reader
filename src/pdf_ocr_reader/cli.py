from __future__ import annotations

import argparse
import os
import sys

from pdf_ocr_reader.document import Document, DocumentError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pdf-ocr-reader")
    sub = parser.add_subparsers(dest="command", required=True)

    info_p = sub.add_parser("info", help="Page count and per-page text-layer status")
    info_p.add_argument("pdf")

    ocr_p = sub.add_parser("ocr", help="OCR every image-only page and cache the result")
    ocr_p.add_argument("pdf")

    search_p = sub.add_parser("search", help="Search inside a PDF (OCRs image-only pages first)")
    search_p.add_argument("pdf")
    search_p.add_argument("query", nargs="+")
    search_p.add_argument("--no-ocr", action="store_true", help="search only existing text (skip OCR)")

    export_p = sub.add_parser("export", help="Write a Ctrl+F-searchable copy of the PDF")
    export_p.add_argument("pdf")
    export_p.add_argument("out")

    args = parser.parse_args(argv)

    if not os.path.isfile(args.pdf):
        print(f"File not found: {args.pdf}")
        return 1

    try:
        doc = Document.open(args.pdf)
    except DocumentError as exc:
        print(str(exc))
        return 1

    try:
        if args.command == "info":
            print(f"pages: {doc.page_count}")
            for i in range(doc.page_count):
                kind = "text layer" if doc.has_text_layer(i) else "image only"
                print(f"p.{i + 1}: {kind}")
            return 0

        if args.command == "ocr":
            done_count = {"n": 0}

            def _progress(done, total):
                done_count["n"] = done
                print(f"OCR {done}/{total}", file=sys.stderr)

            doc.ocr_all(progress=_progress)
            print(f"OCR complete: {done_count['n']} page(s)")
            return 0

        if args.command == "export":
            from pdf_ocr_reader.exporter import ExportError, save_searchable_pdf

            doc.ocr_all(progress=lambda d, t: print(f"OCR {d}/{t}", file=sys.stderr))
            try:
                save_searchable_pdf(doc, args.out)
            except ExportError as exc:
                print(str(exc))
                return 1
            print(f"Saved searchable copy: {args.out}")
            return 0

        from pdf_ocr_reader.search import search as run_search

        if not args.no_ocr:
            doc.ocr_all(progress=lambda d, t: print(f"OCR {d}/{t}", file=sys.stderr))

        hits = run_search(doc, " ".join(args.query), ocr=not args.no_ocr)
        print(f"{len(hits)} result(s)")
        for h in hits:
            print(f"p.{h.page_index + 1}  {h.snippet}")
        return 0
    finally:
        doc.close()


if __name__ == "__main__":
    raise SystemExit(main())
