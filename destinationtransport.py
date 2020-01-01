from dataclasses import dataclass
from territory import Territory
from detailedunit import DetailedUnit

@dataclass
class DestinationTransport:
    territory: Territory
    transportUnit: DetailedUnit = None
    unload1: DetailedUnit = None
    unload2: DetailedUnit = None

    def __str__(self) -> str:
        string = self.territory.name
        if self.transportUnit:
            string += " Transport: " + str(self.transportUnit)
        return string

    def __repr__(self) -> str:
        return(str(self))
