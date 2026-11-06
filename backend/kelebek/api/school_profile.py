"""Yerel okul profili ve yönetici bilgileri uç noktaları."""

from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import delete, select

from kelebek.models import SchoolAdministrator, SchoolProfile


school_profile_api = Blueprint("school_profile", __name__)
PROFILE_FIELDS = {
    "school_name": (160, True),
    "province": (100, False),
    "district": (100, False),
    "address": (500, False),
    "phone": (40, False),
    "email": (254, False),
}
ADMIN_ROLES = {"principal", "vice_principal"}


def _serialize(profile: SchoolProfile | None, administrators: list[SchoolAdministrator]) -> dict:
    result = {
        field: getattr(profile, field, "") if profile else ""
        for field in PROFILE_FIELDS
    }
    result["is_saved"] = profile is not None
    result["is_configured"] = bool(
        profile
        and profile.school_name.strip()
        and any(admin.role == "principal" and admin.full_name.strip() for admin in administrators)
    )
    result["administrators"] = [
        {
            "id": admin.id,
            "role": admin.role,
            "full_name": admin.full_name,
            "title": admin.title,
            "display_order": admin.display_order,
        }
        for admin in administrators
    ]
    return result


@school_profile_api.get("/school-profile")
def get_school_profile():
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        profile = session.get(SchoolProfile, 1)
        administrators = session.scalars(
            select(SchoolAdministrator)
            .where(SchoolAdministrator.profile_id == 1)
            .order_by(SchoolAdministrator.display_order, SchoolAdministrator.role)
        ).all()
    return jsonify({"profile": _serialize(profile, administrators)})


@school_profile_api.put("/school-profile")
def save_school_profile():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Okul profili bilgileri gönderilmelidir."}), 400

    values: dict[str, str] = {}
    for field, (max_length, required) in PROFILE_FIELDS.items():
        value = payload.get(field, "")
        if not isinstance(value, str):
            return jsonify({"error": f"{field} metin olarak gönderilmelidir."}), 400
        value = value.strip()
        if required and not value:
            return jsonify({"error": "Okul adı zorunludur."}), 400
        if len(value) > max_length:
            return jsonify({"error": f"{field} en fazla {max_length} karakter olabilir."}), 400
        values[field] = value

    if values["email"] and ("@" not in values["email"] or len(values["email"]) > 254):
        return jsonify({"error": "E-posta adresini kontrol edin."}), 400

    raw_admins = payload.get("administrators", [])
    if not isinstance(raw_admins, list) or len(raw_admins) > 21:
        return jsonify({"error": "Yönetici listesi geçersiz veya çok uzun."}), 400

    administrators: list[dict[str, str]] = []
    normalized_names: set[str] = set()
    for item in raw_admins:
        role = item.get("role") if isinstance(item, dict) else None
        if not isinstance(role, str) or role not in ADMIN_ROLES:
            return jsonify({"error": "Yönetici görevi geçersiz."}), 400
        name = item.get("full_name", "")
        title = item.get("title", "")
        if not isinstance(name, str) or not isinstance(title, str):
            return jsonify({"error": "Yönetici adı ve unvanı metin olmalıdır."}), 400
        name, title = name.strip(), title.strip()
        if not name or len(name) > 160 or len(title) > 120:
            return jsonify({"error": "Yönetici adı zorunludur; uzunluğu sınırlar içinde olmalıdır."}), 400
        normalized_name = " ".join(name.split()).replace("I", "ı").replace("İ", "i").lower()
        if normalized_name in normalized_names:
            return jsonify({"error": f"{name} birden fazla görevde eklenmiş. Her yönetici yalnızca bir kez kaydedilebilir."}), 400
        normalized_names.add(normalized_name)
        administrators.append({"role": role, "full_name": name, "title": title})

    if sum(admin["role"] == "principal" for admin in administrators) > 1:
        return jsonify({"error": "Bir okul profili için yalnızca bir okul müdürü kaydedilebilir."}), 400

    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory.begin() as session:
        profile = session.get(SchoolProfile, 1)
        if profile is None:
            profile = SchoolProfile(id=1, **values)
            session.add(profile)
            session.flush()
        else:
            for field, value in values.items():
                setattr(profile, field, value)
        session.execute(delete(SchoolAdministrator).where(SchoolAdministrator.profile_id == 1))
        for index, admin in enumerate(administrators):
            session.add(
                SchoolAdministrator(
                    id=str(uuid4()),
                    profile_id=1,
                    role=admin["role"],
                    full_name=admin["full_name"],
                    title=admin["title"],
                    display_order=index,
                )
            )
        session.flush()
        saved_administrators = session.scalars(
            select(SchoolAdministrator)
            .where(SchoolAdministrator.profile_id == 1)
            .order_by(SchoolAdministrator.display_order, SchoolAdministrator.role)
        ).all()
        result = _serialize(profile, saved_administrators)

    return jsonify({"profile": result})
