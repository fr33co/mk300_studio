"""Protocolo USB-MIDI SysEx de la MK300 (verificado con capturas de la app oficial en Windows).

Trama SysEx = F0 + pack7(paquete) + F7. Paquete: 00 59 <cmd> <len16> 00 <payload> <chk>,
chk = ~sum(payload). Las escrituras (cmd 0x22) van a RAM; device.py solo las expone con comprobaciones.
"""
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
