import fitz

from pdf_ocr_reader.document import Document
from pdf_ocr_reader.search import search


def test_single_term_finds_the_right_pages(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        hits = search(doc, "reactor")
    pages = {h.page_index for h in hits}
    assert pages == {0, 1}
    assert all("reactor" in h.snippet.lower() for h in hits)


def test_ranks_page_with_more_occurrences_first(tmp_path):
    p = tmp_path / "rank.pdf"
    d = fitz.open()
    d.new_page().insert_text((72, 72), "pompa sekali saja disebut")
    d.new_page().insert_text((72, 72), "pompa pompa pompa tiga kali")
    d.save(str(p))
    d.close()

    with Document.open(str(p)) as doc:
        hits = search(doc, "pompa")
    assert [h.page_index for h in hits] == [1, 0]


def test_and_of_terms_requires_all_on_the_page(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        hits = search(doc, "reactor monitoring")
    assert [h.page_index for h in hits] == [1]


def test_hit_carries_matching_span_bboxes(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        hits = search(doc, "reactor")
    first = next(h for h in hits if h.page_index == 0)
    assert first.span_bboxes
    for x0, y0, x1, y1 in first.span_bboxes:
        assert x1 > x0 and y1 > y0


def test_blank_query_returns_nothing(born_digital_pdf):
    with Document.open(born_digital_pdf) as doc:
        assert search(doc, "   ") == []
