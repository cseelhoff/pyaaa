from typing import List
from typing import Dict
from player import Player
from territory import Territory
from detailedunit import DetailedUnit
from unitquantity import UnitQuantity
from connection import Connection
from gamedata import GameData
from unittype import UnitType

class GameState:
    def __init__(self):
        self.gamedata = GameData()
        self.a=0
        #static
        self.turnOrder: List[Player] = []
        self.territories: List[Territory] = []
        self.landTerritories: List[Territory] = []
        self.seaTerritories: List[Territory] = []
        self.allTerritoryUnits: List[DetailedUnit] = []
        self.allies: Dict[Player, List[Player]] = {}
        self.enemies: Dict[Player, List[Player]] = {}
        self.capital: Dict[Player, Territory] = {}
        self.fullUnits: Dict[Player, List[DetailedUnit]] = {}
        self.payload: Dict[DetailedUnit, List[DetailedUnit]] = {}
        self.connectionSource: Dict[Connection, Territory] = {}
        self.connectionDestination: Dict[Connection, Territory] = {}
        self.requiredTerritories: Dict[Connection, List[Territory]] = {}
        self.unitAfterMove: Dict[DetailedUnit, DetailedUnit] = {}
        self.unitAfterHit: Dict[DetailedUnit, DetailedUnit] = {}
        self.unitAfterTurn: Dict[DetailedUnit, DetailedUnit] = {}
        self.unitAfterLoadUnitType: Dict[DetailedUnit, Dict[UnitType, DetailedUnit]] = {}
        self.unitAfterUnload1: Dict[DetailedUnit, DetailedUnit] = {}
        self.unitAfterUnload2: Dict[DetailedUnit, DetailedUnit] = {}
        self.unitAfterUnloadBoth: Dict[DetailedUnit, DetailedUnit] = {}
        self.payloadPendingUnload: Dict[DetailedUnit, List[DetailedUnit]] = {}
        self.unitAfterUnload: Dict[DetailedUnit, DetailedUnit] = {}
        
        #dynamic
        self.backupUnitQuantitiesForTerritory: Dict[bytes, Dict[Player, Dict[Territory, List[UnitQuantity]]]] = {}
        self.beachheadSourcesIndexed: bool = False
        self.territoriesIndexed: bool = False
        self.unitQuantitiesForTerritoryIndexed: bool = False
        self.unitQuantitiesForConnectionIndexed: bool = False
        self._beachheadSources: List[Territory] = []
        self._ownedTerritories: Dict[Player, List[Territory]] = {}
        self._ownedValuedTerritories: Dict[Player, List[Territory]] = {}
        self._ownedFactoryTerritories: Dict[Player, List[Territory]] = {}
        self._unitQuantitiesForTerritory: Dict[Player, Dict[Territory, List[UnitQuantity]]] = {}
        self._unitQuantitiesForConnection: Dict[Connection, List[UnitQuantity]] = {}

    def backupUQFT(self) -> None:
        dataBytes = bytes(self.gamedata.rawByteArray)
        if dataBytes not in self.backupUnitQuantitiesForTerritory:
            uqft1 = self._unitQuantitiesForTerritory.copy()
            self.backupUnitQuantitiesForTerritory[dataBytes] = uqft1
            for player in uqft1:
                uqft2 = uqft1[player].copy()
                uqft1[player] = uqft2
                for territory in uqft2:
                    uqft3 = uqft2[territory].copy()
                    uqft2[territory] = uqft3

    def restoreUQFT(self, dataBytes: bytes) -> None:
        uqft1 = self.backupUnitQuantitiesForTerritory[dataBytes].copy()
        for player in uqft1:
            uqft2 = uqft1[player].copy()
            uqft1[player] = uqft2
            for territory in uqft2:
                uqft3 = uqft2[territory].copy()
                uqft2[territory] = uqft3
        self._unitQuantitiesForTerritory = uqft1

    def allocateAndGetIndex(self) -> int:
        self.gamedata.rawByteArray.append(0)
        return len(self.gamedata.rawByteArray) - 1

    def clearIndexes(self) -> None:
        self.beachheadSourcesIndexed = False
        self.territoriesIndexed = False
        self.unitQuantitiesForTerritoryIndexed = True
        self.unitQuantitiesForConnectionIndexed = False

    def restore(self, savedState: bytes) -> None:
        self.gamedata.rawByteArray = bytearray(savedState)
        self.clearIndexes()
        self.restoreUQFT(savedState)

    def backup(self) -> bytearray:
        self.backupUQFT()
        return bytes(self.gamedata.rawByteArray)

    def completeSetup(self) -> None:
        self.clearIndexes()
        self.gamedata.rawByteArray = bytearray(self.gamedata.rawByteArray)
        self.indexUnitQuantitiesForTerritory()

    def addConnection(self, connection: Connection, territory: Territory) -> None:
        territory.connections.append(connection)
        destination = self.connectionDestination[connection]
        territory.getConnectionTo[destination] = connection
        territory.adjacentAirTerritories.append(destination)
        if destination.isWater:
            territory.waterConnections.append(connection)
            territory.adjacentWaterTerritories.append(destination)
            territory.buildableTerritories.append(destination)
        else:
            territory.adjacentLandTerritories.append(destination)
            territory.landConnections.append(connection)

    def createLand(self, name: str, landValue: int, owner: Player) -> Territory:
        territory = Territory(gamedata=self.gamedata, turnOrder=self.turnOrder, name=name, allTerritoryUnits=self.allTerritoryUnits, landValue=landValue, owner=owner)
        self.landTerritories.append(territory)
        self.territories.append(territory)
        return territory

    def createSea(self, name: str) -> Territory:
        territory = Territory(gamedata=self.gamedata, turnOrder=self.turnOrder, name=name, allTerritoryUnits=self.allTerritoryUnits, isWater=True)
        self.seaTerritories.append(territory)
        self.territories.append(territory)
        return territory

    def indexTerritories(self) -> None:
        for player in self.turnOrder:
            self._ownedTerritories[player] = []
            self._ownedValuedTerritories[player] = []
            self._ownedFactoryTerritories[player] = []
        for territory in self.landTerritories:
            self._ownedTerritories[territory.owner].append(territory)
            if territory.landValue > 0:
                self._ownedValuedTerritories[territory.owner].append(territory)
            if territory.factoryMax > 0:
                self._ownedFactoryTerritories[territory.owner].append(territory)

    @property
    def ownedTerritories(self) -> List[Territory]:
        if not self.territoriesIndexed:
            self.indexTerritories()
            self.territoriesIndexed = True
        return self._ownedTerritories

    @property
    def ownedValuedTerritories(self) -> List[Territory]:
        if not self.territoriesIndexed:
            self.indexTerritories()
            self.territoriesIndexed = True
        return self._ownedValuedTerritories

    @property
    def ownedFactoryTerritories(self) -> List[Territory]:
        if not self.territoriesIndexed:
            self.indexTerritories()
            self.territoriesIndexed = True
        return self._ownedFactoryTerritories

    @property
    def beachheadSources(self) -> List[Territory]:
        if not self.beachheadSourcesIndexed:
            self._beachheadSources = []
            for territory in self.seaTerritories:
                if territory.isBeachheadSource:
                    self._beachheadSources.append(territory)
            self.beachheadSourcesIndexed = True
        return self._beachheadSources

        
    def buildFactory(self, territory: Territory) -> None:
        territory.factoryMax = territory.landValue
        territory.factoryHealth = territory.factoryMax
        territory.constructionRemaining = territory.factoryHealth
        self.ownedFactoryTerritories[territory.owner].append(territory)
    

    def addUnit(self, territory:Territory, detailedUnit: DetailedUnit) -> None:
        unitQuantity = territory.getUnitQuantities[detailedUnit]
        unitQuantity.quantity += 1
        if unitQuantity.quantity == 1:
            if not self.unitQuantitiesForTerritoryIndexed:
                self.indexUnitQuantitiesForTerritory()
            else:
                player = detailedUnit.unitType.player
                if territory not in self._unitQuantitiesForTerritory[player]:
                    self._unitQuantitiesForTerritory[player][territory] = []
                self._unitQuantitiesForTerritory[player][territory].append(unitQuantity)
                if detailedUnit in self.payload:
                    payload = self.payload[detailedUnit]
                    if len(payload) > 0:
                        p0player = payload[0].unitType.player
                        if p0player != player:
                            if territory not in self._unitQuantitiesForTerritory[p0player]:
                                self._unitQuantitiesForTerritory[p0player][territory] = []
                            self._unitQuantitiesForTerritory[p0player][territory].append(unitQuantity)
                        if len(payload) > 1:
                            p1player = payload[1].unitType.player
                            if p0player == player and p1player != player:
                                if territory not in self._unitQuantitiesForTerritory[p1player]:
                                    self._unitQuantitiesForTerritory[p1player][territory] = []
                                self._unitQuantitiesForTerritory[p1player][territory].append(unitQuantity)

    def removeUnit(self, territory:Territory, detailedUnit: DetailedUnit) -> None:
        unitQuantity = territory.getUnitQuantities[detailedUnit]
        if unitQuantity.quantity == 0:
            print("ERROR removing unit " + str(detailedUnit.unitType) + " in territory: " + territory.name)
        unitQuantity.quantity -= 1
        if unitQuantity.quantity == 0:
            player = detailedUnit.unitType.player
            self.unitQuantitiesForTerritory[player][territory].remove(unitQuantity)
            if detailedUnit in self.payload:
                payload = self.payload[detailedUnit]
                if len(payload) > 0:
                    p0player = payload[0].unitType.player
                    if p0player != player:
                        self._unitQuantitiesForTerritory[p0player][territory].remove(unitQuantity)
                    if len(payload) > 1:
                        p1player = payload[1].unitType.player
                        if p0player == player and p1player != player:
                            self._unitQuantitiesForTerritory[p1player][territory].remove(unitQuantity)
                
    def changeOwner(self, territory: Territory, conqueredBy: Player) -> None:
        oldOwner = territory.owner
        self.ownedTerritories[oldOwner].remove(territory)
        if territory.landValue > 0:
            self.ownedValuedTerritories[oldOwner].remove(territory)
        if territory.factoryMax > 0:
            self.ownedFactoryTerritories[oldOwner].remove(territory)
        newOwner = conqueredBy
        if territory.originalOwner.team == conqueredBy.team:
            newOwner = territory.originalOwner
        territory.owner = newOwner

        for enemy in self.enemies[conqueredBy]:
            if territory in self.unitQuantitiesForTerritory[enemy]:
                unitQuantities = self.unitQuantitiesForTerritory[enemy][territory]
                for unitQuantity in unitQuantities:
                    if unitQuantity.detailedUnit.unitType.isAA:
                        #todo fix hardcoded
                        newAA = None
                        for fullunit in self.fullUnits[newOwner]:
                            if fullunit.unitType.isAA:
                                newAA = fullunit.unitAfterMove
                                break
                        for _ in range(unitQuantity.quantity):
                            self.removeUnit(territory=territory, detailedUnit=unitQuantity.detailedUnit)
                            self.addUnit(territory=territory, detailedUnit=newAA)

        self.ownedTerritories[newOwner].append(territory)
        if territory.landValue > 0:
            self.ownedValuedTerritories[newOwner].append(territory)
        if territory.factoryMax > 0:
            self.ownedFactoryTerritories[newOwner].append(territory)

        if self.capital[oldOwner] == territory:
            conqueredBy.money += oldOwner.money
            oldOwner.money = 0
        territory.planesCanLand = False
        territory.constructionRemaining = 0
    
    def indexUnitQuantitiesForTerritory(self) -> None:
        self.unitQuantitiesForTerritoryIndexed = True
        for player in self.turnOrder:
            self._unitQuantitiesForTerritory[player] = {}
        for territory in self.territories:
            for unitQuantity in territory.unitQuantities:
                if unitQuantity.quantity > 0:
                    detailedUnit = unitQuantity.detailedUnit
                    player = detailedUnit.unitType.player
                    if territory not in self._unitQuantitiesForTerritory[player]:
                        self._unitQuantitiesForTerritory[player][territory] = []
                    self._unitQuantitiesForTerritory[player][territory].append(unitQuantity)
                    if detailedUnit in self.payload:
                        payload = detailedUnit.payload
                        if len(payload) > 0:
                            p0player = detailedUnit.payload[0].unitType.player
                            if p0player != player:
                                if territory not in self._unitQuantitiesForTerritory[p0player]:
                                    self._unitQuantitiesForTerritory[p0player][territory] = []
                                self._unitQuantitiesForTerritory[p0player][territory].append(unitQuantity)
                            if len(payload) > 1:
                                p1player = detailedUnit.payload[1].unitType.player
                                if p0player == player and p1player != player:
                                    if territory not in self._unitQuantitiesForTerritory[p1player]:
                                        self._unitQuantitiesForTerritory[p1player][territory] = []
                                    self._unitQuantitiesForTerritory[p1player][territory].append(unitQuantity)

    @property
    def unitQuantitiesForTerritory(self) -> Dict[Player, Dict[Territory, UnitQuantity]]:
        if not self.unitQuantitiesForTerritoryIndexed:
            self.indexUnitQuantitiesForTerritory()
            
        return self._unitQuantitiesForTerritory

    @property
    def unitQuantitiesForConnection(self) -> List[UnitQuantity]:
        if not self.unitQuantitiesForConnectionIndexed:
            self._unitQuantitiesForConnection: Dict[Connection, List[UnitQuantity]] = {}
            for beachheadSource in self.beachheadSources:
                for connection in beachheadSource:
                    for unitQuantity in connection.unitQuantity:
                        if unitQuantity.quantity > 0:
                            if connection not in self._unitQuantitiesForConnection.keys():
                                self._unitQuantitiesForConnection[connection] = []
                            self._unitQuantitiesForConnection[connection].append(unitQuantity)
            self.unitQuantitiesForConnectionIndexed = True
        return self._unitQuantitiesForConnection

    @property
    def currentTurn(self) -> int:
        return self.gamedata.rawByteArray[0]

    @currentTurn.setter
    def currentTurn(self, currentTurn) -> None:
        self.gamedata.rawByteArray[0] = currentTurn

    @property
    def currentPhase(self) -> int:
        return self.gamedata.rawByteArray[1]

    @currentPhase.setter
    def currentPhase(self, currentPhase) -> None:
        self.gamedata.rawByteArray[1] = currentPhase
