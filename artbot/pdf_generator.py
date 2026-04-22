from __future__ import annotations

import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

import requests
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from artbot.domain import Artwork
from artbot.messages import MISSING_VALUE

logger = logging.getLogger(__name__)

PDF_TITLE = "Artwork card"


def generate_artwork_pdf(
    artwork: Artwork,
    request_timeout_seconds: float = 4.0,
    font_path: str | None = None,
    bold_font_path: str | None = None,
) -> bytes:
    return generate_artworks_pdf(
        [artwork],
        request_timeout_seconds=request_timeout_seconds,
        font_path=font_path,
        bold_font_path=bold_font_path,
    )


def generate_artworks_pdf(
    artworks: list[Artwork],
    request_timeout_seconds: float = 4.0,
    font_path: str | None = None,
    bold_font_path: str | None = None,
) -> bytes:
    font_name, bold_font_name = _register_fonts(font_path, bold_font_path)
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=PDF_TITLE,
        author="Airtable Telegram Bot",
    )

    styles = _styles(font_name, bold_font_name)
    story: list[object] = []
    for index, artwork in enumerate(artworks):
        if index:
            story.append(PageBreak())
        story.extend(_artwork_story(artwork, request_timeout_seconds, styles))

    document.build(story)
    return buffer.getvalue()


def _artwork_story(
    artwork: Artwork,
    request_timeout_seconds: float,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    story: list[object] = []

    artwork_images = _build_image_flowables(
        _artwork_image_urls(artwork),
        request_timeout_seconds,
        max_height=118 * mm,
    )
    if artwork_images:
        story.extend(_with_image_spacing(artwork_images))
    else:
        story.append(Paragraph(" ", styles["ImagePlaceholder"]))
    story.append(Spacer(1, 9 * mm))

    for value, style_name in _artwork_text_lines(artwork):
        story.append(Paragraph(_pdf_text(value), styles[style_name]))
        story.append(Spacer(1, 3 * mm))

    if artwork.provenance:
        story.extend(_provenance_story(artwork.provenance, styles))

    if artwork.expertise_image_urls:
        story.extend(
            _section_images(
                "Экспертиза",
                artwork.expertise_image_urls,
                request_timeout_seconds,
                styles,
            )
        )
    if artwork.framing_image_urls:
        story.extend(
            _section_images(
                "Обрамление",
                artwork.framing_image_urls,
                request_timeout_seconds,
                styles,
            )
        )

    return story


def _artwork_text_lines(artwork: Artwork) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    if artwork.title:
        lines.append((artwork.title, "ArtworkTitle"))
    if artwork.author:
        lines.append((artwork.author, "ArtworkText"))
    if artwork.technique:
        lines.append((artwork.technique, "ArtworkText"))
    if artwork.size:
        lines.append((artwork.size, "ArtworkText"))
    if artwork.year:
        lines.append((artwork.year, "ArtworkText"))
    if not lines:
        lines.append((MISSING_VALUE, "ArtworkText"))
    return lines


def _artwork_image_urls(artwork: Artwork) -> tuple[str, ...]:
    urls = tuple(url for url in artwork.image_urls if url)
    if urls:
        return urls
    if artwork.image_url:
        return (artwork.image_url,)
    return ()


def _section_images(
    title: str,
    image_urls: tuple[str, ...],
    request_timeout_seconds: float,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    images = _build_image_flowables(
        image_urls,
        request_timeout_seconds,
        max_height=190 * mm,
    )
    if not images:
        return []

    return [
        KeepTogether(
            [
                Spacer(1, 5 * mm),
                Paragraph(_pdf_text(title), styles["SectionTitle"]),
                Spacer(1, 4 * mm),
                images[0],
            ]
        ),
        Spacer(1, 6 * mm),
        *_with_image_spacing(images[1:]),
    ]


def _provenance_story(
    provenance: str,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    paragraphs = _text_paragraphs(provenance)
    if not paragraphs:
        return []

    story: list[object] = [
        KeepTogether(
            [
                Spacer(1, 5 * mm),
                Paragraph(_pdf_text("Провенанс/публикации/литература"), styles["SectionTitle"]),
                Spacer(1, 2 * mm),
                Paragraph(_pdf_text(paragraphs[0]), styles["ArtworkText"]),
            ]
        ),
        Spacer(1, 3 * mm),
    ]
    for paragraph in paragraphs[1:]:
        story.append(Paragraph(_pdf_text(paragraph), styles["ArtworkText"]))
        story.append(Spacer(1, 3 * mm))
    return story


def _text_paragraphs(value: str) -> list[str]:
    paragraphs: list[str] = []
    current_lines: list[str] = []
    for line in value.splitlines():
        stripped = line.strip()
        if stripped:
            current_lines.append(stripped)
        elif current_lines:
            paragraphs.append("\n".join(current_lines))
            current_lines = []
    if current_lines:
        paragraphs.append("\n".join(current_lines))
    return paragraphs


def _with_image_spacing(images: Iterable[Image]) -> list[object]:
    flowables: list[object] = []
    for image in images:
        flowables.append(image)
        flowables.append(Spacer(1, 6 * mm))
    return flowables


def _build_image_flowables(
    image_urls: Iterable[str],
    request_timeout_seconds: float,
    max_height: float,
) -> list[Image]:
    images: list[Image] = []
    for image_url in image_urls:
        image_flowable = _build_image(
            image_url,
            request_timeout_seconds,
            max_height=max_height,
        )
        if image_flowable:
            images.append(image_flowable)
    return images


def _build_image(
    image_url: str | None,
    request_timeout_seconds: float,
    max_height: float = 118 * mm,
) -> Image | None:
    if not image_url:
        return None

    try:
        response = requests.get(
            image_url,
            timeout=request_timeout_seconds,
            headers={"User-Agent": "artbot/1.0"},
        )
        response.raise_for_status()
        image_bytes = response.content
        reader = ImageReader(BytesIO(image_bytes))
        width, height = reader.getSize()
        if width <= 0 or height <= 0:
            return None
        max_width = A4[0] - 36 * mm
        scale = min(max_width / width, max_height / height)
        return Image(BytesIO(image_bytes), width=width * scale, height=height * scale, hAlign="CENTER")
    except Exception as exc:
        logger.warning("Could not load image for PDF: %s", exc)
        return None


def _details_table(artwork: Artwork, font_name: str, _bold_font_name: str) -> Table:
    value_style = ParagraphStyle(
        "DetailValue",
        fontName=font_name,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#111111"),
    )
    data = [[_paragraph(value, value_style)] for value, _style_name in _artwork_text_lines(artwork)]
    table = Table(data, colWidths=[156 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111111")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _styles(font_name: str, bold_font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "ImagePlaceholder": ParagraphStyle(
            "ImagePlaceholder",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=11,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#777777"),
            borderColor=colors.HexColor("#D9D9D9"),
            borderWidth=0.5,
            borderPadding=45,
        ),
        "ArtworkTitle": ParagraphStyle(
            "ArtworkTitle",
            parent=base["Heading1"],
            fontName=bold_font_name,
            fontSize=18,
            leading=23,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111111"),
        ),
        "ArtworkText": ParagraphStyle(
            "ArtworkText",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=12,
            leading=17,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111111"),
        ),
        "SectionTitle": ParagraphStyle(
            "SectionTitle",
            parent=base["Heading2"],
            fontName=bold_font_name,
            fontSize=12,
            leading=16,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111111"),
            spaceBefore=2 * mm,
        ),
    }


def _paragraph(value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_pdf_text(value), style)


def _pdf_text(value: str) -> str:
    return escape(value).replace("\n", "<br/>")


def _register_fonts(font_path: str | None, bold_font_path: str | None) -> tuple[str, str]:
    regular = _first_existing([font_path, *_regular_font_candidates()])
    bold = _first_existing([bold_font_path, *_bold_font_candidates()])

    if regular:
        pdfmetrics.registerFont(TTFont("ArtBotSans", regular))
    else:
        logger.warning("No Cyrillic TTF font found. Falling back to Helvetica.")
        return "Helvetica", "Helvetica-Bold"

    if bold:
        pdfmetrics.registerFont(TTFont("ArtBotSansBold", bold))
        return "ArtBotSans", "ArtBotSansBold"

    return "ArtBotSans", "ArtBotSans"


def _first_existing(paths: Iterable[str | None]) -> str | None:
    for path in paths:
        if path and Path(path).exists():
            return path
    return None


def _regular_font_candidates() -> list[str]:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    return [
        str(Path(windir) / "Fonts" / "arial.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]


def _bold_font_candidates() -> list[str]:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    return [
        str(Path(windir) / "Fonts" / "arialbd.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
