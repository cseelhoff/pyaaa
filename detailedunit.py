from dataclasses import dataclass
from dataclasses import field
from typing import List
from typing import Dict
from unittype import UnitType
from player import Player

@dataclass(eq=False)
class DetailedUnit:
    unitType: UnitType
    movesRemaining: int = 0
    hitsRemaining: int = 0
    canLoadUnitType: Dict[UnitType, bool] = field(default_factory=dict)
    payloadHasPlayer: Dict[Player, bool] = field(default_factory=dict)

    def __str__(self):
        player = self.unitType.player
        if player:
            string = player.name + ' ' + self.unitType.name + ' Moves: ' + str(self.movesRemaining)
            if self.unitType.maxHits > 1:
                string += ' HP: ' + str(self.hitsRemaining)
        else:
            string = self.unitType.name
        return string

    def __repr__(self):
        return(str(self))
