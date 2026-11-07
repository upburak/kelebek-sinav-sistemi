"""Logical seat-neighbor graph derived from the classroom grid."""

GRID_STEP = 2.0
EPSILON = 1e-6


def build_neighbor_pairs(desks: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """Return side-by-side and front/back seat pairs for adjacent grid cells.

    Every desk is one grid cell. Columns grow away from the board (increasing
    y); aisles are represented by distinct block labels. Disabled seats are
    omitted, and a missing cell never creates a bridge to a farther cell.
    """
    cells = {}
    for desk in desks:
        key = (round(desk["x"] / GRID_STEP), round(desk["y"] / GRID_STEP))
        if key in cells:
            raise ValueError("Bir ızgara hücresinde birden fazla masa var.")
        cells[key] = desk

    adjacent: set[tuple[str, str]] = set()
    front_back: set[tuple[str, str]] = set()

    def add(target: set[tuple[str, str]], first: dict, second: dict) -> None:
        pair = tuple(sorted((first["id"], second["id"])))
        target.add(pair)

    for (column, row), desk in cells.items():
        seats = sorted(desk["seats"], key=lambda seat: seat["seat_index"])
        available = [seat for seat in seats if seat["is_available"]]
        # Seats in a shared desk sit side by side in seat-index order.
        by_index = {seat["seat_index"]: seat for seat in available}
        for index, seat in by_index.items():
            neighbor = by_index.get(index + 1)
            if neighbor:
                add(adjacent, seat, neighbor)

        right = cells.get((column + 1, row))
        if right:
            left_seats = [seat for seat in seats if seat["is_available"]]
            right_seats = [seat for seat in right["seats"] if seat["is_available"]]
            if left_seats and right_seats:
                add(adjacent, max(left_seats, key=lambda seat: seat["seat_index"]),
                    min(right_seats, key=lambda seat: seat["seat_index"]))

        behind = cells.get((column, row + 1))
        if behind:
            behind_by_index = {
                seat["seat_index"]: seat for seat in behind["seats"] if seat["is_available"]
            }
            for seat in available:
                neighbor = behind_by_index.get(seat["seat_index"])
                if neighbor:
                    add(front_back, seat, neighbor)

    return {
        "adjacent": sorted(adjacent),
        "front_back": sorted(front_back),
    }
