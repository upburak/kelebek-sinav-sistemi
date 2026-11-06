"""Geliştirme ve kullanıcı önizlemesi için gerçek dışı öğrenci örnekleri."""


def build_demo_student_records() -> list[dict[str, str]]:
    """Dört sınıf düzeyi ve farklı şubeleri kapsayan sentetik kayıtlar üret."""
    groups = [
        ("9", "A", ""), ("9", "B", ""), ("10", "A", ""), ("10", "B", ""),
        ("11", "A", "Sayısal"), ("11", "B", "Eşit Ağırlık"),
        ("12", "A", "Sözel"), ("12", "B", "Dil"),
    ]
    records = []
    index = 1
    for grade, section, area in groups:
        for _ in range(6):
            records.append({
                "school_number": f"DEMO-{index:03d}",
                "first_name": f"ÖRNEK AD {index:03d}",
                "last_name": f"SENTETİK SOYAD {index:03d}",
                "class_level": grade,
                "section": section,
                "area": area,
            })
            index += 1
    return records
