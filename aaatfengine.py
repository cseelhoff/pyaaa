from typing import List
from typing import Dict
from typing import Set
from player import Player
from territory import Territory
from detailedunit import DetailedUnit
from unitquantity import UnitQuantity
from connection import Connection
from gamedata import GameData
from unittype import UnitType
from aaastate import AAAstate
from buildoption import BuildOption
from destinationtransport import DestinationTransport
from moveoption import MoveOption
import random
import tensorflow as tf
import numpy as np

class AAAengine:
    def __init__(self):
        #static
        self.model = tf.keras.models.load_model('model01.h5')
        """
        self.model = tf.keras.models.Sequential([
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(
                units=1024,
                kernel_regularizer=tf.keras.regularizers.l2(0.01),
                activation='relu'
                ),
            tf.keras.layers.Dense(
                units=1024,
                kernel_regularizer=tf.keras.regularizers.l2(0.01),
                activation='relu'
                ),
            tf.keras.layers.Dense(
                units=1024,
                kernel_regularizer=tf.keras.regularizers.l2(0.01),
                activation='relu'
                ),
            tf.keras.layers.Dense(
                units=1
                )
        ])

        self.model.compile(
                loss='mse', 
                optimizer=tf.keras.optimizers.Nadam(lr=0.0001)
        )
        """

        self.verbose = False
        self.gamedata = GameData()
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
        
        factoryUnitType = UnitType(player=None, name="Factory", attack=0, defense=0, maxMoves=0, maxHits=0, cost=15)
        self.factoryUnit = DetailedUnit(unitType=factoryUnitType, movesRemaining=0, hitsRemaining=0)
        repairUnitType = UnitType(player=None, name="Repair", attack=0, defense=0, maxMoves=0, maxHits=0, cost=1)
        self.repairUnit = DetailedUnit(unitType=repairUnitType, movesRemaining=0, hitsRemaining=0)

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

    @property
    def currentPlayer(self):
        return self.turnOrder[self.currentTurn]

    def getPossibleNextStates(self, aaaState: AAAstate):
        self.restoreGameState(aaaState)
        futureStates1 = set()
        futureStates2 = set()
        if self.currentPhase == 0:
            self.linkStatesAfterCombatMove(linkFrom=futureStates1)
            for gameState in futureStates1:
                self.restoreGameState(gameState)
                self.currentPhase = 1
                futureStates2.add(self.backupGameState())
        elif self.currentPhase == 1:
            for gameState in futureStates1:
                self.restoreGameState(gameState)
                self.resolveSeaCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
                self.resolveBombards() # rand select unit Casulaty
                self.unloadTransports2() # no options here...
                self.resolveLandCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
                self.currentPhase = 2
                futureStates2.add(self.backupGameState())
        elif self.currentPhase == 2:
            self.linkStatesAfterMove(linkFrom=futureStates1)
            for gameState in futureStates1:
                self.restoreGameState(gameState)
                self.currentPhase = 3
                futureStates2.add(self.backupGameState())
        elif self.currentPhase == 3:
            self.linkStatesFromPurchase(linkFrom=futureStates1)
            for gameState in futureStates1:
                self.restoreGameState(gameState)
                self.crashPlanes()
                self.resetUnitsFully()
                self.resetConstruction()
                self.collectMoney()
                self.advanceTurn()
                self.currentPhase = 0
                futureStates2.add(self.backupGameState())
        return futureStates2

    def advanceTurn(self):
        self.currentTurn = (self.currentTurn + 1) % (len(self.turnOrder))


    def resetConstruction(self):
        for territory in self.ownedFactoryTerritories[self.currentPlayer]:
            territory.constructionRemaining = territory.factoryHealth


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
        self.unitQuantitiesForConnectionIndexed = False

    def restoreGameState(self, savedState: bytes) -> None:
        self.gamedata.rawByteArray = bytearray(savedState)
        self.clearIndexes()
        self.restoreUQFT(savedState)

    def backupGameState(self) -> bytearray:
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
                
    def conquer(self, territory: Territory) -> None:
        conqueredBy = self.currentPlayer
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
            #conqueredBy.money += oldOwner.money
            conqueredBy.reservedMoney += oldOwner.money
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
                for connection in beachheadSource.connections:
                    for unitQuantity in connection.unitQuantities:
                        if unitQuantity.quantity > 0:
                            if connection not in self._unitQuantitiesForConnection:
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

    def readableStatus(self) -> str:
        territories = self.territories
        status = 'CurrentTurn: ' + str(self.currentPlayer) + " Phase: " + str(self.currentPhase) + " Money: " + str(self.currentPlayer.money) + "\n"
        for territory in territories:
            status += str(territory) + "\n"
        return status

    def connectTerritories(self, territoryFrom: Territory, territoryTo: Territory, requiredTerritories: List[Territory]=[], isOneWay: bool=False, unloadingTransports: List[DetailedUnit]=None) -> None:
        connection = Connection()
        self.connectionSource[connection] = territoryFrom
        self.connectionDestination[connection] = territoryTo
        self.requiredTerritories[connection] = requiredTerritories
        self.addConnection(connection, territoryFrom)
        if territoryFrom.isWater and not territoryTo.isWater:
            for unloadingTransport in unloadingTransports:
                unitQuantity = UnitQuantity(gamedata=self.gamedata, detailedUnit=unloadingTransport, quantity=0)
                connection.unitQuantities.append(unitQuantity)
                connection.getUnitQuantities[unloadingTransport] = unitQuantity
        if not isOneWay:
            self.connectTerritories(territoryFrom=territoryTo, territoryTo=territoryFrom, requiredTerritories=requiredTerritories, isOneWay=True, unloadingTransports=unloadingTransports)

    def getAllBuildOptions(self) -> List[BuildOption]:
        player = self.currentPlayer
        fullUnits = self.fullUnits[player]
        allBuildOptions = []
        territories = self.ownedFactoryTerritories[player]
        for territory in territories:
            if territory.constructionRemaining > 0:
                buildToTerritories = territory.buildableTerritories
                for buildTo in buildToTerritories:
                    for fullUnit in fullUnits:
                        if fullUnit.unitType.cost <= player.money and ((fullUnit.unitType.isAir and (buildTo.isWater or buildTo == territory)) or (not fullUnit.unitType.isAir and fullUnit.unitType.isWater == buildTo.isWater)):
                            buildOption = BuildOption(buildFrom=territory, buildTo=buildTo, detailedUnit=fullUnit)
                            allBuildOptions.append(buildOption)
            if territory.factoryHealth < territory.factoryMax and player.money > 0:
                buildOption = BuildOption(buildFrom=territory, buildTo=territory, detailedUnit=self.repairUnit)
                allBuildOptions.append(buildOption)
            if territory.factoryMax < territory.landValue and player.money >= 15:
                buildOption = BuildOption(buildFrom=territory, buildTo=territory, detailedUnit=self.factoryUnit)
                allBuildOptions.append(buildOption)
        return allBuildOptions

    def collectMoney(self) -> None:
        player = self.currentPlayer
        player.money += player.reservedMoney
        player.reservedMoney = 0
        territories = self.ownedValuedTerritories[player]
        for territory in territories:
            player.money += territory.landValue

    def boardTransport(self, destinationTransport: DestinationTransport, boardingUnit: DetailedUnit):    
        transportUnit = destinationTransport.transportUnit
        newTransportUnit = self.unitAfterLoadUnitType[transportUnit][boardingUnit.unitType]
        destination = destinationTransport.territory
        self.removeUnit(destination, transportUnit)
        self.addUnit(destination, newTransportUnit)

    def unloadTransport(self, moveFrom: Territory, detailedUnit: DetailedUnit, destinationTransport: DestinationTransport):
        self.removeUnit(moveFrom, detailedUnit)
        unloadingTransport = None
        #player = None
        if destinationTransport.unload1:
            #player = destinationTransport.unload1.unitType.player
            if destinationTransport.unload2:
                unloadingTransport = detailedUnit.unitAfterUnloadBoth
            else:
                unloadingTransport = detailedUnit.unitAfterUnload1
        elif destinationTransport.unload2:
            #player = destinationTransport.unload2.unitType.player
            unloadingTransport = detailedUnit.unitAfterUnload2

        connection = moveFrom.getConnectionTo[destinationTransport.territory]
        unitQuantity = connection.getUnitQuantities[unloadingTransport]
        unitQuantity.quantity += 1
        moveFrom.isBeachheadSource = True
        self.beachheadSources.append(moveFrom)

    def moveUnit(self, moveFrom: Territory, detailedUnit: DetailedUnit, destinationTransport: DestinationTransport):
        if self.verbose:
            print("Moving unit: " + str(detailedUnit) + " from: " + str(moveFrom.name) + " to: " + str(destinationTransport))
        if not destinationTransport.unload1 and not destinationTransport.unload2:
            self.removeUnit(moveFrom, detailedUnit)
        else:
            self.unloadTransport(moveFrom=moveFrom, detailedUnit=detailedUnit, destinationTransport=destinationTransport)
        if destinationTransport.transportUnit:
            self.boardTransport(destinationTransport, detailedUnit)
        elif not destinationTransport.unload1 and not destinationTransport.unload2:
            moveTo = destinationTransport.territory
            newUnit = detailedUnit.unitAfterMove
            enemyUnits = self.getEnemyUnitsInTerritory(moveTo)
            if self.unitsRemaining(enemyUnits) > 0:
                while(newUnit.movesRemaining > 0):
                    newUnit = newUnit.unitAfterMove
            else:
                if not moveTo.isWater:
                    if moveTo.owner.team != self.currentPlayer.team and not newUnit.unitType.isAir:
                        self.conquer(moveTo)
            self.addUnit(moveTo, newUnit)

    def resetUnitsFully(self) -> None:
        unitQuantitiesForTerritory = self.unitQuantitiesForTerritory
        for territory in self.ownedTerritories[self.currentPlayer]:
            territory.planesCanLand = True
        for territory in unitQuantitiesForTerritory[self.currentPlayer]:
            unitQuantitiesCopy = unitQuantitiesForTerritory[self.currentPlayer][territory][:]
            for unitQuantity in unitQuantitiesCopy:
                detailedUnit = unitQuantity.detailedUnit
                if detailedUnit.unitAfterTurn != detailedUnit:
                    for _ in range(unitQuantity.quantity):
                        self.removeUnit(territory, detailedUnit)
                        self.addUnit(territory, detailedUnit.unitAfterTurn)

    def getAllAvailableMoveOrders(self, combatAllowed: bool=True) -> List[MoveOption]:
        player = self.currentPlayer
        unitQuantitiesForTerritory = self.unitQuantitiesForTerritory[player]
        occupiedTerritories = unitQuantitiesForTerritory.keys()
        allMoveOptions = []
        for territoryFrom in occupiedTerritories:
            unitQuantities = unitQuantitiesForTerritory[territoryFrom]
            for unitQuantity in unitQuantities:
                detailedUnit = unitQuantity.detailedUnit
                if detailedUnit.movesRemaining > 0 and (not detailedUnit.unitType.isAA or not combatAllowed):
                    unitType = detailedUnit.unitType
                    #moving unit isAir
                    if unitType.isAir:
                        adjacentAirTerritories = territoryFrom.adjacentAirTerritories
                        for destination in adjacentAirTerritories:
                            destinationTransport = DestinationTransport(destination)
                            moveOption = MoveOption(moveFrom=territoryFrom, selectedUnit=detailedUnit, moveTo=destinationTransport)
                            allMoveOptions.append(moveOption)
                    #moving unit isWater
                    elif unitType.isWater:
                        waterConnections = territoryFrom.waterConnections
                        for connection in waterConnections:
                            destination = self.connectionDestination[connection]
                            if unitType.player == player:
                                requiredTerritories = self.requiredTerritories[connection]
                                requirementsMet = True
                                #optimize
                                for requiredTerritory in requiredTerritories:
                                    if requiredTerritory.owner.team != detailedUnit.player.team:
                                        requirementsMet = False
                                        break
                                if requirementsMet:
                                    enemyUnits = self.getEnemyUnitsInTerritory(destination)
                                    if self.unitsRemaining(enemyUnits) == 0 or combatAllowed:
                                        destinationTransport = DestinationTransport(destination)
                                        moveOption = MoveOption(moveFrom=territoryFrom, selectedUnit=detailedUnit, moveTo=destinationTransport)
                                        allMoveOptions.append(moveOption)
                        if detailedUnit in self.payload:
                            # unload transport
                            payload = self.payload[detailedUnit]
                            loadedUnit1 = payload[0]
                            for connection in territoryFrom.landConnections:
                                destination = self.connectionDestination[connection]
                                enemyUnits = self.getEnemyUnitsInTerritory(destination)
                                if self.unitsRemaining(enemyUnits) == 0 or combatAllowed:
                                    if loadedUnit1.unitType.player == player:
                                        destinationTransport = DestinationTransport(territory=destination, unload1=loadedUnit1)
                                        moveOption = MoveOption(moveFrom=territoryFrom, selectedUnit=detailedUnit, moveTo=destinationTransport)
                                        allMoveOptions.append(moveOption)
                                    if len(payload) > 1:
                                        loadedUnit2 = payload[1]
                                        if loadedUnit2.unitType.player == player:
                                            destinationTransport = DestinationTransport(territory=destination, unload2=loadedUnit2)
                                            moveOption = MoveOption(moveFrom=territoryFrom, selectedUnit=detailedUnit, moveTo=destinationTransport)
                                            allMoveOptions.append(moveOption)
                                            if loadedUnit1.unitType.player == player:
                                                destinationTransport = DestinationTransport(territory=destination, unload1=loadedUnit1, unload2=loadedUnit2)
                                                moveOption = MoveOption(moveFrom=territoryFrom, selectedUnit=detailedUnit, moveTo=destinationTransport)
                                                allMoveOptions.append(moveOption)
                    #moving unit is land
                    else:
                        for destination in territoryFrom.adjacentLandTerritories:
                            # land unit to land territory
                            enemyUnits = self.getEnemyUnitsInTerritory(destination)
                            if (self.unitsRemaining(enemyUnits) == 0 and destination.owner.team == player.team) or combatAllowed:
                                destinationTransport = DestinationTransport(destination)
                                moveOption = MoveOption(moveFrom=territoryFrom, selectedUnit=detailedUnit, moveTo=destinationTransport)
                                allMoveOptions.append(moveOption)
                        for destinationWater in territoryFrom.adjacentWaterTerritories:
                            # land unit to water
                            playerAndAllies = self.allies[player][:]
                            playerAndAllies.append(player)
                            for ally in playerAndAllies:
                                unitQuantitiesForTerritoryAlly = self.unitQuantitiesForTerritory[ally]
                                if destinationWater in unitQuantitiesForTerritoryAlly:
                                    unitQuantities2 = unitQuantitiesForTerritoryAlly[destinationWater]
                                    for unitQuantity2 in unitQuantities2:
                                        detailedUnitTransport = unitQuantity2.detailedUnit
                                        #optimize
                                        if len(detailedUnitTransport.canLoadUnitType) > 0:
                                            loadUnitType = detailedUnit.unitType
                                            canLoadUnitType = detailedUnitTransport.canLoadUnitType.get(loadUnitType, False)
                                            if canLoadUnitType:
                                                destinationTransport = DestinationTransport(territory=destinationWater, transportUnit=detailedUnitTransport)
                                                moveOption = MoveOption(moveFrom=territoryFrom, selectedUnit=detailedUnit, moveTo=destinationTransport)
                                                allMoveOptions.append(moveOption)
        return allMoveOptions

    def getConflictedTerritories(self) -> List[Territory]:
        player = self.currentPlayer
        unitQuantitiesForTerritory = self.unitQuantitiesForTerritory
        territoriesWithUnits = unitQuantitiesForTerritory[player].keys()
        territoriesWithUnits2 = list(territoriesWithUnits)
        territoriesWithUnits2.extend(self.beachheadSources)
        enemyTerrritories = []
        for enemy in self.enemies[player]:
            enemyTerrritories.extend(list(unitQuantitiesForTerritory[enemy].keys()))
        conflictedTerritories = intersection(territoriesWithUnits2, enemyTerrritories)
        return conflictedTerritories

    def getConflictedSeaTerritories(self) -> List[Territory]:
        conflictedTerritories = self.getConflictedTerritories()
        conflictedSeaTerritories = []
        for territory in conflictedTerritories:
            if territory.isWater:
                conflictedSeaTerritories.append(territory)
        return conflictedSeaTerritories

    def getConflictedLandTerritories(self) -> List[Territory]:
        conflictedTerritories = self.getConflictedTerritories()
        conflictedSeaTerritories = []
        for territory in conflictedTerritories:
            if not territory.isWater:
                conflictedSeaTerritories.append(territory)
        return conflictedSeaTerritories

    def getFriendlyUnitsInSea(self, territory: Territory) -> List[UnitQuantity]:
        player = self.currentPlayer
        friendlyUnitQuantities = []
        if territory in self.unitQuantitiesForTerritory[player]:
            friendlyUnitQuantities.extend(list(self.unitQuantitiesForTerritory[player][territory]))
        for ally in self.allies[player]:
            if territory in self.unitQuantitiesForTerritory[ally]:
                friendlyUnitQuantities.extend(list(self.unitQuantitiesForTerritory[ally][territory]))
        for connection in territory.connections:
            if player in self.unitQuantitiesForConnection:
                if connection in self.unitQuantitiesForConnection[player]:
                    for unitQuantity in self.unitQuantitiesForConnection[player][connection]:
                        friendlyUnitQuantities.append(unitQuantity)
        return friendlyUnitQuantities
                
    def getEnemyUnitsInTerritory(self, territory: Territory) -> List[UnitQuantity]:
        enemyUnitQuantities = []
        for enemy in self.enemies[self.currentPlayer]:
            unitQuantitiesForTerritoryEnemy = self.unitQuantitiesForTerritory[enemy]
            if territory in unitQuantitiesForTerritoryEnemy:
                enemyUnitQuantities.extend(unitQuantitiesForTerritoryEnemy[territory])
        return enemyUnitQuantities

    def fireForHits(self, unitQuantities: List[UnitQuantity], numberOfBombersToBomb: int=0, useDefense: bool=False, subsTurn: bool=False, lowLuck: bool=True) -> int:
        
        hits = 0
        totalStrength = 0
        maxSupportable = 0
        maxSupported = 0
        if not useDefense:
            for unitQuantity in unitQuantities:
                unitType = unitQuantity.detailedUnit.unitType
                quantity = unitQuantity.quantity
                if unitType.maxSupportable > 0:
                    maxSupportable = quantity
                if unitType.maxSupported > 0:
                    maxSupported = quantity                                
        maxBonusUnits = min(maxSupportable, maxSupported)
        for unitQuantity in unitQuantities:
            unitType = unitQuantity.detailedUnit.unitType
            if unitType.isSub == subsTurn:
                quantity = unitQuantity.quantity
                if unitType.bomber > 0:
                    quantity -= numberOfBombersToBomb
                if quantity > 0:
                    if self.verbose:
                        print("firing: " + str(unitType) + " x" + str(quantity)) 
                    #hack
                    fireValue = 0
                    if useDefense:
                        fireValue = unitType.defense
                    else:
                        fireValue = unitType.attack
                        if unitType.maxSupportable > 0:
                            quantity -= maxBonusUnits
                            if lowLuck:
                                totalStrength += (fireValue + 1) * maxBonusUnits
                            else:
                                for _ in range(maxBonusUnits):
                                    if random.randint(1,6) <= fireValue + 1:
                                        hits +=1
                    if lowLuck:
                        totalStrength += (fireValue * quantity)
                    else:
                        for _ in range(quantity):
                            if random.randint(1,6) <= fireValue:
                                hits +=1
            if lowLuck:
                hits = totalStrength // 6
                if random.randint(1,6) <= totalStrength % 6:
                    hits += 1
        if self.verbose:
            print(str(hits) + " hit(s)")
        return hits


    def removeCasualty(self, territory: Territory, unitQuantities: List[UnitQuantity], numberOfBombersToBomb:int=0, onlyNonAir: bool=False, submerged: bool=False) -> None:
        # change from automatic to ask
        cheapestUnitQuantity = None
        cheapestUnitValue = 999
        for unitQuantity in unitQuantities:
            detailedUnit = unitQuantity.detailedUnit
            unitType = detailedUnit.unitType
            if not unitType.isAA and (not onlyNonAir or not unitType.isAir) and (not submerged or not unitType.isSub):
                # bug count all bombers, not just detailed unit moves remaining
                if unitType.bomber == 0 or numberOfBombersToBomb < unitQuantity.quantity:
                    unitValue = unitType.cost + (detailedUnit.movesRemaining * 0.1)
                    if detailedUnit in self.payload:
                        payload = self.payload[detailedUnit]
                        if len(payload) > 0:
                            for loadedUnit in payload:
                                unitValue += loadedUnit.unitType.cost
                    if detailedUnit.hitsRemaining > 1:
                        unitValue = 0
                    if unitValue < cheapestUnitValue:
                        cheapestUnitValue = unitValue
                        cheapestUnitQuantity = unitQuantity
        if cheapestUnitQuantity:
            if self.verbose:
                print("removing unit:" + str(cheapestUnitQuantity.detailedUnit))
            self.removeUnit(territory, cheapestUnitQuantity.detailedUnit)
            if cheapestUnitQuantity.detailedUnit.hitsRemaining > 1:
                self.addUnit(territory, cheapestUnitQuantity.detailedUnit.unitAfterHit)


    def unitsRemaining(self, unitQuantities: List[UnitQuantity], numberOfBombersToBomb: int=0, onlyNonAir: bool=False, submerged:bool=False) -> int:
        unitsRemaining = 0
        for unitQuantity in unitQuantities:
            unitType = unitQuantity.detailedUnit.unitType
            if not unitType.isAA and (not onlyNonAir or not unitType.isAir) and (not submerged or not unitType.isSub):
                unitsRemaining += unitQuantity.quantity
        return unitsRemaining - numberOfBombersToBomb

    def askSubmergeSubs(self, friendlyUnits: List[UnitQuantity], enemyUnits: List[UnitQuantity]) -> bool:
        response = False
        destroyersExist = False
        for friendlyUnit in friendlyUnits:
            if friendlyUnit.detailedUnit.unitType.isAntiSub:
                destroyersExist = True
                break
        if destroyersExist == False:
            for enemyUnit in enemyUnits:
                if enemyUnit.detailedUnit.unitType.isSub:
                    if self.verbose:
                        print("Submerging Subs") # ask question instead of default yes
                    if random.randint(0, 1) < 2:
                        response = True
                    else:
                        response = False
                break
        return response

    def askRetreat(self, friendlyUnits: List[UnitQuantity], enemyUnits: List[UnitQuantity]) -> bool:
        if self.verbose:
            print("Never Retreat") # ask question instead of default yes
        #ask for each unit where to retreat to
        if random.randint(0,3) > 4:
            response = True
        else:
            response = False
        return response

    def resolveSeaCombat(self) -> None:
        #optimize
        player = self.currentPlayer
        conflictedSeaTerritories = self.getConflictedSeaTerritories()
        for conflictedSeaTerritory in conflictedSeaTerritories:
            continueFighting = True
            submerged = False
            while continueFighting:
                friendlyUnits = self.getFriendlyUnitsInSea(conflictedSeaTerritory)
                enemyUnits = self.getEnemyUnitsInTerritory(conflictedSeaTerritory)
                for friendlyUnitQuantity in friendlyUnits:
                    if self.verbose:
                        print(str(friendlyUnitQuantity))
                for enemyUnitQuantity in enemyUnits:
                    if self.verbose:
                        print(str(enemyUnitQuantity))
                friendlyHits = self.fireForHits(unitQuantities=friendlyUnits, subsTurn=True)
                if submerged:
                    if self.verbose:
                        print("subs are submerged")
                    enemyHits = 0
                else:
                    enemyHits = self.fireForHits(unitQuantities=enemyUnits, useDefense=True, subsTurn=True)
                while friendlyHits > 0 and self.unitsRemaining(unitQuantities=enemyUnits, onlyNonAir=True) > 0:
                    self.removeCasualty(territory=conflictedSeaTerritory, unitQuantities=enemyUnits, onlyNonAir=True, submerged=submerged)
                    enemyUnits = self.getEnemyUnitsInTerritory(conflictedSeaTerritory)
                    friendlyHits -=1
                while enemyHits > 0 and self.unitsRemaining(unitQuantities=friendlyUnits, onlyNonAir=True) > 0:
                    self.removeCasualty(territory=conflictedSeaTerritory, unitQuantities=friendlyUnits, onlyNonAir=True)
                    friendlyUnits = self.getFriendlyUnitsInSea(conflictedSeaTerritory)
                    enemyHits -=1
                friendlyHits = self.fireForHits(friendlyUnits)
                enemyHits = self.fireForHits(enemyUnits, useDefense=True)
                while friendlyHits > 0 and self.unitsRemaining(enemyUnits) > 0:
                    self.removeCasualty(territory=conflictedSeaTerritory, unitQuantities=enemyUnits, submerged=submerged)
                    enemyUnits = self.getEnemyUnitsInTerritory(conflictedSeaTerritory)
                    friendlyHits -= 1
                while enemyHits > 0 and self.unitsRemaining(friendlyUnits) > 0:
                    self.removeCasualty(territory=conflictedSeaTerritory, unitQuantities=friendlyUnits)
                    friendlyUnits = self.getFriendlyUnitsInSea( conflictedSeaTerritory)
                    enemyHits -= 1
                if submerged == False:
                    submerged = self.askSubmergeSubs(friendlyUnits, enemyUnits)
                retreatDecision = self.askRetreat(friendlyUnits, enemyUnits)
                continueFighting = not retreatDecision and self.unitsRemaining(friendlyUnits) > 0 and self.unitsRemaining(enemyUnits, submerged=submerged) > 0
            friendlyUnits = []
            if conflictedSeaTerritory in self.unitQuantitiesForTerritory[player]:
                friendlyUnits = self.unitQuantitiesForTerritory[player][conflictedSeaTerritory]
            for friendlyUnit in set(friendlyUnits):
                newUnit = friendlyUnit.detailedUnit
                if not newUnit.unitType.isAir and newUnit.movesRemaining > 0:
                    while(newUnit.movesRemaining > 0):
                        newUnit = newUnit.unitAfterMove
                    for _ in range(friendlyUnit.quantity):
                        self.removeUnit(conflictedSeaTerritory, friendlyUnit.detailedUnit)
                        self.addUnit(conflictedSeaTerritory, newUnit)

    def getBombers(self, friendlyUnits: List[UnitQuantity]) -> int:
        bombers = 0
        for unitQuantity in friendlyUnits:
            if unitQuantity.detailedUnit.unitType.bomber > 0:
                bombers += unitQuantity.quantity
        return bombers

    def resolveLandCombat(self, lowLuck:bool = True) -> None:
        player = self.currentPlayer
        #optimize
        conflictedLandTerritories = self.getConflictedLandTerritories()
        for conflictedLandTerritory in conflictedLandTerritories:
            continueFighting = True
            friendlyUnits = self.unitQuantitiesForTerritory[player][conflictedLandTerritory]
            enemyUnits = self.getEnemyUnitsInTerritory(conflictedLandTerritory)
            #optimize
            for enemyUnit in enemyUnits:
                if enemyUnit.detailedUnit.unitType.isAA:
                    if self.verbose:
                        print("Firing AntiAir")
                    if lowLuck:
                        planeCount = 0
                        for friendlyUnit in friendlyUnits:
                            if friendlyUnit.detailedUnit.unitType.isAir:
                                planeCount += friendlyUnit.quantity
                        aaHits = planeCount // 6
                        if random.randint(1,6) <= planeCount % 6:
                            aaHits += 1
                        while(aaHits > 0):
                            airUnits = []
                            for friendlyUnit in friendlyUnits:
                                if friendlyUnit.detailedUnit.unitType.isAir:
                                    airUnits.append(friendlyUnit)
                            self.removeCasualty(conflictedLandTerritory, airUnits)
                            aaHits -= 1
                    else:
                        for friendlyUnit in friendlyUnits:
                            if friendlyUnit.detailedUnit.unitType.isAir:
                                for _ in range(friendlyUnit.quantity):
                                    if random.randint(1,6) <= 1:
                                        if player.isHuman:
                                            print("Antiair hit!")
                                        conflictedLandTerritory.removeUnit(friendlyUnit.detailedUnit)
                    break
            friendlyUnits = self.unitQuantitiesForTerritory[player][conflictedLandTerritory]
            numberOfBombersToBomb = 0
            if conflictedLandTerritory.constructionRemaining > 0:
                #ask
                numberOfBombersToBomb = self.getBombers(friendlyUnits)
            if lowLuck:
                damage = (numberOfBombersToBomb // 2) * 7
                if numberOfBombersToBomb % 2 == 1:
                    damage += random.randint(3,4)
                conflictedLandTerritory.damageFactory(damage)
                if player.isHuman:
                    print("bombed: " + str(conflictedLandTerritory.name) + ' for ' + str(damage) + ' damage')
            else:
                for _ in range(numberOfBombersToBomb):
                    #optimize safety
                    damage = random.randint(1,6)
                    conflictedLandTerritory.damageFactory(damage)
                    if player.isHuman:
                        print("bombed: " + str(conflictedLandTerritory.name) + ' for ' + str(damage) + ' damage')

            while continueFighting:
                friendlyHits = self.fireForHits(friendlyUnits, numberOfBombersToBomb=numberOfBombersToBomb)
                enemyHits = self.fireForHits(enemyUnits, useDefense=True)
                while friendlyHits > 0 and self.unitsRemaining(enemyUnits) > 0:
                    self.removeCasualty(conflictedLandTerritory, enemyUnits)
                    enemyUnits = self.getEnemyUnitsInTerritory(conflictedLandTerritory)
                    friendlyHits -= 1
                while enemyHits > 0 and self.unitsRemaining(friendlyUnits, numberOfBombersToBomb=numberOfBombersToBomb) > 0:
                    self.removeCasualty(conflictedLandTerritory, friendlyUnits, numberOfBombersToBomb=numberOfBombersToBomb)
                    friendlyUnits = self.unitQuantitiesForTerritory[player][conflictedLandTerritory]
                    enemyHits -= 1
                retreatDecision = self.askRetreat(friendlyUnits, enemyUnits)
                continueFighting = not retreatDecision and self.unitsRemaining(friendlyUnits, numberOfBombersToBomb=numberOfBombersToBomb) > 0 and self.unitsRemaining(enemyUnits) > 0
            if retreatDecision:
                if player.isHuman:
                    print("retreat implement todo")
            elif self.unitsRemaining(friendlyUnits, onlyNonAir=True) > 0:
                self.conquer(conflictedLandTerritory)


    def resolveBombards(self, lowLuck:bool=True) -> None:
        player = self.currentPlayer
        unitQuantitiesForConnection = self.unitQuantitiesForConnection
        for unloadingConnection in unitQuantitiesForConnection:
            unloadedUnitQuantity = 0
            for unitQuantity in unitQuantitiesForConnection[unloadingConnection]:
                unloadedUnitQuantity += unitQuantity.quantity
            seaTerritoryFrom = self.connectionSource[unloadingConnection]
            battleShipsToSkip = seaTerritoryFrom.bombardsUsed
            destination = self.connectionDestination[unloadingConnection]
            enemyUnits = self.getEnemyUnitsInTerritory(destination)
            if seaTerritoryFrom in self.unitQuantitiesForTerritory[player]:
                for unitQuantity in self.unitQuantitiesForTerritory[player][seaTerritoryFrom]:
                    bombardValue = unitQuantity.detailedUnit.unitType.bombard
                    if unitQuantity.detailedUnit.unitType.bombard > 0:
                        if battleShipsToSkip > 0:
                            battleShipsToSkip -= 1
                            #todo: ask bombard
                            #todo: implement lowluck
                        elif self.unitsRemaining(enemyUnits) > 0:
                            seaTerritoryFrom.bombardsUsed += 1
                            if player.isHuman:
                                print("bombarding: " + str(destination))
                            if random.randint(1,6) <= bombardValue:
                                if player.isHuman:
                                    print("bombard hit!")
                                destination = self.connectionDestination[unloadingConnection]
                                self.removeCasualty(destination, unitQuantities=enemyUnits)
        for unloadingConnection in unitQuantitiesForConnection:
            self.connectionSource[unloadingConnection].bombardsUsed = 0

    def unloadTransports2(self):
        unitQuantitiesForConnection = self.unitQuantitiesForConnection
        for unloadingConnection in unitQuantitiesForConnection:
            for unitQuantity in self.unitQuantitiesForConnection[unloadingConnection]:
                for _ in range(unitQuantity.quantity):
                    transportUnit = unitQuantity.detailedUnit
                    destination = self.connectionDestination[unloadingConnection]
                    for boardedUnit in self.payload[transportUnit]:
                        self.addUnit(destination, boardedUnit)
                    source = self.connectionSource[unloadingConnection]
                    self.addUnit(source, transportUnit.unitAfterUnload)
                    unitQuantity.quantity -= 1
            self.connectionSource[unloadingConnection].isBeachheadSource = False
        unitQuantitiesForConnection.clear()
        self.beachheadSources.clear()

    def crashPlanes(self):
        player = self.currentPlayer
        unitQuantitiesPlayer = self.unitQuantitiesForTerritory[self.currentPlayer]
        for territory in unitQuantitiesPlayer:
            if territory.isWater or territory.owner.team != player.team or not territory.planesCanLand:        
                unitQuantities = unitQuantitiesPlayer[territory]
                totalCarrierSpace = 0
                for unitQuantity in unitQuantities:
                    totalCarrierSpace += (unitQuantity.detailedUnit.unitType.maxAir * unitQuantity.quantity)
                allPlanes = []
                planeCount = 0
                for unitQuantity in unitQuantities:
                    detailedUnit = unitQuantity.detailedUnit
                    if detailedUnit.unitType.isAir:
                        allPlanes.append(unitQuantity)
                        planeCount += unitQuantity.quantity
                unlandablePlaneCount = planeCount - totalCarrierSpace
                while(unlandablePlaneCount > 0):
                    self.removeCasualty(territory, allPlanes)
                    unlandablePlaneCount -= 1
                    allPlanes = []
                    #optimize
                    for unitQuantity in unitQuantities:
                        detailedUnit = unitQuantity.detailedUnit
                        if detailedUnit.unitType.isAir:
                            allPlanes.append(unitQuantity)


    def linkStatesAfterCombatMove(self, linkFrom: Set[bytes]):
        newGameState = self.backupGameState()
        if newGameState not in linkFrom:
            linkFrom.add(newGameState)
            movesAvailable = self.getAllAvailableMoveOrders(combatAllowed=True)
            if len(movesAvailable) > 0:
                backupGameState = self.backupGameState()
                for moveAvailable in movesAvailable:
                    self.moveUnit(moveAvailable.moveFrom, moveAvailable.selectedUnit, moveAvailable.moveTo)
                    self.linkStatesAfterCombatMove(linkFrom=linkFrom)
                    self.restoreGameState(backupGameState)

    def linkStatesAfterMove(self, linkFrom: Set[bytes]):
        newGameState = self.backupGameState()
        if newGameState not in linkFrom:
            linkFrom.add(newGameState)
            movesAvailable = self.getAllAvailableMoveOrders(combatAllowed=False)
            if len(movesAvailable) > 0:
                backupGameState = self.backupGameState()
                for moveAvailable in movesAvailable:
                    self.moveUnit(moveAvailable.moveFrom, moveAvailable.selectedUnit, moveAvailable.moveTo)
                    self.linkStatesAfterMove(linkFrom=linkFrom)
                    self.restoreGameState(backupGameState)

    def linkStatesFromPurchase(self, linkFrom: Set[bytes]):
        newGameState = self.backupGameState()
        if newGameState not in linkFrom:
            linkFrom.add(newGameState)
            currentPlayer = self.currentPlayer
            purchasesAvailable = self.getAllBuildOptions()
            if len(purchasesAvailable) > 0:
                backupGameState = self.backupGameState()
                for buildOption in purchasesAvailable:
                    buildFrom = buildOption.buildFrom
                    buildTo = buildOption.buildTo
                    unitSelected = buildOption.detailedUnit
                    currentPlayer.money -= unitSelected.unitType.cost
                    if unitSelected == self.factoryUnit:
                        if self.verbose:
                            print("Purchase: Factory in: " + str(buildTo))
                        buildFrom.buildFactory()
                        buildFrom.constructionRemaining = 0
                    elif unitSelected == self.repairUnit:
                        if self.verbose:
                            print("Repair: " + str(unitSelected) + " in: " + str(buildTo))
                        buildFrom.factoryHealth += 1
                        buildFrom.constructionRemaining += 1
                    else:
                        if self.verbose:
                            print("Purchase: " + str(unitSelected) + " in: " + str(buildTo))
                        buildFrom.constructionRemaining -= 1
                        self.addUnit(buildTo, unitSelected)
                    self.linkStatesFromPurchase(linkFrom=linkFrom)
                    self.restoreGameState(backupGameState)

    def randomMove(self, combatAllowed:bool):
        v = self.verbose
        self.verbose = False
        futureStates1 = []
        futureStates2 = []
        preMoveGameState = self.backupGameState()
        self.currentPhase = 1
        gameState = self.backupGameState()
        futureStates1.append(gameState)
        futureStates2.append(list(gameState))
        self.restoreGameState(preMoveGameState)
        movesAvailable = self.getAllAvailableMoveOrders(combatAllowed=combatAllowed)
        for moveAvailable in movesAvailable:
            self.moveUnit(moveAvailable.moveFrom, moveAvailable.selectedUnit, moveAvailable.moveTo)
            gameState = self.backupGameState()
            futureStates1.append(gameState)
            futureStates2.append(list(gameState))
            self.restoreGameState(preMoveGameState)
        if random.random() < 0.5:
            npMovesAvailable = np.asarray(futureStates2)
            predictions = self.model.predict(npMovesAvailable)
            if self.currentPlayer.team == 1:
                winchance = np.amax(predictions)
            else:
                winchance = np.amin(predictions)
            #print(winchance)
            bestMove = np.where(predictions == winchance)
            newState = futureStates1[bestMove[0][0]]
        else:
            newState = random.choice(futureStates1)
        self.restoreGameState(newState)
        self.verbose = v

    def randomPurchase(self):
        v = self.verbose
        self.verbose = False
        futureStates1 = []
        futureStates2 = []
        prePurchaseGameState = self.backupGameState()
        #prePurchaseGameState2 = bytes(self.gamedata.rawByteArray)
        purchasesAvailable = self.getAllBuildOptions()
        if self.currentPlayer.money < 24 or len(purchasesAvailable) == 0:
            self.crashPlanes()
            self.resetUnitsFully()
            self.resetConstruction()
            self.collectMoney()
            self.advanceTurn()
            self.currentPhase = 0
            gameState = self.backupGameState()
            futureStates1.append(gameState)
            futureStates2.append(list(gameState))
            #self.gamedata.rawByteArray = bytearray(prePurchaseGameState2)
            self.restoreGameState(prePurchaseGameState)
        for buildOption in purchasesAvailable:
            buildFrom = buildOption.buildFrom
            buildTo = buildOption.buildTo
            unitSelected = buildOption.detailedUnit
            self.currentPlayer.money -= unitSelected.unitType.cost
            if unitSelected == self.factoryUnit:
                if self.verbose:
                    print("Purchase: Factory in: " + str(buildTo))
                buildFrom.buildFactory()
                buildFrom.constructionRemaining = 0
            elif unitSelected == self.repairUnit:
                if self.verbose:
                    print("Repair: " + str(unitSelected) + " in: " + str(buildTo))
                buildFrom.factoryHealth += 1
                buildFrom.constructionRemaining += 1
            else:
                if self.verbose:
                    print("Purchase: " + str(unitSelected) + " in: " + str(buildTo))
                buildFrom.constructionRemaining -= 1
                self.addUnit(buildTo, unitSelected)
            gameState = self.backupGameState()
            futureStates1.append(bytes(gameState))
            futureStates2.append(list(bytes(gameState)))
            #futureStates1.append(bytes(self.gamedata.rawByteArray))
            #futureStates2.append(list(bytes(self.gamedata.rawByteArray)))
            #self.gamedata.rawByteArray = bytearray(prePurchaseGameState2)
            self.restoreGameState(prePurchaseGameState)
        if random.random() < 0.5:
            npPurchasesAvailable = np.asarray(futureStates2)
            predictions = self.model.predict(npPurchasesAvailable)
            if self.currentPlayer.team == 1:
                winchance = np.amax(predictions)
            else:
                winchance = np.amin(predictions)
            #print(winchance)
            bestMove = np.where(predictions == winchance)
            newState = futureStates1[bestMove[0][0]]
            #self.gamedata.rawByteArray = bytearray(newState)
        else:
            newState = random.choice(futureStates1)
        self.restoreGameState(newState)
        self.verbose = v
        return newState

    def lookAheadSmall(self, currentGameState: bytes) -> Set[bytes]:
        self.restoreGameState(currentGameState)
        futureStates1 = set()
        if self.currentPhase == 0:
            self.currentPhase = 1
            futureStates1.add(self.backupGameState())
            self.restoreGameState(currentGameState)
            movesAvailable = self.getAllAvailableMoveOrders(combatAllowed=True)
            for moveAvailable in movesAvailable:
                self.moveUnit(moveAvailable.moveFrom, moveAvailable.selectedUnit, moveAvailable.moveTo)
                futureStates1.add(self.backupGameState())
                self.restoreGameState(currentGameState)
        elif self.currentPhase == 1:
            probablilities = {}
            highest_occurence = 0
            highest_gameState = None
            for _ in range(100):
                self.resolveSeaCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
                self.resolveBombards() # rand select unit Casulaty
                self.unloadTransports2() # no options here...
                self.resolveLandCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
                gameState = self.backupGameState()
                if gameState not in probablilities:
                    probablilities[gameState] = 0
                probablilities[gameState] += 1
                self.restoreGameState(currentGameState)
            for gameState, occurences in probablilities.items():
                if occurences > highest_occurence:
                    highest_gameState = gameState
            self.restoreGameState(highest_gameState)
            self.currentPhase = 2
            futureStates1.add(self.backupGameState())
        elif self.currentPhase == 2:
            self.currentPhase = 3
            futureStates1.add(self.backupGameState())
            self.restoreGameState(currentGameState)
            movesAvailable = self.getAllAvailableMoveOrders(combatAllowed=False)
            for moveAvailable in movesAvailable:
                self.moveUnit(moveAvailable.moveFrom, moveAvailable.selectedUnit, moveAvailable.moveTo)
                futureStates1.add(self.backupGameState())
                self.restoreGameState(currentGameState)
        elif self.currentPhase == 3:
            self.crashPlanes()
            self.resetUnitsFully()
            self.resetConstruction()
            self.collectMoney()
            self.advanceTurn()
            self.currentPhase = 0
            futureStates1.add(self.backupGameState())
            self.restoreGameState(currentGameState)
            purchasesAvailable = self.getAllBuildOptions()
            for buildOption in purchasesAvailable:
                buildFrom = buildOption.buildFrom
                buildTo = buildOption.buildTo
                unitSelected = buildOption.detailedUnit
                self.currentPlayer.money -= unitSelected.unitType.cost
                if unitSelected == self.factoryUnit:
                    buildFrom.buildFactory()
                    buildFrom.constructionRemaining = 0
                elif unitSelected == self.repairUnit:
                    buildFrom.factoryHealth += 1
                    buildFrom.constructionRemaining += 1
                else:
                    buildFrom.constructionRemaining -= 1
                    self.addUnit(buildTo, unitSelected)
                futureStates1.add(self.backupGameState())
                self.restoreGameState(currentGameState)
        return futureStates1

    def lookAhead(self, currentGameState: bytes) -> Set[bytes]:
        self.restoreGameState(currentGameState)
        futureStates1 = set()
        futureStates2 = set()
        if self.currentPhase == 0:
            self.linkStatesAfterCombatMove(linkFrom=futureStates1)
            for gameStateBytes in futureStates1:
                self.restoreGameState(gameStateBytes)
                self.currentPhase = 1
                futureStates2.add(self.backupGameState())
        elif self.currentPhase == 1:
            probablilities = {}
            highest_occurence = 0
            highest_gameState = None
            for _ in range(10):
                self.resolveSeaCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
                self.resolveBombards() # rand select unit Casulaty
                self.unloadTransports2() # no options here...
                self.resolveLandCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
                gameState = self.backupGameState()
                if gameState not in probablilities:
                    probablilities[gameState] = 0
                probablilities[gameState] += 1
                self.restoreGameState(currentGameState)
            for gameState, occurences in probablilities.items():
                if occurences > highest_occurence:
                    highest_gameState = gameState
            self.restoreGameState(highest_gameState)
            self.currentPhase = 2
            futureStates2.add(self.backupGameState())
        elif self.currentPhase == 2:
            self.linkStatesAfterMove(linkFrom=futureStates1)
            for gameStateBytes in futureStates1:
                self.restoreGameState(gameStateBytes)
                self.currentPhase = 3
                futureStates2.add(self.backupGameState())
        elif self.currentPhase == 3:
            self.linkStatesFromPurchase(linkFrom=futureStates1)
            for gameStateBytes in futureStates1:
                self.restoreGameState(gameStateBytes)
                self.crashPlanes()
                self.resetUnitsFully()
                self.resetConstruction()
                self.collectMoney()
                self.advanceTurn()
                self.currentPhase = 0
                futureStates2.add(self.backupGameState())
        return futureStates2

    def isStateTerminal(self, gameState: bytes):
        self.restoreGameState(gameState)
        return self.isTerminal()

    def isTerminal(self) -> bool:
        currentPlayer = self.currentPlayer
        terminal = True
        for player in self.turnOrder:
            if self.capital[player].owner.team != self.capital[currentPlayer].owner.team:
                terminal = False
                break
        return terminal

    def rolloutAllies(self, gameStateToEval: bytes) -> float:
        gsList = list(gameStateToEval)
        if(self.isStateTerminal(gameStateToEval)):
            if gsList[0]==0 or gsList[0]==2:
                reward = 1
            else:
                reward = -1
        else:
            npGameStates = np.asarray([gsList])
            prediction = self.model.predict(npGameStates)
            reward = prediction[0][0]
            if reward > 0.99:
                reward = 0.99
            if reward < -0.99:
                reward = -0.99
        return reward

    def rolloutAxis(self, gameStateToEval: bytes) -> float:
        gsList = list(gameStateToEval)
        if(self.isStateTerminal(gameStateToEval)):
            if gsList[0]==0 or gsList[0]==2:
                reward = -1
            else:
                reward = 1
        else:
            npGameStates = np.asarray([gsList])
            prediction = self.model.predict(npGameStates)
            reward = -1 * prediction[0][0]
            if reward > 0.99:
                reward = 0.99
            if reward < -0.99:
                reward = -0.99
        return reward

    def tfGameToEnd(self, currentGameState: bytes, policy: str="random") -> float:
        self.restoreGameState(currentGameState)
        currentPlayer = self.currentPlayer
        currentTeam = currentPlayer.team
            
        if self.currentPhase == 1:
            probablilities = {}
            highest_occurence = 0
            highest_gameState = None
            for _ in range(100):
                self.resolveSeaCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
                self.resolveBombards() # rand select unit Casulaty
                self.unloadTransports2() # no options here...
                self.resolveLandCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
                gameState = self.backupGameState()
                if gameState not in probablilities:
                    probablilities[gameState] = 0
                probablilities[gameState] += 1
                self.restoreGameState(currentGameState)
            for gameState, occurences in probablilities.items():
                if occurences > highest_occurence:
                    highest_gameState = gameState
            self.restoreGameState(highest_gameState)
            self.currentPhase = 2

        if self.currentPhase == 0:
            movesAvailable = self.getAllAvailableMoveOrders(combatAllowed=True)
            futureStates1 = []
            futureStates2 = []
            preMoveGameState = self.backupGameState()
            self.currentPhase = 1
            gameState = self.backupGameState()
            futureStates1.append(gameState)
            futureStates2.append(list(gameState))
            self.restoreGameState(preMoveGameState)
            for moveAvailable in movesAvailable:
                self.moveUnit(moveAvailable.moveFrom, moveAvailable.selectedUnit, moveAvailable.moveTo)
                gameState = self.backupGameState()
                futureStates1.append(gameState)
                futureStates2.append(list(gameState))
                self.restoreGameState(preMoveGameState)
            npMovesAvailable = np.asarray(futureStates2)
            predictions = self.model.predict(npMovesAvailable)
            if currentTeam == 1:
                winchance = np.amax(predictions)
                reward = winchance
            else:
                winchance = np.amin(predictions)
                reward = winchance * -1
            #bestMove = np.where(predictions == winchance)
            #newState = futureStates1[bestMove[0][0]]
            #self.restoreGameState(newState)

        elif self.currentPhase == 2:
            movesAvailable = self.getAllAvailableMoveOrders(combatAllowed=False)
            futureStates1 = []
            futureStates2 = []
            preMoveGameState = self.backupGameState()
            self.currentPhase = 3
            gameState = self.backupGameState()
            futureStates1.append(gameState)
            futureStates2.append(list(gameState))
            self.restoreGameState(preMoveGameState)
            for moveAvailable in movesAvailable:
                self.moveUnit(moveAvailable.moveFrom, moveAvailable.selectedUnit, moveAvailable.moveTo)
                gameState = self.backupGameState()
                futureStates1.append(gameState)
                futureStates2.append(list(gameState))
                self.restoreGameState(preMoveGameState)
            npMovesAvailable = np.asarray(futureStates2)
            predictions = self.model.predict(npMovesAvailable)
            if currentTeam == 1:
                winchance = np.amax(predictions)
                reward = winchance
            else:
                winchance = np.amin(predictions)
                reward = winchance * -1
            #bestMove = np.where(predictions == winchance)
            #newState = futureStates1[bestMove[0][0]]
            #self.restoreGameState(newState)

        elif self.currentPhase == 3:
            futureStates1 = []
            futureStates2 = []
            prePurchaseGameState = self.backupGameState()
            purchasesAvailable = self.getAllBuildOptions()
            if self.currentPlayer.money < 24 or len(purchasesAvailable) == 0:
                self.crashPlanes()
                self.resetUnitsFully()
                self.resetConstruction()
                self.collectMoney()
                self.advanceTurn()
                self.currentPhase = 0
                gameState = self.backupGameState()
                futureStates1.append(gameState)
                futureStates2.append(list(gameState))
                self.restoreGameState(prePurchaseGameState)
            for buildOption in purchasesAvailable:
                buildFrom = buildOption.buildFrom
                buildTo = buildOption.buildTo
                unitSelected = buildOption.detailedUnit
                self.currentPlayer.money -= unitSelected.unitType.cost
                if unitSelected == self.factoryUnit:
                    buildFrom.buildFactory()
                    buildFrom.constructionRemaining = 0
                elif unitSelected == self.repairUnit:
                    buildFrom.factoryHealth += 1
                    buildFrom.constructionRemaining += 1
                else:
                    buildFrom.constructionRemaining -= 1
                    self.addUnit(buildTo, unitSelected)
                gameState = self.backupGameState()
                futureStates1.append(bytes(gameState))
                futureStates2.append(list(bytes(gameState)))
                self.restoreGameState(prePurchaseGameState)
            npPurchasesAvailable = np.asarray(futureStates2)
            predictions = self.model.predict(npPurchasesAvailable)
            if currentTeam == 1:
                winchance = np.amax(predictions)
                reward = winchance
            else:
                winchance = np.amin(predictions)
                reward = winchance * -1
            #bestMove = np.where(predictions == winchance)
            #newState = futureStates1[bestMove[0][0]]
            #self.restoreGameState(newState)

        self.restoreGameState(currentGameState)
        if reward > 0.99:
            reward = 0.99
        if reward < -0.99:
            reward = -0.99
        if self.isTerminal():
            if self.capital[currentPlayer].owner == currentPlayer:
                reward = 1
            else:
                reward = -1
        return reward

    def simulateGameToEnd(self, currentGameState: bytes, policy: str="random") -> int:
        self.restoreGameState(currentGameState)
        originalPlayer = self.currentPlayer
        while(not self.isTerminal()):
            currentPlayer = self.currentPlayer
            if self.verbose:
                print(self.readableStatus())
            if self.currentPhase == 0:
                if self.verbose:
                    print(str(currentPlayer.name) + ": Combat")
                self.randomMove(combatAllowed=True)
                self.currentPhase = 1
            elif self.currentPhase == 1:
                self.resolveSeaCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
                self.resolveBombards() # rand select unit Casulaty
                self.unloadTransports2() # no options here...
                self.resolveLandCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
                self.currentPhase = 2
            elif self.currentPhase == 2:
                if self.verbose:
                    print(str(currentPlayer.name) + ": Move")
                self.randomMove(combatAllowed=False)
                self.currentPhase = 3
            elif self.currentPhase == 3:
                if self.verbose:
                    print(str(currentPlayer.name) + ": Purchase")
                newState = self.randomPurchase()
                self.restoreGameState(newState)

        reward = 0
        if self.capital[originalPlayer].owner == originalPlayer:
            reward = 1
        else:
            reward = -1
        return reward

def intersection(lst1, lst2): 
    # optimize
    lst3 = [value for value in lst1 if value in lst2] 
    return lst3 
