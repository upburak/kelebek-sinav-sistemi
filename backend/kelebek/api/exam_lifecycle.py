"""Sınav yaşam döngüsü API'si: tek düzenleme oturumu, arşiv, kopya ve öğrenci farkları."""

import re
import threading
import time

from flask import Blueprint, current_app, jsonify, request

from kelebek.api.exam_organizations import _distribution_fingerprint
from kelebek.models import ExamOrganization
from kelebek.services.exam_lifecycle import (
    apply_student_changes, archive_organization, copy_organization, student_changes,
)
from kelebek.services.exam_organizer import ExamOrganizerError

exam_lifecycle_api = Blueprint("exam_lifecycle", __name__)

LOCK_TTL_SECONDS = 30
TAB_HEADER = "X-Kelebek-Tab"
_ORG_PATH = re.compile(r"^/api/exam-organizations/([^/]+)(/.*)?$")
_LOCK_FREE_SUFFIXES = ("/edit-lock", "/copy", "/distribution-progress/stop")
_locks: dict[str, dict] = {}
_locks_guard = threading.Lock()


def _tab_token() -> str | None:
    token = request.headers.get(TAB_HEADER) or request.args.get("tab")
    return token if token and 8 <= len(token) <= 80 else None


def _fresh_lock(organization_id: str):
    lock = _locks.get(organization_id)
    if lock and time.monotonic() - lock["seen"] > LOCK_TTL_SECONDS:
        _locks.pop(organization_id, None)
        return None
    return lock


def _acquire(organization_id: str, token: str, takeover: bool = False) -> bool:
    with _locks_guard:
        lock = _fresh_lock(organization_id)
        if lock and lock["tab"] != token and not takeover:
            return False
        _locks[organization_id] = {"tab": token, "seen": time.monotonic()}
        return True


def _locks_for(token: str | None) -> dict:
    with _locks_guard:
        for organization_id in list(_locks):
            _fresh_lock(organization_id)
        return {org_id: {"mine": lock["tab"] == token} for org_id, lock in _locks.items()}


def guard_exam_writes():
    """Arşivlenmiş sınavları salt okunur tut ve başka sekmenin düzenlediği sınavı koru."""
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    match = _ORG_PATH.match(request.path)
    if not match or (match.group(2) or "").endswith(_LOCK_FREE_SUFFIXES):
        return None
    organization_id = match.group(1)
    session_factory = current_app.extensions["kelebek_session_factory"]
    with session_factory() as session:
        organization = session.get(ExamOrganization, organization_id)
        archived = organization is not None and organization.archived_at is not None
    if archived:
        return jsonify({"error": "Tamamlanmış ve arşivlenmiş sınav salt okunurdur. Değişiklik için çalışma kopyası oluşturun."}), 403
    token = _tab_token()
    if token and not _acquire(organization_id, token):
        return jsonify({"error": "Bu sınav başka bir sekmede düzenleniyor. Bu sekme önizleme modunda (salt okunur).",
                        "edit_locked": True}), 423
    return None


@exam_lifecycle_api.get("/edit-locks")
def get_edit_locks():
    return jsonify({"locks": _locks_for(_tab_token()), "ttl_seconds": LOCK_TTL_SECONDS})


@exam_lifecycle_api.post("/edit-locks/heartbeat")
def heartbeat_edit_locks():
    token = _tab_token()
    if token:
        with _locks_guard:
            for lock in _locks.values():
                if lock["tab"] == token:
                    lock["seen"] = time.monotonic()
    return jsonify({"locks": _locks_for(token), "ttl_seconds": LOCK_TTL_SECONDS})


@exam_lifecycle_api.post("/edit-locks/release")
def release_edit_locks():
    token = _tab_token()
    with _locks_guard:
        for organization_id in [key for key, lock in _locks.items() if lock["tab"] == token]:
            _locks.pop(organization_id, None)
    return jsonify({"released": True})


@exam_lifecycle_api.post("/exam-organizations/<organization_id>/edit-lock")
def take_edit_lock(organization_id: str):
    token = _tab_token()
    if not token:
        return jsonify({"error": "Sekme kimliği eksik."}), 400
    takeover = bool((request.get_json(silent=True) or {}).get("takeover"))
    if not _acquire(organization_id, token, takeover):
        return jsonify({"error": "Bu sınav başka bir sekmede düzenleniyor.", "edit_locked": True}), 423
    return jsonify({"locks": _locks_for(token)})


def _load(session, organization_id):
    organization = session.get(ExamOrganization, organization_id)
    if organization is None:
        raise ExamOrganizerError("Sınav organizasyonu bulunamadı.", 404)
    return organization


@exam_lifecycle_api.get("/exam-organizations/<organization_id>/student-changes")
def get_student_changes(organization_id: str):
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory() as session:
            changes = student_changes(session, _load(session, organization_id))
    except ExamOrganizerError as error:
        return jsonify({"error": str(error)}), error.status_code
    return jsonify({"changes": changes})


@exam_lifecycle_api.post("/exam-organizations/<organization_id>/student-changes/apply")
def post_student_changes(organization_id: str):
    payload = request.get_json(silent=True) or {}
    participant_ids = payload.get("participant_ids")
    if payload.get("confirm") is not True or not isinstance(participant_ids, list) \
            or any(not isinstance(item, str) for item in participant_ids):
        return jsonify({"error": "Değişiklikleri uygulamak için öğrenci seçip açıkça onaylayın."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            count = apply_student_changes(session, _load(session, organization_id), participant_ids,
                                          _distribution_fingerprint)
    except ExamOrganizerError as error:
        return jsonify({"error": str(error)}), error.status_code
    return jsonify({"applied": count})


@exam_lifecycle_api.post("/exam-organizations/<organization_id>/complete")
def post_complete_organization(organization_id: str):
    if (request.get_json(silent=True) or {}).get("confirm") is not True:
        return jsonify({"error": "Sınavı tamamlamak için açık onay gereklidir."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            organization = archive_organization(session, _load(session, organization_id))
    except ExamOrganizerError as error:
        return jsonify({"error": str(error)}), error.status_code
    return jsonify({"organization": organization})


@exam_lifecycle_api.post("/exam-organizations/<organization_id>/copy")
def post_copy_organization(organization_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Kopya bilgileri JSON biçiminde gönderilmelidir."}), 400
    session_factory = current_app.extensions["kelebek_session_factory"]
    try:
        with session_factory.begin() as session:
            result = copy_organization(session, _load(session, organization_id), payload)
    except ExamOrganizerError as error:
        return jsonify({"error": str(error)}), error.status_code
    return jsonify(result), 201
