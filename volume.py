from dataclasses import dataclass


@dataclass
class Volume:
    pass


@dataclass
class SimpleVolume(Volume):
    source: str
    target: str


@dataclass
class VolumeWithDriver(Volume):
    name: str
    driver: str
    driver_opts: dict
    target: str
