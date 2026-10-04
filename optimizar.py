#!/usr/bin/env python3
"""
Optimiza las fotos y el audio de la invitación Urías Fest 3.

Uso:
    python3 optimizar.py            # procesa lo nuevo o lo que cambió
    python3 optimizar.py --forzar   # vuelve a procesar todo

Qué hace:
  1. Fotos de fotos/pagina/ (portada, pasado_1, ...) -> img/<nombre>.webp
  2. Fotos de fotos/vivio/ -> img/vivio/<nombre>.webp, y arma la galería
     "Así se vivió el año pasado" dentro de index.html (si no hay fotos, la oculta).
  3. Audios de la raíz y de audio-original/ -> audio/<nombre>.mp3
     Si el archivo se llama "WhatsApp Audio ...", usa el título de la canción.

Requisitos:
  - Pillow:  sudo apt install python3-pil   (o pip install Pillow)
  - ffmpeg (opcional, para recomprimir audio):  sudo apt install ffmpeg
    Sin ffmpeg, los MP3 se copian tal cual y los demás formatos se omiten.

Los archivos originales nunca se modifican ni se borran.
"""

import argparse
import html
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
INDEX = RAIZ / "index.html"

DIR_IMG = RAIZ / "img"
DIR_PAGINA_ORIGEN = RAIZ / "fotos" / "pagina"
DIR_VIVIO_ORIGEN = RAIZ / "fotos" / "vivio"
DIR_VIVIO_SALIDA = DIR_IMG / "vivio"
DIR_AUDIO_ORIGEN = RAIZ / "audio-original"
DIR_AUDIO_SALIDA = RAIZ / "audio"

EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}
EXT_AUDIO = {".mp3", ".mpeg", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".flac"}

LADO_MAXIMO = 1600       # px del lado más largo
CALIDAD_WEBP = 80        # 0-100
BITRATE_AUDIO = "128k"   # suficiente para música en el celular

MARCA_INICIO = "<!-- GALERIA-VIVIO:INICIO"
MARCA_FIN = "<!-- GALERIA-VIVIO:FIN -->"


def slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto or "archivo"


def kb(n: int) -> str:
    return f"{n / 1024:,.0f} KB"


def necesita_proceso(origen: Path, destino: Path, forzar: bool) -> bool:
    return forzar or not destino.exists() or destino.stat().st_mtime < origen.stat().st_mtime


# --------------------------------------------------------------------------
# Imágenes
# --------------------------------------------------------------------------
def comprimir_imagen(origen: Path, destino: Path, forzar: bool) -> tuple[int, int]:
    """Devuelve (ancho, alto) de la imagen resultante."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not necesita_proceso(origen, destino, forzar):
        with Image.open(destino) as im:
            return im.size

    with Image.open(origen) as im:
        im = ImageOps.exif_transpose(im)   # respeta la rotación del celular
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        im.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)
        im.save(destino, "WEBP", quality=CALIDAD_WEBP, method=6)
        tamano = im.size

    antes, despues = origen.stat().st_size, destino.stat().st_size
    print(f"  🖼  {origen.name} -> {destino.relative_to(RAIZ)}  "
          f"{kb(antes)} -> {kb(despues)}  ({100 - despues * 100 // max(antes, 1)}% menos)")
    return tamano


def procesar_imagenes_pagina(forzar: bool) -> None:
    if not DIR_PAGINA_ORIGEN.is_dir():
        return
    fotos = sorted(p for p in DIR_PAGINA_ORIGEN.iterdir() if p.is_file() and p.suffix.lower() in EXT_IMAGEN)
    if not fotos:
        return
    print("Fotos de la página:")
    for foto in fotos:
        comprimir_imagen(foto, DIR_IMG / f"{slug(foto.stem)}.webp", forzar)


def procesar_galeria_vivio(forzar: bool) -> None:
    fotos = []
    if DIR_VIVIO_ORIGEN.is_dir():
        fotos = sorted(p for p in DIR_VIVIO_ORIGEN.rglob("*")
                       if p.is_file() and p.suffix.lower() in EXT_IMAGEN)

    items = []
    if fotos:
        print(f"Galería 'Así se vivió el año pasado' ({len(fotos)} fotos):")
    for foto in fotos:
        destino = DIR_VIVIO_SALIDA / f"{slug(foto.stem)}.webp"
        ancho, alto = comprimir_imagen(foto, destino, forzar)
        items.append((destino.relative_to(RAIZ).as_posix(), ancho, alto))

    escribir_galeria_en_index(items)


def escribir_galeria_en_index(items: list[tuple[str, int, int]]) -> None:
    if not INDEX.exists():
        return
    contenido = INDEX.read_text(encoding="utf-8")
    inicio = contenido.find(MARCA_INICIO)
    fin = contenido.find(MARCA_FIN)
    if inicio == -1 or fin == -1:
        print("  ⚠  No encontré las marcas GALERIA-VIVIO en index.html; no toqué la galería.")
        return

    sangria = " " * 10

    def cuadro(i: int, ruta: str, ancho: int, alto: int, copia: bool) -> str:
        ruta = html.escape(ruta)
        extra = ' tabindex="-1" aria-hidden="true"' if copia else ""
        etiqueta = "" if copia else f' aria-label="Ver foto {i} en grande"'
        return (f'{sangria}<button type="button" class="film-frame"{etiqueta}{extra}>'
                f'<img src="{ruta}" alt="Urías Fest 2, foto {i}" width="{ancho}" height="{alto}" '
                f'loading="lazy" decoding="async"></button>')

    # Con pocas fotos se repiten hasta llenar la cinta (mínimo 8 cuadros por vuelta)
    vuelta = [(i, item) for i, item in enumerate(items, 1)]
    while vuelta and len(vuelta) < 8:
        vuelta += vuelta[:len(items)]
    lineas = [cuadro(i, *item, copia=pos >= len(items)) for pos, (i, item) in enumerate(vuelta)]
    # Segunda vuelta idéntica para que la cinta gire sin cortes
    lineas += [cuadro(i, *item, copia=True) for i, item in vuelta]

    cierre_marca = contenido.find("-->", inicio) + 3
    nuevo_bloque = (f'\n{sangria}<div class="filmstrip-track" style="--n:{len(vuelta)}">\n'
                    + "\n".join(lineas)
                    + f"\n{sangria}</div>\n{sangria}") if items else f"\n{sangria}"
    contenido = contenido[:cierre_marca] + nuevo_bloque + contenido[fin:]

    # Muestra u oculta la sección según haya fotos
    patron = re.compile(r'<section id="asi-se-vivio"( hidden)?')
    contenido = patron.sub('<section id="asi-se-vivio"' + ("" if items else " hidden"), contenido, count=1)

    INDEX.write_text(contenido, encoding="utf-8")
    if items:
        print(f"  ✅ Galería actualizada en index.html con {len(items)} fotos.")
    else:
        print(f"Galería 'Así se vivió': sin fotos en {DIR_VIVIO_ORIGEN.relative_to(RAIZ)}/, la sección queda oculta.")


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
    procesar_galeria_vivio(args.forzar)
    procesar_audio(args.forzar)
    print("Listo ✨")


if __name__ == "__main__":
    main()
