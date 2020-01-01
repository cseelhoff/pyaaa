from dataclasses import dataclass
from territory import Territory
from detailedunit import DetailedUnit

@dataclass
class BuildOption:
    buildFrom: Territory
    buildTo: Territory
    detailedUnit: DetailedUnit

