from detailedunit import DetailedUnit
from gamedata import GameData

class UnitQuantity:
    def __init__(self, gamedata: GameData, detailedUnit: DetailedUnit, quantity: int):
        self.gamedata: GameData = gamedata
        self.detailedUnit: DetailedUnit = detailedUnit
        self.quantityIndex: int = self.gamedata.allocateAndGetIndex()
        self.quantity: int = quantity
            
    @property
    def quantity(self) -> int:
        return self.gamedata.rawByteArray[self.quantityIndex]

    @quantity.setter
    def quantity(self, quantity: int) -> None:
        if quantity > 255:
            self.gamedata.rawByteArray[self.quantityIndex] = 255
        elif quantity < 0:
            self.gamedata.rawByteArray[self.quantityIndex] = 0
        else:
            self.gamedata.rawByteArray[self.quantityIndex] = quantity

    def __str__(self) -> str:
        string = ''
        if self.quantity > 0:
            string += self.detailedUnit.unitType.player.name + " " + self.detailedUnit.unitType.name + ': ' + str(self.quantity)
        return string
