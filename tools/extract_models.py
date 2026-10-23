#!/usr/bin/env python3
"""Extrae los nombres de modelos DS/AMP/CAB de los .bin de recursos de la MK300.

Cada registro empieza por la magia AM2\\0 / AM4\\0 (pedal DS o ampli) o CAB\\0
(pantalla), seguida de "<n><nombre>" en ASCII; <n> es el id de unidad. En los
registros AM la numeración se reinicia en 1 al pasar de DS a AMP.
"""
import json
import re
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
models = {}
for mode, magic in (("am3", b"AM2\x00"), ("am4", b"AM4\x00")):
    d = open(f"{SRC}/mk300_{mode}_ampCab.bin", "rb").read()
    am, cab = [], []
    for m in re.finditer(re.escape(magic) + rb"([0-9]+)([ -~]{2,18}?)\x00", d):
        am.append((int(m.group(1)), m.group(2).decode()))
    for m in re.finditer(rb"CAB\x00([0-9]+)([ -~]{2,18}?)\x00", d):
        cab.append((int(m.group(1)), m.group(2).decode()))
    ds, amp, cur = {}, {}, None
    prev = 0
    target = ds
    for i, n in am:
        if i <= prev and target is ds:  # la numeración se reinicia: empieza AMP
            target = amp
        target[i] = n
        prev = i
    models[mode] = {"DS": ds, "AMP": amp, "CAB": {i: n for i, n in cab}}
    print(mode, {k: len(v) for k, v in models[mode].items()})
json.dump(models, open(OUT, "w"), indent=1)
