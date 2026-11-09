"""Uygulama kapandığında dosya tutamağı bırakmaması.

Gerileme (CI'nın Windows işinde yakalandı): `create_app()` SQLite veritabanını ve
`logs/application.log` dosyasını açık tutuyordu. Windows açık dosyanın silinmesine
izin vermediği için geçici veri klasörüyle çalışan testler
`PermissionError: [WinError 32]` ile düşüyordu.

Linux'ta `/proc/self/fd` ile ölçülür; Windows'ta zaten klasörün silinememesi
hatanın kendisini gösterir, bu yüzden orada bu test atlanır.
"""

import os
import tempfile
import unittest
from pathlib import Path

from _support import release_app_resources

from kelebek import create_app


def _open_files_under(root: str) -> list[str]:
    found = []
    for entry in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(entry)
        except OSError:
            continue
        if target.startswith(root):
            found.append(target)
    return sorted(found)


@unittest.skipUnless(Path("/proc/self/fd").is_dir(), "Açık dosya listesi yalnızca Linux'ta okunur.")
class FileHandleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_data_dir = os.environ.get("KELEBEK_DATA_DIR")
        os.environ["KELEBEK_DATA_DIR"] = self.temp_dir.name

    def tearDown(self):
        if self.previous_data_dir is None:
            os.environ.pop("KELEBEK_DATA_DIR", None)
        else:
            os.environ["KELEBEK_DATA_DIR"] = self.previous_data_dir
        self.temp_dir.cleanup()

    def test_release_closes_database_and_log_handles(self):
        root = str(Path(self.temp_dir.name).resolve())
        app = create_app()
        app.test_client().get("/api/health")
        self.assertTrue(_open_files_under(root), "Uygulama hiç dosya açmadı; test anlamsız.")

        release_app_resources(app)
        self.assertEqual(
            _open_files_under(root), [],
            "Uygulama kapandıktan sonra dosya tutamağı kaldı; Windows'ta veri klasörü silinemez.",
        )

    def test_second_app_logs_into_its_own_data_dir(self):
        # app.logger modül adına bağlı olduğu için süreç içinde paylaşılır; veri
        # klasörü değiştiğinde günlüğün eski klasöre yazmaya devam etmemesi gerekir.
        first = create_app()
        release_app_resources(first)
        with tempfile.TemporaryDirectory() as second_dir:
            os.environ["KELEBEK_DATA_DIR"] = second_dir
            second = create_app()
            try:
                handlers = [h for h in second.logger.handlers if getattr(h, "_kelebek_handler", False)]
                self.assertTrue(handlers, "Günlük işleyicisi kurulmadı.")
                for handler in handlers:
                    self.assertTrue(
                        Path(handler.baseFilename).is_relative_to(Path(second_dir).resolve()),
                        f"Günlük eski veri klasörüne yazıyor: {handler.baseFilename}",
                    )
            finally:
                release_app_resources(second)
                os.environ["KELEBEK_DATA_DIR"] = self.temp_dir.name


if __name__ == "__main__":
    unittest.main()
