from __future__ import annotations

import argparse
import os

from pdf_ocr_reader.document import Document, DocumentError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pdf-ocr-reader")
    sub = parser.add_subparsers(dest="command", required=True)

    info_p = sub.add_parser("info", help="Page count and per-page text-layer status")
    info_p.add_argument("pdf")

    search_p = sub.add_parser("search", help="Search inside a PDF (native text only in Phase 1)")
    search_p.add_argument("pdf")
    search_p.add_argument("query", nargs="+")

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

        from pdf_ocr_reader.search import search as run_search

        hits = run_search(doc, " ".join(args.query))
        print(f"{len(hits)} result(s)")
        for h in hits:
            print(f"p.{h.page_index + 1}  {h.snippet}")
        return 0
    finally:
        doc.close()


if __name__ == "__main__":
    raise SystemExit(main())
