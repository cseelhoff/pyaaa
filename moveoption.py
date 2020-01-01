from dataclasses import dataclass
from territory import Territory
from detailedunit import DetailedUnit
from destinationtransport import DestinationTransport

@dataclass
class MoveOption:
    moveFrom: Territory
    selectedUnit: DetailedUnit
    moveTo: DestinationTransport
