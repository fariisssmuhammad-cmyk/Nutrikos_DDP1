# Hasil validasi NutriKos

Diperiksa pada 24 November 2026.

- Runtime pengujian: Python 3.14.6, Streamlit 1.67.0, Plotly 7.1.0.
- `unittest`: **21 metode pengujian lulus**, termasuk subkasus batas persentase.
- Pengujian antarmuka memakai Streamlit AppTest, bukan pemeriksaan visual browser.
- Pemeriksaan AST: 10 berkas Python, 67 fungsi/class; seluruhnya memiliki
  docstring, seluruh parameter selain self/cls dan hasil fungsi memiliki type hints.

Ringkasan cakupan:
1. BMR pria/wanita, empat faktor aktivitas, dan tiga tujuan.
2. Target makro serta presisi perhitungan antara langkah.
3. Batas 70/90/110/115 persen dan angka desimal di antaranya.
4. Batas protein 75 persen, penolakan angka invalid, dan keunikan ID.
5. Setengah/dua porsi, perubahan porsi tanpa pengalian ganda, snapshot katalog.
6. File belum ada, simpan/muat ulang, skema salah, tanggal invalid.
7. JSON rusak, kunci duplikat, NaN, konflik sesi, dan kegagalan penggantian file.
8. Ekspor JSON/CSV serta penanganan nama seperti formula spreadsheet.
9. AppTest: profil contoh, tambah, ubah, hapus, pindah halaman, dan grafik.
10. AppTest: dua tanggal, simpan, dan buka sesi baru.
11. AppTest: makanan manual invalid dan catatan dengan nol energi.

Pengujian ini memverifikasi perilaku perangkat lunak. Pengujian ini **tidak**
memverifikasi angka gizi katalog atau kelayakan target untuk kebutuhan medis.
Katalog bawaan tetap ilustratif. Riwayat menggunakan target profil saat ini,
dan penyimpanan dirancang untuk satu pengguna lokal.

Jalankan ulang setelah mengubah rumus, kontrak JSON, alur form, atau katalog:

```powershell
python -m unittest discover -s tests -v
```
