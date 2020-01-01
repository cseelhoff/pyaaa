from dataclasses import dataclass
from player import Player

@dataclass(eq=False)
class UnitType:
    player: Player
    name: str
    attack: int = 0
    defense: int = 0
    maxMoves: int = 1
    maxHits: int = 1
    cost: int = 1
    maxSupportable: int = 0
    maxSupported: int = 0
    weight: int = 1
    isAir: bool = False
    bomber: int = 0
    isWater: bool = False
    maxLand: int = 0
    maxAir: int = 0
    isSub: bool = False
    isAntiSub: bool = False
    bombard: int = 0
    isAA: bool = False

    def __str__(self):
        string = self.name + " " + self.player.name
        return string

    def __repr__(self):
        return str(self)
        