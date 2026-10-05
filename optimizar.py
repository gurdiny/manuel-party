#!/usr/bin/env python3
"""
Optimiza las fotos y el audio de la invitación Urías Fest 3.

Uso:
    python3 optimizar.py            # procesa lo nuevo o lo que cambió
    python3 optimizar.py --forzar   # vuelve a procesar todo

Qué hace:
  1. Fotos de fotos/pagina/ (portada, pasado_1, ...) -> img/<nombre>.webp
     Las imágenes con fondo transparente se recortan al contorno del personaje.
  2. Audios de la raíz y de audio-original/ -> audio/<nombre>.mp3
     Si el archivo se llama "WhatsApp Audio ...", usa el título de la canción.

Requisitos:
  - Pillow:  sudo apt install python3-pil   (o pip install Pillow)
  - ffmpeg (opcional, para recomprimir audio):  sudo apt install ffmpeg
    Sin ffmpeg, los MP3 se copian tal cual y los demás formatos se omiten.

Los archivos originales nunca se modifican ni se borran.
"""

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Falta Pillow. Instálalo con: sudo apt install python3-pil  (o pip install Pillow)")

RAIZ = Path(__file__).resolve().parent

DIR_IMG = RAIZ / "img"
DIR_PAGINA_ORIGEN = RAIZ / "fotos" / "pagina"
DIR_AUDIO_ORIGEN = RAIZ / "audio-original"
DIR_AUDIO_SALIDA = RAIZ / "audio"

EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}
EXT_AUDIO = {".mp3", ".mpeg", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".flac"}

LADO_MAXIMO = 1600       # px del lado más largo
CALIDAD_WEBP = 80        # 0-100
CALIDAD_WEBP_ALFA = 88   # un poco más alta para no ensuciar los bordes de los recortes
MARGEN_RECORTE = 24      # px de aire alrededor del personaje al recortar transparencia
BITRATE_AUDIO = "128k"   # suficiente para música en el celular


def slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9_]+", "-", texto).strip("-_").lower()
    return texto or "archivo"


def kb(n: int) -> str:
    return f"{n / 1024:,.0f} KB"


def necesita_proceso(origen: Path, destino: Path, forzar: bool) -> bool:
    return forzar or not destino.exists() or destino.stat().st_mtime < origen.stat().st_mtime


# --------------------------------------------------------------------------
# Imágenes
# --------------------------------------------------------------------------
def recortar_transparencia(im: Image.Image) -> Image.Image:
    """Quita el espacio vacío alrededor de un recorte con fondo transparente."""
    caja = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not caja:
        return im
    izq, arr, der, aba = caja
    m = MARGEN_RECORTE
    return im.crop((max(izq - m, 0), max(arr - m, 0), min(der + m, im.width), min(aba + m, im.height)))


def comprimir_imagen(origen: Path, destino: Path, forzar: bool) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not necesita_proceso(origen, destino, forzar):
        return

    with Image.open(origen) as im:
        im = ImageOps.exif_transpose(im)   # respeta la rotación del celular
        tiene_alfa = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        im = im.convert("RGBA" if tiene_alfa else "RGB")
        if tiene_alfa:
            im = recortar_transparencia(im)
        im.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)
        im.save(destino, "WEBP", quality=CALIDAD_WEBP_ALFA if tiene_alfa else CALIDAD_WEBP, method=6)

    antes, despues = origen.stat().st_size, destino.stat().st_size
    cambio = 100 - despues * 100 // max(antes, 1)
    detalle = f"{cambio}% menos" if cambio > 0 else "recortada, sin ahorro de peso"
    print(f"  🖼  {origen.name} -> {destino.relative_to(RAIZ)}  {kb(antes)} -> {kb(despues)}  ({detalle})")


def procesar_imagenes_pagina(forzar: bool) -> None:
    if not DIR_PAGINA_ORIGEN.is_dir():
        return
    fotos = sorted(p for p in DIR_PAGINA_ORIGEN.iterdir() if p.is_file() and p.suffix.lower() in EXT_IMAGEN)
    if not fotos:
        return
    print("Fotos de la página:")
    for foto in fotos:
        comprimir_imagen(foto, DIR_IMG / f"{slug(foto.stem)}.webp", forzar)


# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------
def buscar_ffmpeg() -> str | None:
    ruta = shutil.which("ffmpeg")
    if ruta:
        return ruta
    try:
        import imageio_ffmpeg  # pip install imageio-ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def titulo_id3(ruta: Path) -> str | None:
    """Lee el título (TIT2) de un MP3 con etiquetas ID3v2.3/2.4."""
    def syncsafe(b: bytes) -> int:
        return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]

    with open(ruta, "rb") as f:
        cabecera = f.read(10)
        if len(cabecera) < 10 or cabecera[:3] != b"ID3":
            return None
        version = cabecera[3]
        datos = f.read(syncsafe(cabecera[6:10]))

    i = 0
    while i + 10 <= len(datos):
        marco = datos[i:i + 4]
        if marco == b"\0\0\0\0":
            break
        crudo = datos[i + 4:i + 8]
        tamano = syncsafe(crudo) if version == 4 else int.from_bytes(crudo, "big")
        if marco == b"TIT2":
            cuerpo = datos[i + 10:i + 10 + tamano]
            codificacion = {0: "latin-1", 1: "utf-16", 2: "utf-16-be", 3: "utf-8"}.get(cuerpo[0], "latin-1")
            return cuerpo[1:].decode(codificacion, errors="ignore").strip("\x00 ").strip() or None
        i += 10 + tamano
    return None


def nombre_audio(origen: Path) -> str:
    if origen.stem.lower().startswith("whatsapp audio"):
        titulo = titulo_id3(origen)
        if titulo:
            return slug(titulo)
    return slug(origen.stem)


def procesar_audio(forzar: bool) -> None:
    candidatos = [p for p in RAIZ.iterdir() if p.is_file() and p.suffix.lower() in EXT_AUDIO]
    if DIR_AUDIO_ORIGEN.is_dir():
        candidatos += [p for p in DIR_AUDIO_ORIGEN.rglob("*") if p.is_file() and p.suffix.lower() in EXT_AUDIO]
    if not candidatos:
        return

    print("Audio:")
    ffmpeg = buscar_ffmpeg()
    DIR_AUDIO_SALIDA.mkdir(exist_ok=True)

    for origen in sorted(candidatos):
        destino = DIR_AUDIO_SALIDA / f"{nombre_audio(origen)}.mp3"
        if not necesita_proceso(origen, destino, forzar):
            print(f"  🎵 {destino.relative_to(RAIZ)} ya está al día.")
            continue

        es_mp3 = origen.read_bytes()[:3] == b"ID3" or origen.suffix.lower() in {".mp3", ".mpeg"}

        if ffmpeg:
            temporal = destino.with_suffix(".tmp.mp3")
            resultado = subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-i", str(origen),
                 "-vn", "-map_metadata", "-1", "-ac", "2", "-ar", "44100",
                 "-codec:a", "libmp3lame", "-b:a", BITRATE_AUDIO, str(temporal)],
                capture_output=True, text=True,
            )
            if resultado.returncode != 0:
                temporal.unlink(missing_ok=True)
                print(f"  ❌ {origen.name}: ffmpeg falló -> {resultado.stderr.strip()[:200]}")
                continue
            # Si recomprimir no ahorra nada, conserva el original
            if es_mp3 and temporal.stat().st_size >= origen.stat().st_size:
                temporal.unlink()
                shutil.copy2(origen, destino)
            else:
                temporal.replace(destino)
        elif es_mp3:
            shutil.copy2(origen, destino)
            print("  ℹ  Sin ffmpeg: copio el MP3 sin recomprimir (sudo apt install ffmpeg para comprimirlo).")
        else:
            print(f"  ⚠  {origen.name}: necesito ffmpeg para convertirlo a MP3 (sudo apt install ffmpeg).")
            continue

        print(f"  🎵 {origen.name} -> {destino.relative_to(RAIZ)}  "
              f"{kb(origen.stat().st_size)} -> {kb(destino.stat().st_size)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimiza fotos y audio de la invitación.")
    parser.add_argument("--forzar", action="store_true", help="vuelve a procesar aunque ya exista la salida")
    args = parser.parse_args()

    procesar_imagenes_pagina(args.forzar)
    procesar_audio(args.forzar)
    print("Listo ✨")


if __name__ == "__main__":
    main()
