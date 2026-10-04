# 🎃 Urías Fest 3

Invitación web para el cumpleaños de Manuel Urias: fiesta de disfraces, viernes 16 de octubre de 2026, 10:00 PM.

Es una sola página (`index.html`) sin frameworks ni dependencias: HTML, CSS y JavaScript.

## Estructura

```
index.html          La invitación (todo el diseño y la lógica viven aquí)
img/                Fotos optimizadas en WebP (las genera optimizar.py)
  vivio/            Fotos de la cinta "Así se vivió el año pasado"
audio/              Música de fondo optimizada (la genera optimizar.py)
optimizar.py        Script para comprimir fotos y audio (no se publica)
.github/workflows/  Deploy automático a GitHub Pages
```

Carpetas que solo existen en tu compu (están en `.gitignore`):

```
fotos/pagina/       Originales de la portada y de "Así se puso el año pasado"
fotos/vivio/        Originales de la galería "Así se vivió el año pasado"
audio-original/     Pon aquí audios originales (o déjalos en la raíz)
```

## Ver la página en tu compu

Abre `index.html` en el navegador, o levanta un servidor local:

```bash
python3 -m http.server 8000
# abre http://localhost:8000
```

## Agregar o cambiar fotos y música

1. Copia los archivos originales:
   - Portada o fotos de la sección "Así se puso…": en `fotos/pagina/` (`portada.jpeg`, `pasado_1.jpeg`, …). Se convierten a `img/portada.webp`, `img/pasado-1.webp`, etc.
   - Fotos para la cinta "Así se vivió el año pasado": en `fotos/vivio/`.
   - Música: en la raíz o en `audio-original/` (mp3, m4a, ogg, wav…). Si el archivo se llama "WhatsApp Audio…", el script usa el título de la canción como nombre.
2. Corre el script:

   ```bash
   python3 optimizar.py            # procesa solo lo nuevo
   python3 optimizar.py --forzar   # vuelve a procesar todo
   ```

El script:

- Convierte las fotos a WebP (máximo 1600 px, calidad 80) y respeta la rotación del celular.
- Arma la cinta "Así se vivió" dentro de `index.html`. Si no hay fotos, oculta la sección.
- Convierte el audio a MP3 de 128 kbps.

Nunca borra ni modifica los originales.

**Requisitos:** Python 3.10+ y Pillow (`sudo apt install python3-pil`). Para comprimir o convertir audio necesitas ffmpeg (`sudo apt install ffmpeg`). Sin ffmpeg, los MP3 se copian tal cual.

## Publicar (deploy)

Cada `git push` a `main` publica la página en GitHub Pages. El workflow copia **solo** `index.html`, `img/` y `audio/`; `optimizar.py`, este README y los originales no se publican.

Configuración de una sola vez: en GitHub ve a **Settings → Pages → Source** y elige **GitHub Actions**.

## Cambios comunes en `index.html`

| Qué | Dónde buscar |
|---|---|
| Fecha y hora del contador | `new LuxuryCountdown('2026-10-16T22:00:00-05:00')` |
| Número de WhatsApp | `https://wa.me/525522194706` (aparece en varios botones) |
| Agenda | sección `id="lo-basico"`, bloque `timeline` |
| Ubicación | iframe de Google Maps en `id="ubicacion"` (coordenadas `21.1733894,-86.8515625`) |
| Playlist | sección `id="playlist"` |
| Colores | variables `--c-orange`, `--c-amber`, `--c-magenta`, `--c-purple` al inicio del `<style>` |

La hora usa `-05:00` porque Cancún no cambia de horario. Si mueves la fecha, actualiza también el enlace de "Guardar fecha" (está en UTC) y el bloque JSON-LD del `<head>`.
