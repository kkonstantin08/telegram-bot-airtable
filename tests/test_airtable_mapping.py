from artbot.airtable_repository import _extract_image_url, _record_to_artwork, _to_text
from artbot.config import AirtableFieldMapping


FIELDS = AirtableFieldMapping(
    row_id="Row Number",
    title="Title",
    author="Author",
    technique="Technique",
    size="Size",
    year="Year",
    price="Price",
    image="Image",
)


def test_record_to_artwork_maps_configured_fields() -> None:
    record = {
        "id": "rec123",
        "fields": {
            "Title": "Object",
            "Author": "Artist",
            "Technique": "Canvas",
            "Size": "10 x 20",
            "Year": 2026,
            "Price": 1000,
            "Image": [{"url": "https://example.com/image.jpg"}],
        },
    }

    artwork = _record_to_artwork(record, row_id=7, fields=FIELDS)

    assert artwork.row_id == 7
    assert artwork.title == "Object"
    assert artwork.author == "Artist"
    assert artwork.year == "2026"
    assert artwork.price == "1000"
    assert artwork.image_url == "https://example.com/image.jpg"
    assert artwork.airtable_record_id == "rec123"


def test_to_text_handles_empty_and_list_values() -> None:
    assert _to_text(None) is None
    assert _to_text("  ") is None
    assert _to_text(["A", "B"]) == "A, B"


def test_extract_image_url_supports_attachment_and_text_url() -> None:
    assert _extract_image_url([{"url": "https://example.com/a.jpg"}]) == "https://example.com/a.jpg"
    assert _extract_image_url(" https://example.com/b.jpg ") == "https://example.com/b.jpg"
    assert _extract_image_url([]) is None
