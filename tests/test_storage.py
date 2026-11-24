"""Pengujian penyimpanan pada direktori sementara tanpa menyentuh data asli."""

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nutrikos.core import buat_entri, hitung_target_harian
from nutrikos.storage import (KesalahanData, baca_json, data_kosong, ekspor_csv,
                              ekspor_json, muat_katalog, muat_pengguna, sidik_file, simpan_pengguna)


class TestStorage(unittest.TestCase):
    """Menjamin simpan/muat, konflik, file rusak, dan ekspor memenuhi kontrak."""

    def setUp(self) -> None:
        """Membuat direktori terisolasi dan data valid."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "user_data.json"
        self.data = data_kosong()
        profil = {"nama": "Mahasiswa", "jenis_kelamin": "Pria", "usia": 19, "berat_kg": 62.0,
                  "tinggi_cm": 170.0, "tingkat_aktivitas": "Aktivitas Ringan (1.375)", "tujuan": "Pertahankan BB"}
        profil["target_harian"] = hitung_target_harian(profil)
        self.data["profil"] = profil

    def test_belum_ada_tidak_menulis_file(self) -> None:
        """Muat awal membuat data kosong di memori saja."""
        data, versi = muat_pengguna(self.path)
        self.assertEqual(data, data_kosong())
        self.assertEqual(versi, "")
        self.assertFalse(self.path.exists())

    def test_simpan_muat_dan_simpan_ulang(self) -> None:
        """Menguji perjalanan pulang-pergi JSON tanpa duplikasi catatan."""
        self.data["riwayat_log"]["2026-11-24"] = []
        versi = simpan_pengguna(self.data, self.path, "")
        terbaca, sidik = muat_pengguna(self.path)
        self.assertEqual(terbaca, self.data)
        self.assertEqual(sidik, versi)
        simpan_pengguna(terbaca, self.path, sidik)
        self.assertEqual(len(muat_pengguna(self.path)[0]["riwayat_log"]), 1)

    def test_file_rusak_tidak_ditimpa(self) -> None:
        """File rusak harus tetap identik setelah percobaan baca atau simpan."""
        for isi in ['{rusak', '{"profil": {}, "riwayat_log": NaN}',
                    '{"profil":{},"profil":{},"riwayat_log":{}}']:
            with self.subTest(isi=isi):
                self.path.write_text(isi, encoding="utf-8")
                with self.assertRaises(KesalahanData):
                    muat_pengguna(self.path)
                with self.assertRaises(KesalahanData):
                    simpan_pengguna(self.data, self.path, sidik_file(self.path))
                self.assertEqual(self.path.read_text(encoding="utf-8"), isi)

    def test_konflik_sesi_ditolak(self) -> None:
        """Sesi dengan sidik lama tidak boleh menimpa perubahan sesi lain."""
        versi = simpan_pengguna(self.data, self.path, "")
        self.data["profil"]["nama"] = "Baru"
        simpan_pengguna(self.data, self.path, versi)
        with self.assertRaises(KesalahanData):
            simpan_pengguna(self.data, self.path, versi)

    def test_gagal_replace_mempertahankan_file(self) -> None:
        """Kegagalan penggantian file tidak merusak data dan membersihkan berkas sementara."""
        versi = simpan_pengguna(self.data, self.path, "")
        sebelum = self.path.read_bytes()
        self.data["profil"]["nama"] = "Perubahan"
        with patch("nutrikos.storage.os.replace", side_effect=OSError("uji gagal")):
            with self.assertRaises(KesalahanData):
                simpan_pengguna(self.data, self.path, versi)
        self.assertEqual(self.path.read_bytes(), sebelum)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_skema_invalid_ditolak(self) -> None:
        """Memeriksa tanggal palsu dan target yang tidak sesuai profil."""
        self.data["riwayat_log"]["2026-02-30"] = []
        with self.assertRaises(ValueError):
            simpan_pengguna(self.data, self.path, "")
        self.data["riwayat_log"] = {}
        self.data["profil"]["target_harian"]["bmr"] = 1
        with self.assertRaises(ValueError):
            simpan_pengguna(self.data, self.path, "")

    def test_ekspor_csv_dan_json(self) -> None:
        """CSV menyimpan total per tanggal, mengutip nama, dan menetralkan rumus spreadsheet."""
        self.data["profil"]["nama"] = "=SUM(1,2)"
        makanan = {"id_makanan": "X", "nama_makanan": "Contoh", "kategori": "Uji",
                   "kalori_kkal": 100.0, "protein_gram": 2.0, "karbo_gram": 10.0, "lemak_gram": 1.0}
        self.data["riwayat_log"]["2026-11-24"] = [buat_entri(makanan, 2)]
        baris = list(csv.DictReader(io.StringIO(ekspor_csv(self.data))))
        self.assertEqual(baris[0]["kalori_kkal"], "200.0")
        self.assertTrue(baris[0]["nama"].startswith("'="))
        self.assertEqual(json.loads(ekspor_json(self.data)), self.data)

    def test_katalog_bawaan(self) -> None:
        """Memeriksa jumlah, keunikan ID, dan angka nonnegatif dari seluruh katalog."""
        path = Path(__file__).resolve().parents[1] / "data" / "katalog_makanan.json"
        katalog = muat_katalog(path)
        self.assertGreaterEqual(len(katalog), 15)
        self.assertLessEqual(len(katalog), 20)


if __name__ == "__main__":
    unittest.main()
