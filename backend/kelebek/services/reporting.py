"""Kesinleşmiş sınavlar için yerel rapor üretimi."""

import os
import re
import hashlib
import json
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A3, A4, A5, LEGAL, LETTER, landscape, portrait
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import func, select

from kelebek.config import get_data_dir
from kelebek.models import (
    Classroom,
    ClassroomLayout,
    Course,
    Desk,
    DistributionReport,
    ExamCourse,
    ExamOrganization,
    ExamOrganizationClassroom,
    ExamParticipant,
    SchoolProfile,
    Seat,
    SeatAssignment,
)


PAGE_SIZE = landscape(A4)
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
FONT_REGULAR = "KelebekSans"
FONT_BOLD = "KelebekSansBold"
SEATING_PLAN_REPORT_TYPE = "seating_plan_pdf"
ATTENDANCE_REPORT_TYPE = "attendance_pdf"
ROOM_STUDENT_LIST_REPORT_TYPE = "room_student_list_pdf"
GENERAL_DISTRIBUTION_REPORT_TYPE = "general_distribution_pdf"
ROOM_STUDENT_LIST_XLSX_REPORT_TYPE = "room_student_list_xlsx"
GENERAL_DISTRIBUTION_XLSX_REPORT_TYPE = "general_distribution_xlsx"
CLASS_STUDENT_LIST_REPORT_TYPE = "class_student_list_pdf"
CLASS_STUDENT_LIST_XLSX_REPORT_TYPE = "class_student_list_xlsx"
REPORT_TYPES = (SEATING_PLAN_REPORT_TYPE, ATTENDANCE_REPORT_TYPE, ROOM_STUDENT_LIST_REPORT_TYPE,
                GENERAL_DISTRIBUTION_REPORT_TYPE, CLASS_STUDENT_LIST_REPORT_TYPE)

REPORT_FIELDS = {
    ATTENDANCE_REPORT_TYPE: ("seat", "school_number", "name", "class", "area"),
    ROOM_STUDENT_LIST_REPORT_TYPE: ("seat", "school_number", "name", "class", "area", "status"),
    ROOM_STUDENT_LIST_XLSX_REPORT_TYPE: ("seat", "school_number", "name", "class", "area", "status"),
    GENERAL_DISTRIBUTION_REPORT_TYPE: ("room", "seat", "school_number", "name", "class", "area"),
    GENERAL_DISTRIBUTION_XLSX_REPORT_TYPE: (
        "room", "seat", "school_number", "name", "class", "area", "courses",
    ),
    CLASS_STUDENT_LIST_REPORT_TYPE: ("room", "seat", "school_number", "name", "class", "area"),
    CLASS_STUDENT_LIST_XLSX_REPORT_TYPE: ("room", "seat", "school_number", "name", "class", "area"),
}
REPORT_FIELD_LABELS = {
    "room": "Derslik", "seat": "Koltuk", "school_number": "Okul numarası",
    "name": "Adı soyadı", "class": "Sınıf/şube", "area": "Alan",
    "status": "Durum", "courses": "Dersler",
}

PAPER_SIZES = {"A4": A4, "A3": A3, "A5": A5, "LETTER": LETTER, "LEGAL": LEGAL}


def resolve_pdf_options(params=None, *, default_orientation="portrait") -> dict:
    params = params or {}
    paper = str(params.get("paper", "A4")).upper()
    orientation = str(params.get("orientation", default_orientation)).lower()
    try:
        margin_mm = float(params.get("margin_mm", "12"))
    except (TypeError, ValueError) as error:
        raise ValueError("Kenar boşluğu 5–30 mm arasında olmalı.") from error
    if paper not in PAPER_SIZES:
        raise ValueError("Kâğıt boyutu A4, A3, A5, Letter veya Legal olmalı.")
    if orientation not in {"portrait", "landscape"}:
        raise ValueError("Sayfa yönü dikey veya yatay olmalı.")
    if not 5 <= margin_mm <= 30:
        raise ValueError("Kenar boşluğu 5–30 mm arasında olmalı.")
    size = PAPER_SIZES[paper]
    page_size = landscape(size) if orientation == "landscape" else portrait(size)
    return {"paper": paper, "orientation": orientation, "margin_points": margin_mm * 72 / 25.4,
            "page_size": page_size}


def resolve_report_fields(params, report_type: str) -> tuple[str, ...]:
    allowed = REPORT_FIELDS.get(report_type)
    if allowed is None:
        raise ValueError("Bu rapor türünde sütun seçimi desteklenmiyor.")
    raw = params.get("fields")
    if raw is None:
        return allowed
    requested = tuple(item.strip() for item in str(raw).split(",") if item.strip())
    unsupported = set(requested) - set(allowed)
    if unsupported:
        raise ValueError("Seçimde bu rapor türünde bulunmayan sütun var.")
    if not requested:
        raise ValueError("En az bir rapor alanı seçmelisin.")
    if len(set(requested)) != len(requested):
        raise ValueError("Bir sütun raporda birden fazla kez seçilemez.")
    return requested


def resolve_report_labels(params, report_type: str, fields: tuple[str, ...]) -> dict[str, str]:
    allowed = set(REPORT_FIELDS.get(report_type, ()))
    raw = params.get("labels")
    if raw is None:
        return {}
    try:
        requested = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("Sütun başlıkları okunamadı.") from error
    if not isinstance(requested, dict):
        raise ValueError("Sütun başlıkları geçersiz.")
    if set(requested) - set(fields):
        raise ValueError("Başlığı yalnız raporda görünür olan sütunlar için değiştirebilirsin.")
    labels = {}
    for key, label in requested.items():
        if not isinstance(label, str):
            raise ValueError("Sütun başlıkları metin olmalı.")
        label = label.strip()
        if not label or len(label) > 40 or any(ord(char) < 32 for char in label):
            raise ValueError("Sütun başlığı 1–40 karakter arasında olmalı.")
        labels[key] = label
    return {key: labels[key] for key in fields if key in labels}


def _register_fonts() -> tuple[str, str]:
    """Use a Turkish-capable system font when available; otherwise use Helvetica."""
    if FONT_REGULAR in pdfmetrics.getRegisteredFontNames():
        return FONT_REGULAR, FONT_BOLD

    if os.name == "nt":
        candidates = [(r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf")]
    elif os.name == "posix" and os.uname().sysname == "Darwin":
        candidates = [
            ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        ]
    else:
        candidates = [
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        ]

    for regular_path, bold_path in candidates:
        if Path(regular_path).is_file() and Path(bold_path).is_file():
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, regular_path))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, bold_path))
            return FONT_REGULAR, FONT_BOLD
    return "Helvetica", "Helvetica-Bold"


def _fit_name(first_name: str, last_name: str, width: float, font: str) -> tuple[list[str], float]:
    """Keep the surname visible and abbreviate the first name only if needed."""
    size = 6.2
    full_name = f"{first_name} {last_name}".strip()
    lines = simpleSplit(full_name, font, size, width)
    if len(lines) > 2:
        abbreviated = f"{first_name[:1]}. {last_name}".strip()
        size = 5.8
        lines = simpleSplit(abbreviated, font, size, width)
    while len(lines) > 2 and size > 4.6:
        size -= 0.3
        lines = simpleSplit(abbreviated, font, size, width)
    return lines[:2], size


def safe_report_stem(name: str) -> str:
    """Create a readable, filesystem-safe export name, including Turkish letters."""
    normalized = name.translate(str.maketrans({
        "ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G",
        "ç": "c", "Ç": "C", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U",
    }))
    return re.sub(r"[^A-Za-z0-9._-]+", "-", normalized).strip("-._")[:60] or "sinav"


def seating_plan_report_filename(organization: ExamOrganization) -> str:
    """Give same-named exams separate files without exposing names in a path."""
    return f"{safe_report_stem(organization.name)}-{organization.id}-oturma-planlari.pdf"


def seating_plan_report_path(file_name: str) -> Path:
    return get_data_dir() / "Exports" / "PDF" / file_name


def report_filename(organization: ExamOrganization, report_type: str) -> str:
    suffixes = {
        SEATING_PLAN_REPORT_TYPE: "oturma-planlari",
        ATTENDANCE_REPORT_TYPE: "yoklama-cizelgesi",
        ROOM_STUDENT_LIST_REPORT_TYPE: "derslik-ogrenci-listesi",
        GENERAL_DISTRIBUTION_REPORT_TYPE: "genel-dagitim-listesi",
        ROOM_STUDENT_LIST_XLSX_REPORT_TYPE: "derslik-ogrenci-listesi",
        GENERAL_DISTRIBUTION_XLSX_REPORT_TYPE: "genel-dagitim-listesi",
        CLASS_STUDENT_LIST_REPORT_TYPE: "sinif-ogrenci-listesi",
        CLASS_STUDENT_LIST_XLSX_REPORT_TYPE: "sinif-ogrenci-listesi",
    }
    if report_type not in suffixes:
        raise ValueError("Bilinmeyen rapor türü.")
    extension = "xlsx" if report_type.endswith("_xlsx") else "pdf"
    return f"{safe_report_stem(organization.name)}-{organization.id}-{suffixes[report_type]}.{extension}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def report_data_fingerprint(session, organization: ExamOrganization, candidate_id: str) -> str:
    assignments = session.execute(
        select(SeatAssignment.participant_id, SeatAssignment.seat_id,
               ExamParticipant.school_number, ExamParticipant.first_name,
               ExamParticipant.last_name, ExamParticipant.class_level, ExamParticipant.section,
               ExamParticipant.area)
        .join(ExamParticipant, ExamParticipant.id == SeatAssignment.participant_id)
        .where(ExamParticipant.is_active.is_(True))
        .where(SeatAssignment.candidate_id == candidate_id)
        .order_by(SeatAssignment.participant_id)
    ).all()
    selections = session.execute(
        select(ExamOrganizationClassroom.classroom_id, Classroom.name,
               ExamOrganizationClassroom.layout_id, ClassroomLayout.name)
        .join(Classroom, Classroom.id == ExamOrganizationClassroom.classroom_id)
        .join(ClassroomLayout, ClassroomLayout.id == ExamOrganizationClassroom.layout_id)
        .where(ExamOrganizationClassroom.organization_id == organization.id)
        .order_by(Classroom.name)
    ).all()
    layout_data = []
    for _room_id, room_name, layout_id, layout_name in selections:
        desks = session.execute(
            select(Desk.id, Desk.label, Desk.block_label, Desk.x, Desk.y)
            .where(Desk.layout_id == layout_id).order_by(Desk.y, Desk.x)
        ).all()
        seats = session.execute(
            select(Seat.id, Seat.desk_id, Seat.seat_number, Seat.seat_index, Seat.is_available)
            .where(Seat.layout_id == layout_id).order_by(Seat.seat_number)
        ).all()
        layout_data.append({
            "room": room_name, "layout": layout_name,
            "desks": [list(row) for row in desks], "seats": [list(row) for row in seats],
        })
    course_names = session.scalars(
        select(Course.name).join(ExamCourse, ExamCourse.course_id == Course.id)
        .where(ExamCourse.organization_id == organization.id).order_by(ExamCourse.display_order)
    ).all()
    profile = session.get(SchoolProfile, 1)
    snapshot = {
        "organization": [organization.name, organization.exam_date.isoformat(), course_names,
                         profile.school_name if profile else ""],
        "candidate_id": candidate_id,
        "assignments": [list(row) for row in assignments],
        "layouts": layout_data,
    }
    raw = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def report_status(session, organization: ExamOrganization, report_type: str = SEATING_PLAN_REPORT_TYPE) -> dict:
    report = session.scalar(select(DistributionReport).where(
        DistributionReport.organization_id == organization.id,
        DistributionReport.report_type == report_type,
    ))
    if report is None:
        return {"report_status": "not_generated", "report_updated_at": None}
    report_path = seating_plan_report_path(report.file_name)
    duplicate_path = session.scalar(select(func.count(DistributionReport.id)).where(
        DistributionReport.file_name == report.file_name,
        DistributionReport.report_type == report_type,
        DistributionReport.organization_id != organization.id,
    )) or 0
    current = (
        report.candidate_id == organization.selected_candidate_id
        and duplicate_path == 0
        and report_path.is_file()
        and report.file_sha256 is not None
        and report.file_sha256 == _sha256_file(report_path)
        and report.data_fingerprint == report_data_fingerprint(
            session, organization, organization.selected_candidate_id or ""
        )
    )
    return {
        "report_status": "current" if current else "stale",
        "report_updated_at": report.created_at.isoformat(),
    }


def all_report_statuses(session, organization: ExamOrganization) -> dict[str, dict]:
    return {kind: report_status(session, organization, kind) for kind in REPORT_TYPES}


def record_seating_plan_report(session, organization: ExamOrganization, candidate_id: str, file_name: str) -> None:
    record_report(session, organization, candidate_id, SEATING_PLAN_REPORT_TYPE, file_name)


def record_report(session, organization: ExamOrganization, candidate_id: str,
                  report_type: str, file_name: str) -> None:
    report_path = seating_plan_report_path(file_name)
    if not report_path.is_file():
        raise FileNotFoundError("Oluşturulan PDF raporu bulunamadı.")
    file_sha256 = _sha256_file(report_path)
    report = session.scalar(select(DistributionReport).where(
        DistributionReport.organization_id == organization.id,
        DistributionReport.report_type == report_type,
    ))
    if report is None:
        report = DistributionReport(
            organization_id=organization.id,
            candidate_id=candidate_id,
            report_type=report_type,
            data_fingerprint=report_data_fingerprint(session, organization, candidate_id),
            file_sha256=file_sha256,
            file_name=file_name,
        )
        session.add(report)
    else:
        report.candidate_id = candidate_id
        report.data_fingerprint = report_data_fingerprint(session, organization, candidate_id)
        report.file_sha256 = file_sha256
        report.file_name = file_name
        report.created_at = datetime.now(timezone.utc)


def _report_context(session, organization: ExamOrganization, candidate_id: str):
    school = session.get(SchoolProfile, 1)
    school_name = school.school_name.strip() if school and school.school_name.strip() else "Kelebek Sınav Sistemi"
    course_names = session.scalars(
        select(Course.name).join(ExamCourse, ExamCourse.course_id == Course.id)
        .where(ExamCourse.organization_id == organization.id).order_by(ExamCourse.display_order)
    ).all()
    assignments = session.execute(
        select(SeatAssignment.seat_id, ExamParticipant)
        .join(ExamParticipant, ExamParticipant.id == SeatAssignment.participant_id)
        .where(ExamParticipant.is_active.is_(True), SeatAssignment.candidate_id == candidate_id,
               SeatAssignment.seat_id.is_not(None))
    ).all()
    students_by_seat = {seat_id: participant for seat_id, participant in assignments}
    rooms = session.execute(
        select(Classroom, ClassroomLayout)
        .join(ExamOrganizationClassroom, ExamOrganizationClassroom.classroom_id == Classroom.id)
        .join(ClassroomLayout, ClassroomLayout.id == ExamOrganizationClassroom.layout_id)
        .where(ExamOrganizationClassroom.organization_id == organization.id)
        .order_by(ExamOrganizationClassroom.display_order, Classroom.name)
    ).all()
    if not rooms:
        raise ValueError("PDF oluşturmak için seçili derslik düzeni bulunamadı.")
    room_data = []
    for classroom, layout in rooms:
        seats = session.scalars(select(Seat).where(Seat.layout_id == layout.id)
                                .order_by(Seat.seat_number)).all()
        room_data.append((classroom, layout, [(seat, students_by_seat.get(seat.id)) for seat in seats]))
    return school_name, course_names, room_data


def _draw_table_page(pdf, organization, school_name, course_names, classroom, layout,
                     report_title, headers, rows, page_size, page_number, page_total,
                     regular, bold, options, column_keys, attendance=False, general=False):
    width, height = page_size
    margin = options["margin_points"]
    vertical_offset = margin - 32
    pdf.setFillColor(HexColor("#183943"))
    _draw_fitted_text(pdf, school_name, margin, height - 34 - vertical_offset, width - 2 * margin, bold, 14, 8)
    pdf.setFont(bold, 11)
    pdf.drawString(margin, height - 54 - vertical_offset, report_title)
    pdf.setFillColor(HexColor("#52636A"))
    _draw_fitted_text(pdf, organization.name, width - margin, height - 54 - vertical_offset,
                      width - 2 * margin, regular, 8.5, 5, "right")
    course_label = " · ".join(course_names) if course_names else "Genel sınav"
    _draw_fitted_text(pdf, f"{organization.exam_date.strftime('%d.%m.%Y')}  ·  {course_label}",
                      margin, height - 70 - vertical_offset, width - 2 * margin, regular, 8, 5)
    pdf.setFillColor(HexColor("#245B52"))
    _draw_fitted_text(pdf, f"{classroom.name}  ·  {layout.name}", margin, height - 91 - vertical_offset,
                      width - 2 * margin, bold, 10, 6)
    table_top = height - 108 - vertical_offset
    available_width = width - 2 * margin
    weights = {"room": 90, "seat": 42, "school_number": 82, "name": 220,
               "class": 75, "area": 80, "status": 58, "plus": 80, "minus": 80}
    proportional_total = sum(weights[key] for key in column_keys)
    col_widths = [available_width * weights[key] / proportional_total for key in column_keys]
    x_positions = [margin]
    for col_width in col_widths:
        x_positions.append(x_positions[-1] + col_width)
    pdf.setFillColor(HexColor("#E8EFF0"))
    pdf.rect(margin, table_top - 22, sum(col_widths), 22, fill=1, stroke=0)
    pdf.setFillColor(HexColor("#183943"))
    for index, header in enumerate(headers):
        _draw_fitted_text(pdf, header, x_positions[index] + 4, table_top - 14,
                          col_widths[index] - 7, bold, 7.2, 5)
    y = table_top - 22
    row_height = 22
    available_rows = max(1, int((table_top - margin - 10) / row_height))
    row_start = (page_number - 1) * available_rows
    for row_index, row in enumerate(rows[row_start:row_start + available_rows]):
        row_y = y - (row_index + 1) * row_height
        if row_index % 2 == 0:
            pdf.setFillColor(HexColor("#F7F9F9"))
            pdf.rect(margin, row_y, sum(col_widths), row_height, fill=1, stroke=0)
        pdf.setStrokeColor(HexColor("#D8E0E2"))
        pdf.line(margin, row_y, margin + sum(col_widths), row_y)
        pdf.setFillColor(HexColor("#26383D"))
        for col_index, value in enumerate(row):
            cell_x = x_positions[col_index]
            cell_width = col_widths[col_index]
            if attendance and column_keys[col_index] in {"plus", "minus"}:
                pdf.setStrokeColor(HexColor("#60767D"))
                box = 11
                pdf.rect(cell_x + (cell_width - box) / 2, row_y + (row_height - box) / 2,
                         box, box, fill=0, stroke=1)
            elif column_keys[col_index] == "name" and isinstance(value, tuple):
                name_lines, name_size = _fit_name(value[0], value[1], cell_width - 8, regular)
                text_y = row_y + row_height - 8
                for line in name_lines:
                    font_size = min(7.2, name_size)
                    pdf.setFont(regular, font_size)
                    pdf.drawString(cell_x + 4, text_y, line)
                    text_y -= font_size + 1
            else:
                _draw_fitted_text(pdf, str(value), cell_x + 4, row_y + 6,
                                  cell_width - 7, regular, 7.2, 5)
    pdf.setStrokeColor(HexColor("#D8E0E2"))
    footer_line_y = max(17, margin - 6)
    pdf.line(margin, footer_line_y, width - margin, footer_line_y)
    pdf.setFillColor(HexColor("#64747A"))
    pdf.setFont(regular, 7)
    item_label = "öğrenci" if attendance or general else "oturma yeri"
    footer_y = max(5, margin - 21)
    pdf.drawString(margin, footer_y, f"{len(rows)} {item_label}  ·  {classroom.name}")
    pdf.drawRightString(width - margin, footer_y, f"{page_number}/{page_total}")
    pdf.showPage()


def _build_room_report_pdf(session, organization, candidate_id, report_type, options=None,
                           fields=None, labels=None):
    attendance = report_type == ATTENDANCE_REPORT_TYPE
    general = report_type == GENERAL_DISTRIBUTION_REPORT_TYPE
    if options is None:
        options = resolve_pdf_options(default_orientation="landscape" if attendance or general else "portrait")
    page_size = options["page_size"]
    fields = fields or REPORT_FIELDS[report_type]
    labels = labels or {}
    column_keys = (*fields, "plus", "minus") if attendance else fields
    headers = ["+" if key == "plus" else "−" if key == "minus" else labels.get(key, REPORT_FIELD_LABELS[key])
               for key in column_keys]
    school_name, course_names, room_data = _report_context(session, organization, candidate_id)
    regular, bold = _register_fonts()
    pages = []
    for classroom, layout, seats in room_data:
        rows = []
        for seat, student in seats:
            if (attendance or general) and (not seat.is_available or student is None):
                continue
            if not attendance and not seat.is_available:
                continue
            values = {
                "room": classroom.name,
                "seat": str(seat.seat_number),
                "school_number": student.school_number if student else "—",
                "name": (student.first_name, student.last_name) if student else "—",
                "class": f"{student.class_level}/{student.section}" if student else "—",
                "area": student.area or "—" if student else "—",
                "status": "Dolu" if student else "Boş",
                "plus": "", "minus": "",
            }
            rows.append([values[key] for key in column_keys])
        margin_offset = options["margin_points"] - 32
        table_top = page_size[1] - 108 - margin_offset
        content_height = table_top - options["margin_points"] - 10
        row_height = 22
        rows_per_page = max(1, int(content_height / row_height))
        page_count = max(1, (len(rows) + rows_per_page - 1) // rows_per_page)
        for page_index in range(page_count):
            pages.append((classroom, layout, rows, page_index + 1, page_count))
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=page_size, pageCompression=1)
    report_title = ("YOKLAMA ÇİZELGESİ" if attendance else "GENEL SINAV DAĞITIM LİSTESİ"
                    if general else "DERSLİK BAZLI ÖĞRENCİ LİSTESİ")
    pdf.setTitle(f"{organization.name} - {report_title.title()}")
    pdf.setAuthor(school_name)
    for classroom, layout, rows, page_index, page_count in pages:
        _draw_table_page(pdf, organization, school_name, course_names, classroom, layout,
                         report_title, headers, rows, page_size, page_index, page_count,
                         regular, bold, options, column_keys, attendance, general)
    pdf.save()
    result = output.getvalue()
    export_dir = get_data_dir() / "Exports" / "PDF"
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / report_filename(organization, report_type)).write_bytes(result)
    return result


def build_attendance_pdf(session, organization, candidate_id: str, options=None,
                         fields=None, labels=None) -> bytes:
    return _build_room_report_pdf(
        session, organization, candidate_id, ATTENDANCE_REPORT_TYPE, options, fields, labels,
    )


def build_room_student_list_pdf(session, organization, candidate_id: str, options=None,
                                fields=None, labels=None) -> bytes:
    return _build_room_report_pdf(
        session, organization, candidate_id, ROOM_STUDENT_LIST_REPORT_TYPE, options, fields, labels,
    )


def build_general_distribution_pdf(session, organization, candidate_id: str, options=None,
                                   fields=None, labels=None) -> bytes:
    return _build_room_report_pdf(
        session, organization, candidate_id, GENERAL_DISTRIBUTION_REPORT_TYPE, options, fields, labels,
    )


def build_class_student_list_pdf(session, organization, candidate_id: str, options=None,
                                 fields=None, labels=None) -> bytes:
    options = options or resolve_pdf_options()
    fields = fields or REPORT_FIELDS[CLASS_STUDENT_LIST_REPORT_TYPE]
    labels = labels or {}
    school_name, course_names, rooms = _report_context(session, organization, candidate_id)
    grouped = {}
    for classroom, _layout, seats in rooms:
        for seat, student in seats:
            if student is None or not seat.is_available:
                continue
            key = (student.class_level, student.section)
            values = {
                "room": classroom.name, "seat": str(seat.seat_number),
                "school_number": student.school_number, "name": (student.first_name, student.last_name),
                "class": f"{student.class_level}/{student.section}", "area": student.area or "—",
            }
            grouped.setdefault(key, []).append([values[field] for field in fields])
    if not grouped:
        raise ValueError("Sınıf listesi oluşturmak için yerleşmiş öğrenci bulunamadı.")
    regular, bold = _register_fonts()
    page_size = options["page_size"]
    margin_offset = options["margin_points"] - 32
    table_top = page_size[1] - 108 - margin_offset
    rows_per_page = max(1, int((table_top - options["margin_points"] - 10) / 22))
    pages = []
    for class_group, rows in sorted(grouped.items(), key=lambda item: (int(item[0][0]), item[0][1])):
        name_index = fields.index("name") if "name" in fields else None
        if name_index is not None:
            rows.sort(key=lambda row: (str(row[name_index][1]).casefold(), str(row[name_index][0]).casefold()))
        page_count = max(1, (len(rows) + rows_per_page - 1) // rows_per_page)
        for page_index in range(page_count):
            pages.append((class_group, rows, page_index + 1, page_count))
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=page_size, pageCompression=1)
    pdf.setTitle(f"{organization.name} - Sınıf Öğrenci Listesi")
    pdf.setAuthor(school_name)
    for (class_level, section), rows, page_index, page_count in pages:
        group = type("ReportGroup", (), {"name": f"Sınıf {class_level}/{section}"})()
        layout = type("ReportLayout", (), {"name": "Öğrenci listesi"})()
        _draw_table_page(
            pdf, organization, school_name, course_names, group, layout,
            "SINIF BAZLI ÖĞRENCİ LİSTESİ",
            [labels.get(field, REPORT_FIELD_LABELS[field]) for field in fields],
            rows, page_size, page_index, page_count, regular, bold, options, fields, general=True,
        )
    pdf.save()
    result = output.getvalue()
    export_dir = get_data_dir() / "Exports" / "PDF"
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / report_filename(organization, CLASS_STUDENT_LIST_REPORT_TYPE)).write_bytes(result)
    return result


def _write_workbook(rows_by_sheet: list[tuple[str, list[list[object]]]]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    header_fill = PatternFill("solid", fgColor="E8EFF0")
    for sheet_name, rows in rows_by_sheet:
        sheet = workbook.create_sheet(sheet_name[:31] or "Liste")
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:{get_column_letter(max(1, len(rows[0]) if rows else 1))}{max(1, len(rows))}"
        for row_index, row in enumerate(rows, start=1):
            sheet.append(row)
            for cell in sheet[row_index]:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
            if row_index == 1:
                for cell in sheet[row_index]:
                    cell.font = Font(bold=True, color="183943")
                    cell.fill = header_fill
        for column in sheet.columns:
            letter = column[0].column_letter
            max_width = max((len(str(cell.value or "")) for cell in column), default=10)
            sheet.column_dimensions[letter].width = min(42, max(12, max_width + 2))
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def build_room_student_list_xlsx(session, organization, candidate_id: str, fields=None, labels=None) -> bytes:
    fields = fields or REPORT_FIELDS[ROOM_STUDENT_LIST_XLSX_REPORT_TYPE]
    labels = labels or {}
    _school, _courses, rooms = _report_context(session, organization, candidate_id)
    sheets = []
    for classroom, _layout, seats in rooms:
        rows = [[labels.get(field, REPORT_FIELD_LABELS[field]) for field in fields]]
        for seat, student in seats:
            if not seat.is_available:
                continue
            values = {
                "room": classroom.name, "seat": seat.seat_number,
                "school_number": student.school_number if student else "",
                "name": f"{student.first_name} {student.last_name}" if student else "",
                "class": f"{student.class_level}/{student.section}" if student else "",
                "area": student.area or "" if student else "",
                "status": "Dolu" if student else "Boş",
            }
            rows.append([values[field] for field in fields])
        sheets.append((classroom.name, rows))
    return _write_workbook(sheets)


def build_general_distribution_xlsx(session, organization, candidate_id: str, fields=None, labels=None) -> bytes:
    fields = fields or REPORT_FIELDS[GENERAL_DISTRIBUTION_XLSX_REPORT_TYPE]
    labels = labels or {}
    _school, course_names, rooms = _report_context(session, organization, candidate_id)
    rows = [[labels.get(field, REPORT_FIELD_LABELS[field]) for field in fields]]
    for classroom, _layout, seats in rooms:
        for seat, student in seats:
            if student is None or not seat.is_available:
                continue
            values = {
                "room": classroom.name, "seat": seat.seat_number,
                "school_number": student.school_number,
                "name": f"{student.first_name} {student.last_name}",
                "class": f"{student.class_level}/{student.section}",
                "area": student.area or "", "courses": " · ".join(course_names),
            }
            rows.append([values[field] for field in fields])
    return _write_workbook([("Genel dağıtım", rows)])


def build_class_student_list_xlsx(session, organization, candidate_id: str,
                                  fields=None, labels=None) -> bytes:
    fields = fields or REPORT_FIELDS[CLASS_STUDENT_LIST_XLSX_REPORT_TYPE]
    labels = labels or {}
    _school, _courses, rooms = _report_context(session, organization, candidate_id)
    grouped = {}
    for classroom, _layout, seats in rooms:
        for seat, student in seats:
            if student is None or not seat.is_available:
                continue
            key = (student.class_level, student.section)
            values = {
                "room": classroom.name, "seat": seat.seat_number,
                "school_number": student.school_number,
                "name": f"{student.first_name} {student.last_name}",
                "class": f"{student.class_level}/{student.section}",
                "area": student.area or "",
            }
            grouped.setdefault(key, []).append([values[field] for field in fields])
    sheets = []
    for (class_level, section), students in sorted(
        grouped.items(), key=lambda item: (int(item[0][0]), item[0][1])
    ):
        name_index = fields.index("name") if "name" in fields else None
        school_number_index = fields.index("school_number") if "school_number" in fields else None
        if name_index is not None:
            students.sort(key=lambda row: (str(row[name_index]).casefold(),
                                           str(row[school_number_index]) if school_number_index is not None else ""))
        sheets.append((f"{class_level}-{section}", [[
            labels.get(field, REPORT_FIELD_LABELS[field]) for field in fields
        ], *students]))
    if not sheets:
        raise ValueError("Sınıf listesi oluşturmak için yerleşmiş öğrenci bulunamadı.")
    return _write_workbook(sheets)


def _draw_fitted_text(pdf, text: str, x: float, y: float, max_width: float,
                      font: str, size: float, minimum_size: float, align: str = "left") -> None:
    while size > minimum_size and pdfmetrics.stringWidth(text, font, size) > max_width:
        size = max(minimum_size, size - 0.5)
    if pdfmetrics.stringWidth(text, font, size) > max_width:
        while text and pdfmetrics.stringWidth(text + "...", font, size) > max_width:
            text = text[:-1]
        text = text.rstrip() + "..."
    pdf.setFont(font, size)
    if align == "right":
        pdf.drawRightString(x, y, text)
    else:
        pdf.drawString(x, y, text)


def _draw_seat(pdf, seat, student, x: float, y: float, width: float, height: float, regular: str, bold: str) -> None:
    if not seat.is_available:
        fill = (0.98, 0.91, 0.89)
        label_color = (0.66, 0.27, 0.23)
    elif student:
        fill = (0.89, 0.93, 1.0)
        label_color = (0.18, 0.31, 0.57)
    else:
        fill = (0.91, 0.96, 0.93)
        label_color = (0.17, 0.42, 0.31)

    pdf.setFillColorRGB(*fill)
    pdf.setStrokeColorRGB(0.78, 0.82, 0.85)
    pdf.roundRect(x, y, width, height, 4, fill=1, stroke=1)
    pdf.setFillColorRGB(*label_color)
    pdf.setFont(bold, max(4.7, min(6.3, width / 11)))
    pdf.drawString(x + 3, y + height - 8, f"Koltuk {seat.seat_number}")

    if not seat.is_available:
        pdf.setFont(regular, 5.2)
        pdf.drawCentredString(x + width / 2, y + max(5, height / 2 - 2), "Kullanım dışı")
        return
    if not student:
        pdf.setFont(regular, 5.5)
        pdf.drawCentredString(x + width / 2, y + max(5, height / 2 - 2), "Boş yer")
        return

    text_width = max(14, width - 6)
    pdf.setFillColorRGB(0.2, 0.24, 0.3)
    compact = height < 38
    pdf.setFont(bold, max(4.3, min(5.7, width / 14)))
    pdf.drawString(x + 3, y + height - (14 if compact else 18), f"{student.class_level}/{student.section}")
    name_lines, name_size = _fit_name(student.first_name, student.last_name, text_width, regular)
    if compact:
        name_lines = simpleSplit(f"{student.first_name[:1]}. {student.last_name}", regular, 4.4, text_width)
        name_size = 4.4
    pdf.setFont(regular, name_size)
    name_y = y + height - (21 if compact else 30)
    for line in name_lines:
        if name_y < y + 7:
            break
        pdf.drawString(x + 3, name_y, line)
        name_y -= name_size + 1
    if height >= 32:
        pdf.setFillColorRGB(0.37, 0.42, 0.49)
        pdf.setFont(regular, max(4.1, min(5.2, width / 15)))
        pdf.drawString(x + 3, y + 3, student.school_number)


def _draw_room_page(pdf, school_name: str, organization: ExamOrganization, course_names: list[str],
                    classroom: Classroom, layout: ClassroomLayout, desks: list[Desk],
                    seats_by_desk: dict[str, list[Seat]], students_by_seat: dict[str, ExamParticipant],
                    page_index: int, page_count: int, regular: str, bold: str,
                    page_size=PAGE_SIZE, margin=28) -> None:
    page_width, page_height = page_size
    pdf.setFillColorRGB(0.10, 0.22, 0.28)
    _draw_fitted_text(pdf, school_name or "Kelebek Sınav Sistemi", margin, page_height - 35,
                      page_width - 2 * margin, bold, 16, 9)
    pdf.setFont(bold, 12)
    pdf.drawString(margin, page_height - 55, "SINAV OTURMA PLANI")
    pdf.setFillColorRGB(0.35, 0.41, 0.47)
    _draw_fitted_text(pdf, organization.name, page_width - margin, page_height - 55,
                      page_width - 2 * margin, regular, 9, 5.5, "right")
    course_label = " · ".join(course_names) if course_names else "Genel sınav"
    exam_label = f"{organization.exam_date.strftime('%d.%m.%Y')}  ·  {course_label}"
    _draw_fitted_text(pdf, exam_label, margin, page_height - 73,
                      page_width - 2 * margin, regular, 9, 5.5)
    pdf.setFont(bold, 10)
    pdf.setFillColorRGB(0.15, 0.38, 0.34)
    _draw_fitted_text(pdf, f"{classroom.name}  ·  {layout.name}", margin, page_height - 96,
                      page_width - 2 * margin, bold, 10, 6)
    pdf.setStrokeColorRGB(0.83, 0.87, 0.88)
    pdf.line(margin, page_height - 105, page_width - margin, page_height - 105)

    plan_left = margin + 36
    plan_right = page_width - margin - 12
    plan_top = page_height - 137
    plan_bottom = margin + 10
    grid_step = 2.0
    min_x = min((desk.x for desk in desks), default=0)
    min_y = min((desk.y for desk in desks), default=0)
    max_column = max((round((desk.x - min_x) / grid_step) for desk in desks), default=0)
    max_row = max((round((desk.y - min_y) / grid_step) for desk in desks), default=0)
    column_count = max_column + 1
    row_count = max_row + 1
    cell_width = (plan_right - plan_left) / max(1, column_count)
    cell_height = (plan_top - plan_bottom) / max(1, row_count)
    card_width = max(38, cell_width - 8)
    max_seats = max((len(seats_by_desk.get(desk.id, [])) for desk in desks), default=1)
    card_height = min(cell_height - 7, max(48, 34 + max_seats * 14))
    card_height = max(30, card_height)

    board_width = min(190, max(112, plan_right - plan_left - 20))
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setStrokeColorRGB(0.72, 0.78, 0.81)
    pdf.roundRect((page_width - board_width) / 2, plan_top + 7, board_width, 17, 4, fill=1, stroke=1)
    pdf.setFillColorRGB(0.41, 0.49, 0.53)
    pdf.setFont(bold, 7)
    pdf.drawCentredString(page_width / 2, plan_top + 12, "TAHTA / ÖĞRETMEN MASASI")

    column_positions = sorted({round((desk.x - min_x) / grid_step) for desk in desks})
    for left_column, right_column in zip(column_positions, column_positions[1:]):
        if right_column - left_column > 1:
            aisle_x = plan_left + ((left_column + right_column) / 2 + 0.5) * cell_width
            pdf.saveState()
            pdf.translate(aisle_x, (plan_top + plan_bottom) / 2)
            pdf.rotate(90)
            pdf.setFillColorRGB(0.65, 0.47, 0.2)
            pdf.setFont(bold, 5.5)
            pdf.drawCentredString(0, 0, "KORİDOR")
            pdf.restoreState()

    for desk in desks:
        column = round((desk.x - min_x) / grid_step)
        row = round((desk.y - min_y) / grid_step)
        x = plan_left + column * cell_width + (cell_width - card_width) / 2
        y = plan_top - (row + 1) * cell_height + (cell_height - card_height) / 2
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setStrokeColorRGB(0.72, 0.79, 0.81)
        pdf.roundRect(x, y, card_width, card_height, 5, fill=1, stroke=1)
        pdf.setFillColorRGB(0.35, 0.43, 0.46)
        pdf.setFont(bold, max(5, min(7, card_width / 18)))
        desk_title = f"{desk.block_label} · {desk.label}" if desk.block_label else desk.label or "Masa"
        pdf.drawCentredString(x + card_width / 2, y + card_height - 9, desk_title[:36])
        seats = seats_by_desk.get(desk.id, [])
        seat_gap = 3
        seat_width = (card_width - 8 - seat_gap * max(0, len(seats) - 1)) / max(1, len(seats))
        seat_height = max(18, card_height - 15)
        seat_y = y + 3
        for index, seat in enumerate(seats):
            seat_x = x + 4 + index * (seat_width + seat_gap)
            _draw_seat(pdf, seat, students_by_seat.get(seat.id), seat_x, seat_y, seat_width, seat_height, regular, bold)

    pdf.setStrokeColorRGB(0.87, 0.89, 0.9)
    pdf.line(margin, max(17, margin - 6), page_width - margin, max(17, margin - 6))
    pdf.setFillColorRGB(0.47, 0.52, 0.57)
    pdf.setFont(regular, 7)
    total_students = sum(1 for seat_id in students_by_seat if seat_id in {seat.id for desk in desks for seat in seats_by_desk.get(desk.id, [])})
    footer_y = max(5, margin - 21)
    pdf.drawString(margin, footer_y, f"{total_students} öğrenci  ·  {len(desks)} masa  ·  {sum(len(seats_by_desk.get(desk.id, [])) for desk in desks)} koltuk")
    pdf.drawRightString(page_width - margin, footer_y, f"{page_index}/{page_count}")
    pdf.showPage()


def build_seating_plan_pdf(session, organization: ExamOrganization, candidate_id: str, options=None) -> bytes:
    """Build one A4 landscape page for every selected classroom layout."""
    options = options or resolve_pdf_options(default_orientation="landscape")
    page_size = options["page_size"]
    margin = options["margin_points"]
    school = session.get(SchoolProfile, 1)
    school_name = school.school_name.strip() if school and school.school_name.strip() else "Kelebek Sınav Sistemi"
    course_names = session.scalars(
        select(Course.name)
        .join(ExamCourse, ExamCourse.course_id == Course.id)
        .where(ExamCourse.organization_id == organization.id)
        .order_by(ExamCourse.display_order)
    ).all()
    assignments = session.execute(
        select(SeatAssignment.seat_id, ExamParticipant)
        .join(ExamParticipant, ExamParticipant.id == SeatAssignment.participant_id)
        .where(ExamParticipant.is_active.is_(True))
        .where(SeatAssignment.candidate_id == candidate_id, SeatAssignment.seat_id.is_not(None))
    ).all()
    students_by_seat = {seat_id: participant for seat_id, participant in assignments}
    selections = session.execute(
        select(Classroom, ClassroomLayout)
        .join(ExamOrganizationClassroom, ExamOrganizationClassroom.classroom_id == Classroom.id)
        .join(ClassroomLayout, ClassroomLayout.id == ExamOrganizationClassroom.layout_id)
        .where(ExamOrganizationClassroom.organization_id == organization.id)
        .order_by(Classroom.name)
    ).all()
    if not selections:
        raise ValueError("PDF oluşturmak için seçili derslik düzeni bulunamadı.")

    regular, bold = _register_fonts()
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=page_size, pageCompression=1)
    pdf.setTitle(f"{organization.name} - Oturma Planı")
    pdf.setAuthor(school_name)
    for page_index, (classroom, layout) in enumerate(selections, start=1):
        desks = session.scalars(
            select(Desk).where(Desk.layout_id == layout.id).order_by(Desk.y, Desk.x)
        ).all()
        seats_by_desk = {}
        for seat in session.scalars(
            select(Seat).where(Seat.layout_id == layout.id).order_by(Seat.seat_index)
        ).all():
            seats_by_desk.setdefault(seat.desk_id, []).append(seat)
        _draw_room_page(
            pdf, school_name, organization, course_names, classroom, layout, desks,
            seats_by_desk, students_by_seat, page_index, len(selections), regular, bold,
            page_size, margin,
        )
    pdf.save()
    output.seek(0)

    export_dir = get_data_dir() / "Exports" / "PDF"
    export_dir.mkdir(parents=True, exist_ok=True)
    report_path = export_dir / seating_plan_report_filename(organization)
    report_path.write_bytes(output.getvalue())
    return output.getvalue()
