"""Banco de presets de la MK300 (formato de los .bin de la app oficial).

Verificado sobre los bancos de fábrica AM3 y AM4: 160 parches de 448 bytes y un
pie de 8 bytes con el ASCII "PATCHEND". Mapa de un parche (offsets en bytes):

  0x00  nombre (ASCII, relleno 0x00)
  0x11..0x13  relleno (siempre 0)
  0x14  color   4 bytes B,G,R,flag (flag=255 si el parche tiene color propio)
  0x18  vol     uint16 (60 en todos los bancos de fábrica: posición por orden de struct)
  0x1a  tempo   uint16, bpm (verificado: 80..179 en AM4)
  0x1c  pan     int16 (0 en fábrica: posición por orden de struct)
  0x1e  pedalState[2]
  0x20  chain[11]   orden de los efectos
  0x2b  effon[11]   interruptor de cada slot (0/1)
  0x36  effunit[11] tipo/modelo de cada slot
  0x42  effpara[11][12]  int16 little-endian por slot
  0x14a..0x1bf  resto sin mapear

El orden de campos sale de la estructura TPatch de la app; los offsets están
contrastados con los 160 parches de fábrica.
"""
import struct
from dataclasses import dataclass, field

PATCH_SIZE = 448
PATCH_COUNT = 160
NAME_LEN = 16
GLOBAL_SIZE = 8
FOOTER = b"PATCHEND"
SLOTS = 11
PARAMS = 12
OFF_COLOR, OFF_VOL, OFF_TEMPO, OFF_PAN, OFF_PEDAL = 0x14, 0x18, 0x1A, 0x1C, 0x1E
OFF_HEADER, OFF_CHAIN, OFF_EFFON, OFF_EFFUNIT, OFF_EFFPARA = 0x11, 0x20, 0x2B, 0x36, 0x42
BANK_SIZE = PATCH_SIZE * PATCH_COUNT + GLOBAL_SIZE  # 71688


@dataclass
class Patch:
    raw: bytearray

    @property
    def name(self) -> str:
        return bytes(self.raw[:NAME_LEN]).split(b"\0")[0].decode("ascii", "replace").rstrip()

    @name.setter
    def name(self, value: str) -> None:
        b = value.encode("ascii", "replace")[:NAME_LEN]
        self.raw[:NAME_LEN] = b.ljust(NAME_LEN, b"\0")

    @property
    def color(self):
        """(r, g, b, personalizado)"""
        b, g, r, flag = self.raw[OFF_COLOR:OFF_COLOR + 4]
        return r, g, b, flag == 255

    def set_color(self, r, g, b, custom=True):
        self.raw[OFF_COLOR:OFF_COLOR + 4] = bytes([b, g, r, 255 if custom else 0])

    @property
    def vol(self):
        return struct.unpack_from("<H", self.raw, OFF_VOL)[0]

    @vol.setter
    def vol(self, v):
        struct.pack_into("<H", self.raw, OFF_VOL, v)

    @property
    def tempo(self):
        return struct.unpack_from("<H", self.raw, OFF_TEMPO)[0]

    @tempo.setter
    def tempo(self, v):
        struct.pack_into("<H", self.raw, OFF_TEMPO, v)

    @property
    def pan(self):
        return struct.unpack_from("<h", self.raw, OFF_PAN)[0]

    @pan.setter
    def pan(self, v):
        struct.pack_into("<h", self.raw, OFF_PAN, v)

    def chain(self):
        return list(self.raw[OFF_CHAIN:OFF_CHAIN + SLOTS])

    def set_chain(self, order):
        if sorted(order) != list(range(SLOTS)):
            raise ValueError("el orden debe ser una permutación de los 11 slots")
        self.raw[OFF_CHAIN:OFF_CHAIN + SLOTS] = bytes(order)

    def enabled(self, slot):
        return bool(self.raw[OFF_EFFON + slot])

    def set_enabled(self, slot, on):
        self.raw[OFF_EFFON + slot] = 1 if on else 0

    def unit(self, slot):
        return self.raw[OFF_EFFUNIT + slot]

    def set_unit(self, slot, v):
        self.raw[OFF_EFFUNIT + slot] = v

    def param(self, slot, i):
        return struct.unpack_from("<h", self.raw, OFF_EFFPARA + (slot * PARAMS + i) * 2)[0]

    def set_param(self, slot, i, v):
        struct.pack_into("<h", self.raw, OFF_EFFPARA + (slot * PARAMS + i) * 2, v)


@dataclass
class Bank:
    patches: list = field(default_factory=list)
    tail: bytearray = field(default_factory=lambda: bytearray(GLOBAL_SIZE))

    @classmethod
    def from_bytes(cls, data: bytes) -> "Bank":
        if len(data) != BANK_SIZE:
            raise ValueError(f"Tamaño inválido: {len(data)} bytes (se esperaban {BANK_SIZE})")
        patches = [Patch(bytearray(data[i * PATCH_SIZE:(i + 1) * PATCH_SIZE])) for i in range(PATCH_COUNT)]
        return cls(patches, bytearray(data[PATCH_COUNT * PATCH_SIZE:]))

    @classmethod
    def load(cls, path: str) -> "Bank":
        with open(path, "rb") as f:
            return cls.from_bytes(f.read())

    def to_bytes(self) -> bytes:
        return b"".join(bytes(p.raw) for p in self.patches) + bytes(self.tail)

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            f.write(self.to_bytes())
