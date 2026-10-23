"""Cliente SOLO LECTURA de la MK300 por USB-MIDI (ALSA rawmidi, sin dependencias).

Solo envía consulta de identidad (0x11) y lecturas (0x23); nunca escribe.

    python3 mk300_read.py [/dev/snd/midiC1D0] [--compare ../windows/dumps]
"""
import os
import select
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mk300_sysex as sx


def find_device():
    out = subprocess.run(["amidi", "-l"], capture_output=True, text=True).stdout
    for line in out.splitlines()[1:]:
        if "MK300" in line or "3654" in line or "Jieli" in line.lower():
            hw = line.split()[1]  # hw:1,0,0
            card, dev = hw[3:].split(",")[:2]
            return f"/dev/snd/midiC{card}D{dev}"
    return None


class Pedal:
    def __init__(self, path):
        self.fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)

    def _recv(self, timeout=2.0):
        buf, end = b"", time.time() + timeout
        while time.time() < end:
            if select.select([self.fd], [], [], 0.1)[0]:
                buf += os.read(self.fd, 4096)
                if b"\xF7" in buf:
                    i = buf.index(b"\xF0")
                    return buf[i:buf.index(b"\xF7") + 1]
        raise TimeoutError("sin respuesta")

    def _txrx(self, frame):
        os.write(self.fd, frame)
        return sx.parse(self._recv())

    def identity(self):
        r = self._txrx(sx.query())
        return r["payload"].rstrip(b"\0").decode(errors="replace")

    def read(self, addr, length, type_=4):
        out = b""
        while len(out) < length:
            n = min(sx.READ_CHUNK, length - len(out))
            r = self._txrx(sx.read_req(addr + len(out), n, type_))
            if r["cmd"] != sx.CMD_READ or not r["ok_checksum"]:
                raise IOError(f"respuesta inesperada cmd=0x{r['cmd']:02x} {r['payload'].hex()}")
            out += r["data"]
        return out


def main():
    argv = list(sys.argv[1:])
    if "--compare" in argv:
        i = argv.index("--compare")
        del argv[i:i + 2]
    path = argv[0] if argv else find_device()
    if not path:
        sys.exit("No se ve la MK300 en 'amidi -l' (¿conectada por USB?).")
    p = Pedal(path)
    print("identidad:", p.identity())
    cur = p.read(0x10000000, 448)
    print("preset actual:", cur[:20].rstrip(b"\0").decode(errors="replace"))
    if "--compare" in sys.argv:
        d = sys.argv[sys.argv.index("--compare") + 1]
        ref = open(os.path.join(d, "t4_10000000_448.bin"), "rb").read()
        print("igual al volcado de Windows" if ref == cur else
              f"difiere en {sum(a != b for a, b in zip(ref, cur))} bytes (normal si cambió de preset)")


if __name__ == "__main__":
    main()
