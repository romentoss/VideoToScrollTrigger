# video-to-frames

Convierte un video en un **HTML atomico y auto-contenido** que se anima con scroll. Un solo archivo. Sin dependencias locales. Abrelo con doble clic, pegalo en una web o mandalo por correo: no necesita servidor ni hace ninguna peticion de red.

> Para redes sociales (LinkedIn, X...) no sirve subir el HTML: no alojan contenido interactivo. Graba la pantalla del archivo abierto y publica ese video.

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

---

## Llevar la animacion a tu propia pagina

El HTML que genera `build.py` es **atomico**: lleva dentro los frames, el CSS, el JS y los CDN. Puedes usarlo tal cual o extraer las piezas para integrarlo en un proyecto existente. Aqui van las dos rutas.

### Opcion A · Iframe (cero riesgo)

Si solo quieres **mostrar** la animacion dentro de tu web sin tocarla:

```html
<iframe src="scroll.html" style="width:100%; height:100vh; border:0"></iframe>
```

Cero conflictos de CSS, cero JS. El precio: el scroll del iframe es independiente del de tu pagina, asi que pierdes la sensacion de "una sola pagina".

### Opcion B · Integrar en tu pagina (manual)

El HTML generado tiene **4 capas**. Tienes que llevartelas todas o algunas no funcionan.

#### 1. CDN en el `<head>` (obligatorio)

```html
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/lenis@1.1.20/dist/lenis.min.js"></script>
```

GSAP solo no incluye ScrollTrigger: son dos librerias separadas.

#### 2. CSS minimo

Las clases sin las que la animacion se rompe:

- `.sequence` — define la altura total del scroll (se le inyecta `height` desde JS = `scrollMultiplier * frameCount` vh).
- `.sticky` — el contenedor que `pin` mantiene fijo en pantalla.
- `canvas` — tamano `min(85vh, 85vw)` para mantenerlo cuadrado y centrado.
- `html.lenis, html.lenis body { height: auto }` — necesario para que Lenis no rompa el alto calculado.

Si reusas tu propio tema, **cambia las variables CSS** (`--bg`, `--fg`, `--line`) o sobreescribe los selectores en tu hoja.

#### 3. Markup contenedor

```html
<section class="sequence" id="sequence">
  <div class="sticky">
    <canvas id="canvas"></canvas>
  </div>
</section>
```

Cuidado: `.sequence` es el que recibe el `height` dinamico en vh y el que `ScrollTrigger` usa de `trigger`. Si renombras clases o ids, actualiza el `getElementById('sequence')` y el `pin: '.sticky'` en el JS.

#### 4. JS (el bloque mas delicado)

```js
const FRAMES = [/* data URIs con tus frames */];

gsap.registerPlugin(ScrollTrigger);

sequenceEl.style.height = `${scrollMultiplier * frameCount}vh`;
```

Lo que **no puedes saltarte**:

- `sequenceEl.style.height` (en vh) — clave para que el scroll tenga la duracion correcta. Si `frameCount = 160` y `scrollMultiplier = 12`, la zona ocupa `1920vh` de scroll.
- `ScrollTrigger.create({ trigger: sequenceEl, start: 'top top', end: 'bottom bottom', pin: '.sticky', scrub: 0.4, onUpdate: ... })` — esto es lo que pinta un frame u otro segun el progreso.

Lo que **puedes saltarte** si ya tienes tu propio loader o no quieres la barra:

- La barra `.progress` / `progressFill` / `progressCount` y el `<div class="loader">` son opcionales.
- La precarga `preloadFrames()` si quieres probar rapido, pero es necesaria para evitar saltos en los primeros frames.

#### 5. Donde van los frames (la decision clave)

El `build.py` embebe los frames como **data URIs base64** dentro del HTML. Practico para un archivo aislado, pero si tu web ya tiene assets esto no escala (160 frames ≈ 30-50 MB).

Alternativas:

- **Carpeta estatica**: cambia `FRAMES = [...]` por `FRAMES = ["frames/frame_001.webp", "frames/frame_002.webp", ...]`. WebP o AVIF bajan el peso 5-10× frente a PNG base64.
- **Sprite sheet**: una sola imagen con todos los frames y dibujas con `drawImage(img, sx, sy, sw, sh, 0, 0, cw, ch)`. Reduces las peticiones HTTP a 1.
- **Solo el efecto**: si te interesa la mecanica scroll → cambio de frame, sustituye los frames por un `<video>` + `requestVideoFrameCallback` y ni tocas el sistema de ScrollTrigger.

### Checklist de integracion

1. Define `frameCount` (numero de frames) y `scrollMultiplier` (12 vh/frame es buen punto de partida; baja para mas densidad, sube para mas recorrido).
2. Prepara los frames (carpeta, sprite o data URIs copiados del HTML generado).
3. Pega los CDN.
4. Anade el HTML del `sequence` + `sticky` + `canvas`.
5. Anade el CSS (variables y clases).
6. Pega el JS, ajustando `FRAMES` a tu fuente.
7. Cambia `const scrollMultiplier = 12;` por el valor que quieras (buscalo en el HTML generado y reemplazalo).

### Adaptaciones que rompen la cosa

- **`overflow: hidden` en `body`** → ScrollTrigger no detecta el scroll. Usa `overflow-x: hidden` si lo necesitas.
- **Tu CSS resetea `html { height: 100% }`** → Lenis necesita `height: auto`. La regla `html.lenis, html.lenis body { height: auto }` lo arregla, pero si tu reset es mas fuerte lo pisa.
- **Cambias `class="sticky"` por otro selector** → actualiza el `pin: '.sticky'` y el `querySelector('.sticky')`.
- **Cargas GSAP por npm** → da igual, pero `gsap.registerPlugin(ScrollTrigger)` debe ir antes de cualquier `ScrollTrigger.create`.
