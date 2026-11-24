"""Baca/tulis JSON yang tervalidasi serta ekspor CSV tanpa kode tampilan."""

import csv
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from nutrikos.core import total_asupan
from nutrikos.validation import validasi_data_pengguna, validasi_katalog


class KesalahanData(ValueError):
    """Menandakan file rusak, skema tidak sesuai, atau konflik penyimpanan."""


def data_kosong() -> dict[str, Any]:
    """Menghasilkan wadah baru sesuai dua kunci utama kontrak JSON."""
    return {"profil": {}, "riwayat_log": {}}


def tolak_konstanta(nilai: str) -> None:
    """Menolak NaN dan Infinity yang bukan angka JSON standar."""
    raise KesalahanData(f"Konstanta {nilai} tidak diizinkan dalam JSON.")


def objek_unik(pasangan: list[tuple[str, Any]]) -> dict[str, Any]:
    """Menolak kunci berulang agar data lama tidak diam-diam tertimpa saat dibaca."""
    hasil: dict[str, Any] = {}
    for kunci, nilai in pasangan:
        if kunci in hasil:
            raise KesalahanData(f"Kunci JSON berulang: {kunci}.")
        hasil[kunci] = nilai
    return hasil


def baca_json(path: Path) -> Any:
    """Membaca UTF-8 dan melaporkan kesalahan tanpa mengubah file asli."""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"),
                          parse_constant=tolak_konstanta, object_pairs_hook=objek_unik)
    except (OSError, UnicodeError, ValueError) as exc:
        raise KesalahanData(f"Tidak dapat membaca {path.name}: {exc}") from exc


def sidik_file(path: Path) -> str:
    """Menghasilkan sidik isi untuk mendeteksi perubahan dari sesi lokal lain."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
    except OSError as exc:
        raise KesalahanData(f"Tidak dapat membaca versi file: {exc}") from exc


def muat_pengguna(path: Path) -> tuple[dict[str, Any], str]:
    """Memuat data dan sidik versinya; hanya file yang belum ada mendapat data kosong."""
    if not path.exists():
        return data_kosong(), ""
    # Periksa sebelum/sesudah membaca agar isi dan sidik berasal dari versi yang sama.
    sebelum = sidik_file(path)
    data = baca_json(path)
    sesudah = sidik_file(path)
    if sebelum != sesudah:
        raise KesalahanData("File berubah saat dibaca; coba muat ulang.")
    try:
        validasi_data_pengguna(data)
    except ValueError as exc:
        raise KesalahanData(f"Skema {path.name} tidak sesuai: {exc}") from exc
    return data, sesudah


def muat_katalog(path: Path) -> list[dict[str, Any]]:
    """Membaca katalog serta memeriksa nilai dan ID makanan."""
    data = baca_json(path)
    try:
        validasi_katalog(data)
    except ValueError as exc:
        raise KesalahanData(f"Katalog tidak valid: {exc}") from exc
    return data


def simpan_pengguna(data: dict[str, Any], path: Path, versi_diharapkan: str) -> str:
    """Menulis melalui file sementara, menolak konflik, dan mempertahankan file lama saat gagal.

    Ditujukan bagi satu pengguna lokal, bukan basis data transaksi multi-pengguna.
    """
    validasi_data_pengguna(data)
    if sidik_file(path) != versi_diharapkan:
        raise KesalahanData("File sudah berubah. Ekspor cadangan sesi ini lalu muat ulang; penyimpanan dibatalkan.")
    if path.exists():
        muat_pengguna(path)  # File rusak tidak boleh ditimpa walaupun sidiknya cocok.
    isi = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    sementara: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                         suffix=".tmp", delete=False) as file:
            sementara = Path(file.name)
            file.write(isi)
            file.flush()
            os.fsync(file.fileno())
        if sidik_file(path) != versi_diharapkan:
            raise KesalahanData("File berubah sebelum penyimpanan selesai; muat ulang.")
        os.replace(sementara, path)
    except OSError as exc:
        raise KesalahanData(f"Gagal menyimpan; perubahan sesi tetap tersedia: {exc}") from exc
    finally:
        if sementara is not None and sementara.exists():
            sementara.unlink()
    return hashlib.sha256(isi.encode("utf-8")).hexdigest()


def ekspor_json(data: dict[str, Any]) -> str:
    """Membuat cadangan JSON tanpa mengubah file data aplikasi."""
    validasi_data_pengguna(data)
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)


def sel_csv(nilai: str) -> str:
    """Mencegah nama pengguna diperlakukan sebagai rumus oleh aplikasi spreadsheet."""
    return "'" + nilai if nilai.lstrip().startswith(("=", "+", "-", "@")) else nilai


def ekspor_csv(data: dict[str, Any]) -> str:
    """Mengekspor rekap per tanggal dengan modul csv dan satuan pada judul kolom."""
    validasi_data_pengguna(data)
    keluaran = io.StringIO(newline="")
    penulis = csv.writer(keluaran)
    penulis.writerow(["tanggal", "nama", "jumlah_entri", "kalori_kkal", "protein_gram", "karbo_gram", "lemak_gram"])
    nama = sel_csv(data["profil"].get("nama", ""))
    for tanggal in sorted(data["riwayat_log"]):
        entri = data["riwayat_log"][tanggal]
        total = total_asupan(entri)
        penulis.writerow([tanggal, nama, len(entri), total["kalori_kkal"],
                          total["protein_gram"], total["karbo_gram"], total["lemak_gram"]])
    return keluaran.getvalue()
