"""Oturma planının yapısını değiştiren işlemler: satır/sütun ekle, taşı, masa türü, masa sil.

Plan bir ızgaradır (bkz. ``distribution/neighbors.py``): masa ``x / 2`` sütununda,
``y / 2`` satırındadır; atlanan sütun koridordur. Buradaki her işlemden sonra
masa adları (``S<satır>-M<sütun>``), blok adları ve koltuk numaraları ızgaraya
göre yeniden verilir; böylece elle kurulan ve kendiliğinden üretilen planlar aynı
kurallarla düzenlenir.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from kelebek.models import Desk, Seat

GRID_STEP = 2.0
MAX_CELL = 60  # ızgara sınırı: 0..120 koordinat
MAX_SEATS = 600
SEAT_COUNTS = (1, 2, 3)


class StructureError(ValueError):
    """Kullanıcıya gösterilecek, işlemin neden yapılamadığını anlatan hata."""


def _snap(value: float) -> float:
    return round(float(value) / GRID_STEP) * GRID_STEP


def _desks(session: Session, layout_id: str) -> list[Desk]:
    return list(session.scalars(select(Desk).where(Desk.layout_id == layout_id)).all())


def _seats(session: Session, desk_id: str) -> list[Seat]:
    return list(session.scalars(select(Seat).where(Seat.desk_id == desk_id).order_by(Seat.seat_index)).all())


def _seat_x(desk_x: float, seat_index: int) -> float:
    return desk_x + 0.25 + (seat_index - 1) * 0.45


def _add_desk(session: Session, layout_id: str, x: float, y: float, seat_count: int, serial: int) -> None:
    desk = Desk(layout_id=layout_id, label=f"yeni-{serial}", block_label=None, x=x, y=y, rotation_degrees=0)
    session.add(desk)
    session.flush()
    for seat_index in range(1, seat_count + 1):
        session.add(Seat(layout_id=layout_id, desk_id=desk.id, seat_number=900000 + serial * 10 + seat_index,
                         seat_index=seat_index, x=_seat_x(x, seat_index), y=y, is_available=True))
    session.flush()


def _typical_seat_count(session: Session, desks: list[Desk]) -> int:
    counts = [len(_seats(session, desk.id)) for desk in desks]
    return max(set(counts), key=counts.count) if counts else 2


def renumber(session: Session, layout_id: str) -> None:
    """Masa adlarını, blokları ve koltuk numaralarını ızgara sırasına göre yeniden ver."""
    desks = _desks(session, layout_id)
    columns = sorted({desk.x for desk in desks})
    rows = sorted({desk.y for desk in desks})
    block_of, block = {}, 0
    for index, x in enumerate(columns):
        if index == 0 or x - columns[index - 1] > GRID_STEP + 1e-6:
            block += 1
        block_of[x] = f"B{block}"
    # Benzersizlik kısıtları ara adımda çakışmasın diye önce geçici değerler yazılır.
    for index, desk in enumerate(desks):
        desk.label = f"~{index}"
    all_seats = list(session.scalars(select(Seat).where(Seat.layout_id == layout_id)).all())
    for index, seat in enumerate(all_seats):
        seat.seat_number = 1_000_000 + index
    session.flush()
    seat_number = 1
    for desk in sorted(desks, key=lambda item: (item.x, item.y)):
        desk.label = f"S{rows.index(desk.y) + 1}-M{columns.index(desk.x) + 1}"
        desk.block_label = block_of[desk.x]
        for seat in _seats(session, desk.id):
            seat.seat_number = seat_number
            seat.x, seat.y = _seat_x(desk.x, seat.seat_index), desk.y
            seat_number += 1
    session.flush()


def _require_room(session: Session, layout_id: str, extra_seats: int) -> None:
    total = len(list(session.scalars(select(Seat.id).where(Seat.layout_id == layout_id)).all()))
    if total + extra_seats > MAX_SEATS:
        raise StructureError(f"Bir plan en fazla {MAX_SEATS} oturma yeri içerebilir.")


def add_row(session: Session, layout_id: str) -> None:
    desks = _desks(session, layout_id)
    if not desks:
        raise StructureError("Önce planı oluşturun; sonra satır ekleyebilirsiniz.")
    y = max(desk.y for desk in desks) + GRID_STEP
    if y / GRID_STEP > MAX_CELL:
        raise StructureError("Plan daha fazla satır alamaz.")
    columns = sorted({desk.x for desk in desks})
    count = _typical_seat_count(session, desks)
    _require_room(session, layout_id, count * len(columns))
    for serial, x in enumerate(columns):
        _add_desk(session, layout_id, x, y, count, serial)
    renumber(session, layout_id)


def add_column(session: Session, layout_id: str) -> None:
    desks = _desks(session, layout_id)
    if not desks:
        raise StructureError("Önce planı oluşturun; sonra sütun ekleyebilirsiniz.")
    x = max(desk.x for desk in desks) + GRID_STEP
    if x / GRID_STEP > MAX_CELL:
        raise StructureError("Plan daha fazla sütun alamaz.")
    rows = sorted({desk.y for desk in desks})
    count = _typical_seat_count(session, desks)
    _require_room(session, layout_id, count * len(rows))
    for serial, y in enumerate(rows):
        _add_desk(session, layout_id, x, y, count, serial)
    renumber(session, layout_id)


def _move_line(session: Session, layout_id: str, axis: str, source: float, target: float) -> None:
    source, target = _snap(source), _snap(target)
    if not 0 <= target / GRID_STEP <= MAX_CELL:
        raise StructureError("Hedef konum planın dışında.")
    desks = _desks(session, layout_id)
    moving = [desk for desk in desks if getattr(desk, axis) == source]
    if not moving:
        raise StructureError("Taşınacak satır ya da sütun bulunamadı.")
    if source == target:
        return
    if any(getattr(desk, axis) == target for desk in desks):
        raise StructureError("Hedefte başka masalar var. Boş bir satır ya da sütuna bırakın.")
    for desk in moving:
        setattr(desk, axis, target)
    session.flush()
    renumber(session, layout_id)


def move_row(session: Session, layout_id: str, source_y: float, target_y: float) -> None:
    _move_line(session, layout_id, "y", source_y, target_y)


def move_column(session: Session, layout_id: str, source_x: float, target_x: float) -> None:
    _move_line(session, layout_id, "x", source_x, target_x)


def _desk_by_label(session: Session, layout_id: str, label: str) -> Desk:
    desk = session.scalar(select(Desk).where(Desk.layout_id == layout_id, Desk.label == label))
    if desk is None:
        raise StructureError("Masa bulunamadı.")
    return desk


def set_desk_seats(session: Session, layout_id: str, label: str, count: int) -> None:
    if count not in SEAT_COUNTS:
        raise StructureError("Masa tekli, çiftli ya da üçlü olabilir.")
    desk = _desk_by_label(session, layout_id, label)
    seats = _seats(session, desk.id)
    if len(seats) == count:
        return
    if len(seats) < count:
        _require_room(session, layout_id, count - len(seats))
        for seat_index in range(len(seats) + 1, count + 1):
            session.add(Seat(layout_id=layout_id, desk_id=desk.id, seat_number=900000 + seat_index,
                             seat_index=seat_index, x=_seat_x(desk.x, seat_index), y=desk.y, is_available=True))
    else:
        for seat in seats[count:]:
            session.delete(seat)
    session.flush()
    renumber(session, layout_id)


def delete_desk(session: Session, layout_id: str, label: str) -> None:
    desk = _desk_by_label(session, layout_id, label)
    if len(_desks(session, layout_id)) == 1:
        raise StructureError("Plandaki son masa silinemez.")
    for seat in _seats(session, desk.id):
        session.delete(seat)
    session.flush()
    session.delete(desk)
    session.flush()
    renumber(session, layout_id)


def removes_seats(session: Session, layout_id: str, operation: dict) -> bool:
    """İşlem koltuk siliyor mu? (Öyleyse dağıtımda geçen plan kopyalanarak düzenlenir.)"""
    kind = operation.get("op")
    if kind == "delete_desk":
        return True
    if kind == "set_desk_seats":
        desk = session.scalar(select(Desk).where(Desk.layout_id == layout_id, Desk.label == operation.get("label")))
        return desk is not None and isinstance(operation.get("count"), int) \
            and operation["count"] < len(_seats(session, desk.id))
    return False


def apply(session: Session, layout_id: str, operation: dict) -> None:
    kind = operation.get("op")

    def number(key: str) -> float:
        value = operation.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not -1e6 < value < 1e6:
            raise StructureError("Konum geçersiz.")
        return float(value)

    if kind == "add_row":
        add_row(session, layout_id)
    elif kind == "add_column":
        add_column(session, layout_id)
    elif kind == "move_row":
        move_row(session, layout_id, number("from"), number("to"))
    elif kind == "move_column":
        move_column(session, layout_id, number("from"), number("to"))
    elif kind == "set_desk_seats":
        if not isinstance(operation.get("label"), str) or type(operation.get("count")) is not int:
            raise StructureError("Masa ve koltuk sayısı gerekli.")
        set_desk_seats(session, layout_id, operation["label"], operation["count"])
    elif kind == "delete_desk":
        if not isinstance(operation.get("label"), str):
            raise StructureError("Masa gerekli.")
        delete_desk(session, layout_id, operation["label"])
    else:
        raise StructureError("Bilinmeyen plan işlemi.")
