"""Pengujian alur Streamlit dengan AppTest dan unittest, tanpa browser atau data asli."""

import importlib.util
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import patch

UI_TERSEDIA = importlib.util.find_spec("streamlit") is not None and importlib.util.find_spec("plotly") is not None


@unittest.skipUnless(UI_TERSEDIA, "Pasang requirements.txt untuk menguji antarmuka.")
class TestApp(unittest.TestCase):
    """Memeriksa alur utama dari profil hingga penyimpanan dan grafik."""

    def setUp(self) -> None:
        """Mengisolasi file pengguna agar pengujian tidak menyentuh catatan nyata."""
        from streamlit.testing.v1 import AppTest

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = patch.dict(os.environ, {"NUTRIKOS_DATA_DIR": self.tmp.name})
        env.start()
        self.addCleanup(env.stop)
        self.app_path = Path(__file__).resolve().parents[1] / "app.py"
        self.at = AppTest.from_file(str(self.app_path), default_timeout=30).run()
        self.assertEqual(len(self.at.exception), 0)

    def tombol(self, label: str) -> Any:
        """Mencari tombol berdasarkan label supaya tes tidak bergantung urutan tampilan."""
        return next(tombol for tombol in self.at.button if tombol.label == label)

    def contoh(self) -> None:
        """Mengaktifkan profil contoh melalui interaksi pengguna."""
        self.tombol("Coba profil contoh").click().run()
        self.assertEqual(len(self.at.exception), 0)

    def test_profil_log_edit_hapus_dan_grafik(self) -> None:
        """Menguji porsi, rerun tanpa duplikasi, identitas entri, serta halaman grafik."""
        self.contoh()
        self.at.sidebar.radio[0].set_value("Catatan Makanan").run()
        self.at.number_input[0].set_value(0.5)
        self.tombol("Tambahkan makanan").click().run()
        self.assertEqual(len(self.at.exception), 0)
        tanggal = self.at.sidebar.date_input[0].value.isoformat()
        entri = self.at.session_state["data"]["riwayat_log"][tanggal]
        self.assertEqual(entri[0]["kalori_kkal"], 260)
        self.at.run()
        self.assertEqual(len(self.at.session_state["data"]["riwayat_log"][tanggal]), 1)
        porsi_baru = next(n for n in self.at.number_input if n.label == "Porsi baru")
        porsi_baru.set_value(2.0)
        self.tombol("Ubah porsi").click().run()
        self.assertEqual(self.at.session_state["data"]["riwayat_log"][tanggal][0]["kalori_kkal"], 1040)
        self.at.sidebar.radio[0].set_value("Analisis & Riwayat").run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(len(self.at.get("plotly_chart")), 2)
        self.at.sidebar.radio[0].set_value("Catatan Makanan").run()
        self.tombol("Hapus entri terpilih").click().run()
        self.assertEqual(self.at.session_state["data"]["riwayat_log"][tanggal], [])

    def test_tanggal_simpan_dan_buka_kembali(self) -> None:
        """Memastikan dua tanggal terpisah dan sesi baru membaca JSON tersimpan."""
        from streamlit.testing.v1 import AppTest

        self.contoh()
        self.at.sidebar.radio[0].set_value("Catatan Makanan").run()
        self.at.sidebar.date_input[0].set_value(date(2026, 11, 23)).run()
        self.tombol("Tambahkan makanan").click().run()
        self.at.sidebar.date_input[0].set_value(date(2026, 11, 24)).run()
        self.tombol("Tambahkan makanan").click().run()
        self.tombol("Simpan semua perubahan").click().run()
        self.assertEqual(len(self.at.exception), 0)
        baru = AppTest.from_file(str(self.app_path), default_timeout=30).run()
        self.assertEqual(len(baru.exception), 0)
        self.assertEqual(len(baru.session_state["data"]["riwayat_log"]), 2)
        self.assertEqual(baru.session_state["data"]["profil"]["nama"], "Mahasiswa Kos")

    def test_manual_invalid_dan_nol_energi(self) -> None:
        """Nama kosong ditolak, air putih dapat dicatat, dan diagram nol tidak menyebabkan error."""
        self.contoh()
        self.at.sidebar.radio[0].set_value("Catatan Makanan").run()
        self.tombol("Tambahkan manual").click().run()
        self.assertGreater(len(self.at.error), 0)
        self.at.text_input[0].set_value("Air putih manual")
        self.tombol("Tambahkan manual").click().run()
        self.assertEqual(len(self.at.exception), 0)
        self.at.sidebar.radio[0].set_value("Analisis & Riwayat").run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(len(self.at.get("plotly_chart")), 1)


if __name__ == "__main__":
    unittest.main()
