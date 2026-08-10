# video-to-frames

Convierte un video en un **HTML atomico y auto-contenido** que se anima con scroll. Un solo archivo. Sin dependencias locales. Abrelo con doble clic, pegalo en una web, subelo a LinkedIn.

## Instalacion

```bash
pip install pillow
```

Tambien necesitas **ffmpeg** en PATH:
- Windows: `winget install Gyan.FFmpeg`
- Mac: `brew install ffmpeg`
- Linux: `apt install ffmpeg`

## Uso

```bash
# Por defecto: nombre "scroll.html" y primeros 20s del video
python build.py mi_video.mp4

# Cambiar el nombre del HTML de salida
python build.py mi_video.mp4 -o mi_demo.html
python build.py mi_video.mp4 -o ~/Desktop/reloj.html
```

El resto se ajusta editando el HTML generado, no desde el CLI.

## Opciones

| Flag                  | Default       | Descripcion                                       |
|-----------------------|---------------|---------------------------------------------------|
| `video`               | (obligatorio) | Ruta al video de entrada                          |
| `-o, --output`        | `scroll.html` | **Nombre del archivo HTML de salida**             |
| `--title`             | `Scroll sequence` | Titulo de la pagina (<title>)                |
| `--duration`          | `20`          | Segundos del video original a usar                |
| `-f, --fps`           | `8`           | Frames por segundo extraidos                      |
| `--max-size`          | `800`         | Ancho maximo en px (mantiene proporcion)          |
| `--scroll-multiplier` | `12`          | vh de scroll por frame (mas bajo = mas denso)     |

## Personalizar el HTML

El script genera el HTML con tema oscuro y barra de progreso sutil arriba. Si quieres cambiar colores, fuentes o estructura, edita el archivo generado directamente. El HTML es un unico archivo y se entiende sin comprimir.

## Como funciona

1. **ffmpeg** toma los primeros `--duration` segundos del video y extrae `--fps` frames por segundo como PNGs.
2. Los PNGs se embeben en el HTML como **data URIs base64** (un solo archivo, sin dependencias externas para los frames).
3. **GSAP + ScrollTrigger** pintan el canvas y lo van actualizando segun el scroll.
4. **Lenis** le da al scroll una sensacion inercial suave.

## Tamano de salida

Aproximadamente 200-400 KB por frame. Para 20s a 8 fps (160 frames) el HTML pesa ~30-50 MB. Si necesitas algo mas ligero, baja `--fps` o `--max-size`.
