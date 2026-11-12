"""Derslik düzenlerinde "aktif düzen" ve silme kuralları.

Her derslik ve eğitim yılı için en fazla bir düzen aktiftir; sınav için derslik
seçildiğinde varsayılan olarak o düzen gelir. Şablonlar (yılı olmayan düzenler)
aktif olamaz.
"""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from kelebek.db import current_academic_year_start
from kelebek.models import (
    AcademicYear,
    ClassroomLayout,
    Desk,
    ExamOrganization,
    ExamOrganizationClassroom,
    Seat,
)


class LayoutReadOnlyError(ValueError):
    """Arşiv yılına ait plan değiştirilemez."""


def _siblings(layout: ClassroomLayout):
    return (
        ClassroomLayout.classroom_id == layout.classroom_id,
        ClassroomLayout.academic_year_id == layout.academic_year_id,
    )


def activate_layout(session: Session, layout: ClassroomLayout) -> None:
    """Bu düzeni aktif yap; aynı derslik ve yıldaki diğerlerini pasifleştir."""
    if layout.academic_year_id is None:
        raise ValueError("Şablon düzenler aktif yapılamaz; önce bir eğitim yılına kopyalayın.")
    session.execute(update(ClassroomLayout).where(*_siblings(layout)).values(is_active=False))
    layout.is_active = True
    session.flush()


def ensure_active_layout(session: Session, layout: ClassroomLayout) -> None:
    """Derslikte o yıl için aktif düzen yoksa bu düzeni aktif yap."""
    if layout.academic_year_id is None:
        return
    active = session.scalar(
        select(func.count(ClassroomLayout.id)).where(*_siblings(layout), ClassroomLayout.is_active.is_(True))
    ) or 0
    if not active:
        activate_layout(session, layout)


def layout_exam_count(session: Session, layout_id: str) -> int:
    return session.scalar(
        select(func.count(ExamOrganizationClassroom.id)).where(ExamOrganizationClassroom.layout_id == layout_id)
    ) or 0


def delete_layout(session: Session, layout: ClassroomLayout) -> None:
    """Hiçbir sınavda kullanılmayan düzeni koltuk ve masalarıyla birlikte sil.

    Silinen düzen aktifse, aynı derslik ve yılda kalan en yeni düzen aktif olur.
    """
    if layout_exam_count(session, layout.id):
        raise ValueError("Bu düzen bir sınavda kullanılıyor; geçmiş kayıtların bozulmaması için silinemez.")
    was_active = layout.is_active
    siblings = _siblings(layout)
    for seat in session.scalars(select(Seat).where(Seat.layout_id == layout.id)).all():
        session.delete(seat)
    session.flush()
    for desk in session.scalars(select(Desk).where(Desk.layout_id == layout.id)).all():
        session.delete(desk)
    session.flush()
    layout_id = layout.id
    session.delete(layout)
    session.flush()
    if was_active:
        replacement = session.scalars(
            select(ClassroomLayout)
            .where(*siblings, ClassroomLayout.id != layout_id)
            .order_by(ClassroomLayout.created_at.desc(), ClassroomLayout.version.desc())
            .limit(1)
        ).first()
        if replacement is not None:
            activate_layout(session, replacement)


def is_archive_layout(session: Session, layout: ClassroomLayout) -> bool:
    if not layout.academic_year_id:
        return False
    year = session.get(AcademicYear, layout.academic_year_id)
    return year is not None and year.start_year < current_academic_year_start()


def clone_layout(session: Session, source: ClassroomLayout) -> ClassroomLayout:
    """Planı masaları ve koltuklarıyla yeni sürüm olarak kopyala; aktiflik değişmez."""
    version = session.scalar(
        select(func.max(ClassroomLayout.version)).where(
            ClassroomLayout.classroom_id == source.classroom_id,
            ClassroomLayout.name == source.name,
            ClassroomLayout.academic_year_id == source.academic_year_id,
        )
    ) or source.version
    copy = ClassroomLayout(
        classroom_id=source.classroom_id,
        academic_year_id=source.academic_year_id,
        name=source.name,
        version=version + 1,
    )
    session.add(copy)
    session.flush()
    for source_desk in session.scalars(
        select(Desk).where(Desk.layout_id == source.id).order_by(Desk.y, Desk.x)
    ).all():
        desk = Desk(
            layout_id=copy.id,
            label=source_desk.label,
            block_label=source_desk.block_label,
            x=source_desk.x,
            y=source_desk.y,
            rotation_degrees=source_desk.rotation_degrees,
        )
        session.add(desk)
        session.flush()
        for source_seat in session.scalars(
            select(Seat).where(Seat.desk_id == source_desk.id).order_by(Seat.seat_index)
        ).all():
            session.add(Seat(
                layout_id=copy.id,
                desk_id=desk.id,
                seat_number=source_seat.seat_number,
                seat_index=source_seat.seat_index,
                x=source_seat.x,
                y=source_seat.y,
                is_available=source_seat.is_available,
                unavailable_reason=source_seat.unavailable_reason,
            ))
    session.flush()
    return copy


def _exams_using(layout_id: str):
    return (
        select(ExamOrganization)
        .join(ExamOrganizationClassroom, ExamOrganizationClassroom.organization_id == ExamOrganization.id)
        .where(ExamOrganizationClassroom.layout_id == layout_id)
    )


def _is_frozen_exam():
    return (ExamOrganization.status == "completed") | ExamOrganization.archived_at.is_not(None)


def layout_finalized_exam_count(session: Session, layout_id: str) -> int:
    return len(session.scalars(_exams_using(layout_id).where(_is_frozen_exam())).all())


def layout_draft_exam_count(session: Session, layout_id: str) -> int:
    """Bu planı kullanan taslak sınav sayısı; plan değişince dağıtımları yenilenmelidir."""
    return len(session.scalars(_exams_using(layout_id).where(~_is_frozen_exam())).all())


def is_layout_frozen(session: Session, layout_id: str) -> bool:
    """Plan kesinleşmiş ya da arşivlenmiş bir sınavda kullanılıyor mu?"""
    return session.scalars(_exams_using(layout_id).where(_is_frozen_exam()).limit(1)).first() is not None


def rebind_draft_exams(session: Session, old_layout: ClassroomLayout, new_layout: ClassroomLayout) -> int:
    """Eski planı kullanan taslak sınavları yeni plana bağla; seçili dağıtımları düşür."""
    if old_layout.id == new_layout.id:
        return 0
    drafts = session.scalars(_exams_using(old_layout.id).where(~_is_frozen_exam())).all()
    for exam in drafts:
        session.execute(
            update(ExamOrganizationClassroom)
            .where(
                ExamOrganizationClassroom.organization_id == exam.id,
                ExamOrganizationClassroom.layout_id == old_layout.id,
            )
            .values(layout_id=new_layout.id)
        )
        exam.selected_candidate_id = None
    session.flush()
    return len(drafts)


def prepare_layout_for_edit(session: Session, layout: ClassroomLayout) -> tuple[ClassroomLayout, int]:
    """Düzenlenecek planı döndür: kesinleşmiş sınavda kullanılıyorsa kopyası, değilse kendisi.

    Kopya dersliğin aktif planı olur ve taslak sınavlar ona bağlanır; kesinleşmiş
    sınavlar eski planı, dolayısıyla krokilerini korur.
    """
    if is_archive_layout(session, layout):
        raise LayoutReadOnlyError("Arşiv yılı düzenleri salt okunur.")
    if layout.academic_year_id is None or not is_layout_frozen(session, layout.id):
        return layout, 0
    copy = clone_layout(session, layout)
    activate_layout(session, copy)
    return copy, rebind_draft_exams(session, layout, copy)
