"""e-Okul Excel dosyaları için kaydetmeden yapılan okuma önizlemesi."""

from datetime import date, datetime, time
from io import BytesIO
import json
import re
import unicodedata
from zipfile import BadZipFile

from flask import Blueprint, current_app, jsonify, request, send_file
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import select

from kelebek.db import current_academic_year_start
from kelebek.services.backup import create_safety_backup


student_import_api = Blueprint("student_import", __name__)
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_HEADER_SCAN_ROWS = 20
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
AREA_OPTIONS = {"Sayısal", "Eşit Ağırlık", "Sözel", "Dil"}
HEADER_ALIASES = {
    "school_number": {"okul no", "okul numarasi", "ogrenci no", "ogrenci numarasi", "okul num", "numara", "no", "school number", "student number"},
    "first_name": {"ad", "adi", "ogrenci adi", "first name", "firstname", "given name"},
    "last_name": {"soyad", "soyadi", "ogrenci soyadi", "last name", "lastname", "surname", "family name"},
    "class_level": {"sinif", "sinif seviyesi", "sinif duzeyi", "sinif kademesi", "grade", "class level", "grade level"},
    "section": {"sube", "sinif subesi", "sube adi", "section", "class section"},
    "area": {"alan", "bolum", "program", "academic area", "field of study"},
}


def _normalize_header(value):
    text = str(value or "").casefold().replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _auto_map_headers(headers):
    normalized_aliases = {
        field: {_normalize_header(alias) for alias in aliases}
        for field, aliases in HEADER_ALIASES.items()
    }
    candidates = {}
    for column, header in enumerate(headers):
        normalized = _normalize_header(header)
        if not normalized:
            continue
        for field, aliases in normalized_aliases.items():
            if normalized in aliases:
                candidates.setdefault(field, []).append(column)
    # Only map a field when exactly one column matches and that column is not
    # also a candidate for another field. Ambiguous workbooks stay editable.
    counts = {}
    for columns in candidates.values():
        for column in columns:
            counts[column] = counts.get(column, 0) + 1
    return {
        field: columns[0]
        for field, columns in candidates.items()
        if len(columns) == 1 and counts[columns[0]] == 1
    }


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


def _validate_rows(sheet, header_row_number, mapping):
    if not isinstance(mapping, dict):
        return {"error": "Sütun eşleştirmesi geçersiz."}, 400

    normalized = {}
    try:
        for field in (*REQUIRED_FIELDS, "area"):
            index = mapping.get(field)
            if index in (None, ""):
                if field in REQUIRED_FIELDS:
                    return {"error": f"{FIELD_LABELS[field]} sütununu seçin."}, 400
                continue
            normalized[field] = int(index)
    except (TypeError, ValueError):
        return {"error": "Sütun eşleştirmesi geçersiz."}, 400

    if any(index < 0 for index in normalized.values()) or len(set(normalized.values())) != len(normalized):
        return {"error": "Her bilgi için farklı bir sütun seçin."}, 400

    counts = {}
    seen_school_numbers = set()
    issues = []
    records = []
    total_rows = 0
    upper_grade_missing_area = 0
    missing_area_counts = {}

    for row_number, row in enumerate(sheet.iter_rows(min_row=header_row_number + 1, values_only=True), start=header_row_number + 1):
        if not any(value not in (None, "") for value in row):
            continue
        total_rows += 1
        values = {field: _cell_text(row[index] if index < len(row) else None) for field, index in normalized.items()}
        missing = [field for field in REQUIRED_FIELDS if not values.get(field)]
        if missing:
            issues.append({"row": row_number, "fields": [FIELD_LABELS[field] for field in missing], "issue": "Zorunlu bilgi boş"})

        school_number = values.get("school_number", "")
        if school_number:
            if school_number in seen_school_numbers:
                issues.append({"row": row_number, "fields": [FIELD_LABELS["school_number"]], "issue": "Okul numarası dosyada tekrar ediyor"})
            seen_school_numbers.add(school_number)

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
    """XLSX içeriğini diske/veritabanına yazmadan okuyup örnek satır döndür."""
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({"error": "Önizleme için bir .xlsx dosyası seçin."}), 400
    if not uploaded_file.filename.lower().endswith(".xlsx"):
        return jsonify({"error": "Yalnızca .xlsx biçimindeki e-Okul dosyaları destekleniyor."}), 400

    content = uploaded_file.stream.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        return jsonify({"error": "Seçilen dosya boş."}), 400
    if len(content) > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Dosya boyutu 12 MB sınırını aşıyor."}), 413

    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except (InvalidFileException, BadZipFile, OSError, ValueError):
        return jsonify({"error": "Dosya açılamadı. Geçerli bir .xlsx dosyası seçin."}), 400

    try:
        sheet = workbook.active
        if sheet is None:
            return jsonify({"error": "Dosyada okunabilir çalışma sayfası bulunamadı."}), 400

        header_row_number = None
        headers = []
        for row_number, row in enumerate(
            sheet.iter_rows(min_row=1, max_row=MAX_HEADER_SCAN_ROWS, values_only=True), start=1
        ):
            values = [_json_value(value) for value in row]
            if sum(value not in (None, "") for value in values) >= 2:
                header_row_number = row_number
                headers = values
                break

        if header_row_number is None:
            return jsonify({"error": "İlk 20 satırda okunabilir sütun başlığı bulunamadı."}), 400

        mapping_raw = request.form.get("mapping")
        if mapping_raw is not None:
            try:
                mapping = json.loads(mapping_raw)
            except json.JSONDecodeError:
                return jsonify({"error": "Sütun eşleştirmesi okunamadı."}), 400
            result, status = _validate_rows(sheet, header_row_number, mapping)
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
                        ("area" in mapping and mapping["area"] not in (None, ""))
                        or bool(area_assignments),
                    )
            return jsonify(
                {
                    "filename": uploaded_file.filename,
                    "sheet_name": sheet.title,
                    "header_row": header_row_number,
                    "headers": headers,
                    "auto_mapping": _auto_map_headers(headers),
                    "saved": False,
                    **result,
                    "diff": diff_report,
                }
            )

        preview_rows = []
        for row in sheet.iter_rows(
            min_row=header_row_number + 1,
            max_row=header_row_number + PREVIEW_ROWS + 5,
            values_only=True,
        ):
            values = [_json_value(value) for value in row]
            if any(value not in (None, "") for value in values):
                preview_rows.append(values[: len(headers)])
                if len(preview_rows) == PREVIEW_ROWS:
                    break

        return jsonify(
            {
                "filename": uploaded_file.filename,
                "sheet_name": sheet.title,
                "sheet_names": workbook.sheetnames,
                "header_row": header_row_number,
                "headers": headers,
                "auto_mapping": _auto_map_headers(headers),
                "preview_rows": preview_rows,
                "saved": False,
            }
        )
    finally:
        workbook.close()


@student_import_api.post("/student-import/commit")
def commit_student_workbook():
    """Kullanıcı onayıyla doğrulanmış listeyi seçili yılın yerel DB'sine aktar."""
    if request.form.get("confirm") != "true":
        return jsonify({"error": "İçe aktarma için açık onay gereklidir."}), 400

    uploaded_file = request.files.get("file")
    academic_year_id = request.form.get("academic_year_id")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({"error": "İçe aktarılacak .xlsx dosyasını seçin."}), 400
    if not uploaded_file.filename.lower().endswith(".xlsx"):
        return jsonify({"error": "Yalnızca .xlsx biçimindeki e-Okul dosyaları destekleniyor."}), 400
    if not academic_year_id:
        return jsonify({"error": "Eğitim-öğretim yılı seçili değil."}), 400

    content = uploaded_file.stream.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        return jsonify({"error": "Seçilen dosya boş."}), 400
    if len(content) > MAX_UPLOAD_BYTES:
        return jsonify({"error": "Dosya boyutu 12 MB sınırını aşıyor."}), 413
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except (InvalidFileException, BadZipFile, OSError, ValueError):
        return jsonify({"error": "Dosya açılamadı. Geçerli bir .xlsx dosyası seçin."}), 400

    try:
        sheet = workbook.active
        if sheet is None:
            return jsonify({"error": "Dosyada okunabilir çalışma sayfası bulunamadı."}), 400
        header_row_number = None
        for row_number, row in enumerate(
            sheet.iter_rows(min_row=1, max_row=MAX_HEADER_SCAN_ROWS, values_only=True), start=1
        ):
            if sum(value not in (None, "") for value in row) >= 2:
                header_row_number = row_number
                break
        if header_row_number is None:
            return jsonify({"error": "İlk 20 satırda okunabilir sütun başlığı bulunamadı."}), 400

        try:
            mapping = json.loads(request.form.get("mapping", ""))
        except json.JSONDecodeError:
            return jsonify({"error": "Sütun eşleştirmesi okunamadı."}), 400
        try:
            area_assignments = json.loads(request.form.get("area_assignments", "{}"))
        except json.JSONDecodeError:
            return jsonify({"error": "Sınıf alan atamaları okunamadı."}), 400
        result, status = _validate_rows(sheet, header_row_number, mapping)
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
                    old.is_active = False
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
                    updated += 1
                else:
                    unchanged += 1

            for school_number, old in old_by_number.items():
                if school_number not in incoming_by_number and old.is_active:
                    old.is_active = False
                    deactivated += 1

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
                "review": {
                    "new": len(diff["new_students"]),
                    "departed": len(diff["departed_students"]),
                    "changed": len(diff["changed_students"]),
                    "unchanged": diff["unchanged_count"],
                },
            }
        )
    finally:
        workbook.close()
