#!/usr/bin/env python3
"""Completa data/catalog.json con lo que el extractor no recoge del ensamblador.

Fuente de cada corrección (vídeo de la app oficial, lista desplegable de cada categoría):
  - DLY: además de los tipos extraídos, los mono incluyen Filter (tras Tremolo) y
    Pattern (tras Lofi). Verificado con el parche de fábrica "D7N DSSOLO" (tipo 12).
  - FX: el último tipo es Whammy (buildMk300WhammyChildType): Mode (0-2: MBody, Oct1, Oct2), Bend y Mix.
  - EQ: nombres de bandas (cadenas de effect_params.dart y fotogramas del vídeo), incluido Bass EQ 7.
"""
import copy
import json
import sys

path = sys.argv[1]
cat = json.load(open(path, encoding="utf-8"))

dly = cat["DLY"]
if not any(c["name"] == "Filter" for c in dly):
    by = {c["name"]: c for c in dly}

    def mono(n):
        c = copy.deepcopy(by[n + " Stereo"])
        c["name"] = n
        return c

    cat["DLY"] = dly[:7] + [mono("Filter")] + dly[7:9] + [mono("Pattern")] + dly[9:]

WHAMMY = [{"name": "Mode", "minVal": 0, "maxVal": 2}, {"name": "Bend"}, {"name": "Mix"}]
whammy = next((c for c in cat["FX"] if c["name"] == "Whammy"), None)
if whammy is None:
    cat["FX"].append({"name": "Whammy", "params": WHAMMY})
else:
    whammy["params"] = WHAMMY

EQ = {
    "Guitar EQ 6": ["100Hz", "200Hz", "400Hz", "800Hz", "1.6kHz", "3.2kHz"],
    "Bass EQ 7": ["50Hz", "120Hz", "400Hz", "500Hz", "800Hz", "4.5kHz", "10k"],
    "Normal EQ 10": ["31.25Hz", "62.5Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"],
}
for c in cat["EQ"]:
    if c["name"] in EQ:
        c["params"] = [{"name": n, "minVal": -24, "maxVal": 24} for n in EQ[c["name"]]]

json.dump(cat, open(path, "w"), indent=1, ensure_ascii=False)
print({k: len(v) for k, v in cat.items()})
