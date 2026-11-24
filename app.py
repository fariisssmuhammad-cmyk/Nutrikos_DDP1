"""Antarmuka Streamlit NutriKos; perhitungan dan akses file berada di modul terpisah."""

import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st

from nutrikos.charts import grafik_makro, grafik_target
from nutrikos.core import (buat_entri, energi_makro, evaluasi_kalori, evaluasi_protein,
                           hitung_target_harian, total_asupan, ubah_porsi)
from nutrikos.storage import (KesalahanData, ekspor_csv, ekspor_json, muat_katalog,
                              muat_pengguna, simpan_pengguna)
from nutrikos.validation import AKTIVITAS, TUJUAN

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("NUTRIKOS_DATA_DIR", str(ROOT / "data")))
USER_FILE = DATA_DIR / "user_data.json"


def profil_contoh() -> dict[str, Any]:
    """Menyediakan profil fiktif tanpa membaca data pribadi pengguna."""
    profil: dict[str, Any] = {"nama": "Mahasiswa Kos", "jenis_kelamin": "Pria", "usia": 19,
                              "berat_kg": 62.0, "tinggi_cm": 170.0,
                              "tingkat_aktivitas": "Aktivitas Ringan (1.375)", "tujuan": "Pertahankan BB"}
    profil["target_harian"] = hitung_target_harian(profil)
    return profil


def tandai_perubahan() -> None:
    """Menandai data sesi agar pengguna mengetahui perlunya menyimpan ke JSON."""
    st.session_state["dirty"] = True


def ringkasan(entri: list[dict[str, Any]], target: dict[str, float]) -> None:
    """Menampilkan angka tercatat dan status model tanpa menyimpulkan diagnosis."""
    total = total_asupan(entri)
    a, b, c = st.columns(3)
    a.metric("Kalori tercatat", f'{total["kalori_kkal"]:,.1f} kkal')
    b.metric("Target model", f'{target["target_kalori"]:,.1f} kkal')
    selisih = target["target_kalori"] - total["kalori_kkal"]
    c.metric("Selisih dari target" if selisih >= 0 else "Di atas target", f"{abs(selisih):,.1f} kkal")
    rasio = total["kalori_kkal"] / target["target_kalori"]
    st.progress(min(rasio, 1.0), text=f"Tercatat {rasio * 100:.1f}% dari target model")
    if not entri:
        st.info("Belum ada makanan tercatat. Tambahkan makanan untuk melihat ringkasan.")
        return
    hasil = evaluasi_kalori(total["kalori_kkal"], target["target_kalori"])
    pesan = f'Kategori aturan proyek: **{hasil["status"]}**. {hasil["pesan"]}'
    if hasil["warna"] == "success":
        st.success(pesan)
    elif hasil["warna"] == "warning":
        st.warning(pesan)
    else:
        st.info(pesan)
    st.caption("Kategori ini hanya membandingkan catatan dengan target perkiraan. Catatan bisa belum lengkap; status bukan diagnosis atau penilaian kecukupan gizi.")
    saran = evaluasi_protein(total["protein_gram"], target["target_protein_g"])
    if saran:
        st.info("Protein tercatat belum mencapai 75% target model. " + saran)


def halaman_profil(data: dict[str, Any]) -> None:
    """Mengumpulkan profil dan menyerahkan perhitungannya ke modul core."""
    st.header("Profil & target model")
    st.caption("Deskripsi aktivitas: sedentari = jarang olahraga; ringan = 1–3x/minggu; sedang = 3–5x/minggu; sangat aktif = 6–7x/minggu. Kategori ini penyederhanaan, bukan pengukuran aktivitas.")
    profil = data["profil"] or profil_contoh()
    with st.form("profil_form"):
        nama = st.text_input("Nama panggilan", value=profil["nama"], max_chars=200)
        kiri, kanan = st.columns(2)
        jenis = kiri.selectbox("Jenis kelamin untuk persamaan", ["Pria", "Wanita"],
                               index=["Pria", "Wanita"].index(profil["jenis_kelamin"]))
        usia = kanan.number_input("Usia (tahun)", 18, 100, int(profil["usia"]), step=1)
        berat = kiri.number_input("Berat badan (kg)", 20.0, 350.0, float(profil["berat_kg"]), step=0.5)
        tinggi = kanan.number_input("Tinggi badan (cm)", 100.0, 250.0, float(profil["tinggi_cm"]), step=0.5)
        aktivitas = st.selectbox("Tingkat aktivitas", list(AKTIVITAS),
                                index=list(AKTIVITAS).index(profil["tingkat_aktivitas"]))
        tujuan = st.selectbox("Tujuan model", TUJUAN, index=TUJUAN.index(profil["tujuan"]))
        submit = st.form_submit_button("Hitung & gunakan profil", type="primary")
    if submit:
        baru = {"nama": nama.strip(), "jenis_kelamin": jenis, "usia": usia, "berat_kg": berat,
                "tinggi_cm": tinggi, "tingkat_aktivitas": aktivitas, "tujuan": tujuan}
        try:
            baru["target_harian"] = hitung_target_harian(baru)
        except ValueError as exc:
            st.error(str(exc))
        else:
            data["profil"] = baru
            tandai_perubahan()
            st.rerun()
    if not data["profil"]:
        st.info("Isi formulir lalu hitung profil, atau gunakan contoh dari sidebar.")
        return
    target = data["profil"]["target_harian"]
    a, b, c = st.columns(3)
    a.metric("Estimasi energi istirahat (BMR/REE)", f'{target["bmr"]:,.1f} kkal/hari')
    b.metric("Estimasi TDEE", f'{target["tdee"]:,.1f} kkal/hari')
    c.metric("Target model", f'{target["target_kalori"]:,.1f} kkal/hari')
    st.write(f'Karbohidrat **{target["target_karbo_g"]:.1f} g** · Protein **{target["target_protein_g"]:.1f} g** · Lemak **{target["target_lemak_g"]:.1f} g**')
    st.caption("Pembagian energi 50/20/30 adalah pengaturan model. Tujuan turun/naik memakai aturan ±300 kkal; pembatasan ke BMR bukan jaminan aman bagi setiap orang. Riwayat dibandingkan dengan target profil saat ini.")


def halaman_log(data: dict[str, Any], katalog: list[dict[str, Any]], tanggal: str) -> None:
    """Menangani tambah, ubah porsi, dan hapus entri hanya ketika pengguna mengirim form."""
    st.header("Catatan makanan")
    st.caption(f"Tanggal catatan: {tanggal} · 1 porsi mengacu pada keterangan contoh dalam katalog.")
    with st.form("tambah_katalog"):
        pilihan = {f'{m["id_makanan"]} · {m["nama_makanan"]} — {m["kategori"]}': m for m in katalog}
        label = st.selectbox("Pilih makanan", list(pilihan))
        porsi = st.number_input("Jumlah porsi", min_value=0.1, max_value=100.0, value=1.0, step=0.25)
        ditambah = st.form_submit_button("Tambahkan makanan", type="primary")
    if ditambah:
        data["riwayat_log"].setdefault(tanggal, []).append(buat_entri(pilihan[label], porsi))
        tandai_perubahan()
        st.rerun()
    with st.expander("Makanan tidak ditemukan? Tambah manual"):
        st.caption("Masukkan gizi per SATU porsi yang kamu definisikan. Gunakan label produk atau sumber yang jelas.")
        with st.form("manual"):
            nama = st.text_input("Nama makanan dan ukuran porsi", max_chars=200)
            kalori = st.number_input("Kalori per porsi (kkal)", 0.0, 10000.0, 0.0, step=1.0)
            protein = st.number_input("Protein per porsi (g)", 0.0, 1000.0, 0.0, step=0.5)
            karbo = st.number_input("Karbohidrat per porsi (g)", 0.0, 1000.0, 0.0, step=0.5)
            lemak = st.number_input("Lemak per porsi (g)", 0.0, 1000.0, 0.0, step=0.5)
            jumlah = st.number_input("Porsi makanan manual", 0.1, 100.0, 1.0, step=0.25)
            manual_submit = st.form_submit_button("Tambahkan manual")
        if manual_submit:
            makanan = {"id_makanan": "MANUAL-" + uuid4().hex[:12], "nama_makanan": nama.strip(),
                       "kategori": "Manual", "kalori_kkal": kalori, "protein_gram": protein,
                       "karbo_gram": karbo, "lemak_gram": lemak}
            try:
                entri_baru = buat_entri(makanan, jumlah)
            except ValueError as exc:
                st.error(str(exc))
            else:
                data["riwayat_log"].setdefault(tanggal, []).append(entri_baru)
                tandai_perubahan()
                st.rerun()
    entri = data["riwayat_log"].get(tanggal, [])
    if entri:
        st.dataframe(entri, hide_index=True, width="stretch")
        opsi = {f'{i + 1}. {m["nama_makanan"]} ({m["porsi"]:g} porsi)': i for i, m in enumerate(entri)}
        pilihan_edit = st.selectbox("Entri yang ingin diubah/dihapus", list(opsi))
        index = opsi[pilihan_edit]
        with st.form("edit_entri"):
            baru = st.number_input("Porsi baru", 0.1, 100.0, min(100.0, max(0.1, float(entri[index]["porsi"]))), step=0.25)
            edit = st.form_submit_button("Ubah porsi")
            hapus = st.form_submit_button("Hapus entri terpilih")
        if edit:
            entri[index] = ubah_porsi(entri[index], baru)
        if hapus:
            entri.pop(index)
        if edit or hapus:
            tandai_perubahan()
            st.rerun()
    ringkasan(entri, data["profil"]["target_harian"])


def halaman_analisis(data: dict[str, Any], tanggal: str) -> None:
    """Menampilkan grafik dengan satuan konsisten dan rekap tanggal yang benar-benar dicatat."""
    st.header("Analisis & riwayat")
    entri = data["riwayat_log"].get(tanggal, [])
    target = data["profil"]["target_harian"]
    total = total_asupan(entri)
    ringkasan(entri, target)
    if entri:
        a, b = st.columns(2)
        if sum(energi_makro(total).values()) > 0:
            a.plotly_chart(grafik_makro(total), width="stretch")
        else:
            a.info("Energi makro masih nol; diagram proporsi belum dapat dibuat.")
        b.plotly_chart(grafik_target(total, target), width="stretch")
        st.caption("Diagram donat memakai perkiraan energi 4/4/9, bukan perbandingan gram. Angkanya dapat berbeda dari kalori pada katalog/label.")
    rekap: list[dict[str, Any]] = []
    for hari in sorted(data["riwayat_log"], reverse=True):
        catatan = data["riwayat_log"][hari]
        rekap.append({"Tanggal": hari, "Jumlah entri": len(catatan), **total_asupan(catatan)})
    if rekap:
        st.subheader("Rekap catatan")
        st.dataframe(rekap, hide_index=True, width="stretch")
    else:
        st.info("Riwayat belum tersedia. Hari tanpa catatan tidak diasumsikan sebagai nol konsumsi.")
    st.download_button("Unduh rekap CSV", "\ufeff" + ekspor_csv(data), "nutrikos_rekap.csv", "text/csv")


def main() -> None:
    """Menjalankan aplikasi lokal dengan satu profil, keadaan sesi, dan penyimpanan eksplisit."""
    st.set_page_config(page_title="NutriKos", page_icon="🥗", layout="wide")
    st.title("NutriKos")
    st.caption("Catat makananmu, pahami angka gizinya. Proyek pembelajaran DDP 1.")
    st.warning("Katalog bawaan berisi DATA CONTOH ILUSTRATIF, belum terverifikasi. Ganti dengan data bersumber sebelum digunakan untuk pencatatan nyata.")
    with st.expander("Cara kerja & batas model"):
        st.write("Aplikasi edukasi untuk dewasa, bukan diagnosis atau resep diet. Estimasi tidak berlaku sebagai anjuran personal bagi anak, kehamilan/menyusui, atau kondisi medis tertentu. BMR bukan batas aman diet universal. Kategori status adalah aturan proyek dan tidak memastikan kecukupan gizi.")
        st.write("Tidak ada kamera, akun, atau layanan luar. Satu file lokal dipakai bersama oleh sesi aplikasi ini; gunakan satu pengguna pada satu waktu. Tekan Simpan semua perubahan sebelum menutup atau memuat ulang tab.")
    try:
        katalog = muat_katalog(ROOT / "data" / "katalog_makanan.json")
        if "data" not in st.session_state:
            data_awal, versi = muat_pengguna(USER_FILE)
            st.session_state["data"] = data_awal
            st.session_state["versi"] = versi
            st.session_state["dirty"] = False
    except KesalahanData as exc:
        st.error(str(exc))
        st.info("File asli tidak diubah. Perbaiki file atau pulihkan salinan yang valid lalu muat ulang aplikasi.")
        st.stop()
    data = st.session_state["data"]
    st.sidebar.title("Ruang NutriKos")
    st.sidebar.caption("Satu profil lokal · simpan secara eksplisit")
    if not data["profil"] and st.sidebar.button("Coba profil contoh"):
        data["profil"] = deepcopy(profil_contoh())
        tandai_perubahan()
        st.rerun()
    halaman = st.sidebar.radio("Halaman", ["Profil", "Catatan Makanan", "Analisis & Riwayat"])
    hari_ini = datetime.now(timezone(timedelta(hours=7))).date()
    tanggal = st.sidebar.date_input("Tanggal catatan (WIB)", value=hari_ini).isoformat()
    if st.sidebar.button("Simpan semua perubahan", type="primary"):
        try:
            versi_baru = simpan_pengguna(data, USER_FILE, st.session_state["versi"])
        except (KesalahanData, ValueError) as exc:
            st.sidebar.error(str(exc))
        else:
            st.session_state["versi"] = versi_baru
            st.session_state["dirty"] = False
            st.sidebar.success("Data tersimpan.")
    st.sidebar.caption("● Ada perubahan belum disimpan" if st.session_state["dirty"] else "Tidak ada perubahan belum disimpan")
    st.sidebar.download_button("Cadangkan sesi ke JSON", ekspor_json(data), "nutrikos_cadangan.json", "application/json")
    if halaman == "Profil":
        halaman_profil(data)
    elif not data["profil"]:
        st.info("Buat profil pada halaman Profil terlebih dahulu.")
    elif halaman == "Catatan Makanan":
        halaman_log(data, katalog, tanggal)
    else:
        halaman_analisis(data, tanggal)


if __name__ == "__main__":
    main()
