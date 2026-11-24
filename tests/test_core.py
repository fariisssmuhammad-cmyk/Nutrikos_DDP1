"""Pengujian rumus, batas kategori, snapshot porsi, dan validasi."""

import unittest

from nutrikos.core import (buat_entri, energi_makro, evaluasi_kalori, evaluasi_protein,
                           hitung_bmr, hitung_target_harian, hitung_target_kalori,
                           hitung_target_makro, hitung_tdee, total_asupan, ubah_porsi)
from nutrikos.validation import validasi_data_pengguna, validasi_katalog


class TestCore(unittest.TestCase):
    """Memastikan angka hasil dan kontrak log sesuai aturan proyek."""

    def setUp(self) -> None:
        """Menyiapkan profil dan makanan deterministik untuk tiap pengujian."""
        self.profil = {"nama": "Contoh", "jenis_kelamin": "Pria", "usia": 19,
                       "berat_kg": 62.0, "tinggi_cm": 170.0,
                       "tingkat_aktivitas": "Aktivitas Ringan (1.375)", "tujuan": "Pertahankan BB"}
        self.makanan = {"id_makanan": "MKN-001", "nama_makanan": "Contoh", "kategori": "Contoh",
                        "kalori_kkal": 520.0, "protein_gram": 32.5, "karbo_gram": 58.0, "lemak_gram": 16.0}

    def test_bmr_dua_persamaan(self) -> None:
        """Memeriksa kedua konstanta terhadap hasil perhitungan tangan."""
        self.assertEqual(hitung_bmr(62, 170, 19, "Pria"), 1592.5)
        self.assertEqual(hitung_bmr(62, 170, 19, "Wanita"), 1426.5)

    def test_tdee_semua_faktor(self) -> None:
        """Memeriksa setiap faktor dengan angka dasar sederhana."""
        for faktor, hasil in [(1.2, 1200), (1.375, 1375), (1.55, 1550), (1.725, 1725)]:
            with self.subTest(faktor=faktor):
                self.assertEqual(hitung_tdee(1000, faktor), hasil)

    def test_tujuan_dan_batas_model(self) -> None:
        """Menguji tujuan dan cabang max yang membatasi target ke BMR model."""
        self.assertEqual(hitung_target_kalori(1600, 2200, "Pertahankan BB"), 2200)
        self.assertEqual(hitung_target_kalori(1600, 2200, "Turun BB"), 1900)
        self.assertEqual(hitung_target_kalori(1600, 2200, "Naik BB"), 2500)
        self.assertEqual(hitung_target_kalori(1600, 1800, "Turun BB"), 1600)

    def test_target_tanpa_pembulatan_antara(self) -> None:
        """Menguji kontrak profil dan energi makro yang kembali ke target."""
        target = hitung_target_harian(self.profil)
        self.assertEqual(target["tdee"], 2189.6875)
        self.assertEqual(target["target_kalori"], 2189.6875)
        makro = hitung_target_makro(2000)
        self.assertEqual(makro["target_karbo_g"], 250)
        self.assertEqual(makro["target_protein_g"], 100)
        self.assertAlmostEqual(makro["target_lemak_g"], 66.66666666666667)
        self.profil["target_harian"] = target
        validasi_data_pengguna({"profil": self.profil, "riwayat_log": {}})

    def test_batas_status_kontinu(self) -> None:
        """Memeriksa batas tepat dan celah desimal yang tidak boleh tidak terklasifikasi."""
        kasus = [(0, "Defisit Terlalu Ekstrem"), (69.999, "Defisit Terlalu Ekstrem"),
                 (70, "Defisit Ringan"), (89, "Defisit Ringan"), (89.5, "Defisit Ringan"),
                 (90, "Target Tercapai Ideal"), (110, "Target Tercapai Ideal"),
                 (110.5, "Surplus Ringan"), (111, "Surplus Ringan"),
                 (115, "Surplus Ringan"), (115.001, "Surplus Berlebih")]
        for persen, status in kasus:
            with self.subTest(persen=persen):
                self.assertEqual(evaluasi_kalori(persen, 100)["status"], status)

    def test_protein_batas(self) -> None:
        """Membedakan tepat 75 persen dengan nilai di bawahnya."""
        self.assertIsNotNone(evaluasi_protein(74.9, 100))
        self.assertIsNone(evaluasi_protein(75, 100))

    def test_snapshot_porsi_tidak_dikali_dua_kali(self) -> None:
        """Menguji setengah porsi, dua porsi, dan ketahanan terhadap perubahan katalog."""
        setengah = buat_entri(self.makanan, 0.5)
        dua = buat_entri(self.makanan, 2)
        self.makanan["kalori_kkal"] = 999
        self.assertEqual(setengah["kalori_kkal"], 260)
        self.assertEqual(total_asupan([setengah, dua])["kalori_kkal"], 1300)
        self.assertEqual(ubah_porsi(setengah, 1)["kalori_kkal"], 520)
        self.assertEqual(setengah["porsi"], 0.5)

    def test_kosong_dan_energi(self) -> None:
        """Menangani catatan kosong dan membedakan bobot energi lemak."""
        self.assertEqual(sum(total_asupan([]).values()), 0)
        self.assertEqual(energi_makro({"karbo_gram": 10, "protein_gram": 10, "lemak_gram": 10}),
                         {"Karbohidrat": 40, "Protein": 40, "Lemak": 90})

    def test_input_tidak_valid(self) -> None:
        """Menolak nilai negatif, boolean, tak hingga, NaN, serta teks angka."""
        for nilai in [-1, 0, True, float("nan"), float("inf"), "62"]:
            with self.subTest(nilai=nilai), self.assertRaises(ValueError):
                hitung_bmr(nilai, 170, 19, "Pria")
        for porsi in [0, -1, True, float("nan")]:
            with self.subTest(porsi=porsi), self.assertRaises(ValueError):
                buat_entri(self.makanan, porsi)
        with self.assertRaises(ValueError):
            hitung_tdee(1000, 1.3)
        with self.assertRaises(ValueError):
            evaluasi_kalori(100, 0)
        with self.assertRaises(ValueError):
            hitung_bmr(62, 170, 19, "lain")

    def test_profil_dan_id_invalid(self) -> None:
        """Memeriksa batas usia aplikasi dan duplikasi ID katalog."""
        self.profil["usia"] = 17
        with self.assertRaises(ValueError):
            hitung_target_harian(self.profil)
        with self.assertRaises(ValueError):
            validasi_katalog([self.makanan, self.makanan])


if __name__ == "__main__":
    unittest.main()
