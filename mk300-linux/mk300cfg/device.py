"""Acceso a la MK300 por USB-MIDI (ALSA rawmidi, /dev/snd/midiC*D*).

Mapa verificado en la pedalera (2026-10-23):
  0x20000000  globales; bytes 0..1 = índice (desde 0) del preset activo, se actualiza al cambiar en la pedalera
  0x10000000  preset activo (448 bytes, RAM): escribir aquí cambia el sonido sin guardar
  n*448       preset n en flash: escribir 448 bytes y luego 0xf0000000 (vacío) lo guarda
  0xe0000000+n  escribir 1 byte (0) selecciona el preset n
"""
import os
import select
import subprocess
import time

from . import protocol as sx
from .bank import BANK_SIZE, PATCH_SIZE, PATCH_COUNT

ADDR_GLOBAL, ADDR_LIVE, ADDR_SELECT, ADDR_COMMIT = 0x20000000, 0x10000000, 0xE0000000, 0xF0000000
ADDR_NAMES, NAMES_SIZE = 0x70200000, PATCH_COUNT * 17  # nombres de preset: 160 registros de 17 bytes
# Listas de nombres de modelo (type 5): registros de 14 bytes "<id><nombre>", id desde 1.
MODEL_TABLES = {"CAB": (0x80000000, 100), "AMP": (0x90000000, 120), "DS": (0xA0000000, 40)}


class DeviceError(Exception):
    pass


def find_device():
    try:
        out = subprocess.run(["amidi", "-l"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError) as e:
        raise DeviceError(f"No se pudo ejecutar amidi: {e}")
    for line in out.splitlines()[1:]:
        if "MK300" in line:
            card, dev = line.split()[1][3:].split(",")[:2]
            return f"/dev/snd/midiC{card}D{dev}"
    raise DeviceError("No se ve la MK300 por USB (amidi -l).")


def pedal_present():
    try:
        find_device()
        return True
    except DeviceError:
        return False


class Pedal:
    def __init__(self, path=None):
        try:
            self.fd = os.open(path or find_device(), os.O_RDWR | os.O_NONBLOCK)
        except OSError as e:
            raise DeviceError(f"No se pudo abrir el dispositivo: {e}")

    def close(self):
        os.close(self.fd)

    def _txrx(self, frame, timeout=2.0):
        os.write(self.fd, frame)
        buf, end = b"", time.time() + timeout
        while time.time() < end:
            if select.select([self.fd], [], [], 0.1)[0]:
                buf += os.read(self.fd, 4096)
                if b"\xF7" in buf:
                    return sx.parse(buf[buf.index(b"\xF0"):buf.index(b"\xF7") + 1])
        raise DeviceError("La pedalera no respondió.")

    def identity(self):
        return self._txrx(sx.query())["payload"].rstrip(b"\0").decode(errors="replace")

    def read(self, addr, length, type_=4):
        out = b""
        while len(out) < length:
            n = min(sx.READ_CHUNK, length - len(out))
            r = self._txrx(sx.read_req(addr + len(out), n, type_))
            if r["cmd"] != sx.CMD_READ or not r["ok_checksum"]:
                raise DeviceError(f"Respuesta inesperada: cmd=0x{r['cmd']:02x}")
            out += r["data"]
        return out

    def read_bank(self):
        data = self.read(0x0, BANK_SIZE)
        if data[-8:] != b"PATCHEND":
            raise DeviceError("El banco leído no termina en PATCHEND.")
        return data

    # --- escritura (solo estas operaciones; nada de borrado ni direcciones libres) ---
    def _write(self, addr, data):
        r = self._txrx(sx.write_req(addr, data))
        if r["cmd"] != sx.CMD_ACK or r["payload"] != b"\x00":
            raise DeviceError(f"La pedalera rechazó la escritura en 0x{addr:08x}")

    def current_index(self):
        return self.read(ADDR_GLOBAL, 2)[0]

    def read_model_names(self):
        """Nombres de DS/AMP/CAB tal como los muestra la pedalera: {categoría: {id: nombre}}."""
        out = {}
        for cat, (addr, n) in MODEL_TABLES.items():
            raw = self.read(addr, n * 14, 5)
            names = {}
            for i in range(n):
                s = raw[i * 14:(i + 1) * 14].split(b"\0")[0].decode("latin1")
                if s.startswith(str(i + 1)):  # algún registro llega sin su id: se deja al respaldo del archivo
                    names[i + 1] = s[len(str(i + 1)):]
            out[cat] = names
        return out

    def read_names(self):
        return self.read(ADDR_NAMES, NAMES_SIZE)

    def read_globals(self):
        return self.read(ADDR_GLOBAL, 86)

    def write_global(self, offset, data):
        """Escribe ajustes globales (RAM; así lo hace la app oficial, sin comando de guardado)."""
        if offset < 0 or offset + len(data) > 86:
            raise DeviceError("Escritura fuera del bloque de globales")
        self._write(ADDR_GLOBAL + offset, data)

    def read_live(self):
        return self.read(ADDR_LIVE, PATCH_SIZE)

    def select_preset(self, idx):
        if not 0 <= idx < PATCH_COUNT:
            raise DeviceError("Preset fuera de rango")
        self._write(ADDR_SELECT + idx, b"\x00")

    def write_live(self, offset, data):
        if offset < 0 or offset + len(data) > PATCH_SIZE:
            raise DeviceError("Escritura fuera del preset")
        self._write(ADDR_LIVE + offset, data)

    def save_preset(self, idx, data):
        """Guarda un preset completo en flash y lo verifica leyéndolo de vuelta."""
        if not 0 <= idx < PATCH_COUNT or len(data) != PATCH_SIZE:
            raise DeviceError("Preset inválido")
        self._write(idx * PATCH_SIZE, bytes(data))
        self._write(ADDR_COMMIT, b"")
        time.sleep(0.3)
        if self.read(idx * PATCH_SIZE, PATCH_SIZE) != bytes(data):
            raise DeviceError("El preset guardado no coincide al releerlo")
