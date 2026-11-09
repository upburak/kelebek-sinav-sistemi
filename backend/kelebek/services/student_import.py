"""Read supported XLSX and text-based PDF student-list tables in memory."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

MAX_HEADER_SCAN_ROWS = 1000
HEADER_ALIASES = {
    "school_number": {"okul no", "okul numarasi", "ogrenci no", "ogrenci numarasi", "school number", "student number"},
    "first_name": {"ad", "adi", "ogrenci adi", "first name", "firstname", "given name"},
    "last_name": {"soyad", "soyadi", "ogrenci soyadi", "last name", "lastname", "surname", "family name"},
    "class_level": {"sinif", "sinif seviyesi", "sinif duzeyi", "sinif kademesi", "grade", "class level", "grade level"},
    "section": {"sube", "sinif subesi", "sube adi", "section", "class section"},
    "area": {"alan", "bolum", "program", "academic area", "field of study"},
}
CORE_FIELDS = ("school_number", "first_name", "last_name")


@dataclass(frozen=True)
class ImportTable:
    name: str
    rows: list[tuple]
    header_index: int
    headers: list
    class_level: str | None
    section: str | None
    formula_cells: frozenset[tuple[int, int]] = frozenset()

    @property
    def header_row(self) -> int:
        return self.header_index + 1


def normalize_header(value) -> str:
    text = str(value or "").casefold().replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


_NORMALIZED_ALIASES = {
    field: {normalize_header(alias) for alias in aliases}
    for field, aliases in HEADER_ALIASES.items()
}


def auto_map_headers(headers) -> dict[str, int]:
    candidates = {}
    for column, header in enumerate(headers):
        normalized = normalize_header(header)
        for field, aliases in _NORMALIZED_ALIASES.items():
            if normalized and normalized in aliases:
                candidates.setdefault(field, []).append(column)
    counts = {}
    for columns in candidates.values():
        for column in columns:
            counts[column] = counts.get(column, 0) + 1
    return {
        field: columns[0]
        for field, columns in candidates.items()
        if len(columns) == 1 and counts[columns[0]] == 1
    }


def find_header(rows) -> tuple[int, list] | None:
    best = None
    for index, row in enumerate(rows[:MAX_HEADER_SCAN_ROWS]):
        headers = list(row)
        mapping = auto_map_headers(headers)
        score = sum(field in mapping for field in CORE_FIELDS)
        if score >= 2 and (best is None or score > best[0]):
            best = (score, index, headers)
            if score == len(CORE_FIELDS):
                break
    return (best[1], best[2]) if best else None


def infer_class_context(name: str, preceding_rows=()) -> tuple[str | None, str | None]:
    candidates = [str(name)]
    for row in preceding_rows:
        candidates.extend(str(value) for value in row if value not in (None, ""))
    pattern = re.compile(
        r"(?<!\d)(9|10|11|12)\s*\.?\s*(?:sınıf|sinif)?\s*[/\-–]\s*([a-z0-9]+)(?:\s*(?:şubesi|subesi))?",
        re.IGNORECASE,
    )
    for value in candidates:
        match = pattern.search(value.strip())
        if match:
            return match.group(1), match.group(2).upper()
    return None, None


def _as_rows(rows):
    return [tuple(value for value in row) for row in rows]


def _find_table(name: str, rows, preceding_rows=(), formula_cells=frozenset()) -> ImportTable | None:
    rows = _as_rows(rows)
    header = find_header(rows)
    if header is None:
        return None
    header_index, headers = header
    grade, section = infer_class_context(name, [*preceding_rows, *rows[:header_index]])
    return ImportTable(name, rows, header_index, headers, grade, section, formula_cells)


def read_student_tables(content: bytes, filename: str) -> list[ImportTable]:
    """Extract recognized roster tables; never writes uploaded data to disk."""
    extension = filename.casefold().rsplit(".", 1)[-1]
    tables: list[ImportTable] = []
    if extension == "xlsx":
        try:
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
            formula_workbook = load_workbook(BytesIO(content), read_only=True, data_only=False)
        except (InvalidFileException, BadZipFile, OSError, ValueError) as error:
            raise ValueError("Dosya açılamadı. Geçerli bir .xlsx dosyası seçin.") from error
        try:
            # İki çalışma kitabı aynı dosyadan açıldığı için sayfa sayıları eşittir;
            # yine de eşitlik açıkça istenir ki bozuk dosyada sessizce sayfa atlanmasın.
            for sheet, formula_sheet in zip(workbook.worksheets, formula_workbook.worksheets, strict=True):
                rows = list(sheet.iter_rows(values_only=True))
                formula_cells = frozenset(
                    (row_index, column_index)
                    for row_index, row in enumerate(formula_sheet.iter_rows())
                    for column_index, cell in enumerate(row)
                    if cell.data_type == "f"
                )
                table = _find_table(sheet.title, rows, formula_cells=formula_cells)
                if table:
                    tables.append(table)
        finally:
            workbook.close()
            formula_workbook.close()
    elif extension == "pdf":
        try:
            import pdfplumber
        except ImportError as error:
            raise RuntimeError("PDF içe aktarma bileşeni kurulu değil. Uygulamayı güncelleyin.") from error
        try:
            with pdfplumber.open(BytesIO(content)) as document:
                previous_headers = None
                for page_number, page in enumerate(document.pages, start=1):
                    page_text = page.extract_text() or ""
                    page_tables = page.extract_tables() or []
                    if not page_tables:
                        page_tables = page.extract_tables(table_settings={
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                        }) or []
                    for raw_rows in page_tables:
                        rows = _as_rows(raw_rows)
                        table = _find_table(f"Sayfa {page_number}", rows, [page_text])
                        if table:
                            previous_headers = table.headers
                            tables.append(table)
                        elif previous_headers and rows:
                            grade, section = infer_class_context(f"Sayfa {page_number}", [page_text])
                            tables.append(ImportTable(
                                f"Sayfa {page_number}", rows, -1,
                                previous_headers, grade, section,
                            ))
                if not tables:
                    raise ValueError(
                        "PDF içinde metin tabanlı öğrenci tablosu bulunamadı. Görüntü taraması PDF'ler için OCR gerekli."
                    )
        except ValueError:
            raise
        except Exception as error:
            raise ValueError("PDF okunamadı veya tablo düzeni çözümlenemedi.") from error
    else:
        raise ValueError("Yalnızca .xlsx ve metin tabanlı .pdf dosyaları destekleniyor.")

    if not tables:
        raise ValueError("Dosyada tanınan öğrenci tablosu veya başlık satırı bulunamadı.")
    return tables
