"""
build.py
========
Convierte un video en un HTML atomico auto-contenido que se anima
con scroll. Los frames se embeben como base64 dentro del HTML,
asi que el archivo resultante es UN SOLO y funciona en cualquier sitio.

Uso:
    python build.py video.mp4 -o scroll.html
    python build.py video.mp4 -o scroll.html --duration 10 --fps 6

Requisitos:
    pip install pillow
    ffmpeg en PATH
"""

import argparse
import base64
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

from PIL import Image


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    *,*::before,*::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #0a0a0a;
      --fg: #f5f5f7;
      --line: rgba(245,245,247,0.12);
    }}
    html, body {{
      background: var(--bg);
      color: var(--fg);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                   "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
    }}
    html.lenis, html.lenis body {{ height: auto; }}
    .lenis.lenis-smooth {{ scroll-behavior: auto !important; }}
    body.is-loading {{ overflow: hidden; }}

    .sequence {{ position: relative; width: 100%; }}
    .sticky {{
      position: sticky;
      top: 0;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    canvas {{
      display: block;
      width: min(85vh, 85vw);
      height: min(85vh, 85vw);
    }}

    .progress {{
      position: fixed;
      top: 0; left: 0;
      width: 100%;
      height: 3px;
      background: var(--line);
      z-index: 100;
      pointer-events: none;
    }}
    .progress__fill {{
      height: 100%;
      width: 0%;
      background: var(--fg);
      transition: width 0.08s linear;
      box-shadow: 0 0 10px rgba(245,245,247,0.4);
    }}
    .progress__count {{
      position: fixed;
      top: 14px;
      right: 22px;
      font-size: 0.72rem;
      letter-spacing: 0.18em;
      font-variant-numeric: tabular-nums;
      color: var(--fg);
      opacity: 0.55;
      z-index: 100;
      pointer-events: none;
    }}

    .loader {{
      position: fixed; inset: 0;
      background: var(--bg);
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      gap: 1.25rem;
      z-index: 1000;
      transition: opacity 0.7s ease;
    }}
    .loader.is-hidden {{ opacity: 0; pointer-events: none; }}
    .loader__label {{
      font-size: 0.72rem; letter-spacing: 0.32em; text-transform: uppercase;
      color: rgba(245,245,247,0.6);
    }}
    .loader__bar {{
      width: 240px; height: 1px; background: var(--line); overflow: hidden;
    }}
    .loader__bar::after {{
      content: ''; display: block; height: 100%;
      width: var(--progress, 0%); background: var(--fg);
      transition: width 0.2s ease;
    }}
    .loader__count {{
      font-variant-numeric: tabular-nums; font-size: 0.82rem;
      color: rgba(245,245,247,0.36);
    }}
  </style>
</head>
<body class="is-loading">

  <section class="sequence" id="sequence">
    <div class="sticky">
      <canvas id="canvas"></canvas>
    </div>
  </section>

  <div class="progress" aria-hidden="true">
    <div class="progress__fill" id="progressFill"></div>
  </div>
  <div class="progress__count" id="progressCount" aria-hidden="true">0%</div>

  <div class="loader" id="loader" role="status" aria-live="polite">
    <p class="loader__label">Cargando</p>
    <div class="loader__bar" id="loaderBar"></div>
    <p class="loader__count" id="loaderCount">0%</p>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/lenis@1.1.20/dist/lenis.min.js"></script>

  <script>
    const FRAMES = [
{frames}
    ];

    const canvas       = document.getElementById('canvas');
    const ctx          = canvas.getContext('2d');
    const sequenceEl   = document.getElementById('sequence');
    const loaderEl     = document.getElementById('loader');
    const loaderBar    = document.getElementById('loaderBar');
    const loaderCount  = document.getElementById('loaderCount');
    const progressFill   = document.getElementById('progressFill');
    const progressCount  = document.getElementById('progressCount');

    const frameCount = FRAMES.length;
    const scrollMultiplier = {scrollMultiplier};
    const images      = new Array(frameCount);
    let loadedCount   = 0;
    let currentFrame  = 0;
    let lastRendered  = -1;
    let dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));

    function resizeCanvas() {{
      dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
      const rect = canvas.getBoundingClientRect();
      canvas.width  = Math.floor(rect.width  * dpr);
      canvas.height = Math.floor(rect.height * dpr);
      lastRendered = -1;
      render();
    }}

    function drawCover(img, cw, ch) {{
      const imgRatio    = img.naturalWidth / img.naturalHeight;
      const canvasRatio = cw / ch;
      let dw, dh;
      if (canvasRatio > imgRatio) {{ dw = cw; dh = cw / imgRatio; }}
      else                        {{ dh = ch; dw = ch * imgRatio; }}
      const dx = (cw - dw) / 2;
      const dy = (ch - dh) / 2;
      ctx.clearRect(0, 0, cw, ch);
      ctx.drawImage(img, dx, dy, dw, dh);
    }}

    function render() {{
      if (currentFrame === lastRendered) return;
      const img = images[currentFrame];
      if (!img || !img.complete || img.naturalWidth === 0) return;
      drawCover(img, canvas.width, canvas.height);
      lastRendered = currentFrame;
    }}

    function preloadFrames() {{
      return new Promise((resolve) => {{
        const onOne = () => {{
          loadedCount++;
          const pct = Math.round((loadedCount / frameCount) * 100);
          loaderBar.style.setProperty('--progress', pct + '%');
          loaderCount.textContent = pct + '%';
          if (loadedCount === frameCount) resolve();
        }};
        for (let i = 0; i < frameCount; i++) {{
          const img = new Image();
          img.decoding = 'async';
          img.src = FRAMES[i];
          img.onload  = () => onOne();
          img.onerror = () => {{ console.warn('Frame no cargado:', i); onOne(); }};
          images[i] = img;
        }}
      }});
    }}

    (async function init() {{
      gsap.registerPlugin(ScrollTrigger);

      sequenceEl.style.height = `${{scrollMultiplier * frameCount}}vh`;
      resizeCanvas();
      await preloadFrames();
      currentFrame = 0;
      lastRendered = -1;
      render();

      const lenis = new Lenis({{
        easing: (t) => 1 - Math.pow(1 - t, 4),
        duration: 1.4,
        smoothWheel: true,
        wheelMultiplier: 1,
        touchMultiplier: 1.4,
      }});
      lenis.on('scroll', () => ScrollTrigger.update());
      gsap.ticker.add((time) => lenis.raf(time * 1000));
      gsap.ticker.lagSmoothing(0);

      ScrollTrigger.create({{
        trigger: sequenceEl,
        start: 'top top',
        end: 'bottom bottom',
        pin: '.sticky',
        scrub: 0.4,
        onUpdate: (self) => {{
          const progress = self.progress;
          const pct = progress * 100;
          progressFill.style.width = pct.toFixed(2) + '%';
          progressCount.textContent = Math.round(pct) + '%';
          const target = Math.min(
            frameCount - 1,
            Math.floor(progress * frameCount)
          );
          if (target !== currentFrame) {{
            currentFrame = target;
            render();
          }}
        }},
      }});

      requestAnimationFrame(() => {{
        loaderEl.classList.add('is-hidden');
        document.body.classList.remove('is-loading');
        lenis.start();
        setTimeout(() => loaderEl.remove(), 800);
      }});
    }})();

    window.addEventListener('resize', () => {{
      resizeCanvas();
      ScrollTrigger.refresh();
    }});
  </script>
</body>
</html>
"""


def ffmpeg_extract(
    video: Path,
    out_dir: Path,
    fps: float,
    duration: float,
    max_size: int,
) -> int:
    """Extrae frames del video con ffmpeg. Limita por duracion (segundos)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("frame_*.png"):
        f.unlink()

    vf = [f"fps={fps}"]
    if max_size:
        vf.append(f"scale='min({max_size},iw)':-2")

    cmd = [
        "ffmpeg", "-y",
        "-ss", "0", "-t", str(duration),
        "-i", str(video),
        "-vf", ",".join(vf),
        "-start_number", "1",
        str(out_dir / "frame_%03d.png"),
    ]

    print("ffmpeg:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ERROR ffmpeg:\n", r.stderr[-2000:], file=sys.stderr)
        raise SystemExit(1)

    return len(list(out_dir.glob("frame_*.png")))


def frames_to_data_uris(frames_dir: Path) -> List[str]:
    """Lee los PNGs y los devuelve como data URIs base64."""
    uris = []
    for fp in sorted(frames_dir.glob("frame_*.png")):
        b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
        uris.append(f"data:image/png;base64,{b64}")
    return uris


def build_html(
    frames_uris: List[str],
    out_file: Path,
    *,
    title: str,
    scroll_multiplier: int,
) -> None:
    """Escribe el HTML atomico con los frames embebidos."""
    frames_js = ",\n".join(f"      {u!r}" for u in frames_uris)

    html = HTML_TEMPLATE.format(
        title=title,
        frames=frames_js,
        scrollMultiplier=scroll_multiplier,
    )
    out_file.write_text(html, encoding="utf-8")

    size_mb = out_file.stat().st_size / 1024 / 1024
    print(f"\n[OK] {out_file}  ({size_mb:.1f} MB, {len(frames_uris)} frames)")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Convierte un video en un HTML atomico con scroll.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("video", type=Path, help="Video de entrada (mp4, mov, webm...)")
    ap.add_argument("-o", "--output", type=Path, default="scroll.html",
                    help="Nombre del archivo HTML de salida")
    ap.add_argument("--title", default="Scroll sequence",
                    help="Titulo de la pagina (etiqueta <title>)")
    ap.add_argument("--duration", type=float, default=20.0,
                    help="Segundos del video original a usar")
    ap.add_argument("-f", "--fps", type=float, default=8.0,
                    help="Frames por segundo a extraer")
    ap.add_argument("--max-size", type=int, default=800,
                    help="Ancho maximo en px (mantiene proporcion)")
    ap.add_argument("--scroll-multiplier", type=int, default=12,
                    help="vh de scroll por frame (mas bajo = mas denso)")
    args = ap.parse_args()

    if not args.video.exists():
        print(f"No existe el video: {args.video}", file=sys.stderr)
        raise SystemExit(1)

    if shutil.which("ffmpeg") is None:
        print("ffmpeg no esta en PATH.", file=sys.stderr)
        raise SystemExit(1)

    work = args.output.parent / f".{args.output.stem}_work"
    work.mkdir(parents=True, exist_ok=True)
    frames_dir = work / "frames"

    # 1) Extraer frames
    n = ffmpeg_extract(
        args.video, frames_dir,
        fps=args.fps,
        duration=args.duration,
        max_size=args.max_size,
    )
    print(f"Extraidos {n} frames (de los primeros {args.duration}s)")

    # 2) Embeber como base64
    print("\nEmbebiendo frames como base64...")
    uris = frames_to_data_uris(frames_dir)
    total_mb = sum(len(u) for u in uris) / 1024 / 1024
    print(f"  {total_mb:.1f} MB de data URIs")

    # 3) Escribir HTML
    build_html(
        uris, args.output,
        title=args.title,
        scroll_multiplier=args.scroll_multiplier,
    )

    print(f"\nAbre {args.output} en el navegador o pegalo en una web.")


if __name__ == "__main__":
    main()
