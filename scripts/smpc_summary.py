"""Print key SmPC sections (name, composition, form, 6.5 container, MAH, PL) from cached emc pages.
Usage: python -I scripts/smpc_summary.py FILE [FILE...]"""
import re, sys
from bs4 import BeautifulSoup
SECS = [("name", r"1\.\s*Name of the medicinal product", r"2\.\s*Qualitative"),
        ("composition", r"2\.\s*Qualitative and quantitative composition", r"3\.\s*Pharmaceutical form"),
        ("form", r"3\.\s*Pharmaceutical form", r"4\.\s*Clinical particulars"),
        ("container", r"6\.5\s*Nature and contents of container", r"6\.6"),
        ("mah", r"7\.\s*Marketing authorisation holder", r"8\.\s*Marketing"),
        ("pl", r"8\.\s*Marketing authorisation number", r"9\.\s*Date")]
def summary(path):
    t = BeautifulSoup(open(path, encoding="utf-8").read(), "lxml").get_text(" ", strip=True)
    out = {}
    for k, a, b in SECS:
        m = re.search(a, t, re.I)
        if not m: out[k] = ""; continue
        rest = t[m.end():]
        e = re.search(b, rest, re.I)
        out[k] = rest[: e.start() if e else 500][:700].strip()
    return out
if __name__ == "__main__":
    for f in sys.argv[1:]:
        print("=====", f)
        for k, v in summary(f).items(): print(f"  {k}: {v}")
