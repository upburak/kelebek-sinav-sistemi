"""Kesinleşmiş sınavlar için yerel rapor üretimi."""

import os
import re
import hashlib
import json
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy import select

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


def seating_plan_report_path(file_name: str) -> Path:
    return get_data_dir() / "Exports" / "PDF" / file_name


def report_data_fingerprint(session, organization: ExamOrganization, candidate_id: str) -> str:
    assignments = session.execute(
        select(SeatAssignment.participant_id, SeatAssignment.seat_id,
               ExamParticipant.school_number, ExamParticipant.first_name,
               ExamParticipant.last_name, ExamParticipant.class_level, ExamParticipant.section)
        .join(ExamParticipant, ExamParticipant.id == SeatAssignment.participant_id)
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


def report_status(session, organization: ExamOrganization) -> dict:
    report = session.scalar(select(DistributionReport).where(
        DistributionReport.organization_id == organization.id,
        DistributionReport.report_type == SEATING_PLAN_REPORT_TYPE,
    ))
    if report is None:
        return {"report_status": "not_generated", "report_updated_at": None}
    report_path = seating_plan_report_path(report.file_name)
    current = (
        report.candidate_id == organization.selected_candidate_id
        and report_path.is_file()
        and report.data_fingerprint == report_data_fingerprint(
            session, organization, organization.selected_candidate_id or ""
        )
    )
    return {
        "report_status": "current" if current else "stale",
        "report_updated_at": report.created_at.isoformat(),
    }


def record_seating_plan_report(session, organization: ExamOrganization, candidate_id: str, file_name: str) -> None:
    report = session.scalar(select(DistributionReport).where(
        DistributionReport.organization_id == organization.id,
        DistributionReport.report_type == SEATING_PLAN_REPORT_TYPE,
    ))
    if report is None:
        report = DistributionReport(
            organization_id=organization.id,
            candidate_id=candidate_id,
            report_type=SEATING_PLAN_REPORT_TYPE,
            data_fingerprint=report_data_fingerprint(session, organization, candidate_id),
            file_name=file_name,
        )
        session.add(report)
    else:
        report.candidate_id = candidate_id
        report.data_fingerprint = report_data_fingerprint(session, organization, candidate_id)
        report.file_name = file_name
        report.created_at = datetime.now(timezone.utc)


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
                    page_index: int, page_count: int, regular: str, bold: str) -> None:
    margin = 28
    pdf.setFillColorRGB(0.10, 0.22, 0.28)
    _draw_fitted_text(pdf, school_name or "Kelebek Sınav Sistemi", margin, PAGE_HEIGHT - 35,
                      PAGE_WIDTH - 2 * margin, bold, 16, 9)
    pdf.setFont(bold, 12)
    pdf.drawString(margin, PAGE_HEIGHT - 55, "SINAV OTURMA PLANI")
    pdf.setFillColorRGB(0.35, 0.41, 0.47)
    _draw_fitted_text(pdf, organization.name, PAGE_WIDTH - margin, PAGE_HEIGHT - 55,
                      PAGE_WIDTH - 2 * margin, regular, 9, 5.5, "right")
    course_label = " · ".join(course_names) if course_names else "Genel sınav"
    exam_label = f"{organization.exam_date.strftime('%d.%m.%Y')}  ·  {course_label}"
    _draw_fitted_text(pdf, exam_label, margin, PAGE_HEIGHT - 73,
                      PAGE_WIDTH - 2 * margin, regular, 9, 5.5)
    pdf.setFont(bold, 10)
    pdf.setFillColorRGB(0.15, 0.38, 0.34)
    _draw_fitted_text(pdf, f"{classroom.name}  ·  {layout.name}", margin, PAGE_HEIGHT - 96,
                      PAGE_WIDTH - 2 * margin, bold, 10, 6)
    pdf.setStrokeColorRGB(0.83, 0.87, 0.88)
    pdf.line(margin, PAGE_HEIGHT - 105, PAGE_WIDTH - margin, PAGE_HEIGHT - 105)

    plan_left = margin + 36
    plan_right = PAGE_WIDTH - margin - 12
    plan_top = PAGE_HEIGHT - 137
    plan_bottom = 38
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
    pdf.roundRect((PAGE_WIDTH - board_width) / 2, plan_top + 7, board_width, 17, 4, fill=1, stroke=1)
    pdf.setFillColorRGB(0.41, 0.49, 0.53)
    pdf.setFont(bold, 7)
    pdf.drawCentredString(PAGE_WIDTH / 2, plan_top + 12, "TAHTA / ÖĞRETMEN MASASI")

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
    pdf.line(margin, 25, PAGE_WIDTH - margin, 25)
    pdf.setFillColorRGB(0.47, 0.52, 0.57)
    pdf.setFont(regular, 7)
    total_students = sum(1 for seat_id in students_by_seat if seat_id in {seat.id for desk in desks for seat in seats_by_desk.get(desk.id, [])})
    pdf.drawString(margin, 13, f"{total_students} öğrenci  ·  {len(desks)} masa  ·  {sum(len(seats_by_desk.get(desk.id, [])) for desk in desks)} koltuk")
    pdf.drawRightString(PAGE_WIDTH - margin, 13, f"{page_index}/{page_count}")
    pdf.showPage()


def build_seating_plan_pdf(session, organization: ExamOrganization, candidate_id: str) -> bytes:
    """Build one A4 landscape page for every selected classroom layout."""
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
    pdf = canvas.Canvas(output, pagesize=PAGE_SIZE, pageCompression=1)
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
        )
    pdf.save()
    output.seek(0)

    export_dir = get_data_dir() / "Exports" / "PDF"
    export_dir.mkdir(parents=True, exist_ok=True)
    safe_name = safe_report_stem(organization.name)
    report_path = export_dir / f"{safe_name}-oturma-planlari.pdf"
    report_path.write_bytes(output.getvalue())
    return output.getvalue()
