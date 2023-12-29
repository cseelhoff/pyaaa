from typing import List, Optional
import random
import json

class Player:
    def __init__(self, name: str, money: int=0, team: int=0, isHuman: bool=False):
        self.name = name
        self.money = money
        self.team = team
        self.fullUnits = []
        self.ownedFactoryTerritories = []
        self.ownedValuedTerritories = []
        self.ownedTerritories = []
        self.territoriesWithUnits = []
        self.allies = []
        self.enemies = []
        self.beachheadSources = []
        self.unloadingConnections = []
        self.capital = None
        self.isHuman = isHuman
    def reset(self):
        self.money = 0
        self.ownedFactoryTerritories: List[Territory] = []
        self.ownedValuedTerritories: List[Territory] = []
        self.ownedTerritories: List[Territory] = []
        if self.capital:
            self.ownedFactoryTerritories.append(self.capital)
            self.ownedValuedTerritories.append(self.capital)
            self.ownedTerritories.append(self.capital)
        self.territoriesWithUnits: List[Territory] = []
    def __str__(self):
        return self.name
    def __repr__(self):
        return str(self)

class UnitType:
    def __init__(self, player: Player, name: str, attack: int, defense: int, maxMoves: int, maxHits: int, cost: int, weight:int=2, maxSupportable:int=0, maxSupported:int=0, isAir:bool=False, bomber:int=0, isWater:bool=False, maxLand:int=0, maxAir:int=0, isSub:bool=False, isAntiSub:bool=False, bombard:int=0, isAA:bool=False):
        self.player = player
        self.name = name
        self.attack = attack
        self.defense = defense
        self.maxMoves = maxMoves
        self.maxHits = maxHits
        self.cost = cost
        self.maxSupportable = maxSupportable
        self.maxSupported = maxSupported
        self.weight = weight
        self.isAir = isAir
        self.bomber = bomber
        self.isWater = isWater
        self.maxLand = maxLand
        self.maxAir = maxAir
        self.isSub = isSub
        self.isAntiSub = isAntiSub
        self.bombard = bombard
        self.isAA = isAA
        self.unitAfterTurn = None
    def __str__(self):
        return(self.name)
    def __repr__(self):
        return(str(self))

class DetailedUnit:
    def __init__(self, unitType: UnitType, movesRemaining: int, hitsRemaining: int, payload: List[UnitType]=[]):
        self.unitType = unitType
        self.movesRemaining = movesRemaining
        self.hitsRemaining = hitsRemaining
        self.payload = payload
        self.unitAfterMove = None
        self.unitAfterHit = None
        self.unitAfterTurn = None
        self.canLoadUnitType = {}
        self.unitAfterLoadUnitType = {}
        self.unitAfterUnload1 = {}
        self.unitAfterUnload2 = {}
        self.unitAfterUnloadBoth = {}
        self.payloadPendingUnload = None
        self.unitAfterUnload = None
        self.payloadHasPlayer = {}

    def __str__(self):
        player = self.unitType.player
        if player:
            string = player.name + ' ' + self.unitType.name + ' Moves: ' + str(self.movesRemaining)
            if self.unitType.maxHits > 1:
                string += ' HP: ' + str(self.hitsRemaining)
            if self.unitType.maxLand > 0:
                string += ' Payload: ' + str(self.payload)
        else:
            string = self.unitType.name
        return string

    def __repr__(self):
        return(str(self))

class Territory:
    def __init__(self, players: List[Player], name: str, allTerritoryUnits: List[DetailedUnit], landValue: int=0, isWater: bool=False, owner: Optional[Player]=None):
        self.name = name
        self.landValue = landValue
        self.isWater = isWater
        self.connections = []
        self.factoryMax = 0
        self.factoryHealth = 0
        self.constructionRemaining = 0
        self.bombardsUsed = 0
        self.owner = owner
        self.unitQuantities = []
        self.getUnitQuantities = {}
        self.waterConnections = []
        self.landConnections = []
        self.adjacentWaterTerritories = []
        self.adjacentLandTerritories = []
        self.adjacentAirTerritories = []
        self.buildableTerritories = [self]
        self.unitQuantitiesForPlayer = {}
        self.planesCanLand = True
        self.originalOwner = None
        if owner:
            self.owner.ownedTerritories.append(self)
            self.originalOwner = owner
        for player in players:
            self.unitQuantitiesForPlayer[player] = []
        if landValue > 0:
            owner.ownedValuedTerritories.append(self)
        for detailedUnit in allTerritoryUnits:
            unitType = detailedUnit.unitType
            if unitType.isAir or unitType.isWater == isWater:
                unitQuantity = UnitQuantity(detailedUnit, territory=self, quantity=0)
                self.unitQuantities.append(unitQuantity)
                self.getUnitQuantities[detailedUnit] = unitQuantity

    def reset(self):
        self.factoryHealth = self.factoryMax
        self.constructionRemaining = self.factoryHealth
        self.owner = self.originalOwner
        for unitQuantities in self.unitQuantitiesForPlayer.values():
            for unitQuantity in unitQuantities:
                unitQuantity.quantity = 0
        for unitQuantities in self.unitQuantitiesForPlayer.values():
            unitQuantities.clear()

    def changeOwner(self, player: Player):
        if player.isHuman:
            print(str(player) + " conquered " + str(self.name))
        oldOwner = self.owner
        oldOwner.ownedTerritories.remove(self)
        if self.landValue > 0:
            oldOwner.ownedValuedTerritories.remove(self)
        if self.factoryMax > 0:
            oldOwner.ownedFactoryTerritories.remove(self)
        for enemy in player.enemies:
            unitQuantities = self.unitQuantitiesForPlayer[enemy]
            for unitQuantity in unitQuantities:
                if unitQuantity.detailedUnit.unitType.isAA:
                    #todo fix hardcoded
                    newAA = None
                    for fullunit in player.fullUnits:
                        if fullunit.unitType.isAA:
                            newAA = fullunit.unitAfterMove
                            break
                    for _ in range(unitQuantity.quantity):
                        self.removeUnit(unitQuantity.detailedUnit)
                        self.addUnit(newAA)
        if self.originalOwner.team == player.team:
            self.owner = self.originalOwner
        else:
            self.owner = player
        self.owner.ownedTerritories.append(self)
        if self.landValue > 0:
            self.owner.ownedValuedTerritories.append(self)
        if self.factoryMax > 0:
            self.owner.ownedFactoryTerritories.append(self)

        if oldOwner.capital == self:
            if player.isHuman:
                print("captured capital")
            player.money += oldOwner.money
            oldOwner.money = 0
        self.planesCanLand = False
        self.constructionRemaining = 0

    def addUnit(self, detailedUnit: DetailedUnit):
        #print("Adding Unit: " + str(detailedUnit) + " to: " + str(self.name))
        unitQuantity = self.getUnitQuantities[detailedUnit]
        detailedUnit = unitQuantity.detailedUnit
        unitQuantity.quantity +=1
        if unitQuantity.quantity == 1:
            player = detailedUnit.unitType.player
            self.unitQuantitiesForPlayer[player].append(unitQuantity)
            if self not in player.territoriesWithUnits:
                player.territoriesWithUnits.append(self)
            payload = detailedUnit.payload
            if len(payload) > 0:
                p0player = detailedUnit.payload[0].unitType.player
                if p0player != detailedUnit.unitType.player:                
                    self.unitQuantitiesForPlayer[p0player].append(unitQuantity)
                    #todo possible bug
                    if self not in p0player.territoriesWithUnits:
                        p0player.territoriesWithUnits.append(self)
                if len(payload) > 1:
                    p1player = detailedUnit.payload[1].unitType.player
                    if p0player == detailedUnit.unitType.player and p1player != detailedUnit.unitType.player:
                        self.unitQuantitiesForPlayer[p1player].append(unitQuantity)
                        #todo possible bug
                        if self not in p1player.territoriesWithUnits:
                            p1player.territoriesWithUnits.append(self)

    def removeUnitQuantityForPlayer(self, player: Player, unitQuantity):
        self.unitQuantitiesForPlayer[player].remove(unitQuantity)
        if len(self.unitQuantitiesForPlayer[player]) == 0:
            player.territoriesWithUnits.remove(self)

    def removeUnit(self, detailedUnit: DetailedUnit):
        #print("Removing Unit: " + str(detailedUnit) + " from: " + str(self.name))
        unitQuantity = self.getUnitQuantities[detailedUnit]
        detailedUnit = unitQuantity.detailedUnit
        unitQuantity.quantity -=1
        if unitQuantity.quantity == 0:
            player = detailedUnit.unitType.player
            self.removeUnitQuantityForPlayer(player, unitQuantity)
            payload = detailedUnit.payload
            if len(payload) > 0:
                p0player = detailedUnit.payload[0].unitType.player
                if p0player != detailedUnit.unitType.player:
                    self.removeUnitQuantityForPlayer(p0player, unitQuantity)
                    if len(self.unitQuantitiesForPlayer[p0player]) == 0:
                        if self in p0player.territoriesWithUnits:
                            p0player.territoriesWithUnits.remove(self)
                if len(payload) > 1:
                    p1player = detailedUnit.payload[1].unitType.player
                    if detailedUnit.payload[0].unitType.player == detailedUnit.unitType.player and p1player != detailedUnit.unitType.player:
                        self.removeUnitQuantityForPlayer(p1player, unitQuantity)
                        if len(self.unitQuantitiesForPlayer[p1player]) == 0:
                            if self in p1player.territoriesWithUnits:
                                p1player.territoriesWithUnits.remove(self)
                
    def addConnection(self, connection) -> None:
        self.connections.append(connection)
        destination = connection.destination
        self.adjacentAirTerritories.append(destination)
        if destination.isWater:
            self.waterConnections.append(connection)
            self.adjacentWaterTerritories.append(destination)
            self.buildableTerritories.append(destination)
        else:
            self.adjacentLandTerritories.append(destination)
            self.landConnections.append(connection)

    def buildFactory(self) -> None:
        self.factoryMax = self.landValue
        self.factoryHealth = self.factoryMax
        self.constructionRemaining = self.factoryHealth
        self.owner.ownedFactoryTerritories.append(self)
    
    def damageFactory(self, damage) -> None:
        self.factoryHealth -= damage
        if self.factoryHealth < 0:
            self.factoryHealth = 0

    def repairFactoryOnePoint(self) -> None:
        self.factoryHealth += 1
        self.constructionRemaining += 1

    def __str__(self):
        string = 'Territory: ' + self.name + "\n"
        if not self.isWater:
            string += 'Owner: ' + str(self.owner) + "\n"
            string += 'Factory: ' + str(self.constructionRemaining) + '/' + str(self.factoryHealth) + '/' + str(self.factoryMax) + "\n"
        for unitQuantity in self.unitQuantities:
            quantity = unitQuantity.quantity
            if quantity > 0:
                string += str(quantity) + ' ' + str(unitQuantity.detailedUnit) + "\n"
        return string

    def __repr__(self):
        return(self.name)

class DestinationTransport:
    def __init__(self, territory: Territory, transportUnit: DetailedUnit=None, unload1: DetailedUnit=None, unload2: DetailedUnit=None):
        self.territory = territory
        self.transportUnit = transportUnit
        self.unload1 = unload1
        self.unload2 = unload2
    def __str__(self):
        string = self.territory.name
        if self.transportUnit:
            string += ' ' + str(self.transportUnit)
        if self.unload1:
            string += ' Unload1: ' + str(self.unload1)
        if self.unload2:
            string += ' Unload2: ' + str(self.unload2)                
        return (string)
    def __repr__(self):
        return (self.territory.name)

class UnitDestinations:
    def __init__(self, detailedUnit: DetailedUnit, destinationTransports: List[DestinationTransport]):
        self.detailedUnit = detailedUnit
        self.destinations = destinationTransports
    def __str__(self):
        return (str(self.detailedUnit) + ' (' + str(len(self.destinations)) + ')')
    def __repr__(self):
        return str(self)

class TerritoryUnitsDestinations:
    def __init__(self, territory: Territory, unitsDestinations: List[UnitDestinations]):
        self.territory = territory
        self.unitsDestinations = unitsDestinations

    def __str__(self):
        string = self.territory.name + ' (' + str(len(self.unitsDestinations)) + ')'
        return string
    def __repr__(self):
        return str(self)

class Connection:
    def __init__(self, source: Territory, destination: Territory, requiredTerritories: List[Territory]=None):
        self.source = source
        self.destination = destination
        self.requiredTerritories = requiredTerritories
        self.unitQuantities = []
        self.getUnitQuantities = {}

    def addTransportTemplates(self, unloadingTransports: List[DetailedUnit]):
        for unloadingTransport in unloadingTransports:
            unitQuantity = UnitQuantity(unloadingTransport, territory=None, quantity=0)
            self.unitQuantities.append(unitQuantity)
            self.getUnitQuantities[unloadingTransport] = unitQuantity

class UnitQuantity:
    def __init__(self, detailedUnit: DetailedUnit, quantity: int, territory: Territory, connection: Connection=None):
        self.detailedUnit = detailedUnit
        self.quantity = quantity
        self.territory = territory
        self.connection = connection

    def __str__(self):
        string = ''
        if self.quantity > 0:
            string += self.detailedUnit.unitType.player.name + " " + self.detailedUnit.unitType.name + ': ' + str(self.quantity)
        return string

class PayloadCount:
    def __init__(self, player: Player, payload: List[DetailedUnit], unload1: bool=False, unload2: bool=False, count: int=0):
        self.player = player
        self.payload = payload
        self.unload1 = unload1
        self.unload2 = unload2
        self.count = count

class DetailedUnitList:
    def __init__(self, player: Player, allDetailedUnits: List[DetailedUnit]):
        self.player = player
        self.detailedUnitList = []
        self.detailedUnitHash = {}
        for detailedUnit in allDetailedUnits:
            unitQuantity = UnitQuantity(detailedUnit, territory=None, quantity=0)
            self.detailedUnitList.append(unitQuantity)
            self.detailedUnitHash[detailedUnit] = self.detailedUnitList[-1]

    def __str__(self):
        string = ''
        for unitQuantity in self.detailedUnitList:
            string2 = str(unitQuantity)
            if string2 != '':
                string += string2 + "\n"
        return string

def connectTerritories(territoryFrom: Territory, territoryTo: Territory, requiredTerritories: List[Territory]=[], isOneWay: bool=False, unloadingTransports: List[DetailedUnit]=None) -> None:
    connection = Connection(territoryFrom, territoryTo, requiredTerritories)
    territoryFrom.addConnection(connection)
    if territoryFrom.isWater and not territoryTo.isWater:
        connection.addTransportTemplates(unloadingTransports)
    if not isOneWay:
        connectTerritories(territoryFrom=territoryTo, territoryTo=territoryFrom, requiredTerritories=requiredTerritories, isOneWay=True, unloadingTransports=unloadingTransports)

def readableStatus(turnOrder, currentTurn, territories) -> str:
    status = 'CurrentTurn: ' + str(turnOrder[currentTurn]) + "\n"
    for territory in territories:
        status += str(territory) + "\n"
    return status

def createDetailedUnits(unitType: UnitType) -> List[DetailedUnit]:
    detailedUnits = []
    for hitsRemaining in range(1, (unitType.maxHits + 1)):
        for movesRemaining in range(0, (unitType.maxMoves + 1)):
            detailedUnit = DetailedUnit(unitType, movesRemaining, hitsRemaining)
            detailedUnits.append(detailedUnit)
    return detailedUnits

factoryUnitType = UnitType(player=None, name="Factory", attack=0, defense=0, maxMoves=0, maxHits=0, cost=15)
factory = DetailedUnit(unitType=factoryUnitType, movesRemaining=0, hitsRemaining=0, payload=None)
repairUnitType = UnitType(player=None, name="Repair", attack=0, defense=0, maxMoves=0, maxHits=0, cost=1)
repair = DetailedUnit(unitType=repairUnitType, movesRemaining=0, hitsRemaining=0, payload=None)

def buyUnits(player) -> None:
    continueBuying = True
    fullUnits = player.fullUnits
    while continueBuying:
        if player.isHuman:
            print('Money: ' + str(player.money))
        buildFromToOption = {}
        territories = player.ownedTerritories
        for territoryIndex in range(len(territories)):
            territory = territories[territoryIndex]
            if territory.constructionRemaining > 0:
                buildToTerritories = territory.buildableTerritories
                for buildTo in buildToTerritories:
                    for fullUnitIndex in range(len(fullUnits)):
                        fullUnit = fullUnits[fullUnitIndex]
                        if fullUnit.unitType.cost <= player.money and (fullUnit.unitType.isAir or fullUnit.unitType.isWater == buildTo.isWater):
                            if territory not in buildFromToOption:
                                buildFromToOption[territory] = {}
                            if buildTo not in buildFromToOption[territory]:
                                buildFromToOption[territory][buildTo] = set()
                            buildFromToOption[territory][buildTo].add(fullUnit)
            if territory.factoryHealth < territory.factoryMax and player.money > 0:
                if territory not in buildFromToOption:
                    buildFromToOption[territory] = {}
                if territory not in buildFromToOption[territory]:
                    buildFromToOption[territory][territory] = set()
                buildFromToOption[territory][territory].add(repair)
            if territory.factoryMax < territory.landValue and player.money >= 15:
                if territory not in buildFromToOption:
                    buildFromToOption[territory] = {}
                if territory not in buildFromToOption[territory]:
                    buildFromToOption[territory][territory] = set()
                buildFromToOption[territory][territory].add(factory)
        if player.isHuman:
            selectionList = []
            for buildFrom in buildFromToOption.values():
                selectionList.append(buildFrom)
                print(str(len(selectionList) - 1) + '. ' + str(buildFrom))
            selection = int(input('Build From: '))
            if selection in range(len(selectionList)):
                buildFrom = selectionList[selection]
                selectionList = []
                for buildTo in buildFromToOption[buildFrom].values():
                    selectionList.append(buildTo)
                    print(str(len(selectionList) - 1) + '. ' + str(buildTo))
                selection = int(input('Build To: '))
                if selection in range(len(selectionList)):
                    buildTo = selectionList[selection]
                    selectionList = []
                    for buildOption in buildFromToOption[buildFrom][buildTo]:
                        selectionList.append(buildOption)
                        print(str(len(selectionList) - 1) + '. ' + str(buildOption))
                    selection = int(input('Build Option: '))
                    if selection in range(len(selectionList)):
                        unitSelected = selectionList[selection]
                    else:
                        continueBuying = False    
                else:
                    continueBuying = False
            else:
                continueBuying = False
        else:
            if len(buildFromToOption) == 0:
                continueBuying = False
            else:
                buildFrom = random.choice(list(buildFromToOption.keys()))
                buildTo = random.choice(list(buildFromToOption[buildFrom].keys()))
                unitSelected = random.choice(list(buildFromToOption[buildFrom][buildTo]))
        if continueBuying:
            player.money -= unitSelected.unitType.cost
            if unitSelected == factory:
                buildFrom.buildFactory()
                buildFrom.constructionRemaining = 0
            elif unitSelected == repair:
                buildFrom.factoryHealth += 1
                buildFrom.constructionRemaining += 1
            else:
                buildFrom.constructionRemaining -= 1
                buildTo.addUnit(unitSelected)

    for territory in territories:
        territory.constructionRemaining = territory.factoryHealth

def collectMoney(player: Player) -> None:
    territories = player.ownedValuedTerritories
    for territory in territories:
        player.money += territory.landValue

def getDestinationTransports(player: Player, destination: Territory, detailedUnit: DetailedUnit) -> List[DestinationTransport]:
    destinationTransports = []
    unitQuantities = destination.unitQuantitiesForPlayer[player]
    for unitQuantity in unitQuantities:
        detailedUnitTransport = unitQuantity.detailedUnit
        #optimize
        if len(detailedUnitTransport.canLoadUnitType) > 0:
            loadUnitType = detailedUnit.unitType
            canLoadUnitType = detailedUnitTransport.canLoadUnitType.get(loadUnitType, False)
            if canLoadUnitType:
                destinationTransport = DestinationTransport(territory=destination, transportUnit=detailedUnitTransport)
                destinationTransports.append(destinationTransport)
    return destinationTransports

def getUnitDestinations(player: Player, territoryFrom: Territory, detailedUnit: DetailedUnit, combatAllowed:bool=True) -> UnitDestinations:
    unitType = detailedUnit.unitType
    destinationTransports = []
    if unitType.isAir:
        adjacentAirTerritories = territoryFrom.adjacentAirTerritories
        for destination in adjacentAirTerritories:
            destinationTransport = DestinationTransport(destination)
            destinationTransports.append(destinationTransport)
    elif unitType.isWater:
        waterConnections = territoryFrom.waterConnections
        for connection in waterConnections:
            destination = connection.destination
            if unitType.player == player:
                requiredTerritories = connection.requiredTerritories
                requirementsMet = True
                #optimize
                for requiredTerritory in requiredTerritories:
                    if requiredTerritory.owner.team != detailedUnit.player.team:
                        requirementsMet = False
                        break
                if requirementsMet:
                    enemyUnits = getEnemyUnitsInTerritory(player, destination)
                    if unitsRemaining(enemyUnits) == 0 or combatAllowed:
                        destinationTransport = DestinationTransport(destination)
                        destinationTransports.append(destinationTransport)
        if len(detailedUnit.payload) > 0:
            # unload transport
            payload = detailedUnit.payload
            loadedUnit1 = payload[0]
            for connection in territoryFrom.landConnections:
                destination = connection.destination
                enemyUnits = getEnemyUnitsInTerritory(player, destination)
                if unitsRemaining(enemyUnits) == 0 or combatAllowed:
                    if loadedUnit1.unitType.player == player:
                        destinationTransport = DestinationTransport(territory=destination, unload1=loadedUnit1)
                        destinationTransports.append(destinationTransport)
                    if len(payload) > 1:
                        loadedUnit2 = payload[1]
                        if loadedUnit2.unitType.player == player:
                            destinationTransport = DestinationTransport(territory=destination, unload2=loadedUnit2)
                            destinationTransports.append(destinationTransport)
                            if loadedUnit1.unitType.player == player:
                                destinationTransport = DestinationTransport(territory=destination, unload1=loadedUnit1, unload2=loadedUnit2)
                                destinationTransports.append(destinationTransport)
    else:
        for destination in territoryFrom.adjacentLandTerritories:
            # land unit to land territory
            enemyUnits = getEnemyUnitsInTerritory(player, destination)
            if (unitsRemaining(enemyUnits) == 0 and destination.owner.team == player.team) or combatAllowed:
                destinationTransport = DestinationTransport(destination)
                destinationTransports.append(destinationTransport)
        for destination in territoryFrom.adjacentWaterTerritories:
            # land unit to water
            playerDestinationTransports = getDestinationTransports(player=player, destination=destination, detailedUnit=detailedUnit)
            destinationTransports.extend(playerDestinationTransports)
            for ally in player.allies:
                allyDestinationTransports = getDestinationTransports(player=ally, destination=destination, detailedUnit=detailedUnit)
                destinationTransports.extend(allyDestinationTransports)
    unitDestinations = None
    if len(destinationTransports) > 0:
        unitDestinations = UnitDestinations(detailedUnit, destinationTransports)
    return(unitDestinations)

def getTerritoryUnitsDestinations(player, territory, combatAllowed:bool=True) -> TerritoryUnitsDestinations:
    unitsDestinations = []
    unitQuantities = territory.unitQuantitiesForPlayer[player]
    for unitQuantity in unitQuantities:
        detailedUnit = unitQuantity.detailedUnit
        if detailedUnit.movesRemaining > 0 and (not detailedUnit.unitType.isAA or not combatAllowed):
            unitDestinations = getUnitDestinations(player, territory, detailedUnit, combatAllowed)
            if unitDestinations:
                unitsDestinations.append(unitDestinations)
    territoryUnitsDestinations = None
    if len(unitsDestinations) > 0:
        territoryUnitsDestinations = TerritoryUnitsDestinations(territory, unitsDestinations)
    return territoryUnitsDestinations

def boardTransport(destinationTransport: DestinationTransport, boardingUnit: DetailedUnit):    
    transportUnit = destinationTransport.transportUnit
    newTransportUnit = transportUnit.unitAfterLoadUnitType[boardingUnit.unitType]
    destination = destinationTransport.territory
    destination.removeUnit(transportUnit)
    destination.addUnit(newTransportUnit)

def unloadTransport(moveFrom: Territory, detailedUnit: DetailedUnit, destinationTransport: DestinationTransport):
    moveFrom.removeUnit(detailedUnit)
    unloadingTransport = None
    player = None
    if destinationTransport.unload1:
        player = destinationTransport.unload1.unitType.player
        if destinationTransport.unload2:
            unloadingTransport = detailedUnit.unitAfterUnloadBoth
        else:
            unloadingTransport = detailedUnit.unitAfterUnload1
    elif destinationTransport.unload2:
        player = destinationTransport.unload2.unitType.player
        unloadingTransport = detailedUnit.unitAfterUnload2
    #optimize
    for connection in moveFrom.waterConnections:
        if connection.destination == destinationTransport.territory:
            unitQuantity = connection.getUnitQuantities[unloadingTransport]
            unitQuantity.quantity += 1
            player.beachheadSources.append(moveFrom)
            player.unloadingConnections.append(connection)
            break

def moveUnit(player: Player, moveFrom: Territory, detailedUnit: DetailedUnit, destinationTransport: DestinationTransport):
    if not destinationTransport.unload1 and not destinationTransport.unload2:
        moveFrom.removeUnit(detailedUnit)
    else:
        unloadTransport(moveFrom=moveFrom, detailedUnit=detailedUnit, destinationTransport=destinationTransport)
    if destinationTransport.transportUnit:
        boardTransport(destinationTransport, detailedUnit)
    elif not destinationTransport.unload1 and not destinationTransport.unload2:
        moveTo = destinationTransport.territory
        newUnit = detailedUnit.unitAfterMove
        enemyUnits = getEnemyUnitsInTerritory(player, moveTo)
        if unitsRemaining(enemyUnits) > 0:
            while(newUnit.movesRemaining > 0):
                newUnit = newUnit.unitAfterMove
        else:
            if moveTo.owner:
                if moveTo.owner.team != player.team and not newUnit.unitType.isAir:
                    moveTo.changeOwner(player)
        moveTo.addUnit(newUnit)
                

def resetUnitsFully(player: Player) -> None:
    for territory in player.ownedTerritories:
        territory.planesCanLand = True
    for territory in player.territoriesWithUnits:
        unitQuantities = territory.unitQuantitiesForPlayer[player]
        for unitQuantity in set(unitQuantities):
            detailedUnit = unitQuantity.detailedUnit
            if detailedUnit.unitAfterTurn != detailedUnit:
                for _ in range(unitQuantity.quantity):
                    territory.removeUnit(detailedUnit)
                    territory.addUnit(detailedUnit.unitAfterTurn)

class MoveOption:
    def __init__(self, moveFrom: Territory, selectedUnit: DetailedUnit, moveTo: DestinationTransport):
        self.moveFrom = moveFrom
        self.selectedUnit = selectedUnit
        self.moveTo = moveTo

def giveMoveOrders(player: Player, combatAllowed: bool=True) -> None:
    player.beachheadSources.clear()
    continueMovements = True
    while continueMovements:
        territories = player.territoriesWithUnits
        moveFromOptions = []
        allMoveFromOptions = []
        #optimize
        for territory in territories:
            territoryUnitsDestinations = getTerritoryUnitsDestinations(player, territory, combatAllowed)
            if territoryUnitsDestinations:
                if len(territoryUnitsDestinations.unitsDestinations) > 0:
                    #if territoryUnitsDestinations not in moveFromOptions:
                    moveFromOptions.append(territoryUnitsDestinations)
                    for unitDestination in territoryUnitsDestinations.unitsDestinations:
                        selectedUnit = unitDestination.detailedUnit
                        destinations = unitDestination.destinations
                        for destination in destinations:
                            moveOption = MoveOption(moveFrom=territory, selectedUnit=selectedUnit, moveTo=destination)
                            allMoveFromOptions.append(moveOption)
        print(allMoveFromOptions)
        if player.isHuman:
            for moveFromIndex in range(len(moveFromOptions)):
                print(str(moveFromIndex) + '. ' + str(moveFromOptions[moveFromIndex]))
            selection = int(input('Move From: '))
        else:
            maxRand = len(moveFromOptions) - 1
            if maxRand < 0:
                maxRand = 0
            selection = random.randint(0,maxRand)
            if random.randint(0,10) == 0:
                selection = -1
        if selection in range(len(moveFromOptions)):
            moveFrom = moveFromOptions[selection]
            unitsDestinations = moveFrom.unitsDestinations
            if player.isHuman:
                for unitDestinationIndex in range(len(unitsDestinations)):
                    unitDestination = unitsDestinations[unitDestinationIndex]
                    detailedUnit = unitDestination.detailedUnit
                    print(str(unitDestinationIndex) + '. ' + str(detailedUnit))
                selection = int(input('Select Unit: '))
            else:
                maxRand = len(unitsDestinations) - 1
                if maxRand < 0:
                    maxRand = 0
                selection = random.randint(0,maxRand)
            if selection in range(len(unitsDestinations)):
                unitDestination = unitsDestinations[selection]
                destinations = unitDestination.destinations
                if player.isHuman:
                    for destinationIndex in range(len(destinations)):
                        destination = destinations[destinationIndex]
                        print(str(destinationIndex) + '. ' + str(destination))
                    selection = int(input('Move To: '))
                else:
                    maxRand = len(destinations) - 1
                    if maxRand < 0:
                        maxRand = 0
                    selection = random.randint(0,maxRand)
                if selection in range(len(destinations)):
                    destination = destinations[selection]
                    moveUnit(player, moveFrom.territory, unitDestination.detailedUnit, destination)
                else:
                    continueMovements = False
            else:
                continueMovements = False
        else:
            continueMovements = False

def intersection(lst1, lst2): 
    # optimize
    lst3 = [value for value in lst1 if value in lst2] 
    return lst3 

def getConflictedTerritories(player: Player) -> List[Territory]:
    beachheadSources = player.beachheadSources
    territoriesWithUnits = player.territoriesWithUnits
    territoriesWithUnits.extend(beachheadSources)
    enemyTerrritories = []
    for enemy in player.enemies:
        enemyTerrritories.extend(enemy.territoriesWithUnits)
    conflictedTerritories = intersection(territoriesWithUnits, enemyTerrritories)
    return conflictedTerritories

def getConflictedSeaTerritories(player: Player) -> List[Territory]:
    conflictedTerritories = getConflictedTerritories(player=player)
    conflictedSeaTerritories = []
    for territory in conflictedTerritories:
        if territory.isWater:
            conflictedSeaTerritories.append(territory)
    return conflictedSeaTerritories

def getConflictedLandTerritories(player: Player) -> List[Territory]:
    conflictedTerritories = getConflictedTerritories(player=player)
    conflictedSeaTerritories = []
    for territory in conflictedTerritories:
        if not territory.isWater:
            conflictedSeaTerritories.append(territory)
    return conflictedSeaTerritories

def getFriendlyUnitsInSea(player: Player, territory: Territory) -> List[UnitQuantity]:
    friendlyUnitQuantities = []
    friendlyUnitQuantities.extend(territory.unitQuantitiesForPlayer[player])
    for ally in player.allies:
        friendlyUnitQuantities.extend(territory.unitQuantitiesForPlayer[ally])
    for connection in territory.connections:
        for unitQuantity in connection.unitQuantities:
            if unitQuantity.quantity > 0:
                friendlyUnitQuantities.append(unitQuantity)
    return friendlyUnitQuantities
            
def getEnemyUnitsInTerritory(player: Player, territory: Territory) -> List[UnitQuantity]:
    enemyUnitQuantities = []
    for enemy in player.enemies:
        enemyUnitQuantities.extend(territory.unitQuantitiesForPlayer[enemy])
    return enemyUnitQuantities

def fireForHits(unitQuantities: List[UnitQuantity], numberOfBombersToBomb: int=0, useDefense: bool=False, subsTurn: bool=False) -> int:
    hits = 0
    for unitQuantity in unitQuantities:
        unitType = unitQuantity.detailedUnit.unitType
        if unitType.isSub == subsTurn:
            quantity = unitQuantity.quantity
            if unitType.bomber > 0:
                quantity -= numberOfBombersToBomb
            if quantity > 0:
                if player.isHuman:
                    print("firing: " + str(unitType) + " x" + str(quantity)) 
                fireValue = unitType.attack
                if useDefense:
                    fireValue = unitType.defense
                for _ in range(quantity):
                    if random.randint(1,6) <= fireValue:
                        hits +=1
    if player.isHuman:
        print(str(hits) + " hit(s)")
    return hits

def fireDefense(unitQuantities: List[UnitQuantity], subsTurn: bool=False) -> int:
    hits = 0
    for unitQuantity in unitQuantities:
        unitType = unitQuantity.detailedUnit.unitType
        if unitType.isSub == subsTurn:
            if random.randint(1,6) <= unitType.defense:
                hits +=1
    return hits

def removeCasualty(unitQuantities: List[UnitQuantity], numberOfBombersToBomb:int=0, onlyNonAir: bool=False, submerged: bool=False) -> None:
    # change from automatic to ask
    cheapestUnitQuantity = None
    cheapestUnitValue = 999
    for unitQuantity in unitQuantities:
        detailedUnit = unitQuantity.detailedUnit
        unitType = detailedUnit.unitType
        if not unitType.isAA and (not onlyNonAir or not unitType.isAir) and (not submerged or not unitType.isSub):
            if unitType.bomber == 0 or numberOfBombersToBomb < unitQuantity.quantity:
                unitValue = unitType.cost
                payload = detailedUnit.payload
                if len(payload) > 0:
                    for loadedUnit in payload:
                        unitValue += loadedUnit.unitType.cost
                if detailedUnit.hitsRemaining > 1:
                    unitValue = 0
                if unitValue < cheapestUnitValue:
                    cheapestUnitValue = unitValue
                    cheapestUnitQuantity = unitQuantity
    if cheapestUnitQuantity:
        if player.isHuman:
            print("removing unit:" + str(cheapestUnitQuantity.detailedUnit))
        if cheapestUnitQuantity.territory:
            cheapestUnitQuantity.territory.removeUnit(cheapestUnitQuantity.detailedUnit)
            if cheapestUnitQuantity.detailedUnit.hitsRemaining > 1:
                cheapestUnitQuantity.territory.addUnit(cheapestUnitQuantity.detailedUnit.unitAfterHit)
        else:
            cheapestUnitQuantity.quantity -= 1

def unitsRemaining(unitQuantities: List[UnitQuantity], numberOfBombersToBomb: int=0, onlyNonAir: bool=False, submerged:bool=False) -> int:
    unitsRemaining = 0
    for unitQuantity in unitQuantities:
        unitType = unitQuantity.detailedUnit.unitType
        if not unitType.isAA and (not onlyNonAir or not unitType.isAir) and (not submerged or not unitType.isSub):
            unitsRemaining += unitQuantity.quantity
    return unitsRemaining - numberOfBombersToBomb

def askSubmergeSubs(friendlyUnits: List[UnitQuantity], enemyUnits: List[UnitQuantity]) -> bool:
    response = False
    destroyersExist = False
    for friendlyUnit in friendlyUnits:
        if friendlyUnit.detailedUnit.unitType.isAntiSub:
            destroyersExist = True
            break
    if destroyersExist == False:
        for enemyUnit in enemyUnits:
            if enemyUnit.detailedUnit.unitType.isSub:
                if player.isHuman:
                    print("Submerging Subs") # ask question instead of default yes
                if random.randint(0, 1) == True:
                    response = True
                else:
                    response = False
            break
    return response

def askRetreat(friendlyUnits: List[UnitQuantity], enemyUnits: List[UnitQuantity]) -> bool:
    if player.isHuman:
        print("Never Retreat") # ask question instead of default yes
    #ask for each unit where to retreat to
    if random.randint(0,3) == 0:
        response = True
    else:
        response = False
    return response

def resolveSeaCombat(player: Player) -> None:
    #optimize
    conflictedSeaTerritories = getConflictedSeaTerritories(player)
    for conflictedSeaTerritory in conflictedSeaTerritories:
        continueFighting = True
        submerged = False
        while continueFighting:
            friendlyUnits = getFriendlyUnitsInSea(player, conflictedSeaTerritory)
            enemyUnits = getEnemyUnitsInTerritory(player, conflictedSeaTerritory)
            for friendlyUnitQuantity in friendlyUnits:
                if player.isHuman:
                    print(str(friendlyUnitQuantity))
            for enemyUnitQuantity in enemyUnits:
                if player.isHuman:
                    print(str(enemyUnitQuantity))
            friendlyHits = fireForHits(unitQuantities=friendlyUnits, subsTurn=True)
            if submerged:
                if player.isHuman:
                    print("subs are submerged")
                enemyHits = 0
            else:
                enemyHits = fireForHits(unitQuantities=enemyUnits, useDefense=True, subsTurn=True)
            while friendlyHits > 0 and unitsRemaining(unitQuantities=enemyUnits, onlyNonAir=True) > 0:
                removeCasualty(unitQuantities=enemyUnits, onlyNonAir=True, submerged=submerged)
                enemyUnits = getEnemyUnitsInTerritory(player, conflictedSeaTerritory)
                friendlyHits -=1
            while enemyHits > 0 and unitsRemaining(unitQuantities=friendlyUnits, onlyNonAir=True) > 0:
                removeCasualty(unitQuantities=friendlyUnits, onlyNonAir=True)
                friendlyUnits = getFriendlyUnitsInSea(player, conflictedSeaTerritory)
                enemyHits -=1
            friendlyHits = fireForHits(friendlyUnits)
            enemyHits = fireForHits(enemyUnits, useDefense=True)
            while friendlyHits > 0 and unitsRemaining(enemyUnits) > 0:
                removeCasualty(enemyUnits, submerged=submerged)
                enemyUnits = getEnemyUnitsInTerritory(player, conflictedSeaTerritory)
                friendlyHits -= 1
            while enemyHits > 0 and unitsRemaining(friendlyUnits) > 0:
                removeCasualty(friendlyUnits)
                friendlyUnits = getFriendlyUnitsInSea(player, conflictedSeaTerritory)
                enemyHits -= 1
            if submerged == False:
                submerged = askSubmergeSubs(friendlyUnits, enemyUnits)
            retreatDecision = askRetreat(friendlyUnits, enemyUnits)
            continueFighting = not retreatDecision and unitsRemaining(friendlyUnits) > 0 and unitsRemaining(enemyUnits, submerged=submerged) > 0
        friendlyUnits = conflictedSeaTerritory.unitQuantitiesForPlayer[player]
        for friendlyUnit in set(friendlyUnits):
            newUnit = friendlyUnit.detailedUnit
            if not newUnit.unitType.isAir and newUnit.movesRemaining > 0:
                while(newUnit.movesRemaining > 0):
                    newUnit = newUnit.unitAfterMove
                for _ in range(friendlyUnit.quantity):
                    conflictedSeaTerritory.removeUnit(friendlyUnit.detailedUnit)
                    conflictedSeaTerritory.addUnit(newUnit)

def getBombers(friendlyUnits: List[UnitQuantity]) -> int:
    bombers = 0
    for unitQuantity in friendlyUnits:
        if unitQuantity.detailedUnit.unitType.bomber > 0:
            bombers += unitQuantity.quantity
    return bombers

def resolveLandCombat(player: Player) -> None:
    #optimize
    conflictedLandTerritories = getConflictedLandTerritories(player)
    for conflictedLandTerritory in conflictedLandTerritories:
        continueFighting = True
        friendlyUnits = conflictedLandTerritory.unitQuantitiesForPlayer[player]
        enemyUnits = getEnemyUnitsInTerritory(player, conflictedLandTerritory)
        #optimize
        for enemyUnit in enemyUnits:
            if enemyUnit.detailedUnit.unitType.isAA:
                if player.isHuman:
                    print("Firing AntiAir")
                for friendlyUnit in friendlyUnits:
                    if friendlyUnit.detailedUnit.unitType.isAir:
                        for _ in range(friendlyUnit.quantity):
                            if random.randint(1,6) <= 1:
                                if player.isHuman:
                                    print("Antiair hit!")
                                conflictedLandTerritory.removeUnit(friendlyUnit.detailedUnit)
                break
        numberOfBombersToBomb = 0
        if conflictedLandTerritory.constructionRemaining > 0:
            #ask
            numberOfBombersToBomb = getBombers(friendlyUnits)
        for _ in range(numberOfBombersToBomb):
            #optimize safety
            damage = random.randint(1,6)
            conflictedLandTerritory.factoryHealth -= damage
            conflictedLandTerritory.constructionRemaining -= damage
            if player.isHuman:
                print("bombed: " + str(conflictedLandTerritory.name) + ' for ' + str(damage) + ' damage')
        if conflictedLandTerritory.factoryHealth < 0: 
            conflictedLandTerritory.factoryHealth = 0
            conflictedLandTerritory.constructionRemaining = 0

        while continueFighting:
            friendlyHits = fireForHits(friendlyUnits, numberOfBombersToBomb=numberOfBombersToBomb)
            enemyHits = fireForHits(enemyUnits, useDefense=True)
            while friendlyHits > 0 and unitsRemaining(enemyUnits) > 0:
                removeCasualty(enemyUnits)
                enemyUnits = getEnemyUnitsInTerritory(player, conflictedLandTerritory)
                friendlyHits -= 1
            while enemyHits > 0 and unitsRemaining(friendlyUnits, numberOfBombersToBomb=numberOfBombersToBomb) > 0:
                removeCasualty(friendlyUnits, numberOfBombersToBomb=numberOfBombersToBomb)
                friendlyUnits = conflictedLandTerritory.unitQuantitiesForPlayer[player]
                enemyHits -= 1
            retreatDecision = askRetreat(friendlyUnits, enemyUnits)
            continueFighting = not retreatDecision and unitsRemaining(friendlyUnits, numberOfBombersToBomb=numberOfBombersToBomb) > 0 and unitsRemaining(enemyUnits) > 0
        if retreatDecision:
            if player.isHuman:
                print("retreat implement todo")
        elif unitsRemaining(friendlyUnits, onlyNonAir=True) > 0:
            conflictedLandTerritory.changeOwner(player)


def resolveBombards(player: Player) -> None:
    for unloadingConnection in player.unloadingConnections:
        unloadedUnitQuantity = 0
        for unitQuantity in unloadingConnection.unitQuantities:
            unloadedUnitQuantity += unitQuantity.quantity
        seaTerritoryFrom = unloadingConnection.source        
        battleShipsToSkip = seaTerritoryFrom.bombardsUsed
        destination = unloadingConnection.destination
        enemyUnits = getEnemyUnitsInTerritory(player, unloadingConnection.destination)
        for unitQuantity in seaTerritoryFrom.unitQuantitiesForPlayer[player]:
            bombardValue = unitQuantity.detailedUnit.unitType.bombard
            if unitQuantity.detailedUnit.unitType.bombard > 0:
                if battleShipsToSkip > 0:
                    battleShipsToSkip -= 1
                    #todo: ask bombard
                elif unitsRemaining(enemyUnits) > 0:
                    seaTerritoryFrom.bombardsUsed += 1
                    if player.isHuman:
                        print("bombarding: " + str(destination))
                    if random.randint(1,6) <= bombardValue:
                        if player.isHuman:
                            print("bombard hit!")
                        removeCasualty(unitQuantities=enemyUnits)
    for unloadingConnection in player.unloadingConnections:
        unloadingConnection.source.bombardsUsed = 0

def unloadTransports2(player: Player):
    for unloadingConnection in player.unloadingConnections:
        for unitQuantity in unloadingConnection.unitQuantities:
            if unitQuantity.quantity > 0:
                transportUnit = unitQuantity.detailedUnit
                destination = unloadingConnection.destination
                for boardedUnit in transportUnit.payload:
                    destination.addUnit(boardedUnit)
                source = unloadingConnection.source
                source.addUnit(transportableUnit.unitAfterUnload)
                unitQuantity.quantity -= 1
    player.unloadingConnections.clear()
    player.beachheadSources.clear()

def crashPlanes(player: Player):
    territories = player.territoriesWithUnits
    for territory in territories:
        if not territory.owner or territory.owner.team != player.team or not territory.planesCanLand:
            unitQuantities = territory.unitQuantitiesForPlayer[player]
            for unitQuantity in unitQuantities:
                detailedUnit = unitQuantity.detailedUnit
                if detailedUnit.unitType.isAir:
                    for _ in range(unitQuantity.quantity):
                        if player.isHuman:
                            print(str(unitQuantity) + " crashed in " + str(territory))
                        territory.removeUnit(detailedUnit)

random.seed()
rusPlayer = Player(name='Player1Rus', money=10, team=1)
gerPlayer = Player(name='Player2Ger', money=10, team=2)
engPlayer = Player(name='Player3Eng', money=10, team=1)
japPlayer = Player(name='Player4Jap', money=10, team=2)
turnOrder = [rusPlayer, gerPlayer, engPlayer, japPlayer]
rusPlayer.allies.append(engPlayer)
engPlayer.allies.append(rusPlayer)
gerPlayer.allies.append(japPlayer)
japPlayer.allies.append(gerPlayer)
rusPlayer.enemies.append(gerPlayer)
rusPlayer.enemies.append(japPlayer)
engPlayer.enemies.append(gerPlayer)
engPlayer.enemies.append(japPlayer)
gerPlayer.enemies.append(rusPlayer)
gerPlayer.enemies.append(engPlayer)
japPlayer.enemies.append(rusPlayer)
japPlayer.enemies.append(engPlayer)

unitTypes = []
for player in turnOrder:
    unitTypes.append(UnitType(player=player, name='Infantry', attack=1, defense=2, maxMoves=1, maxHits=1, cost=3, maxSupportable=1))
    unitTypes.append(UnitType(player=player, name='Artillery', attack=2, defense=2, maxMoves=1, maxHits=1, cost=4, weight=3, maxSupported=1))
    unitTypes.append(UnitType(player=player, name='Armor', attack=3, defense=3, maxMoves=2, maxHits=1, cost=5, weight=3))
    unitTypes.append(UnitType(player=player, name='Fighter', attack=3, defense=4, maxMoves=4, maxHits=1, cost=10, isAir=True))
    unitTypes.append(UnitType(player=player, name='Bomber', attack=4, defense=1, maxMoves=6, maxHits=1, cost=15, isAir=True, weight=5, bomber=4))
    unitTypes.append(UnitType(player=player, name='Submarine', attack=2, defense=2, maxMoves=2, maxHits=1, cost=8, isWater=True, isSub=True))
    unitTypes.append(UnitType(player=player, name='Carrier', attack=1, defense=3, maxMoves=2, maxHits=1, cost=16, isWater=True, maxAir=5))
    unitTypes.append(UnitType(player=player, name='Destroyer', attack=3, defense=3, maxMoves=2, maxHits=1, cost=12, isWater=True, isAntiSub=True))
    unitTypes.append(UnitType(player=player, name='Battleship', attack=4, defense=4, maxMoves=2, maxHits=2, cost=24, isWater=True, bombard=4))
    unitTypes.append(UnitType(player=player, name='AntiAir', attack=0, defense=0, maxMoves=1, maxHits=1, cost=5, weight=3, isAA=True))
    unitTypes.append(UnitType(player=player, name='Transport', attack=0, defense=1, maxMoves=2, maxHits=1, cost=8, isWater=True, maxLand=5))

allUnloadedUnits = []
for unitType in unitTypes:
    newDetailedUnits = createDetailedUnits(unitType=unitType)
    allUnloadedUnits.extend(newDetailedUnits)

for unloadedUnit in allUnloadedUnits:
    unitType = unloadedUnit.unitType    
    if unloadedUnit.movesRemaining == unitType.maxMoves and unloadedUnit.hitsRemaining == unitType.maxHits:
        unitType.player.fullUnits.append(unloadedUnit)

emptyTransports = []
largestTransportCapacity = 0
for detailedUnit in allUnloadedUnits:
    unitType = detailedUnit.unitType
    maxLand = unitType.maxLand
    if maxLand > 0:
        emptyTransports.append(detailedUnit)
        if largestTransportCapacity < maxLand:
            largestTransportCapacity = maxLand

transportableUnitsWithZeroMoves = []
for detailedUnit in allUnloadedUnits:
    unitType = detailedUnit.unitType
    if not unitType.isAir and not unitType.isWater and detailedUnit.movesRemaining == 0:
        transportableUnitsWithZeroMoves.append(detailedUnit)

payloads = []
payloadOnes = []
payloadTwos = []
payloadOneDict = {}

for transportableIndex in range(len(transportableUnitsWithZeroMoves)):
    transportableUnit = transportableUnitsWithZeroMoves[transportableIndex]
    unitType = transportableUnit.unitType
    if unitType.weight <= largestTransportCapacity:
        loadedUnitTypes = [transportableUnit]
        payloads.append(loadedUnitTypes)
        payloadOnes.append(loadedUnitTypes)
        payloadOneDict[transportableUnit] = loadedUnitTypes
        for transportableIndex2 in range(transportableIndex, len(transportableUnitsWithZeroMoves)):
            transportableUnit2 = transportableUnitsWithZeroMoves[transportableIndex2]
            unitType2 = transportableUnit2.unitType
            if unitType.weight + unitType2.weight <= largestTransportCapacity and unitType.player.team == unitType2.player.team:
                loadedUnitTypes = [transportableUnit, transportableUnit2]
                payloads.append(loadedUnitTypes)
                payloadTwos.append(loadedUnitTypes)

payloadOneTransports = []
unloadingTransports = []
for emptyTransport in emptyTransports:
    transportUnitType = emptyTransport.unitType
    for payloadOne in payloadOnes:
        transportableUnit = payloadOne[0]
        transportableUnitType = transportableUnit.unitType
        if transportUnitType.player.team == transportableUnitType.player.team:
            canLoadUnitType = transportUnitType.maxLand >= transportableUnitType.weight
            emptyTransport.canLoadUnitType[transportableUnitType] = canLoadUnitType
            if canLoadUnitType:
                loadedTransport = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining, payload=payloadOne)
                payloadOneTransports.append(loadedTransport)
                loadedTransport.payloadHasPlayer[transportableUnitType.player] = True
                emptyTransport.unitAfterLoadUnitType[transportableUnitType] = loadedTransport
                unloadingTransport = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining, payload=payloadOne)
                loadedTransport.unitAfterUnload1 = unloadingTransport
                unloadingTransport.payloadPendingUnload = payloadOne
                unloadingTransport.unitAfterUnload = emptyTransport
                unloadingTransports.append(unloadingTransport)

payloadTwoTransports = []
for emptyTransport in emptyTransports:
    transportUnitType = emptyTransport.unitType
    for payloadTwo in payloadTwos:
        transportableUnit1 = payloadTwo[0]
        transportableUnitType1 = transportableUnit1.unitType
        if transportUnitType.player.team == transportableUnitType1.player.team:
            if emptyTransport.canLoadUnitType[transportableUnitType1]:
                transportLoadedWithUnit1 = emptyTransport.unitAfterLoadUnitType[transportableUnitType1]
                transportableUnit2 = payloadTwo[1]
                transportableUnitType2 = transportableUnit2.unitType
                canLoadUnitType2 = transportUnitType.maxLand >= transportableUnitType1.weight + transportableUnitType2.weight
                transportLoadedWithUnit1.canLoadUnitType[transportableUnitType2] = canLoadUnitType2
                if canLoadUnitType2:
                    loadedTransport = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining, payload=payloadTwo)
                    payloadTwoTransports.append(loadedTransport)
                    transportLoadedWithUnit1.unitAfterLoadUnitType[transportableUnitType2] = loadedTransport

                    unloadingTransportBoth = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining, payload=payloadTwo)
                    unloadingTransportBoth.unitAfterUnload = emptyTransport
                    unloadingTransportBoth.payloadPendingUnload = payloadTwo
                    loadedTransport.unitAfterUnloadBoth = unloadingTransportBoth
                    unloadingTransports.append(unloadingTransportBoth)
                    
                    unloadingTransport1 = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining, payload=payloadTwo)
                    unloadingTransport1.unitAfterUnload = emptyTransport.unitAfterLoadUnitType[transportableUnitType2]
                    unloadingTransport1.payloadPendingUnload = payloadOneDict[transportableUnit1]
                    loadedTransport.unitAfterUnload1 = unloadingTransport1
                    unloadingTransports.append(unloadingTransport1)
                    
                    unloadingTransport2 = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining, payload=payloadTwo)
                    unloadingTransport2.unitAfterUnload = emptyTransport.unitAfterLoadUnitType[transportableUnitType1]
                    unloadingTransport2.payloadPendingUnload = payloadOneDict[transportableUnit2]
                    loadedTransport.unitAfterUnload2 = unloadingTransport2
                    unloadingTransports.append(unloadingTransport2)

#optimize
for detailedUnit in allUnloadedUnits:
    for detailedUnit2 in allUnloadedUnits:
        if detailedUnit2.unitType == detailedUnit.unitType:
            if detailedUnit2.movesRemaining == detailedUnit.movesRemaining:
                if detailedUnit2.hitsRemaining == detailedUnit.hitsRemaining - 1:
                    detailedUnit.unitAfterHit = detailedUnit2
            elif detailedUnit2.movesRemaining == detailedUnit.movesRemaining - 1 and detailedUnit2.hitsRemaining == detailedUnit.hitsRemaining:
                detailedUnit.unitAfterMove = detailedUnit2
            if detailedUnit2.movesRemaining == detailedUnit.unitType.maxMoves and detailedUnit2.hitsRemaining == detailedUnit.unitType.maxHits:
                detailedUnit.unitAfterTurn = detailedUnit2

for detailedUnit in payloadOneTransports:
    for detailedUnit2 in payloadOneTransports:
        if detailedUnit2.unitType == detailedUnit.unitType and detailedUnit.payload == detailedUnit2.payload:
            if detailedUnit2.movesRemaining == detailedUnit.movesRemaining:
                if detailedUnit2.hitsRemaining == detailedUnit.hitsRemaining - 1:
                    detailedUnit.unitAfterHit = detailedUnit2
            elif detailedUnit2.movesRemaining == detailedUnit.movesRemaining - 1 and detailedUnit2.hitsRemaining == detailedUnit.hitsRemaining:
                detailedUnit.unitAfterMove = detailedUnit2
            if detailedUnit2.movesRemaining == detailedUnit.unitType.maxMoves and detailedUnit2.hitsRemaining == detailedUnit.unitType.maxHits:
                detailedUnit.unitAfterTurn = detailedUnit2

for detailedUnit in payloadTwoTransports:
    for detailedUnit2 in payloadTwoTransports:
        if detailedUnit2.unitType == detailedUnit.unitType and detailedUnit.payload == detailedUnit2.payload:
            if detailedUnit2.movesRemaining == detailedUnit.movesRemaining:
                if detailedUnit2.hitsRemaining == detailedUnit.hitsRemaining - 1:
                    detailedUnit.unitAfterHit = detailedUnit2
            elif detailedUnit2.movesRemaining == detailedUnit.movesRemaining - 1 and detailedUnit2.hitsRemaining == detailedUnit.hitsRemaining:
                detailedUnit.unitAfterMove = detailedUnit2
            if detailedUnit2.movesRemaining == detailedUnit.unitType.maxMoves and detailedUnit2.hitsRemaining == detailedUnit.unitType.maxHits:
                detailedUnit.unitAfterTurn = detailedUnit2

allTerritoryUnits = []
allTerritoryUnits.extend(allUnloadedUnits)
allTerritoryUnits.extend(payloadOneTransports)
allTerritoryUnits.extend(payloadTwoTransports)

currentTurn = 0

rusTer = Territory(players=turnOrder, name='Russia', allTerritoryUnits=allTerritoryUnits, landValue=10, owner=rusPlayer)
rusPlayer.capital = rusTer
gerTer = Territory(players=turnOrder, name='Germany', allTerritoryUnits=allTerritoryUnits, landValue=10, owner=gerPlayer)
gerPlayer.capital = gerTer
engTer = Territory(players=turnOrder, name='United Kingdom', allTerritoryUnits=allTerritoryUnits, landValue=10, owner=engPlayer)
engPlayer.capital = engTer
japTer = Territory(players=turnOrder, name='Japan', allTerritoryUnits=allTerritoryUnits, landValue=10, owner=japPlayer)
japPlayer.capital = japTer

rusTer.buildFactory()
gerTer.buildFactory()
engTer.buildFactory()
japTer.buildFactory()

rusSea = Territory(players=turnOrder, name='Russia Sea', allTerritoryUnits=allTerritoryUnits, isWater=True)
gerSea = Territory(players=turnOrder, name='Germany Sea', allTerritoryUnits=allTerritoryUnits, isWater=True)
engSea = Territory(players=turnOrder, name='United Kingdom Sea', allTerritoryUnits=allTerritoryUnits, isWater=True)
japSea = Territory(players=turnOrder, name='Japan Sea', allTerritoryUnits=allTerritoryUnits, isWater=True)

connectTerritories(territoryFrom=rusTer, territoryTo=gerTer)
connectTerritories(territoryFrom=engTer, territoryTo=gerTer)
connectTerritories(territoryFrom=rusTer, territoryTo=japTer)
connectTerritories(territoryFrom=engTer, territoryTo=japTer)

connectTerritories(territoryFrom=rusTer, territoryTo=rusSea, unloadingTransports=unloadingTransports)
connectTerritories(territoryFrom=gerSea, territoryTo=gerTer, unloadingTransports=unloadingTransports)
connectTerritories(territoryFrom=japSea, territoryTo=japTer, unloadingTransports=unloadingTransports)
connectTerritories(territoryFrom=engTer, territoryTo=engSea, unloadingTransports=unloadingTransports)

connectTerritories(territoryFrom=rusSea, territoryTo=gerSea)
connectTerritories(territoryFrom=engSea, territoryTo=gerSea)
connectTerritories(territoryFrom=rusSea, territoryTo=japSea)
connectTerritories(territoryFrom=engSea, territoryTo=japSea)

territories = [rusTer, rusSea, gerTer, gerSea, engTer, engSea, japTer, japSea]

#for currentTurn in range(len(turnOrder)):
#    buyUnits(player=turnOrder[currentTurn])
#    collectMoney(player=turnOrder[currentTurn])
#rusInfantryFull = rusPlayer.fullUnits[0]
#rusArtilleryFull = rusPlayer.fullUnits[1]
#rusArmorFull = rusPlayer.fullUnits[2]
#rusFighterFull = rusPlayer.fullUnits[3]
#rusBomberFull = rusPlayer.fullUnits[4]
#rusSubFull = rusPlayer.fullUnits[5]
#rusCarrierFull = rusPlayer.fullUnits[6]
#rusDestroyerFull = rusPlayer.fullUnits[7]
#rusBattleshipFull = rusPlayer.fullUnits[8]
#rusAntiAirFull = rusPlayer.fullUnits[9]
#rusTransportFull = rusPlayer.fullUnits[10]

#gerInfantryFull = gerPlayer.fullUnits[0]
#gerSubFull = gerPlayer.fullUnits[5]

#gerTer.addUnit(rusBomberFull)
#gerTer.addUnit(gerInfantryFull)
#gerTer.addUnit(gerInfantryFull)
gameState = []
allieswins = open("allieswins.txt", "a")
axiswins = open("axiswins.txt", "a")
while(True):
    while(rusPlayer.capital.owner.team != gerPlayer.capital.owner.team or rusPlayer.capital.owner.team != engPlayer.capital.owner.team or rusPlayer.capital.owner.team != japPlayer.capital.owner.team):
        for currentTurn in range(len(turnOrder)):
            currentPlayer = turnOrder[currentTurn]
            if player.isHuman:
                print(readableStatus(turnOrder, currentTurn, territories))
            giveMoveOrders(currentPlayer, combatAllowed=True)
            resolveSeaCombat(currentPlayer)
            resolveBombards(currentPlayer)
            unloadTransports2(currentPlayer)
            resolveLandCombat(currentPlayer)
            giveMoveOrders(currentPlayer, combatAllowed=False)
            crashPlanes(currentPlayer)
            resetUnitsFully(currentPlayer)
            buyUnits(currentPlayer)
            collectMoney(currentPlayer)
    gameState.clear()
    gameState.append(currentTurn)
    for player in turnOrder:
        gameState.append(player.money)
    for territory in territories:
        gameState.append(territory.factoryMax)
        gameState.append(territory.factoryHealth)
        for unitQuantity in territory.unitQuantities:
            gameState.append(unitQuantity.quantity)
        for player in turnOrder:
            gameState.append(int(player == territory.owner))
    jString = json.dumps(gameState)    
    ##print("Team: " + str(rusPlayer.capital.owner.team) + " wins!")
    if rusPlayer.capital.owner.team == 1:
        allieswins.write(jString)
    else:
        axiswins.write(jString)
    for player in turnOrder:
        player.reset()
        player.money = 10
    for territory in territories:
        territory.reset()

