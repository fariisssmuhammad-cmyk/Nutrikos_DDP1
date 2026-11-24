"""Perhitungan deterministik berdasarkan aturan model proyek NutriKos."""

from typing import Any

from nutrikos.validation import AKTIVITAS, GIZI, TUJUAN, angka, validasi_makanan, validasi_profil


def hitung_bmr(berat_kg: float, tinggi_cm: float, usia: int, jenis_kelamin: str) -> float:
    """Menghitung estimasi energi istirahat dengan persamaan Mifflin–St Jeor."""
    berat = angka(berat_kg, "Berat", positif=True)
    tinggi = angka(tinggi_cm, "Tinggi", positif=True)
    umur = angka(usia, "Usia", positif=True)
    if not umur.is_integer() or jenis_kelamin not in ("Pria", "Wanita"):
        raise ValueError("Usia harus bulat dan jenis kelamin harus Pria atau Wanita.")
    konstanta = 5 if jenis_kelamin == "Pria" else -161
    hasil = 10 * berat + 6.25 * tinggi - 5 * umur + konstanta
    return angka(hasil, "Hasil estimasi BMR", positif=True)


def hitung_tdee(bmr: float, faktor_aktivitas: float) -> float:
    """Mengalikan estimasi energi istirahat dengan salah satu faktor proyek."""
    dasar = angka(bmr, "BMR", positif=True)
    faktor = angka(faktor_aktivitas, "Faktor aktivitas", positif=True)
    if faktor not in AKTIVITAS.values():
        raise ValueError("Faktor aktivitas tidak didukung.")
    return angka(dasar * faktor, "TDEE", positif=True)


def hitung_target_kalori(bmr: float, tdee: float, tujuan: str) -> float:
    """Menerapkan perubahan ±300 kkal; batas BMR adalah aturan proyek, bukan jaminan aman."""
    dasar = angka(bmr, "BMR", positif=True)
    total = angka(tdee, "TDEE", positif=True)
    if total < dasar or tujuan not in TUJUAN:
        raise ValueError("TDEE harus >= BMR dan tujuan harus dikenali.")
    if tujuan == "Turun BB":
        return max(dasar, total - 300)
    if tujuan == "Naik BB":
        return angka(total + 300, "Target kalori", positif=True)
    return total


def hitung_target_makro(target_kalori: float) -> dict[str, float]:
    """Mengubah pembagian energi model 50/20/30 menjadi gram makronutrisi."""
    target = angka(target_kalori, "Target kalori", positif=True)
    return {"target_karbo_g": 0.5 * target / 4,
            "target_protein_g": 0.2 * target / 4,
            "target_lemak_g": 0.3 * target / 9}


def hitung_target_harian(profil: dict[str, Any]) -> dict[str, float]:
    """Menghasilkan seluruh target tanpa pembulatan antara langkah perhitungan."""
    validasi_profil(profil)
    bmr = hitung_bmr(profil["berat_kg"], profil["tinggi_cm"], profil["usia"], profil["jenis_kelamin"])
    tdee = hitung_tdee(bmr, AKTIVITAS[profil["tingkat_aktivitas"]])
    kalori = hitung_target_kalori(bmr, tdee, profil["tujuan"])
    return {"bmr": bmr, "tdee": tdee, "target_kalori": kalori, **hitung_target_makro(kalori)}


def evaluasi_kalori(asupan: float, target: float) -> dict[str, str | float]:
    """Mengelompokkan angka menurut aturan tugas, bukan mendiagnosis kondisi kesehatan.

    Rentang kontinu: <70; 70–<90; 90–110; >110–115; >115 persen.
    Pesan spesifikasi disimpan untuk keterlacakan; UI memakai deskripsi netral.
    """
    realisasi = angka(asupan, "Asupan")
    sasaran = angka(target, "Target", positif=True)
    persen = realisasi / sasaran * 100
    # Kalikan dengan bilangan bulat untuk menghindari 1.15 * 100 = 114.999... .
    pembanding = realisasi * 100
    if pembanding < 70 * sasaran:
        status, warna, pesan = "Defisit Terlalu Ekstrem", "warning", "Asupan energi terlalu rendah, berisiko menurunkan fokus belajar."
        netral = "Asupan yang tercatat masih di bawah 70% target model."
    elif pembanding < 90 * sasaran:
        status, warna, pesan = "Defisit Ringan", "info", "Asupan sedikit di bawah target harian, pastikan kebutuhan gizi tetap tercukupi."
        netral = "Asupan yang tercatat berada pada 70% hingga kurang dari 90% target model."
    elif pembanding <= 110 * sasaran:
        status, warna, pesan = "Target Tercapai Ideal", "success", "Kebutuhan kalori harian terpenuhi dengan baik."
        netral = "Asupan yang tercatat berada pada 90–110% target model."
    elif pembanding <= 115 * sasaran:
        status, warna, pesan = "Surplus Ringan", "info", "Asupan sedikit di atas target harian."
        netral = "Asupan yang tercatat di atas 110% hingga 115% target model."
    else:
        status, warna, pesan = "Surplus Berlebih", "warning", "Kalori melebihi batas harian, kurangi porsi camilan/minuman manis."
        netral = "Asupan yang tercatat berada di atas 115% target model."
    return {"status": status, "warna": warna, "pesan_spesifikasi": pesan,
            "pesan": netral, "persentase": persen}


def evaluasi_protein(realisasi: float, target: float) -> str | None:
    """Memberi saran sesuai aturan proyek jika protein tercatat kurang dari 75% target."""
    aktual = angka(realisasi, "Protein")
    sasaran = angka(target, "Target protein", positif=True)
    if aktual < 0.75 * sasaran:
        return "Saran nutrisi: Tambahkan sumber protein seperti telur, dada ayam, tempe, atau tahu."
    return None


def buat_entri(makanan: dict[str, Any], porsi: float) -> dict[str, Any]:
    """Membuat snapshot log dengan semua nilai gizi sudah dikalikan porsi tepat satu kali."""
    validasi_makanan(makanan)
    jumlah = angka(porsi, "Porsi", positif=True)
    entri: dict[str, Any] = {"id_makanan": makanan["id_makanan"],
                             "nama_makanan": makanan["nama_makanan"], "porsi": jumlah}
    for kunci in GIZI:
        entri[kunci] = angka(float(makanan[kunci]) * jumlah, kunci)
    return entri


def ubah_porsi(entri: dict[str, Any], porsi_baru: float) -> dict[str, Any]:
    """Mengubah porsi suatu snapshot tanpa mengambil ulang nilai dari katalog."""
    validasi_makanan(entri, log=True)
    jumlah = angka(porsi_baru, "Porsi baru", positif=True)
    hasil = dict(entri)
    for kunci in GIZI:
        hasil[kunci] = angka(entri[kunci] / entri["porsi"] * jumlah, kunci)
    hasil["porsi"] = jumlah
    return hasil


def total_asupan(entri: list[dict[str, Any]]) -> dict[str, float]:
    """Menjumlahkan snapshot yang sudah dikalikan porsi tanpa mengalikannya kembali."""
    total = dict.fromkeys(GIZI, 0.0)
    for makanan in entri:
        validasi_makanan(makanan, log=True)
        for kunci in GIZI:
            total[kunci] += makanan[kunci]
    for kunci in GIZI:
        angka(total[kunci], kunci)
    return total


def energi_makro(total: dict[str, float]) -> dict[str, float]:
    """Menghasilkan energi tiap makro untuk diagram proporsi energi, bukan proporsi gram."""
    return {"Karbohidrat": angka(total["karbo_gram"], "Karbohidrat") * 4,
            "Protein": angka(total["protein_gram"], "Protein") * 4,
            "Lemak": angka(total["lemak_gram"], "Lemak") * 9}
