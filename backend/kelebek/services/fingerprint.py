"""Dağıtım parmak izi: bir dağıtımın hâlâ geçerli olup olmadığını belirler."""

import hashlib
import json

from sqlalchemy import select

from kelebek.models import Desk, ExamOrganizationClassroom, ExamParticipant, Seat

# Sıra kayıtlı parmak izlerinin parçasıdır; değiştirmek mevcut dağıtımları geçersiz kılar.
FINGERPRINT_RULE_ORDER = (
    "prevent_same_section_adjacent", "prevent_same_section_front_back",
    "prevent_same_grade_adjacent", "prevent_same_grade_front_back",
    "prevent_different_grade_same_area_adjacent", "prevent_different_grade_same_area_front_back",
    "prevent_same_grade_area_adjacent", "prevent_same_grade_area_front_back",
)


def distribution_fingerprint(session, organization) -> str:
    """Dağıtımın dayandığı girdilerin özeti: katılımcılar, derslik planlarının içeriği ve kurallar.

    Bunlardan biri değişirse eski dağıtım geçersiz sayılır. Özetin biçimi kayıtlı
    dağıtımlarla karşılaştırıldığı için değiştirilmemelidir.
    """
    participant_rows = session.execute(
        select(ExamParticipant.id, ExamParticipant.class_level, ExamParticipant.section, ExamParticipant.area)
        .where(
            ExamParticipant.organization_id == organization.id,
            ExamParticipant.is_active.is_(True),
        )
        .order_by(ExamParticipant.id)
    ).all()
    layout_ids = session.scalars(
        select(ExamOrganizationClassroom.layout_id)
        .where(ExamOrganizationClassroom.organization_id == organization.id)
        .order_by(ExamOrganizationClassroom.layout_id)
    ).all()
    physical_layouts = []
    for layout_id in layout_ids:
        desks = session.execute(
            select(Desk.id, Desk.x, Desk.y, Desk.block_label)
            .where(Desk.layout_id == layout_id).order_by(Desk.id)
        ).all()
        seats = session.execute(
            select(Seat.id, Seat.desk_id, Seat.seat_index, Seat.is_available)
            .where(Seat.layout_id == layout_id).order_by(Seat.id)
        ).all()
        physical_layouts.append({"desks": [list(row) for row in desks], "seats": [list(row) for row in seats]})
    snapshot = {
        "participants": [list(row) for row in participant_rows],
        "layouts": layout_ids,
        "physical_layouts": physical_layouts,
        "rules": [bool(getattr(organization, name)) for name in FINGERPRINT_RULE_ORDER],
    }
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
