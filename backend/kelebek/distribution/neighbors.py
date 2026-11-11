"""Logical seat-neighbor graph derived from the classroom grid.

Komşuluk, masa numarasına değil masaların gerçek fiziksel konumuna göre
hesaplanır (Karar 36–37; 10 Kasım 2026 kullanıcı onayıyla güncellendi):

* **adjacent (yan yana):** aynı sıradaki yatay komşuluk. Koridorun karşı
  tarafındaki oturma yeri de yan yana sayılır.
* **front_back (önlü arkalı):** ardışık sıralarda doğrudan hizalı oturma yerleri.
* **diagonal (çapraz):** ardışık sıralarda bir yana kaymış oturma yerleri.
  Önlü/arkalı kurallarına tabidir; yalnızca "aynı sınıf seviyesi" kuralı (8)
  çapraza uygulanmaz, çünkü koltuk sayısı öğrenci sayısına eşitken bu birleşim
  matematiksel olarak ihlalsiz çözüm bırakmaz.
* Önlü arkalı ve çapraz komşuluk koridoru aşmaz.

Izgara modeli: her masa bir hücredir. ``x / GRID_STEP`` sütunu,
``y / GRID_STEP`` satırı verir. Koridor, ızgarada atlanan bir sütundur.
"""

GRID_STEP = 2.0
EPSILON = 1e-6


def build_neighbor_pairs(desks: list[dict],
                         side_by_side_crosses_corridor: bool = True) -> dict[str, list[tuple[str, str]]]:
    """Yan yana ve önlü/arkalı (çapraz dahil) oturma yeri çiftlerini döndür."""
    cells = {}
    for desk in desks:
        key = (round(desk["x"] / GRID_STEP), round(desk["y"] / GRID_STEP))
        if key in cells:
            raise ValueError("Bir ızgara hücresinde birden fazla masa var.")
        cells[key] = desk

    adjacent: set[tuple[str, str]] = set()
    front_back: set[tuple[str, str]] = set()
    diagonal: set[tuple[str, str]] = set()

    def add(target: set[tuple[str, str]], first: dict, second: dict) -> None:
        target.add(tuple(sorted((first["id"], second["id"]))))

    def available(desk: dict) -> list[dict]:
        return sorted((seat for seat in desk["seats"] if seat["is_available"]),
                      key=lambda seat: seat["seat_index"])

    sutunlar = sorted({column for column, _row in cells})

    def yandaki(column: int, row: int, yon: int) -> dict | None:
        """Aynı sıradaki bir sonraki masa.

        Koridorun yan yana komşuluğu kestiği kipte yalnızca bitişik ızgara
        sütununa bakılır. Kesmediği kipte aradaki boşluk atlanarak sıradaki masa
        bulunur; bu yalnızca yan yana ilişkisini etkiler.
        """
        if not side_by_side_crosses_corridor:
            return cells.get((column + yon, row))
        adaylar = [c for c in sutunlar if (c > column if yon > 0 else c < column)]
        for aday in sorted(adaylar, reverse=yon < 0):
            masa = cells.get((aday, row))
            if masa is not None:
                return masa
        return None

    def arkadaki(column: int, row: int, kayma: int) -> dict | None:
        """Bir arkadaki sırada, ``kayma`` kadar yanda duran masa.

        Önlü arkalı ve çapraz komşuluk koridoru hiçbir kipte aşmaz: koridorun
        karşı tarafındaki bir öğrencinin kağıdını önden/arkadan görmek, yanındaki
        öğrencininkini görmekten belirgin biçimde zordur.
        """
        return cells.get((column + kayma, row + 1))

    for (column, row), desk in cells.items():
        seats = available(desk)
        by_index = {seat["seat_index"]: seat for seat in seats}

        # Aynı masadaki koltuklar yan yanadır.
        for index, seat in by_index.items():
            komsu = by_index.get(index + 1)
            if komsu:
                add(adjacent, seat, komsu)

        # Sağdaki masanın en soldaki koltuğu ile bu masanın en sağdaki koltuğu.
        sag = yandaki(column, row, 1)
        if sag:
            sag_seats = available(sag)
            if seats and sag_seats:
                add(adjacent, seats[-1], sag_seats[0])

        # Arkadaki masa: doğrudan hizalı ve çapraz koltuklar (Karar 37).
        arka = arkadaki(column, row, 0)
        if arka:
            arka_by_index = {seat["seat_index"]: seat for seat in available(arka)}
            for seat in seats:
                for fark in (0, 1, -1):
                    komsu = arka_by_index.get(seat["seat_index"] + fark)
                    if komsu:
                        add(front_back if fark == 0 else diagonal, seat, komsu)

        # Çapraz, masa sınırını da aşabilir: bu masanın en sağdaki koltuğu ile
        # arka-sağdaki masanın en soldaki koltuğu (ve simetriği).
        for kayma, bu_uc, oteki_uc in ((1, -1, 0), (-1, 0, -1)):
            capraz = arkadaki(column, row, kayma)
            if not capraz:
                continue
            capraz_seats = available(capraz)
            if seats and capraz_seats:
                add(diagonal, seats[bu_uc], capraz_seats[oteki_uc])

    return {
        "adjacent": sorted(adjacent),
        "front_back": sorted(front_back),
        "diagonal": sorted(diagonal),
    }
