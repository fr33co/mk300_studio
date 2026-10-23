"""Protocolo USB-MIDI SysEx de la MK300 (verificado con capturas de la app oficial en Windows, 2026-10-23).

Trama SysEx = F0 + pack7(paquete) + F7, donde pack7 es un flujo de 7 bits con el bit menos
significativo primero (cada byte MIDI aporta sus 7 bits bajos; el último se rellena con ceros).

Paquete (antes de empaquetar):
    00 59 <cmd> <len_lo> <len_hi> 00  <payload: len bytes>  <chk>
    chk = ~sum(payload) & 0xFF

Comandos vistos:
    0x11 consulta de identidad   payload vacío  -> respuesta cmd 0x11 con "MK300_075"...
    0x23 leer                    payload = type(1) addr(4 LE) len(2 LE) 00
                                 respuesta cmd 0x23 = mismo payload + datos
    0x22 escribir (RAM)          payload = type(1) addr(4 LE) len(2 LE) 00 datos
                                 respuesta cmd 0x00 = ack, payload 1 byte (00 = ok)
    0x15 mensaje MIDI envuelto   payload = 3 bytes MIDI (p. ej. b0 16 7f)
La app trocea las lecturas largas en bloques de 1015 bytes (0x3F7).

Uso:
    python mk300_sysex.py decode <captura.txt> [--dumps DIR]
"""
import argparse
import os
import sys

HDR_SIZE = 6
CMD_ACK = 0x00
CMD_QUERY = 0x11
CMD_MIDI = 0x15
CMD_WRITE = 0x22
CMD_READ = 0x23
READ_CHUNK = 0x3F7


def pack7(data):
    out, acc, n = [], 0, 0
    for b in data:
        acc |= b << n
        n += 8
        while n >= 7:
            out.append(acc & 0x7F)
            acc >>= 7
            n -= 7
    if n:
        out.append(acc & 0x7F)
    return bytes(out)


def unpack7(data):
    out, acc, n = [], 0, 0
    for b in data:
        acc |= (b & 0x7F) << n
        n += 7
        while n >= 8:
            out.append(acc & 0xFF)
            acc >>= 8
            n -= 8
    return bytes(out)


def checksum(payload):
    return ~sum(payload) & 0xFF


def make_packet(cmd, payload=b""):
    n = len(payload)
    return bytes([0x00, 0x59, cmd, n & 0xFF, n >> 8, 0x00]) + bytes(payload) + bytes([checksum(payload)])


def to_sysex(packet):
    return b"\xF0" + pack7(packet) + b"\xF7"


def query():
    return to_sysex(make_packet(CMD_QUERY))


def read_req(addr, length, type_=4):
    p = bytes([type_]) + addr.to_bytes(4, "little") + length.to_bytes(2, "little") + b"\x00"
    return to_sysex(make_packet(CMD_READ, p))


def write_req(addr, data, type_=4):
    p = bytes([type_]) + addr.to_bytes(4, "little") + len(data).to_bytes(2, "little") + b"\x00" + bytes(data)
    return to_sysex(make_packet(CMD_WRITE, p))


def parse(sysex):
    """Devuelve dict con cmd, payload, ok_checksum (y addr/len/data para lectura/escritura)."""
    if sysex[0] != 0xF0 or sysex[-1] != 0xF7:
        raise ValueError("no es SysEx")
    pkt = unpack7(sysex[1:-1])
    if pkt[:2] != b"\x00\x59":
        raise ValueError("cabecera desconocida: " + pkt[:6].hex(" "))
    n = pkt[3] | pkt[4] << 8
    payload = pkt[HDR_SIZE:HDR_SIZE + n]
    r = {"cmd": pkt[2], "payload": payload, "ok_checksum": pkt[HDR_SIZE + n] == checksum(payload)}
    if r["cmd"] in (CMD_READ, CMD_WRITE) and n >= 8:
        r.update(type=payload[0], addr=int.from_bytes(payload[1:5], "little"),
                 len=payload[5] | payload[6] << 8, data=payload[8:])
    return r


def _frames(path):
    for line in open(path, encoding="utf-8"):
        p = line.split()
        if len(p) > 2 and p[1] in ("OUT", "IN"):
            raw = bytes(int(x, 16) for x in p[2:] if len(x) == 2 and x != "#")
            if raw[:1] == b"\xF0":
                yield float(p[0]), p[1], raw


def cmd_decode(args):
    names = {CMD_ACK: "ACK", CMD_QUERY: "QUERY", CMD_MIDI: "MIDI", CMD_WRITE: "WRITE", CMD_READ: "READ"}
    reads = {}
    for t, d, raw in _frames(args.capture):
        r = parse(raw)
        name = names.get(r["cmd"], "0x%02x" % r["cmd"])
        chk = "" if r["ok_checksum"] else " CHECKSUM-MAL"
        if "addr" in r:
            body = r["data"]
            print(f"{t:9.3f} {d:<3} {name:<5} type={r['type']} addr=0x{r['addr']:08x} len={r['len']}"
                  f" data={body[:32].hex(' ')}{' ...' if len(body) > 32 else ''}{chk}")
            if d == "IN" and r["cmd"] == CMD_READ:
                reads.setdefault((r["type"], r["addr"]), body)
        else:
            print(f"{t:9.3f} {d:<3} {name:<5} payload={r['payload'][:40].hex(' ')}{chk}")
    if args.dumps:
        os.makedirs(args.dumps, exist_ok=True)
        # Une los bloques consecutivos de una misma lectura (troceada en 1015 bytes).
        merged = {}
        for (type_, addr), body in sorted(reads.items()):
            for (mt, ma), mb in merged.items():
                if mt == type_ and ma + len(mb) == addr:
                    merged[(mt, ma)] = mb + body
                    break
            else:
                merged[(type_, addr)] = body
        for (type_, addr), body in merged.items():
            fn = os.path.join(args.dumps, f"t{type_}_{addr:08x}_{len(body)}.bin")
            with open(fn, "wb") as f:
                f.write(body)
            print("volcado:", fn, file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decode")
    d.add_argument("capture")
    d.add_argument("--dumps")
    args = ap.parse_args()
    {"decode": cmd_decode}[args.cmd](args)


if __name__ == "__main__":
    main()
