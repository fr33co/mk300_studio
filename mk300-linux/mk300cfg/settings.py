"""Ajustes globales de la MK300 (pestañas Glob, EQ, Looper y Drum de la app oficial).

En la pedalera viven en la estructura TGlob, que NO forma parte de los archivos de
banco. Aquí se guardan en un archivo JSON junto al banco (<banco>.glob.json); no se
escriben en el dispositivo. Los valores por defecto son los que muestra la app original.
Los nombres de campo siguen a los de TGlob (pedalConv0, eqLc, looperRecVol, ...).
"""
import json
import os
from dataclasses import asdict, dataclass, field

# Bloque de globales de la pedalera (0x20000000, 86 bytes). Offsets sacados de los cierres de GlobFields de la app
# original y contrastados con el volcado real y con las escrituras capturadas de la app oficial.
# nombre -> (offset, tamaño en bytes, con signo, nº de elementos o None). Little-endian.
RAW_SIZE = 86
# Tail: un solo byte con máscaras (_tailMode de la app original): OFF = máscara 1 apagada; Auto = encendida y
# máscara 2 apagada; Force = ambas. Delay usa (1, 4) y Reverb (2, 8).
TAIL_OFFSET = 0x4B
TAIL_MASKS = {"tail_delay": (1, 4), "tail_reverb": (2, 8)}
RAW_FIELDS = {
    "music_vol": (0x02, 1, False, None),
    "looper_play_vol": (0x06, 2, False, None),
    "looper_rec_vol": (0x08, 2, False, None),
    "looper_drum_sync": (0x0A, 1, False, None),
    "looper_auto_rec": (0x0B, 1, False, None),
    "looper_position": (0x0C, 1, False, None),
    "looper_auto_rec_db": (0x0D, 1, True, None),
    "drum_vol": (0x0E, 2, False, None),
    "drum_tempo": (0x10, 2, False, None),
    "drum_sync": (0x15, 1, False, None),
    "eq_quality_factor": (0x22, 1, False, 4),
    "eq_peak_gain": (0x26, 1, True, 4),
    "eq_peak_freq": (0x2A, 2, False, 4),
    "eq_lc": (0x32, 2, False, None),
    "eq_hc": (0x34, 2, False, None),
    "eq_enable": (0x36, 2, False, None),
    "pedal_conv0": (0x38, 1, False, None),
    "pedal_sync0": (0x3A, 1, False, None),
    "right_output_mode": (0x3C, 1, False, None),
    "usb_rec_type": (0x3D, 1, False, None),
    "pedal_toe_switch": (0x3E, 1, False, 2),
    "usb_rec_vol": (0x42, 1, False, None),
}


@dataclass
class GlobalSettings:
    # Glob
    pedal_conv0: int = 1           # A/B Convert: 0=OFF 1=ON
    pedal_sync0: int = 1           # Sync: 0=OFF 1=ON
    pedal_state: list = field(default_factory=lambda: [0, 0])   # Pedal State P1/P2: 0=A 1=B
    right_output_mode: int = 0     # RCH: 0=Nor 1=Dry 2=NoCAB
    usb_rec_type: int = 0          # USB Audio: 0=ON 1=OFF 2=RESAMPLE 3=DRY
    music_vol: int = 100           # BT&USB VOL
    usb_rec_vol: int = 50          # USB REC VOL
    pedal_toe_switch: list = field(default_factory=lambda: [1, 1])  # 0=None 1=Resume 2=Disable
    tail_delay: int = 0            # Tail Delay: 0=OFF 1=Auto 2=Force (bits del byte 0x4b)
    tail_reverb: int = 0           # Tail Reverb: 0=OFF 1=Auto 2=Force
    # EQ
    eq_enable: int = 1
    eq_lc: int = 95                # Hz
    eq_hc: int = 13500             # Hz
    eq_peak_freq: list = field(default_factory=lambda: [273, 533, 1100, 4000])  # Hz
    eq_quality_factor: list = field(default_factory=lambda: [90, 11, 1, 59])    # décimas
    eq_peak_gain: list = field(default_factory=lambda: [0, 2, 0, -9])           # dB
    # Looper
    looper_rec_vol: int = 87
    looper_play_vol: int = 100
    looper_auto_rec: int = 0       # 0=OFF 1=ONCE 2=HOLD
    looper_auto_rec_db: int = 0    # Auto Gate
    looper_position: int = 1       # 0=HEAD 1=TAIL
    looper_drum_sync: int = 2      # 0=OFF 1=ON-1 2=ON-2
    # Drum
    drum_vol: int = 57
    drum_tempo: int = 95
    drum_sync: int = 0

    @classmethod
    def from_raw(cls, raw):
        """Ajustes a partir de los 86 bytes leídos de la pedalera (pedal_state vive en el parche, no aquí)."""
        g = cls()
        for name, (off, size, signed, n) in RAW_FIELDS.items():
            vals = [int.from_bytes(raw[off + i * size:off + (i + 1) * size], "little", signed=signed)
                    for i in range(n or 1)]
            setattr(g, name, vals if n else vals[0])
        for name, (m1, m2) in TAIL_MASKS.items():
            b = raw[TAIL_OFFSET]
            setattr(g, name, 0 if not b & m1 else (1 if not b & m2 else 2))
        return g

    def to_raw(self, base):
        """Copia de `base` (86 bytes) con los campos conocidos puestos a los valores actuales."""
        out = bytearray(base)
        for name, (off, size, signed, n) in RAW_FIELDS.items():
            v = getattr(self, name)
            for i, x in enumerate(v if n else [v]):
                out[off + i * size:off + (i + 1) * size] = int(x).to_bytes(size, "little", signed=signed)
        for name, (m1, m2) in TAIL_MASKS.items():
            mode = getattr(self, name)
            out[TAIL_OFFSET] = (out[TAIL_OFFSET] & ~(m1 | m2) & 0xFF) | (m1 if mode >= 1 else 0) | (m2 if mode >= 2 else 0)
        return bytes(out)

    def changed_fields(self, other):
        return [n for n in (*RAW_FIELDS, *TAIL_MASKS) if getattr(self, n) != getattr(other, n)]

    def to_json(self):
        return json.dumps(asdict(self), indent=1)

    @classmethod
    def from_dict(cls, d):
        base = cls()
        for k, v in d.items():
            if hasattr(base, k) and isinstance(v, type(getattr(base, k))):
                setattr(base, k, v)
        return base

    @staticmethod
    def sidecar(bank_path):
        return bank_path + ".glob.json"

    @classmethod
    def load_for(cls, bank_path):
        """Ajustes guardados junto al banco, o los valores por defecto si no hay."""
        try:
            with open(cls.sidecar(bank_path), encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (OSError, ValueError):
            return cls()

    def save_for(self, bank_path):
        with open(self.sidecar(bank_path), "w", encoding="utf-8") as f:
            f.write(self.to_json())
