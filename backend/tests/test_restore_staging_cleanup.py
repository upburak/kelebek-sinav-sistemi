"""Geri yükleme önizlemesi iptal edilince hiçbir iz kalmaması.

Gerileme (CI'nın Windows işinde yakalandı): `discard_pending_restore`
`shutil.rmtree(..., ignore_errors=True)` kullanıyordu. Windows bir dosyayı açık
tutan tutamak serbest kalana kadar silmeye izin vermediği için klasör silinemiyor,
buna karşın uygulama "iptal edildi" diyordu. Klasör kullanıcının veritabanının bir
kopyasını taşıdığından bu hem yanlış bilgi hem de veri hijyeni sorunuydu.

Artık silme kısa aralıklarla yeniden denenir ve başarısız olursa günlüğe yazılır.
"""

import unittest

# Sınıf modül düzeyinde adlandırılmaz; aksi halde unittest onu bu modülde de
# toplar ve test_backup_restore'daki testler ikinci kez çalışır.
import test_backup_restore


class RestoreStagingCleanupTests(unittest.TestCase):
    setUp = test_backup_restore.BackupRestoreTests.setUp
    tearDown = test_backup_restore.BackupRestoreTests.tearDown
    _inspect = test_backup_restore.BackupRestoreTests._inspect

    def _staging_root(self):
        return self.data_dir / ".restore-staging"

    def test_cancelled_preview_leaves_nothing_behind(self):
        response = self._inspect()
        self.assertEqual(response.status_code, 200, response.get_json())
        token = response.get_json()["token"]
        staged = self._staging_root() / token
        self.assertTrue(staged.exists())

        cancelled = self.client.post("/api/backups/restore/cancel", json={"token": token})
        self.assertTrue(cancelled.get_json()["cancelled"])
        self.assertFalse(staged.exists(), "İptal edilen önizlemenin kopyası geride kaldı.")

        root = self._staging_root()
        if root.is_dir():
            self.assertEqual(list(root.iterdir()), [], "Hazırlık kökünde artık kaldı.")

    def test_repeated_preview_and_cancel_does_not_accumulate_copies(self):
        # Kullanıcı birkaç yedeği deneyip vazgeçerse veri klasörü şişmemeli.
        for _ in range(3):
            response = self._inspect()
            self.assertEqual(response.status_code, 200, response.get_json())
            token = response.get_json()["token"]
            self.client.post("/api/backups/restore/cancel", json={"token": token})

        root = self._staging_root()
        if root.is_dir():
            self.assertEqual(list(root.iterdir()), [])

    def test_cancel_with_unknown_token_reports_failure(self):
        response = self.client.post("/api/backups/restore/cancel", json={"token": "yok"})
        self.assertFalse(response.get_json()["cancelled"])


if __name__ == "__main__":
    unittest.main()
