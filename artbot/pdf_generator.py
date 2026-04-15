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
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from artbot.domain import Artwork
from artbot.messages import MISSING_VALUE

logger = logging.getLogger(__name__)

PDF_TITLE = "Карточка объекта"


def generate_artwork_pdf(
    artwork: Artwork,
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
        title=f"{PDF_TITLE} #{artwork.row_id}",
        author="Airtable Telegram Bot",
    )

    styles = _styles(font_name, bold_font_name)
    story = [
        Paragraph(_pdf_text(PDF_TITLE), styles["Title"]),
        Paragraph(f"ID записи: {artwork.row_id}", styles["SubTitle"]),
        Spacer(1, 8 * mm),
    ]

    image_flowable = _build_image(artwork.image_url, request_timeout_seconds)
    if image_flowable:
        story.append(image_flowable)
    else:
        story.append(Paragraph(_pdf_text("Изображение не указано или недоступно"), styles["ImagePlaceholder"]))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph(_pdf_text(_value(artwork.title)), styles["ArtworkTitle"]))
    story.append(Spacer(1, 5 * mm))
    story.append(_details_table(artwork, font_name, bold_font_name))

    document.build(story)
    return buffer.getvalue()


def _build_image(image_url: str | None, request_timeout_seconds: float) -> Image | None:
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
        max_width = A4[0] - 36 * mm
        max_height = 118 * mm
        scale = min(max_width / width, max_height / height)
        return Image(BytesIO(image_bytes), width=width * scale, height=height * scale, hAlign="CENTER")
    except Exception as exc:
        logger.warning("Could not load image for PDF: %s", exc)
        return None


def _details_table(artwork: Artwork, font_name: str, bold_font_name: str) -> Table:
    label_style = ParagraphStyle(
        "DetailLabel",
        fontName=bold_font_name,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#3B3B3B"),
    )
    value_style = ParagraphStyle(
        "DetailValue",
        fontName=font_name,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#111111"),
    )
    data = [
        [_paragraph("Автор", label_style), _paragraph(_value(artwork.author), value_style)],
        [_paragraph("Техника", label_style), _paragraph(_value(artwork.technique), value_style)],
        [_paragraph("Размер", label_style), _paragraph(_value(artwork.size), value_style)],
        [_paragraph("Год", label_style), _paragraph(_value(artwork.year), value_style)],
        [_paragraph("Цена", label_style), _paragraph(_value(artwork.price), value_style)],
    ]
    table = Table(data, colWidths=[36 * mm, 120 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTNAME", (0, 0), (0, -1), bold_font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#3B3B3B")),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111111")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#D9D9D9")),
            ]
        )
    )
    return table


def _styles(font_name: str, bold_font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName=bold_font_name,
            fontSize=22,
            leading=26,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#111111"),
            spaceAfter=4,
        ),
        "SubTitle": ParagraphStyle(
            "SubTitle",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#666666"),
        ),
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
            borderPadding=24,
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
    }


def _value(value: str | None) -> str:
    return value if value else MISSING_VALUE


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
