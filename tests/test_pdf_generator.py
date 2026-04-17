from artbot.domain import Artwork
from artbot.pdf_generator import _artwork_text_lines, generate_artwork_pdf, generate_artworks_pdf


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
