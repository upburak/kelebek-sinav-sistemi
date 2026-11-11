"""Öğrenci Excel/PDF listelerini önizleme, doğrulama ve onaylı aktarım."""

import json
import re
from datetime import date, datetime, time
from io import BytesIO

from flask import Blueprint, current_app, jsonify, request, send_file
from sqlalchemy import func, select

from kelebek.db import current_academic_year_start
from kelebek.services.backup import create_safety_backup
from kelebek.services.layouts import ensure_active_layout
from kelebek.services.student_import import auto_map_headers, read_student_tables
from kelebek.services.student_registry import (
    deactivate_student_in_year,
    sync_draft_exam_snapshots,
)

student_import_api = Blueprint("student_import", __name__)
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
PREVIEW_ROWS = 5
REQUIRED_FIELDS = ("school_number", "first_name", "last_name", "class_level", "section")
FIELD_LABELS = {
    "school_number": "Okul numarası",
    "first_name": "Ad",
    "last_name": "Soyad",
    "class_level": "Sınıf",
    "section": "Şube",
    "area": "Alan",
}
BLOCKS_PER_ROOM = 3  # iki koridorla ayrılmış üç blok

AREA_OPTIONS = {"Sayısal", "Eşit Ağırlık", "Sözel", "Dil"}
@student_import_api.get("/student-import/template")
def download_student_template():
    """İndirmek için örnek satırlı, sentetik öğrenci Excel şablonu üret."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Öğrenci Şablonu"
    headers = ["Okul No", "Ad", "Soyad", "Sınıf", "Şube", "Alan"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(name="Aptos", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="173B57")
        cell.alignment = Alignment(vertical="center")
    examples = [
        ["ÖRNEK-001", "ÖRNEK AD", "ÖRNEK SOYAD", 9, "A", ""],
        ["ÖRNEK-002", "DENEME AD", "DENEME SOYAD", 10, "B", ""],
        ["ÖRNEK-003", "SENTETİK AD", "SENTETİK SOYAD", 11, "A", "Sayısal"],
    ]
    for row in examples:
        sheet.append(row)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:F{sheet.max_row}"
    sheet.row_dimensions[1].height = 25
    for column, width in enumerate((18, 22, 24, 14, 14, 20), start=1):
        sheet.column_dimensions[get_column_letter(column)].width = width
    notes = workbook.create_sheet("Bilgi")
    notes.append(["Bu dosyadaki tüm öğrenci bilgileri sentetiktir; gerçek kişi değildir."])
    notes.append(["Örnek satırları silip kendi listenizi ekleyebilirsiniz."])
    notes.append(["Zorunlu başlıklar: Okul No, Ad, Soyad, Sınıf, Şube. Alan isteğe bağlıdır."])
    notes.append(["Sınıf 11–12 öğrencilerinde Alan boşsa aktarım öncesi uygulama içinden atanır."])
    notes.column_dimensions["A"].width = 100
    for row in notes.iter_rows():
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="kelebek_ogrenci_sablonu_ornek_verili.xlsx",
    )


@student_import_api.get("/student-import/sample")
def download_student_sample():
    """Tamamen sentetik, dengeli sınıf dağılımlı örnek XLSX üret."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    from kelebek.demo_data import build_demo_student_records

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "SENTETİK DEMO"
    headers = ["Okul No", "Ad", "Soyad", "Sınıf", "Şube", "Alan"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="146B68")
        cell.alignment = Alignment(vertical="center")
    for record in build_demo_student_records():
        sheet.append([
            record["school_number"], record["first_name"], record["last_name"],
            int(record["class_level"]), record["section"], record["area"],
        ])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:F{sheet.max_row}"
    sheet.row_dimensions[1].height = 25
    for column, width in enumerate((18, 24, 28, 13, 13, 20), start=1):
        sheet.column_dimensions[get_column_letter(column)].width = width

    notes = workbook.create_sheet("ÖNCE OKUYUN")
    notes.append(["UYARI: Bu çalışma kitabındaki tüm kayıtlar tamamen sentetiktir; gerçek öğrenci değildir."])
    notes.append(["Test için 9, 10, 11 ve 12. sınıflardan toplam 48 örnek öğrenci içerir."])
    notes.append(["Okul numaraları DEMO ile başlar; örnek ad ve soyadlar özellikle gerçek dışı tutulmuştur."])
    notes.append(["Dosyayı uygulamaya aktarırsanız örnek kayıtlar seçili eğitim yılına kaydedilir."])
    notes.column_dimensions["A"].width = 110
    for row in notes.iter_rows():
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="kelebek_sentetik_demo_48_ogrenci.xlsx",
    )


def _json_value(value):
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _validate_rows(tables, mapping):
    if not isinstance(mapping, dict):
        return {"error": "Sütun eşleştirmesi geçersiz."}, 400

    first_table_mapping = auto_map_headers(tables[0].headers) if tables else {}
    counts = {}
    seen_school_numbers = {}
    issues = []
    records = []
    total_rows = 0
    upper_grade_missing_area = 0
    missing_area_counts = {}

    for table in tables:
        detected = auto_map_headers(table.headers)
        normalized = {}
        for field in (*REQUIRED_FIELDS, "area"):
            index = mapping.get(field)
            if index in (None, ""):
                index = detected.get(field)
            if index == "__context__":
                if (field == "class_level" and table.class_level) or (
                    field == "section" and table.section
                ):
                    normalized[field] = None
                    continue
                index = detected.get(field)
            elif field in detected and field in first_table_mapping:
                # The initial UI mapping reflects the first source. Keep that
                # choice automatic across sheets when the user has not changed
                # it, so a different column order cannot shift student fields.
                try:
                    selected_index = int(index)
                except (TypeError, ValueError):
                    selected_index = None
                if selected_index == first_table_mapping[field]:
                    index = detected[field]
            if index in (None, ""):
                if field == "class_level" and table.class_level:
                    normalized[field] = None
                    continue
                if field == "section" and table.section:
                    normalized[field] = None
                    continue
                if field in REQUIRED_FIELDS:
                    return {"error": f"{table.name}: {FIELD_LABELS[field]} sütununu veya sınıf başlığını belirleyin."}, 400
                continue
            try:
                index = int(index)
            except (TypeError, ValueError):
                return {"error": "Sütun eşleştirmesi geçersiz."}, 400
            if index < 0 or index >= len(table.headers):
                return {"error": "Sütun eşleştirmesi dosya başlıklarıyla eşleşmiyor."}, 400
            normalized[field] = index

        column_indexes = [index for index in normalized.values() if index is not None]
        if len(set(column_indexes)) != len(column_indexes):
            return {"error": "Her bilgi için farklı bir sütun seçin."}, 400

        data_start = max(0, table.header_index + 1)
        student_rows_started = False
        blank_rows_after_students = 0
        trailing_section_started = False
        for row_number, row in enumerate(table.rows[data_start:], start=table.header_row + 1):
            values = {
                field: _cell_text(row[index] if index < len(row) else None)
                for field, index in normalized.items()
                if index is not None
            }
            if "class_level" not in values or not values.get("class_level"):
                values["class_level"] = table.class_level or ""
            else:
                grade_match = re.fullmatch(
                    r"\s*(9|10|11|12)\s*(?:\.?\s*(?:sınıf|sinif))?\s*",
                    values["class_level"],
                    re.IGNORECASE,
                )
                if grade_match:
                    values["class_level"] = grade_match.group(1)
            if "section" not in values or not values.get("section"):
                values["section"] = table.section or ""
            else:
                values["section"] = values["section"].upper()

            core_values = [
                values.get(field, "")
                for field in ("school_number", "first_name", "last_name")
            ]
            populated_core_fields = sum(bool(value) for value in core_values)
            if populated_core_fields == 0:
                if student_rows_started:
                    blank_rows_after_students += 1
                continue
            core_formula = any(
                (row_number - 1, normalized[field]) in table.formula_cells
                for field in ("school_number", "first_name", "last_name")
            )
            if blank_rows_after_students >= 2 and core_formula:
                # Some spreadsheets append formula-driven summary or signature
                # rows after the roster. A blank gap plus formulas marks that
                # trailing section; blank gaps alone never discard students.
                trailing_section_started = True
            if trailing_section_started:
                continue
            blank_rows_after_students = 0
            if populated_core_fields >= 2:
                student_rows_started = True
            elif not student_rows_started:
                # Ignore isolated labels before the actual roster begins.
                continue

            total_rows += 1
            missing = [field for field in REQUIRED_FIELDS if not values.get(field)]
            if missing:
                issues.append({
                    "row": row_number,
                    "source": table.name,
                    "fields": [FIELD_LABELS[field] for field in missing],
                    "issue": "Zorunlu bilgi boş",
                })
            if values.get("class_level") and values["class_level"] not in {"9", "10", "11", "12"}:
                issues.append({
                    "row": row_number,
                    "source": table.name,
                    "fields": [FIELD_LABELS["class_level"]],
                    "issue": "Sınıf seviyesi 9, 10, 11 veya 12 olmalı",
                })

            school_number = values.get("school_number", "")
            if school_number:
                if school_number in seen_school_numbers:
                    issues.append({
                        "row": row_number,
                        "source": table.name,
                        "fields": [FIELD_LABELS["school_number"]],
                        "issue": f"Okul numarası {seen_school_numbers[school_number]} kaynağında da bulunuyor",
                    })
                else:
                    seen_school_numbers[school_number] = table.name

            if values.get("class_level") and values.get("section"):
                key = (values["class_level"], values["section"])
                counts[key] = counts.get(key, 0) + 1
            if values.get("class_level", "").strip() in {"11", "12"} and not values.get("area"):
                upper_grade_missing_area += 1
                key = (values.get("class_level", ""), values.get("section", ""))
                missing_area_counts[key] = missing_area_counts.get(key, 0) + 1
            if not missing:
                records.append(values)

    if total_rows == 0:
        return {"error": "Başlık satırından sonra öğrenci satırı bulunamadı."}, 400

    return {
        "validation": {
            "total_rows": total_rows,
            "valid": len(issues) == 0,
            "issue_count": len(issues),
            "issues": issues[:50],
            "issues_truncated": len(issues) > 50,
            "upper_grade_missing_area": upper_grade_missing_area,
            "missing_area_by_class": [
                {"class_level": grade, "section": section, "student_count": count}
                for (grade, section), count in sorted(missing_area_counts.items())
            ],
            "classes": [
                {"class_level": grade, "section": section, "student_count": count}
                for (grade, section), count in sorted(counts.items())
            ],
        },
        "records": records,
    }, 200


def _apply_area_assignments(records, assignments):
    if not isinstance(assignments, dict):
        return [], 0, "Alan eşleştirmeleri geçersiz."

    remaining_by_class = {}
    for record in records:
        grade = record.get("class_level", "").strip()
        section = record.get("section", "").strip()
        if grade not in {"11", "12"} or record.get("area"):
            continue
        key = f"{grade}/{section}"
        area = assignments.get(key)
        if area is not None and area not in AREA_OPTIONS:
            return [], 0, "Seçilen alan seçeneklerden biriyle eşleşmiyor."
        if area:
            record["area"] = area
        else:
            remaining_by_class[key] = remaining_by_class.get(key, 0) + 1

    missing = [
        {
            "class_level": key.split("/", 1)[0],
            "section": key.split("/", 1)[1],
            "student_count": count,
        }
        for key, count in sorted(remaining_by_class.items())
    ]
    return missing, sum(remaining_by_class.values()), None


def _build_diff_report(session, academic_year_id, imported_records, area_mapped):
    from kelebek.models import StudentYearEnrollment

    existing = session.scalars(
        select(StudentYearEnrollment).where(
            StudentYearEnrollment.academic_year_id == academic_year_id,
            StudentYearEnrollment.is_active.is_(True),
        )
    ).all()
    existing_by_number = {item.school_number: item for item in existing}
    imported_by_number = {item["school_number"]: item for item in imported_records}

    def display(record):
        return {
            "school_number": record["school_number"],
            "name": (record["first_name"] + " " + record["last_name"]).strip(),
            "class_level": record["class_level"],
            "section": record["section"],
        }

    new_students, departed_students, changed_students, reassigned_numbers, unchanged = [], [], [], [], []
    for school_number, imported in imported_by_number.items():
        old = existing_by_number.get(school_number)
        if old is None:
            new_students.append(display(imported))
            continue

        if (old.first_name.strip().casefold(), old.last_name.strip().casefold()) != (
            imported["first_name"].casefold(), imported["last_name"].casefold()
        ):
            reassigned_numbers.append(
                {
                    "school_number": school_number,
                    "previous_name": (old.first_name + " " + old.last_name).strip(),
                    "incoming_name": (imported["first_name"] + " " + imported["last_name"]).strip(),
                }
            )
            continue

        changed_fields = []
        for field, label, previous in (
            ("class_level", "Sınıf", old.class_level),
            ("section", "Şube", old.section),
        ):
            if previous.strip() != imported[field]:
                changed_fields.append(label)
        if area_mapped and imported.get("area", "") and (old.area or "").strip() != imported["area"]:
            changed_fields.append("Alan")
        row = display(imported)
        if changed_fields:
            changed_students.append({**row, "changed_fields": changed_fields})
        else:
            unchanged.append(row)

    departed_students.extend(
        display(
            {
                "school_number": item.school_number,
                "first_name": item.first_name,
                "last_name": item.last_name,
                "class_level": item.class_level,
                "section": item.section,
            }
        )
        for school_number, item in existing_by_number.items()
        if school_number not in imported_by_number
    )

    return {
        "new_students": new_students,
        "departed_students": departed_students,
        "changed_students": changed_students,
        "reassigned_numbers": reassigned_numbers,
        "unchanged_count": len(unchanged),
    }


@student_import_api.post("/student-import/preview")
def preview_student_workbook():
    """XLSX/PDF içeriğini diske veya veritabanına yazmadan okuyup önizle."""
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({"error": "Önizleme için .xlsx veya .pdf dosyası seçin."}), 400

    content = uploaded_file.stream.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        return jsonify({"error": "Seçilen dosya boş."}), 400
    if len(content) > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Dosya boyutu 12 MB sınırını aşıyor."}), 413

    try:
        tables = read_student_tables(content, uploaded_file.filename)
        mapping_raw = request.form.get("mapping")
        if mapping_raw is not None:
            try:
                mapping = json.loads(mapping_raw)
            except json.JSONDecodeError:
                return jsonify({"error": "Sütun eşleştirmesi okunamadı."}), 400
            result, status = _validate_rows(tables, mapping)
            if status != 200:
                return jsonify(result), status
            records = result.pop("records")
            validation = result["validation"]
            try:
                area_assignments = json.loads(request.form.get("area_assignments", "{}"))
            except json.JSONDecodeError:
                return jsonify({"error": "Sınıf alan atamaları okunamadı."}), 400
            missing_areas, missing_area_count, area_error = _apply_area_assignments(
                records, area_assignments
            )
            if area_error:
                return jsonify({"error": area_error}), 400
            validation["missing_area_by_class"] = missing_areas
            validation["upper_grade_missing_area"] = missing_area_count
            validation["area_assignment_complete"] = missing_area_count == 0
            diff_report = None
            academic_year_id = request.form.get("academic_year_id")
            if validation["valid"] and validation["area_assignment_complete"] and academic_year_id:
                from kelebek.models import AcademicYear

                session_factory = current_app.extensions["kelebek_session_factory"]
                with session_factory() as session:
                    if session.get(AcademicYear, academic_year_id) is None:
                        return jsonify({"error": "Seçili eğitim yılı bulunamadı."}), 404
                    diff_report = _build_diff_report(
                        session,
                        academic_year_id,
                        records,
                        ("area" in mapping and mapping["area"] not in (None, "", "__context__"))
                        or bool(area_assignments),
                    )
            return jsonify(
                {
                    "filename": uploaded_file.filename,
                    "sheet_name": tables[0].name,
                    "sheet_names": [table.name for table in tables],
                    "header_row": tables[0].header_row,
                    "headers": tables[0].headers,
                    "auto_mapping": _preview_mapping(tables[0]),
                    "saved": False,
                    **result,
                    "diff": diff_report,
                }
            )

        table = tables[0]
        preview_rows = []
        for row in table.rows[table.header_index + 1:]:
            values = [_json_value(value) for value in row]
            if any(value not in (None, "") for value in values):
                preview_rows.append(values[: len(table.headers)])
                if len(preview_rows) == PREVIEW_ROWS:
                    break

        return jsonify(
            {
                "filename": uploaded_file.filename,
                "sheet_name": table.name,
                "sheet_names": [item.name for item in tables],
                "sources": [
                    {
                        "name": item.name,
                        "header_row": item.header_row,
                        "class_level": item.class_level,
                        "section": item.section,
                        "auto_mapping": _preview_mapping(item),
                    }
                    for item in tables
                ],
                "header_row": table.header_row,
                "headers": table.headers,
                "auto_mapping": _preview_mapping(table),
                "preview_rows": preview_rows,
                "saved": False,
            }
        )
    except (RuntimeError, ValueError) as error:
        status = 503 if isinstance(error, RuntimeError) else 400
        return jsonify({"error": str(error)}), status


def _preview_mapping(table):
    mapping = auto_map_headers(table.headers)
    if table.class_level and "class_level" not in mapping:
        mapping["class_level"] = "__context__"
    if table.section and "section" not in mapping:
        mapping["section"] = "__context__"
    return mapping


def _ensure_classrooms_for_groups(session, academic_year_id, groups):
    """Create an editable current-year capacity draft without replacing layouts."""
    from math import ceil

    from kelebek.models import (
        AcademicYear,
        Classroom,
        ClassroomLayout,
        Desk,
        Seat,
    )

    year = session.get(AcademicYear, academic_year_id)
    results = []
    for group in groups:
        grade = str(group["class_level"])
        section = str(group["section"])
        requested_seats = int(group["student_count"])
        if requested_seats < 1:
            continue
        if requested_seats > 600:
            results.append({
                "name": f"{grade}-{section} Derslik",
                "class_level": grade,
                "section": section,
                "requested_capacity": requested_seats,
                "created": False,
                "needs_review": True,
                "message": "600 kişilik tek düzen sınırını aştığı için elle planlanmalı.",
            })
            continue

        desired_name = f"{grade}-{section} Derslik"
        existing = session.scalars(select(Classroom)).all()
        classroom = next(
            (item for item in existing if item.name.casefold() == desired_name.casefold()),
            None,
        )
        created = classroom is None
        if classroom is None:
            classroom = Classroom(name=desired_name)
            session.add(classroom)
            session.flush()

        layouts = session.scalars(
            select(ClassroomLayout)
            .where(
                ClassroomLayout.classroom_id == classroom.id,
                ClassroomLayout.academic_year_id == academic_year_id,
            )
            .order_by(ClassroomLayout.version.desc(), ClassroomLayout.created_at.desc())
        ).all()
        layout = layouts[0] if layouts else None
        if layout is None:
            layout = ClassroomLayout(
                classroom_id=classroom.id,
                academic_year_id=academic_year_id,
                name=f"{year.label} liste başlangıç düzeni",
                version=1,
            )
            session.add(layout)
            session.flush()
            ensure_active_layout(session, layout)

        desk_count = session.scalar(select(func.count(Desk.id)).where(Desk.layout_id == layout.id)) or 0
        generated = False
        if desk_count == 0:
            # Türkiye'deki olağan derslik düzeni: iki koridorla ayrılmış üç blok
            # çiftli masa. Örneğin 36 kişilik sınıf 3 blok × 6 satır olur.
            # Koridor, ızgarada bir sütun atlanarak temsil edilir; komşuluk
            # hesabı (build_neighbor_pairs) bu boşluğu görüp koridorun iki yanını
            # yan yana saymaz. Bu yalnızca başlangıç taslağıdır; kullanıcı gerçek
            # sınıf ölçülerine göre düzenler.
            columns = max(1, min(BLOCKS_PER_ROOM, ceil(requested_seats / 2)))
            rows = ceil(requested_seats / columns / 2)
            seat_number = 1
            remaining = requested_seats
            for row in range(rows):
                for column in range(columns):
                    if remaining <= 0:
                        break
                    x = float(column * 4)
                    block_label = f"B{column + 1}"
                    seats_in_desk = min(2, remaining)
                    desk = Desk(
                        layout_id=layout.id,
                        label=f"S{row + 1}-M{column + 1}",
                        block_label=block_label,
                        x=x,
                        y=float(row * 2),
                        rotation_degrees=0,
                    )
                    session.add(desk)
                    session.flush()
                    for seat_index in range(1, seats_in_desk + 1):
                        session.add(Seat(
                            layout_id=layout.id,
                            desk_id=desk.id,
                            seat_number=seat_number,
                            seat_index=seat_index,
                            x=x + 0.25 + (seat_index - 1) * 0.45,
                            y=float(row * 2),
                            is_available=True,
                        ))
                        seat_number += 1
                    remaining -= seats_in_desk
            generated = True

        actual_seats = session.scalar(
            select(func.count(Seat.id)).where(Seat.layout_id == layout.id)
        ) or 0
        results.append({
            "name": classroom.name,
            "class_level": grade,
            "section": section,
            "requested_capacity": requested_seats,
            "capacity": actual_seats,
            "created": created,
            "layout_created": generated,
            "needs_review": actual_seats != requested_seats,
            "message": (
                "Fiziksel sıra düzeni kullanıcı tarafından doğrulanıp ayarlanmalı."
                if generated
                else "Mevcut düzen korunuyor; mevcut ve kapasiteyi fiziksel duruma göre kontrol edin."
            ),
        })
    return results


@student_import_api.post("/student-import/commit")
def commit_student_workbook():
    """Kullanıcı onayıyla doğrulanmış listeyi seçili yıla aktar."""
    if request.form.get("confirm") != "true":
        return jsonify({"error": "İçe aktarma için açık onay gereklidir."}), 400

    uploaded_file = request.files.get("file")
    academic_year_id = request.form.get("academic_year_id")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({"error": "İçe aktarılacak .xlsx veya .pdf dosyasını seçin."}), 400
    if not academic_year_id:
        return jsonify({"error": "Eğitim-öğretim yılı seçili değil."}), 400

    content = uploaded_file.stream.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        return jsonify({"error": "Seçilen dosya boş."}), 400
    if len(content) > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Dosya boyutu 12 MB sınırını aşıyor."}), 413
    try:
        tables = read_student_tables(content, uploaded_file.filename)
    except (RuntimeError, ValueError) as error:
        status = 503 if isinstance(error, RuntimeError) else 400
        return jsonify({"error": str(error)}), status

    try:
        mapping = json.loads(request.form.get("mapping", ""))
    except json.JSONDecodeError:
        return jsonify({"error": "Sütun eşleştirmesi okunamadı."}), 400
    try:
        area_assignments = json.loads(request.form.get("area_assignments", "{}"))
    except json.JSONDecodeError:
        return jsonify({"error": "Sınıf alan atamaları okunamadı."}), 400
    result, status = _validate_rows(tables, mapping)
    if status != 200:
        return jsonify(result), status
    records = result.pop("records")
    if not result["validation"]["valid"]:
        return jsonify({"error": "Dosyada düzeltilmesi gereken satırlar var.", **result}), 422
    missing_areas, missing_area_count, area_error = _apply_area_assignments(
        records, area_assignments
    )
    if area_error:
        return jsonify({"error": area_error}), 400
    if missing_area_count:
        return jsonify(
            {
                "error": "11–12. sınıfların alan atamalarını tamamlayın.",
                "missing_area_by_class": missing_areas,
            }
        ), 422

    from kelebek.models import AcademicYear, Student, StudentYearEnrollment

    session_factory = current_app.extensions["kelebek_session_factory"]
    area_mapped = mapping.get("area") not in (None, "") or bool(area_assignments)
    incoming_by_number = {row["school_number"]: row for row in records}
    with session_factory.begin() as session:
        academic_year = session.get(AcademicYear, academic_year_id)
        if academic_year is None:
            return jsonify({"error": "Seçili eğitim yılı bulunamadı."}), 404
        if academic_year.start_year < current_academic_year_start():
            return jsonify({"error": "Arşiv eğitim yılları salt okunur olduğu için liste aktarılamaz."}), 403

        old_rows = session.scalars(
            select(StudentYearEnrollment).where(
                StudentYearEnrollment.academic_year_id == academic_year_id,
                StudentYearEnrollment.is_active.is_(True),
            )
        ).all()
        old_by_number = {row.school_number: row for row in old_rows}
        diff = _build_diff_report(session, academic_year_id, records, area_mapped)
        try:
            safety_backup = create_safety_backup("student-import")
        except Exception:
            current_app.logger.exception("Öğrenci aktarımı öncesi güvenlik yedeği alınamadı.")
            return jsonify({"error": "İşlem öncesi güvenlik yedeği alınamadığı için liste aktarılmadı."}), 500
        created = updated = unchanged = reassigned = deactivated = 0

        for school_number, incoming in incoming_by_number.items():
            old = old_by_number.get(school_number)
            if old is not None and (
                old.first_name.strip().casefold(), old.last_name.strip().casefold()
            ) != (incoming["first_name"].casefold(), incoming["last_name"].casefold()):
                deactivate_student_in_year(session, old)
                deactivated += 1
                reassigned += 1
                session.flush()
                old = None

            if old is None:
                student = Student()
                session.add(student)
                session.flush()
                enrollment = StudentYearEnrollment(
                    academic_year_id=academic_year_id,
                    student_id=student.id,
                    school_number=school_number,
                    first_name=incoming["first_name"],
                    last_name=incoming["last_name"],
                    class_level=incoming["class_level"],
                    section=incoming["section"],
                    area=incoming.get("area") or None,
                )
                session.add(enrollment)
                created += 1
                continue

            was_changed = (
                old.first_name != incoming["first_name"]
                or old.last_name != incoming["last_name"]
                or old.class_level != incoming["class_level"]
                or old.section != incoming["section"]
                or (
                    area_mapped
                    and bool(incoming.get("area"))
                    and (old.area or "") != incoming["area"]
                )
            )
            old.first_name = incoming["first_name"]
            old.last_name = incoming["last_name"]
            old.class_level = incoming["class_level"]
            old.section = incoming["section"]
            if area_mapped and incoming.get("area"):
                old.area = incoming["area"]
            if was_changed:
                sync_draft_exam_snapshots(session, old, deactivate=False)
                updated += 1
            else:
                unchanged += 1

        for school_number, old in old_by_number.items():
            if school_number not in incoming_by_number and old.is_active:
                deactivate_student_in_year(session, old)
                deactivated += 1

        classroom_results = _ensure_classrooms_for_groups(
            session, academic_year_id, result["validation"]["classes"]
        )
        session.flush()

    return jsonify(
        {
            "saved": True,
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
            "deactivated": deactivated,
            "reassigned_school_numbers": reassigned,
            "safety_backup": safety_backup.name,
            "classes": result["validation"]["classes"],
            "classrooms": classroom_results,
            "review": {
                "new": len(diff["new_students"]),
                "departed": len(diff["departed_students"]),
                "changed": len(diff["changed_students"]),
                "unchanged": diff["unchanged_count"],
            },
        }
    )
