from typing import List
from typing import Dict
from player import Player
from detailedunit import DetailedUnit
from unitquantity import UnitQuantity
from connection import Connection
from gamedata import GameData

class Territory:
    def __init__(self, gamedata: GameData, turnOrder: List[Player], name: str, allTerritoryUnits: List[DetailedUnit], landValue: int=0, isWater: bool=False, owner: Player=None):
        self.gamedata: GameData = gamedata
        self.turnOrder: List[Player] = turnOrder
        self.name: str = name
        self.landValue: int = landValue
        self.isWater: bool = isWater
        self.bombardsUsed: int = 0
        self.unitQuantities: List[UnitQuantity] = []
        self.getUnitQuantities: Dict[DetailedUnit, UnitQuantity] = {}
        self.connections: List[Connection] = []
        self.getConnectionTo: Dict[Territory, Connection] = {}
        self.waterConnections: List[Connection] = []
        self.landConnections: List[Connection] = []
        self.adjacentWaterTerritories: List[Territory] = []
        self.adjacentLandTerritories: List[Territory] = []
        self.adjacentAirTerritories: List[Territory] = []
        self.buildableTerritories: List[Territory] = [self]
        if owner:
            self.ownerIndex = gamedata.allocateAndGetIndex()
            self.owner: Player = owner
        self.originalOwner: Player = owner
        if landValue > 0:
            self.factoryMaxIndex: int = gamedata.allocateAndGetIndex()
            self.factoryMax: int = 0
            self.factoryHealthIndex: int = gamedata.allocateAndGetIndex()
            self.factoryHealth: int = 0
            self.constructionRemainingIndex: int = gamedata.allocateAndGetIndex()
            self.constructionRemaining: int = 0
        if self.isWater:
            self.isBeachheadSourceIndex: int = gamedata.allocateAndGetIndex()
            self.isBeachheadSource: bool = False
        else:
            self.planesCanLandIndex: int = gamedata.allocateAndGetIndex()
            self.planesCanLand: bool = True

        for detailedUnit in allTerritoryUnits:
            unitType = detailedUnit.unitType
            if unitType.isAir or unitType.isWater == self.isWater:
                unitQuantity = UnitQuantity(gamedata=gamedata, detailedUnit=detailedUnit, quantity=0)
                self.unitQuantities.append(unitQuantity)
                self.getUnitQuantities[detailedUnit] = unitQuantity
                
    @property
    def constructionRemaining(self) -> int:
        return self.gamedata.rawByteArray[self.constructionRemainingIndex]

    @constructionRemaining.setter
    def constructionRemaining(self, constructionRemaining: int) -> None:
        if constructionRemaining > 255:
            self.gamedata.rawByteArray[self.constructionRemainingIndex] = 255
        elif constructionRemaining < 0:
            self.gamedata.rawByteArray[self.constructionRemainingIndex] = 0
        else:
            self.gamedata.rawByteArray[self.constructionRemainingIndex] = constructionRemaining
        
    @property
    def factoryMax(self) -> int:
        return self.gamedata.rawByteArray[self.factoryMaxIndex]

    @factoryMax.setter
    def factoryMax(self, factoryMax: int) -> None:
        if factoryMax > 255:
            self.gamedata.rawByteArray[self.factoryMaxIndex] = 255
        elif factoryMax < 0:
            self.gamedata.rawByteArray[self.factoryMaxIndex] = 0
        else:
            self.gamedata.rawByteArray[self.factoryMaxIndex] = factoryMax
        
    @property
    def factoryHealth(self) -> int:
        return self.gamedata.rawByteArray[self.factoryHealthIndex]

    @factoryHealth.setter
    def factoryHealth(self, factoryHealth: int) -> None:
        if factoryHealth > 255:
            self.gamedata.rawByteArray[self.factoryHealthIndex] = 255
        elif factoryHealth < 0:
            self.gamedata.rawByteArray[self.factoryHealthIndex] = 0
        else:
            self.gamedata.rawByteArray[self.factoryHealthIndex] = int(factoryHealth)
        
    @property
    def planesCanLand(self) -> bool:
        return bool(self.gamedata.rawByteArray[self.planesCanLandIndex])

    @planesCanLand.setter
    def planesCanLand(self, planesCanLand: bool) -> None:
        if planesCanLand:
            self.gamedata.rawByteArray[self.planesCanLandIndex] = 1
        else:
            self.gamedata.rawByteArray[self.planesCanLandIndex] = 0
        
    @property
    def isBeachheadSource(self) -> bool:
        return bool(self.gamedata.rawByteArray[self.isBeachheadSourceIndex])

    @isBeachheadSource.setter
    def isBeachheadSource(self, isBeachheadSource: bool) -> None:
        if isBeachheadSource:
            self.gamedata.rawByteArray[self.isBeachheadSourceIndex] = 1
        else:
            self.gamedata.rawByteArray[self.isBeachheadSourceIndex] = 0
        
    @property
    def owner(self) -> Player:
        return self.turnOrder[self.gamedata.rawByteArray[self.ownerIndex]]

    @owner.setter
    def owner(self, owner: Player) -> None:
        self.gamedata.rawByteArray[self.ownerIndex] = self.turnOrder.index(owner)

    def damageFactory(self, damage: int) -> None:
        self.factoryHealth -= damage
        if self.factoryHealth < 0:
            self.factoryHealth = 0

    def repairFactoryOnePoint(self) -> None:
        self.factoryHealth += 1
        self.constructionRemaining += 1

    def __str__(self) -> str:
        string = 'Territory: ' + self.name 
        
        string += "\n"
        if not self.isWater:
            string += 'Owner: ' + str(self.owner) + "\n"
            string += 'Factory: ' + str(self.constructionRemaining) + '/' + str(self.factoryHealth) + '/' + str(self.factoryMax) + "\n"
        for unitQuantity in self.unitQuantities:
            quantity = unitQuantity.quantity
            if quantity > 0:
                string += str(quantity) + ' ' + str(unitQuantity.detailedUnit) + "\n"
        
        return string

    def __repr__(self) -> str:
        return(self.name)

