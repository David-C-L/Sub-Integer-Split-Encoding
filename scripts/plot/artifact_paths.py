"""Artifact-relative paths shared by every plotting/table script.

ROOT is the artifact root (two levels above this file) unless SIS_ARTIFACT_ROOT is set.
Outputs go to $SIS_FIG_OUT, default <ROOT>/out, so the reference copies in figures/ are never overwritten.
"""
import os

ROOT = os.environ.get("SIS_ARTIFACT_ROOT",
                      os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
DATA = os.path.join(ROOT, "data")
DERIVED = os.path.join(ROOT, "derived")
OUT = os.environ.get("SIS_FIG_OUT", os.path.join(ROOT, "out"))
os.makedirs(OUT, exist_ok=True)
TL = os.path.join(DATA, "toplevel_sec7")             # raw TopLevel Sec. 7 run
TL_DERIVED = os.path.join(DERIVED, "toplevel_sec7")  # intermediates built from it
