"""Derslik düzenlerinde "aktif düzen" ve silme kuralları.

Her derslik ve eğitim yılı için en fazla bir düzen aktiftir; sınav için derslik
seçildiğinde varsayılan olarak o düzen gelir. Şablonlar (yılı olmayan düzenler)
aktif olamaz.
"""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from kelebek.models import ClassroomLayout, Desk, ExamOrganizationClassroom, Seat


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
