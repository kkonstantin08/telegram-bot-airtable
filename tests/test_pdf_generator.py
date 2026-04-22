import pytest
from reportlab.platypus import KeepTogether, Spacer

from artbot.domain import Artwork
from artbot.pdf_generator import (
    _artwork_image_urls,
    _artwork_text_lines,
    _provenance_story,
    _section_images,
    _styles,
    generate_artwork_pdf,
    generate_artworks_pdf,
)


def test_pdf_generation_without_image_produces_pdf_bytes() -> None:
    artwork = Artwork(
        row_id=2,
        title="Без названия",
        author="Петр Орлов",
        technique="Бумага, тушь",
        size="42 x 30 см",
        year="2023",
        price="90 000 ₽",
        image_url=None,
    )

    pdf_bytes = generate_artwork_pdf(artwork)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_pdf_generation_with_missing_fields_does_not_fail() -> None:
    artwork = Artwork(row_id=3, title=None, author=None, image_url=None)

    pdf_bytes = generate_artwork_pdf(artwork)

    assert pdf_bytes.startswith(b"%PDF")


def test_pdf_generation_with_long_and_special_text_does_not_fail() -> None:
    artwork = Artwork(
        row_id=5,
        title="Очень длинное название объекта & серия <эксперимент> " * 8,
        author="Автор с длинным именем " * 6,
        technique="Смешанная техника, бумага, акрил, тушь, коллаж " * 6,
        size="120 x 80 см",
        year="2026",
        price="по запросу",
        image_url=None,
    )

    pdf_bytes = generate_artwork_pdf(artwork)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_pdf_text_lines_include_values_without_labels_or_price() -> None:
    artwork = Artwork(
        row_id=6,
        title="Object",
        author="Artist",
        technique="Canvas",
        size="10 x 20 cm",
        year="2026",
        price="999999",
        image_url=None,
        provenance="Catalogue text",
    )

    values = [value for value, _style in _artwork_text_lines(artwork)]

    assert values == ["Object", "Artist", "Canvas", "10 x 20 cm", "2026"]
    assert "999999" not in values
    assert "Автор" not in values
    assert "Техника" not in values
    assert "Размер" not in values
    assert "Год" not in values


def test_multi_artwork_pdf_generation_produces_pdf_bytes() -> None:
    artworks = [
        Artwork(row_id=1, title="First", author="Author"),
        Artwork(row_id=2, title="Second", author="Author"),
    ]

    pdf_bytes = generate_artworks_pdf(artworks)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_pdf_image_urls_prefer_all_airtable_images() -> None:
    artwork = Artwork(
        row_id=7,
        image_url="https://example.com/main.jpg",
        image_urls=(
            "https://example.com/main.jpg",
            "https://example.com/detail.jpg",
        ),
    )

    assert _artwork_image_urls(artwork) == (
        "https://example.com/main.jpg",
        "https://example.com/detail.jpg",
    )


def test_pdf_image_urls_fall_back_to_legacy_main_image() -> None:
    artwork = Artwork(row_id=8, image_url="https://example.com/main.jpg")

    assert _artwork_image_urls(artwork) == ("https://example.com/main.jpg",)


def test_provenance_story_keeps_title_with_first_text_block() -> None:
    story = _provenance_story("First paragraph\n\nSecond paragraph", _styles("Helvetica", "Helvetica-Bold"))

    assert isinstance(story[0], KeepTogether)
    assert len(story) > 2


def test_section_images_keep_title_with_first_image(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("artbot.pdf_generator._build_image", lambda *_args, **_kwargs: Spacer(1, 1))

    story = _section_images(
        "Section",
        ("https://example.com/first.jpg", "https://example.com/second.jpg"),
        4.0,
        _styles("Helvetica", "Helvetica-Bold"),
    )

    assert isinstance(story[0], KeepTogether)
    assert any(isinstance(flowable, Spacer) for flowable in story[1:])


def test_section_images_without_loaded_images_omits_title(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("artbot.pdf_generator._build_image", lambda *_args, **_kwargs: None)

    assert _section_images("Section", ("https://example.com/missing.jpg",), 4.0, _styles("Helvetica", "Helvetica-Bold")) == []
