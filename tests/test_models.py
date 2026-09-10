from pdf_ocr_reader.models import PageHit, RenderedPage, Span


def test_span_is_frozen_with_text_and_bbox():
    s = Span(text="reactor", bbox=(10.0, 20.0, 90.0, 32.0))
    assert s.text == "reactor"
    assert s.bbox == (10.0, 20.0, 90.0, 32.0)


def test_rendered_page_carries_png_bytes_and_dimensions():
    r = RenderedPage(png_bytes=b"\x89PNG", width=1240, height=1754, dpi=150)
    assert r.png_bytes.startswith(b"\x89PNG")
    assert (r.width, r.height, r.dpi) == (1240, 1754, 150)


def test_page_hit_holds_index_snippet_and_span_bboxes():
    h = PageHit(page_index=3, snippet="...feed to the reactor...", span_bboxes=[(1.0, 2.0, 3.0, 4.0)])
    assert h.page_index == 3
    assert "reactor" in h.snippet
    assert h.span_bboxes == [(1.0, 2.0, 3.0, 4.0)]


def test_span_round_trips_through_dict():
    s = Span(text="corrosion at the nozzle", bbox=(12.5, 30.0, 400.0, 55.0))
    assert Span.from_dict(s.as_dict()) == s
    assert s.as_dict() == {"text": "corrosion at the nozzle", "bbox": [12.5, 30.0, 400.0, 55.0]}
