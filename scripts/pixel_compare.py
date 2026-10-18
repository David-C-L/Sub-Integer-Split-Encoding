"""Rasterise two PDFs at 100 dpi (pdftoppm) and report whether they are pixel-identical. Needs Pillow + numpy."""
import subprocess, sys, tempfile, os
import numpy as np
from PIL import Image
def raster(pdf, d, tag):
    base = os.path.join(d, tag)
    subprocess.run(["pdftoppm", "-r", "100", "-png", "-singlefile", pdf, base], check=True)
    return np.asarray(Image.open(base + ".png").convert("RGB"), dtype=int)
with tempfile.TemporaryDirectory() as d:
    a, b = raster(sys.argv[1], d, "a"), raster(sys.argv[2], d, "b")
if a.shape != b.shape:
    print("pixel-size-differs")
else:
    n = int((np.abs(a - b).max(axis=2) > 30).sum())
    print("pixel-identical" if n == 0 else f"{n} px differ")
