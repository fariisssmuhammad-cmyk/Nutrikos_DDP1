# NutriKos

Aplikasi web lokal untuk proyek akhir DDP 1, dikerjakan dan dipelajari oleh tiga
mahasiswa semester satu. Python + Streamlit + Plotly; `json`, `csv`, dan
`unittest` berasal dari pustaka standar. Tidak ada JavaScript buatan sendiri,
Flask, kamera, API berbayar, atau database server.

## Menjalankan aplikasi

Disarankan Python 3.11 atau lebih baru. Buka terminal di folder ini:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Pada macOS/Linux, gunakan `python3 -m venv .venv` dan `.venv/bin/python`.
Alternatif Windows: klik kanan `jalankan.ps1` lalu pilih Run with PowerShell,
atau jalankan `powershell -File .\jalankan.ps1`. Launcher memakai Python yang
tersedia melalui uv jika ada; uv tidak wajib untuk cara instalasi manual.
Pemasangan pertama memerlukan internet untuk paket Python. Aplikasi dan katalog
tidak memerlukan layanan luar setelah paket terpasang.

## Alur penggunaan

1. Gunakan **Coba profil contoh**, atau isi form Profil kemudian hitung.
2. Pilih tanggal catatan di sidebar (tanggal awal memakai WIB).
3. Buka Catatan Makanan, pilih makanan dan porsi lalu tekan Tambahkan.
4. Boleh menambah makanan manual berdasarkan nilai **per satu porsi**.
5. Pilih entri tertentu untuk mengubah porsi atau menghapusnya.
6. Buka Analisis & Riwayat untuk diagram dan unduhan CSV.
7. Tekan **Simpan semua perubahan** agar profil dan seluruh tanggal tersimpan.
8. Muat ulang browser; data yang telah disimpan akan dibaca dari JSON.

Mengubah input form saja belum mengubah data. Tombol submit yang menerapkan
perubahan. Pindah halaman/tanggal mempertahankan perubahan dalam sesi, tetapi
refresh/menutup tab sebelum menyimpan dapat membuang perubahan. Tombol cadangan
JSON mengunduh isi sesi, termasuk yang belum disimpan.

## Pembagian modul

| Berkas | Tanggung jawab |
|---|---|
| `app.py` | Tampilan, widget, dan keadaan sesi Streamlit |
| `nutrikos/core.py` | BMR, TDEE, tujuan, makro, status, porsi, total |
| `nutrikos/validation.py` | Angka hingga, tipe data, profil, katalog, log |
| `nutrikos/storage.py` | JSON atomik, deteksi perubahan file, ekspor CSV/JSON |
| `nutrikos/charts.py` | Figure Plotly; tidak mengimpor Streamlit |
| `data/katalog_makanan.json` | 18 makanan contoh dalam skema tugas |
| `data/README.md` | Batas penggunaan dan asal data contoh |
| `tests/` | Pengujian dengan `unittest` |

Core dan penyimpanan dapat dipakai atau diuji tanpa mengimpor Streamlit/Plotly.
Fungsi sengaja dipilih daripada class berlapis agar aliran data mudah diikuti.
Semua fungsi dan class memiliki docstring Indonesia; parameter/hasil fungsi
diberi type hints. `Any` hanya dipakai pada wadah JSON yang nilainya beragam;
isinya diperiksa validator saat masuk.

## Kontrak data dan keputusan penting

- JSON pengguna memiliki tepat dua kunci: `profil` dan `riwayat_log`.
- Sebelum profil dibuat, `profil` berupa `{}` dan `riwayat_log` berupa `{}`.
- Nama aktivitas disimpan, misalnya `Aktivitas Ringan (1.375)`.
- Rumus tidak dibulatkan antarlangkah; tampilan memakai satu desimal. Contoh
  pria 62 kg, 170 cm, 19 tahun menghasilkan BMR 1592.5 dan TDEE 2189.6875.
- Log menyimpan **total setelah dikali porsi**. Makanan 520 kkal dengan porsi
  0.5 disimpan 260 kkal. Penjumlahan log tidak mengalikan porsi lagi.
- Saat mengubah porsi, nilai total dibagi porsi lama lalu dikali porsi baru.
- Snapshot log tidak diubah oleh perubahan katalog. Dua makanan sama di hari
  yang sama tetap merupakan dua entri terpisah; penghapusan berdasarkan indeks
  entri, bukan ID katalog.
- Semua tanggal memakai format YYYY-MM-DD dan disimpan terpisah.
- Rentang status kontinu: `<70`, `70–<90`, `90–110`, `>110–115`, `>115` persen.
  Dengan demikian 89.5% dan 110.5% tetap terklasifikasi. Tepat 75% protein tidak
  menghasilkan saran tambahan.
- Nama kategori sesuai tugas. `pesan_spesifikasi` di core menyimpan teks tugas
  untuk keterlacakan; UI sengaja memakai `pesan` yang menjelaskan rasio secara
  netral. Catatan parsial tidak dapat memastikan defisit/kelebihan fisiologis,
  fokus belajar, atau kecukupan gizi. Jangan mengubah teks itu menjadi klaim
  klinis pada presentasi.
- Penyesuaian tujuan ±300 kkal, lantai BMR, faktor aktivitas, dan pembagian
  50/20/30 merupakan **aturan model tugas**, bukan resep diet personal.
- Grafik donat menggunakan energi makro 4/4/9; grafik batang menggunakan gram.
  Diagram nol tidak dibuat karena persentase terhadap total nol tidak terdefinisi.
- Riwayat dibandingkan terhadap **target profil saat ini**. Skema dua-kunci
  tugas belum menyimpan snapshot target per tanggal; aplikasi tidak mengklaim
  perbandingan terhadap target lama. Ini pengembangan setelah MVP jika diperlukan.

## Keamanan penyimpanan dan lingkup lokal

Satu file = satu profil lokal. Ini bukan aplikasi publik multi-pengguna dan
tidak memiliki login. File ditulis ke berkas sementara, di-flush, kemudian
diganti dengan `os.replace` dalam direktori yang sama. Deteksi sidik file
mencegah sesi lama menimpa perubahan yang telah tersimpan, tetapi bukan kunci
transaksi untuk layanan dengan banyak penulis simultan.

File hilang menghasilkan data kosong di memori. File rusak, angka NaN/Infinity,
kunci JSON duplikat, tanggal invalid, dan skema salah menghasilkan pesan error
dan tidak di-reset otomatis. Pulihkan file valid dari cadangan atau perbaiki
file setelah menyimpan salinan aslinya. Aplikasi belum menyediakan impor/restore
melalui UI; cadangan JSON bisa dipulihkan secara manual saat aplikasi berhenti.

Data pribadi `data/user_data.json` diabaikan `.gitignore`. Jika clone GitHub
tidak memiliki file ini, aplikasi akan membuatnya saat penyimpanan pertama.
CSV merangkum hanya tanggal yang pernah dicatat; hari tanpa catatan bukan bukti
tidak makan. Nama yang menyerupai formula spreadsheet diberi awalan apostrof.

## Dataset dan batas estimasi

**Katalog bawaan bersifat ilustratif dan belum terverifikasi.** Nama menu lokal
tidak berarti kandungan gizi suatu penjual tertentu. Tim perlu mengganti nilai
sebelum penggunaan nyata dan mencatat sumber, ukuran porsi, berat, serta kondisi
matang/mentah di `data/README.md`. Nilai input manual juga mengikuti sumber pengguna.

Kalkulator ini dibatasi bagi dewasa dalam rentang input aplikasi (18–100 tahun,
20–350 kg, 100–250 cm); batas ini adalah validasi perangkat lunak, bukan bukti
bahwa persamaan akurat untuk seluruh orang dalam rentang tersebut. Tidak dirancang
untuk anak, kehamilan/menyusui, atau pengelolaan kondisi medis. BMR **bukan batas
aman diet universal**.

Referensi untuk dipelajari saat presentasi:
- Mifflin dkk., persamaan estimasi energi istirahat:
  https://pubmed.ncbi.nlm.nih.gov/2305711/
- USDA, dasar berat porsi serta faktor energi umum/spesifik:
  https://fdc.nal.usda.gov/Foundation_Foods_Documentation/
- NIDDK, contoh batas pengguna kalkulator energi:
  https://www.niddk.nih.gov/health-information/weight-management/body-weight-planner
- Streamlit Session State dan form:
  https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
  https://docs.streamlit.io/develop/concepts/architecture/forms
- Plotly Pie: https://plotly.com/python/pie-charts/

## Pengujian

```powershell
python -m unittest discover -s tests -v
```

Tes core/storage hanya memakai pustaka standar dan berjalan walau Streamlit
belum diinstal. Tes AppTest otomatis dilewati jika dependensi UI belum tersedia.
Seluruh pengujian file menggunakan direktori sementara, bukan riwayat pengguna.

Untuk mengarahkan data pengguna ke direktori lain saat demo/pengujian:
`NUTRIKOS_DATA_DIR` adalah variabel lingkungan opsional. Katalog tetap dibaca
dari folder `data` proyek agar definisi makanan tidak berubah tanpa sengaja.

## Pembagian kerja yang bisa benar-benar dilakukan tim

1. Anggota 1 mempelajari dan mengembangkan core + validation + test_core.
2. Anggota 2 mempelajari app, form, Session State + test_app.
3. Anggota 3 memvalidasi dataset, storage, grafik + test_storage.

Contoh commit **setelah pekerjaan dilakukan**: `test: tambah batas evaluasi`,
`data: verifikasi porsi makanan`, `ui: rapikan alur edit log`. Jangan membagi
commit secara artifisial demi terlihat berkontribusi. Setiap anggota perlu
menjalankan aplikasi, menelusuri aliran satu entri makanan, dan menjelaskan
kode anggota lain. Riwayat commit tidak dibuatkan oleh paket ini.

Demo singkat: profil contoh → setengah porsi makanan → total berubah → edit
jadi dua porsi → hapus entri lain → pindah tanggal → lihat grafik → simpan →
refresh → unduh CSV. Jelaskan perbedaan nilai per porsi dengan total snapshot.
