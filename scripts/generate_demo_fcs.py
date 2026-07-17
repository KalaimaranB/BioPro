"""Generate the minimal demo_tutorial.fcs file for the BioPro onboarding tour.

Run this script from the repo root to regenerate the asset:
    python scripts/generate_demo_fcs.py

The output is committed at biopro/tutorials/assets/demo_tutorial.fcs.
The file is a valid FCS 3.0 file with zero events (TOT=0) — parseable by
the Flow Cytometry module without crashing, but containing no real data.
"""

import os
from pathlib import Path

OUTPUT = Path(__file__).parent.parent / "biopro" / "tutorials" / "assets" / "demo_tutorial.fcs"

DELIMITER = "\\"

KV_PAIRS = [
    ("$BEGINANALYSIS", "0"),
    ("$ENDANALYSIS", "0"),
    ("$BEGINDATA", "0"),
    ("$ENDDATA", "0"),
    ("$BYTEORD", "4,3,2,1"),
    ("$DATATYPE", "F"),
    ("$MODE", "L"),
    ("$NEXTDATA", "0"),
    ("$PAR", "0"),
    ("$TOT", "0"),
    ("$FIL", "demo_tutorial.fcs"),
    ("$SYS", "BioPro Tutorial"),
    ("$INST", "BioPro Demo"),
    ("$OP", "BioPro"),
    ("$EXP", "Onboarding Tutorial"),
    ("$DATE", "01-JAN-2026"),
    ("$BTIM", "00:00:00"),
    ("$ETIM", "00:00:00"),
    ("$CYT", "Demo"),
]

text = DELIMITER
for k, v in KV_PAIRS:
    text += k + DELIMITER + v + DELIMITER

text_bytes = text.encode("utf-8")

TEXT_START = 256
TEXT_END = TEXT_START + len(text_bytes) - 1

header_str = (
    "FCS3.0    "
    + f"{TEXT_START:8d}"
    + f"{TEXT_END:8d}"
    + f"{0:8d}"  # BEGINDATA
    + f"{0:8d}"  # ENDDATA
    + f"{0:8d}"  # BEGINANALYSIS
    + f"{0:8d}"  # ENDANALYSIS
)
header_bytes = header_str.encode("ascii").ljust(256)[:256]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT, "wb") as f:
    f.write(header_bytes)
    f.write(text_bytes)

print(f"Generated: {OUTPUT}  ({os.path.getsize(OUTPUT)} bytes)")
