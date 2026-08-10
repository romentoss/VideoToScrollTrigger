"""
video-to-frames
================
Extrae los frames de un video corto y les quita el fondo (transparente).
Salida: tira de PNGs numerados lista para usar en un scroll sequence.

Uso:
    python extract.py <video> [opciones]

Ejemplos:
    python extract.py clip.mp4
    python extract.py clip.mp4 -o ./out -f 24
    python extract.py clip.mp4 --fps 12 --max-frames 60
    python extract.py clip.mp4 --bg-color "#00ff00"   # chroma key verde

Dependencias:
    pip install rembg pillow
    ffmpeg en PATH
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image


# ────────────────────────────────────────────────────────────────────
# Extraccion de frames con ffmpeg
# ────────────────────────────────────────────────────────────────────
def extract_frames_ffmpeg(
    video_path: Path,
    out_dir: Path,
    fps: Optional[float],
    max_frames: Optional[int],
    max_size: Optional[int],
) -> int:
    """Usa ffmpeg para volcar los frames a PNG en out_dir.
    Devuelve el numero de frames extraidos.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Limpiar previos
    for f in out_dir.glob("frame_*.png"):
        f.unlink()

    cmd = ["ffmpeg", "-y", "-i", str(video_path)]

    # Limitar fps (None = dejar el fps original)
    if fps is not None:
        cmd += ["-vf", f"fps={fps}"]

    # Limitar numero de frames
    if max_frames is not None:
        cmd += ["-frames:v", str(max_frames)]

    # Limitar tamano (ancho maximo, mantiene proporcion)
    if max_size is not None:
        scale = f"scale='min({max_size},iw)':-2"
        if fps is not None:
            cmd[cmd.index("-vf") + 1] += f",{scale}"
        else:
            cmd += ["-vf", scale]

    # Patron de salida con padding de ceros
    cmd += ["-start_number", "1", str(out_dir / "frame_%03d.png")]

    print("ffmpeg:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("ERROR ffmpeg:\n", result.stderr[-2000:], file=sys.stderr)
        raise SystemExit(1)

    frames = sorted(out_dir.glob("frame_*.png"))
    return len(frames)


# ────────────────────────────────────────────────────────────────────
# Quitar fondo con rembg
# ────────────────────────────────────────────────────────────────────
def remove_background_batch(
    in_dir: Path,
    out_dir: Path,
    model: str,
    alpha_matting: bool,
    bg_color: Optional[str],
) -> int:
    """Procesa cada PNG de in_dir con rembg y guarda el resultado en out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from rembg import remove, new_session
    except ImportError:
        print("ERROR: instala rembg -> pip install rembg", file=sys.stderr)
        raise SystemExit(1)

    print(f"Cargando modelo rembg '{model}'...")
    session = new_session(model)

    frames = sorted(in_dir.glob("frame_*.png"))
    total = len(frames)
    if total == 0:
        print("No hay frames para procesar.")
        return 0

    print(f"Procesando {total} frames...")
    for i, fp in enumerate(frames, start=1):
        img = Image.open(fp).convert("RGBA")
        out = remove(
            img,
            session=session,
            alpha_matting=alpha_matting,
            bgcolor=parse_color(bg_color) if bg_color else None,
        )
        out.save(out_dir / fp.name, "PNG", optimize=True)

        if i % 5 == 0 or i == total:
            print(f"  {i}/{total}")

    return total


def parse_color(s: str) -> Tuple[int, int, int, int]:
    """Acepta '#rrggbb', '#rrggbbaa' o 'r,g,b[,a]'."""
    s = s.strip()
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 6:
            h += "ff"
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4, 6))  # type: ignore
    parts = [int(p) for p in s.split(",")]
    while len(parts) < 4:
        parts.append(255)
    return tuple(parts)  # type: ignore


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extrae frames de un video y les quita el fondo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("video", type=Path, help="Ruta al video (mp4, mov, webm...)")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Carpeta de salida (default: <video>_frames/)")
    ap.add_argument("-f", "--fps", type=float, default=None,
                    help="Frames por segundo a extraer (default: fps original)")
    ap.add_argument("--max-frames", type=int, default=None,
                    help="Numero maximo de frames a extraer")
    ap.add_argument("--max-size", type=int, default=None,
                    help="Ancho maximo en px (mantiene proporcion)")
    ap.add_argument("--model", default="u2net",
                    choices=["u2net", "u2netp", "u2net_human_seg",
                             "u2net_cloth_seg", "silueta", "isnet-general-use"],
                    help="Modelo de segmentacion de rembg")
    ap.add_argument("--alpha-matting", action="store_true",
                    help="Alpha matting (mejor calidad, mas lento)")
    ap.add_argument("--bg-color", default=None,
                    help="Color de fondo solido en vez de transparente "
                         "(ej: '#00ff00' o '255,0,0,255')")
    ap.add_argument("--keep-raw", action="store_true",
                    help="Conserva los frames sin fondo en <out>/raw/")
    args = ap.parse_args()

    if not args.video.exists():
        print(f"No existe el video: {args.video}", file=sys.stderr)
        raise SystemExit(1)

    if shutil.which("ffmpeg") is None:
        print("ffmpeg no esta en PATH. Instálalo o añadelo al PATH.",
              file=sys.stderr)
        raise SystemExit(1)

    out_root = args.output or args.video.with_name(args.video.stem + "_frames")
    raw_dir = out_root / "raw"
    final_dir = out_root / "transparent"

    # Paso 1: extraer frames
    n = extract_frames_ffmpeg(
        args.video, raw_dir,
        fps=args.fps,
        max_frames=args.max_frames,
        max_size=args.max_size,
    )
    print(f"Extraidos {n} frames en {raw_dir}\n")

    # Paso 2: quitar fondo
    remove_background_batch(
        raw_dir, final_dir,
        model=args.model,
        alpha_matting=args.alpha_matting,
        bg_color=args.bg_color,
    )

    print(f"\nListo. PNGs sin fondo en: {final_dir}")

    if not args.keep_raw:
        try:
            raw_dir.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    main()
