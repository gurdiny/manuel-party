# 🎃 Urías Fest 3

Invitación web para el cumpleaños de Manuel Urias: fiesta de disfraces, viernes 16 de octubre de 2026, 10:00 PM.

Es una sola página (`index.html`) sin frameworks ni dependencias: HTML, CSS y JavaScript.

## Estructura

```
index.html          La invitación (todo el diseño y la lógica viven aquí)
img/                Fotos optimizadas en WebP (las genera optimizar.py)
audio/              Música de fondo optimizada (la genera optimizar.py)
.github/workflows/  Deploy automático a GitHub Pages
```

Archivos que solo existen en tu compu (están en `.gitignore` y nunca se suben):

```
optimizar.py        Script para comprimir fotos y audio
fotos/pagina/       Originales de la portada y de "Así se puso el año pasado"
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
   - Portada o fotos de la sección "Así se puso…": en `fotos/pagina/` (`portada.webp`, `pasado_1.jpeg`, …). Se convierten a `img/portada.webp`, `img/pasado_1.webp`, etc.
   - Música: en la raíz o en `audio-original/` (mp3, m4a, ogg, wav…). Si el archivo se llama "WhatsApp Audio…", el script usa el título de la canción como nombre.
2. Corre el script:

   ```bash
   python3 optimizar.py            # procesa solo lo nuevo
   python3 optimizar.py --forzar   # vuelve a procesar todo
   ```

El script:

- Convierte las fotos a WebP (máximo 1600 px, calidad 80) y respeta la rotación del celular.
- Si la foto tiene fondo transparente (como la portada), la recorta al contorno del personaje.
- Convierte el audio a MP3 de 128 kbps.

Nunca borra ni modifica los originales.

**Requisitos:** Python 3.10+ y Pillow (`sudo apt install python3-pil`). Para comprimir o convertir audio necesitas ffmpeg (`sudo apt install ffmpeg`). Sin ffmpeg, los MP3 se copian tal cual.

## Publicar (deploy)

Cada `git push` a `main` publica la página en GitHub Pages. El workflow copia **solo** `index.html`, `img/` y `audio/`, y antes de publicar verifica que no haya nada más que archivos estáticos (`.html`, `.webp`, `.jpg`, `.png`, `.mp3`). Si se cuela cualquier otro tipo de archivo, el deploy falla en lugar de publicarlo.

Seguridad:

- `optimizar.py` (y cualquier `.py`) está en `.gitignore`: no se sube ni al repo ni al sitio.
- La página trae una política de seguridad (CSP) que solo permite cargar recursos propios, Google Fonts, Google Maps y Spotify. Si agregas otro servicio embebido, tienes que añadir su dominio en la etiqueta `Content-Security-Policy` del `<head>`.
- Las acciones de GitHub del deploy están fijadas por commit para que no puedan cambiar sin que lo notes.

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
