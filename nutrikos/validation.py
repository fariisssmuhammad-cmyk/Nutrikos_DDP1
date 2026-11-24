"""Pemeriksaan kontrak data tanpa ketergantungan pada Streamlit."""

import math
from datetime import date
from typing import Any

AKTIVITAS: dict[str, float] = {
    "Sedentari (1.2)": 1.2,
    "Aktivitas Ringan (1.375)": 1.375,
    "Aktivitas Sedang (1.55)": 1.55,
    "Sangat Aktif (1.725)": 1.725,
}
TUJUAN: tuple[str, ...] = ("Pertahankan BB", "Turun BB", "Naik BB")
GIZI: tuple[str, ...] = ("kalori_kkal", "protein_gram", "karbo_gram", "lemak_gram")
TARGET: tuple[str, ...] = (
    "bmr", "tdee", "target_kalori", "target_karbo_g", "target_protein_g", "target_lemak_g",
)


def angka(nilai: object, nama: str, minimum: float = 0.0, positif: bool = False) -> float:
    """Memastikan angka hingga, bukan boolean, dan memenuhi batas minimum."""
    if isinstance(nilai, bool) or not isinstance(nilai, (int, float)):
        raise ValueError(f"{nama} harus berupa angka.")
    hasil = float(nilai)
    if not math.isfinite(hasil) or hasil < minimum or (positif and hasil <= 0):
        raise ValueError(f"{nama} tidak memenuhi batas angka yang diizinkan.")
    return hasil


def teks(nilai: object, nama: str) -> str:
    """Memastikan teks tidak kosong dan membatasi panjangnya hingga 200 karakter."""
    if not isinstance(nilai, str) or not nilai.strip() or len(nilai) > 200:
        raise ValueError(f"{nama} harus berupa teks sepanjang 1–200 karakter.")
    return nilai.strip()


def validasi_profil(profil: dict[str, Any]) -> None:
    """Memeriksa profil dewasa dalam rentang input aplikasi edukasi."""
    teks(profil.get("nama"), "Nama")
    if profil.get("jenis_kelamin") not in ("Pria", "Wanita"):
        raise ValueError("Jenis kelamin untuk persamaan harus Pria atau Wanita.")
    usia = angka(profil.get("usia"), "Usia", 18)
    if not usia.is_integer() or usia > 100:
        raise ValueError("Usia harus bilangan bulat 18–100 tahun.")
    berat = angka(profil.get("berat_kg"), "Berat", positif=True)
    tinggi = angka(profil.get("tinggi_cm"), "Tinggi", positif=True)
    if not 20 <= berat <= 350 or not 100 <= tinggi <= 250:
        raise ValueError("Batas input aplikasi: berat 20–350 kg dan tinggi 100–250 cm.")
    if not isinstance(profil.get("tingkat_aktivitas"), str) or profil["tingkat_aktivitas"] not in AKTIVITAS:
        raise ValueError("Tingkat aktivitas tidak dikenali.")
    if profil.get("tujuan") not in TUJUAN:
        raise ValueError("Tujuan tidak dikenali.")


def validasi_makanan(makanan: dict[str, Any], log: bool = False) -> None:
    """Memeriksa makanan; nilai log sudah merupakan total setelah pengalian porsi."""
    if not isinstance(makanan, dict):
        raise ValueError("Makanan harus berupa objek JSON.")
    teks(makanan.get("id_makanan"), "ID makanan")
    teks(makanan.get("nama_makanan"), "Nama makanan")
    if log:
        angka(makanan.get("porsi"), "Porsi", positif=True)
    else:
        teks(makanan.get("kategori"), "Kategori")
    for kunci in GIZI:
        angka(makanan.get(kunci), kunci)


def validasi_katalog(data: object) -> None:
    """Memeriksa daftar makanan serta keunikan identitasnya."""
    if not isinstance(data, list) or not data:
        raise ValueError("Katalog harus berupa daftar makanan yang tidak kosong.")
    identitas: set[str] = set()
    for makanan in data:
        validasi_makanan(makanan)
        if makanan["id_makanan"] in identitas:
            raise ValueError("ID makanan dalam katalog harus unik.")
        identitas.add(makanan["id_makanan"])


def validasi_data_pengguna(data: object) -> None:
    """Memeriksa profil dan catatan bertanggal tanpa mengubah data masukan."""
    if not isinstance(data, dict) or set(data) != {"profil", "riwayat_log"}:
        raise ValueError("Data harus memiliki tepat kunci profil dan riwayat_log.")
    profil = data["profil"]
    if not isinstance(profil, dict):
        raise ValueError("Profil harus berupa objek JSON.")
    if profil:
        validasi_profil(profil)
        target = profil.get("target_harian")
        if not isinstance(target, dict):
            raise ValueError("Target harian tidak tersedia.")
        for kunci in TARGET:
            angka(target.get(kunci), kunci, positif=True)
        # Impor lokal menghindari lingkaran impor antara core dan validation.
        from nutrikos.core import hitung_target_harian

        diharapkan = hitung_target_harian(profil)
        for kunci in TARGET:
            # Toleransi mengizinkan angka contoh kontrak yang dibulatkan satu desimal.
            if abs(float(target[kunci]) - diharapkan[kunci]) > 0.6:
                raise ValueError(f"Target {kunci} tidak sesuai dengan profil; hitung ulang.")
    riwayat = data["riwayat_log"]
    if not isinstance(riwayat, dict):
        raise ValueError("Riwayat harus berupa objek bertanggal.")
    for tanggal, entri in riwayat.items():
        if not isinstance(tanggal, str):
            raise ValueError("Tanggal harus berupa teks YYYY-MM-DD.")
        try:
            parsed = date.fromisoformat(tanggal)
        except ValueError as exc:
            raise ValueError("Tanggal riwayat tidak valid.") from exc
        if parsed.isoformat() != tanggal or not isinstance(entri, list):
            raise ValueError("Tanggal harus YYYY-MM-DD dan catatan harus berupa daftar.")
        for makanan in entri:
            validasi_makanan(makanan, log=True)
