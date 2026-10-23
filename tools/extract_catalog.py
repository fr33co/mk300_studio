#!/usr/bin/env python3
"""Extrae el catálogo de efectos de la MK300 del ensamblador generado por blutter.

Cada categoría (_build*ChildTypes) construye EffectChildType(nombre, [EffectParam...]).
Los parámetros se crean ANTES del nombre de su tipo. Los argumentos con nombre
(minVal/maxVal) se apilan con el primero en la dirección más baja.
"""
import json
import re
import sys

SRC = sys.argv[1]
OUT = sys.argv[2]

BUILDERS = {
    "WAH": "_buildWahChildTypes", "FX": "_buildFxChildTypes", "GATE": "_buildGateChildTypes",
    "EQ": "_buildEqChildTypes", "MOD": "_buildModChildTypes", "DLY": "_buildDlyChildTypes",
    "REV": "_buildRevChildTypes",
}

lines = open(SRC, encoding="utf-8").read().split("\n")


def func_body(name):
    start = next(i for i, l in enumerate(lines) if re.match(rf"  static _ {name}\(", l))
    end = next(i for i in range(start + 1, len(lines)) if re.match(r"  (static|\[closure\]) ", lines[i]) or lines[i].startswith("class "))
    return lines[start:end]


NUM = r"-?(?:0x[0-9a-f]+|\d+)"


def parse(body, helpers=None):
    helpers = helpers or {}
    regs, children, params = {}, [], []
    name = desc = None
    stack = {}
    for idx, l in enumerate(body):
        m = re.match(r"\s+// 0x[0-9a-f]+: (r\d+) = (\"[^\"]*\"|" + NUM + r"|Null)$", l)
        if m:
            r, v = m.groups()
            if r == "r0" and v.startswith('"') and any("EffectChildType" in x for x in body[max(0, idx - 12):idx]):
                children.append({"name": v.strip('"'), "params": params})
                params = []
                continue
            if v.startswith('"'):
                regs[r] = v.strip('"')
            elif v == "Null":
                regs[r] = None
            else:
                regs[r] = int(v, 0)
            if r == "r2" and v.startswith('"'):
                name = v.strip('"')
            continue
        m = re.match(r"\s+// 0x[0-9a-f]+: r4 = const \[(.*)\]$", l)
        if m:
            desc = [x.strip() for x in m.group(1).split(",")]
            continue
        m = re.match(r"\s+// 0x[0-9a-f]+: movn (\w+), #(0x[0-9a-f]+)", l)
        if m:  # movn x16, #0x9f -> ~0x9f
            continue
        m = re.match(r"\s+//\s+0x[0-9a-f]+: stp\s+(\w+), (\w+), \[SP(?:, #(0x[0-9a-f]+))?\]", l)
        if m:
            a, b, off = m.groups()
            o = int(off, 0) if off else 0
            stack[o] = a
            stack[o + 8] = b
            continue
        m = re.match(r"\s+//\s+0x[0-9a-f]+: str\s+(\w+), \[SP(?:, #(0x[0-9a-f]+))?\]", l)
        if m:
            a, off = m.groups()
            stack[int(off, 0) if off else 0] = a
            continue
        mh = re.search(r"\bbl\b.*::(_timeParam|_syncParam|_syncBpmParam|_eqParam)\b", l)
        if mh and mh.group(1) in helpers:
            hp = dict(helpers[mh.group(1)])
            if mh.group(1) == "_eqParam" and name:
                hp["name"] = name
            params.append(hp)
            name = desc = None
            stack = {}
            continue
        if "EffectParam::EffectParam" in l and re.search(r"\bbl\b", l):
            named = {}
            if desc:
                try:
                    n_named = int(desc[2], 0) - 1 if False else None
                except ValueError:
                    pass
                names = [x for x in desc[4:-1] if not re.fullmatch(NUM, x)]
                for i, nm in enumerate(names):
                    reg = stack.get(i * 8)
                    reg = {"lr": "r30"}.get(reg, reg.replace("x", "r") if reg and reg.startswith("x") else reg)
                    named[nm] = regs.get(reg, f"<{reg}>") if reg else None
            params.append({"name": name, **{k: v for k, v in named.items() if isinstance(v, int)},
                           **{k + "_expr": v for k, v in named.items() if not isinstance(v, int)}})
            name = desc = None
            stack = {}
            continue
        m = re.match(r"\s+// 0x[0-9a-f]+: r0 = (\"[^\"]*\")$", l)
        if m and "EffectChildType" in "".join(body[max(0, body.index(l) - 12):body.index(l)]):
            children.append({"name": m.group(1).strip('"'), "params": params})
            params = []
    return children, params


helpers = {}
for h in ("_timeParam", "_syncParam", "_syncBpmParam", "_eqParam"):
    _, hp = parse(func_body(h))
    helpers[h] = hp[0] if hp else {"name": h}
    helpers[h] = {k: v for k, v in helpers[h].items() if not k.endswith("_expr")}
# Rangos leídos a mano del ensamblador de las funciones auxiliares (r16/r30).
helpers["_syncParam"].update(minVal=0, maxVal=2)
helpers["_syncBpmParam"] = {"name": "Sync\\nBpm", "minVal": 80, "maxVal": 480}
for h in helpers:
    print("helper", h, helpers[h])

catalog = {}
for cat, fn in BUILDERS.items():
    catalog[cat] = parse(func_body(fn), helpers)[0]
json.dump(catalog, open(OUT, "w"), indent=1, ensure_ascii=False)
for cat, ch in catalog.items():
    print(cat, len(ch), [c["name"] for c in ch])
