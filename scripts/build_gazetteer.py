"""Build src/image_evidence/data/ua_places.tsv.gz from the GeoNames Ukraine dump.

    curl -O https://download.geonames.org/export/dump/UA.zip && unzip UA.zip
    curl -O https://download.geonames.org/export/dump/admin1CodesASCII.txt
    curl -o altUA.zip https://download.geonames.org/export/dump/alternatenames/UA.zip && unzip altUA.zip -d alt
    python scripts/build_gazetteer.py UA.txt admin1CodesASCII.txt alt/UA.txt

GeoNames data is CC BY 4.0 (https://www.geonames.org). Kept: populated places (feature class P)
with a recorded population or an administrative-centre code. Villages without population data
are left out: many share their name with ordinary words and would cause false matches.
Name forms: the GeoNames name plus current Ukrainian, Russian and English alternate names. Historic
and colloquial names are dropped ("Paris" and "Svoboda" are old names of Ukrainian villages).
"""

import gzip
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src/image_evidence/data/ua_places.tsv.gz"
LETTERS = re.compile(r"^[A-Za-zА-Яа-яІіЇїЄєҐґЁёЪъЫыЭэ'’ʼ\- .]+$")


def main(ua: str, admin1: str, alternates: str) -> None:
    alt: dict[str, set[str]] = {}
    for line in open(alternates, encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        _id, gid, lang, name = f[:4]
        colloquial, historic = (f[6:8] + ["", ""])[:2]
        if lang in ("uk", "ru", "en") and colloquial != "1" and historic != "1":
            alt.setdefault(gid, set()).add(name)
    oblasts = {}
    for line in open(admin1, encoding="utf-8"):
        code, name, _ascii, _id = line.rstrip("\n").split("\t")
        if code.startswith("UA."):
            oblasts[code[3:]] = name
    rows = []
    for line in open(ua, encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        gid, name, _ascii, _alt, lat, lon, fclass, fcode, _cc, _cc2, adm1 = f[:11]
        pop = int(f[14] or 0)
        if fclass != "P" or not (pop > 0 or fcode.startswith("PPLA") or fcode == "PPLC"):
            continue
        forms = {name, *alt.get(gid, ())}
        forms = sorted({x.strip() for x in forms if len(x.strip()) >= 3 and LETTERS.match(x.strip())})
        rows.append("\t".join([gid, name, fcode, oblasts.get(adm1, ""), str(pop), lat, lon, "|".join(forms)]))
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        fh.write("geonameid\tname\tfcode\toblast\tpopulation\tlat\tlon\tforms\n")
        fh.write("\n".join(rows) + "\n")
    print(f"{len(rows)} places -> {OUT}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
