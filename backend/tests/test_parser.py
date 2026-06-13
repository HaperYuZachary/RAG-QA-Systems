import pytest
from zipfile import ZipFile, ZIP_DEFLATED

from app.core.parser import ParsedPage, parse, parse_docx, parse_markdown, parse_pdf


def test_parse_markdown_preserves_heading_structure(tmp_path):
    file_path = tmp_path / "guide.md"
    file_path.write_text("# Title\n\n## Section\n\nBody text.", encoding="utf-8")

    pages = parse_markdown(file_path)

    assert pages == [
        ParsedPage(page=None, text="# Title\n\n## Section\n\nBody text.")
    ]


def test_parse_docx_extracts_non_empty_paragraphs(tmp_path):
    docx = pytest.importorskip("docx")

    file_path = tmp_path / "handbook.docx"
    document = docx.Document()
    document.add_paragraph("Employee handbook")
    document.add_paragraph("")
    document.add_paragraph("Annual leave policy")
    document.save(file_path)

    pages = parse_docx(file_path)

    assert len(pages) == 1
    assert pages[0].page is None
    assert pages[0].text == "Employee handbook\nAnnual leave policy"


def test_parse_docx_extracts_table_cell_text(tmp_path):
    docx = pytest.importorskip("docx")

    file_path = tmp_path / "benefits.docx"
    document = docx.Document()
    document.add_paragraph("Benefits policy")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Years of service"
    table.cell(0, 1).text = "Annual leave"
    table.cell(1, 0).text = "1-10 years"
    table.cell(1, 1).text = "5 days"
    document.save(file_path)

    pages = parse_docx(file_path)

    assert "Benefits policy" in pages[0].text
    assert "Years of service | Annual leave" in pages[0].text
    assert "1-10 years | 5 days" in pages[0].text


def test_parse_docx_tolerates_invalid_internal_bookmark_relationship(tmp_path):
    docx = pytest.importorskip("docx")

    original_path = tmp_path / "source.docx"
    file_path = tmp_path / "bookmark.docx"
    document = docx.Document()
    document.add_paragraph("LLM collaborative filtering content")
    document.save(original_path)
    _copy_docx_with_broken_bookmark_relationship(original_path, file_path)

    pages = parse_docx(file_path)

    assert pages[0].text == "LLM collaborative filtering content"


def test_parse_pdf_extracts_text_by_page(tmp_path):
    fitz = pytest.importorskip("fitz")

    file_path = tmp_path / "policy.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "This PDF contains enough real text for the parser smoke test.",
    )
    document.save(file_path)
    document.close()

    pages = parse_pdf(file_path)

    assert len(pages) == 1
    assert pages[0].page == 1
    assert "real text" in pages[0].text


def test_parse_pdf_rejects_scanned_or_empty_pdf(tmp_path):
    fitz = pytest.importorskip("fitz")

    file_path = tmp_path / "scan.pdf"
    document = fitz.open()
    document.new_page()
    document.save(file_path)
    document.close()

    with pytest.raises(ValueError, match="scanned"):
        parse_pdf(file_path)


def test_parse_pdf_skips_empty_pages_in_mixed_text_pdf(tmp_path):
    fitz = pytest.importorskip("fitz")

    file_path = tmp_path / "mixed.pdf"
    document = fitz.open()
    text_page = document.new_page()
    text_page.insert_text(
        (72, 72),
        "This page has enough extracted text to make the PDF parseable.",
    )
    document.new_page()
    document.save(file_path)
    document.close()

    pages = parse_pdf(file_path)

    assert len(pages) == 1
    assert pages[0].page == 1
    assert pages[0].text


def test_parse_dispatches_by_file_type(tmp_path):
    file_path = tmp_path / "guide.md"
    file_path.write_text("Dispatch markdown text.", encoding="utf-8")

    pages = parse(file_path, "md")

    assert pages[0].text == "Dispatch markdown text."


def _copy_docx_with_broken_bookmark_relationship(source_path, target_path):
    relationship_path = "word/_rels/document.xml.rels"
    with ZipFile(source_path, "r") as source_zip, ZipFile(
        target_path,
        "w",
        ZIP_DEFLATED,
    ) as target_zip:
        for item in source_zip.infolist():
            data = source_zip.read(item.filename)
            if item.filename == relationship_path:
                xml = data.decode("utf-8")
                xml = xml.replace(
                    "</Relationships>",
                    '<Relationship Id="rId999" '
                    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
                    'Target="#bookmark22"/></Relationships>',
                )
                data = xml.encode("utf-8")
            target_zip.writestr(item, data)
