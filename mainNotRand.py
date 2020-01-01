import cProfile
import random
import json
from monte import mcts

from typing import List
from typing import Dict
from typing import Set
from connection import Connection
from unitquantity import UnitQuantity
from detailedunit import DetailedUnit
from unittype import UnitType
from territory import Territory
from player import Player
from gamestate import GameState
from destinationtransport import DestinationTransport
from buildoption import BuildOption
from moveoption import MoveOption
from gamedata import GameData
from aaaengine import AAAengine


def createDetailedUnits(unitType: UnitType) -> List[DetailedUnit]:
    detailedUnits = []
    for hitsRemaining in range(1, (unitType.maxHits + 1)):
        for movesRemaining in range(0, (unitType.maxMoves + 1)):
            detailedUnit = DetailedUnit(unitType, movesRemaining, hitsRemaining)
            detailedUnits.append(detailedUnit)
    return detailedUnits


aaaEngine = AAAengine()
aaaEngine.verbose = False

rusPlayer = Player(gamedata=aaaEngine.gamedata, name='Player1Rus', money=10, team=1)
aaaEngine.allies[rusPlayer] = []
aaaEngine.enemies[rusPlayer] = []
aaaEngine.fullUnits[rusPlayer] = []
gerPlayer = Player(gamedata=aaaEngine.gamedata, name='Player2Ger', money=10, team=2)
aaaEngine.allies[gerPlayer] = []
aaaEngine.enemies[gerPlayer] = []
aaaEngine.fullUnits[gerPlayer] = []
engPlayer = Player(gamedata=aaaEngine.gamedata, name='Player3Eng', money=10, team=1)
aaaEngine.allies[engPlayer] = []
aaaEngine.enemies[engPlayer] = []
aaaEngine.fullUnits[engPlayer] = []
japPlayer = Player(gamedata=aaaEngine.gamedata, name='Player4Jap', money=10, team=2)
aaaEngine.allies[japPlayer] = []
aaaEngine.enemies[japPlayer] = []
aaaEngine.fullUnits[japPlayer] = []
turnOrder = [rusPlayer, gerPlayer, engPlayer, japPlayer]
aaaEngine.turnOrder = turnOrder

aaaEngine.allies[rusPlayer].append(engPlayer)
aaaEngine.allies[engPlayer].append(rusPlayer)
aaaEngine.allies[gerPlayer].append(japPlayer)
aaaEngine.allies[japPlayer].append(gerPlayer)
aaaEngine.enemies[rusPlayer].append(gerPlayer)
aaaEngine.enemies[rusPlayer].append(japPlayer)
aaaEngine.enemies[engPlayer].append(gerPlayer)
aaaEngine.enemies[engPlayer].append(japPlayer)
aaaEngine.enemies[gerPlayer].append(rusPlayer)
aaaEngine.enemies[gerPlayer].append(engPlayer)
aaaEngine.enemies[japPlayer].append(rusPlayer)
aaaEngine.enemies[japPlayer].append(engPlayer)

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
        aaaEngine.fullUnits[unitType.player].append(unloadedUnit)

emptyTransports = []
largestTransportCapacity = 0
for detailedUnit in allUnloadedUnits:
    unitType = detailedUnit.unitType
    maxLand = unitType.maxLand
    if maxLand > 0:
        emptyTransports.append(detailedUnit)
        aaaEngine.unitAfterLoadUnitType[detailedUnit] = {}
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
                loadedTransport = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining)
                aaaEngine.unitAfterLoadUnitType[loadedTransport] = {}
                aaaEngine.payload[loadedTransport] = payloadOne
                payloadOneTransports.append(loadedTransport)
                loadedTransport.payloadHasPlayer[transportableUnitType.player] = True
                aaaEngine.unitAfterLoadUnitType[emptyTransport][transportableUnitType] = loadedTransport
                unloadingTransport = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining)
                aaaEngine.payload[unloadingTransport] = payloadOne
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
                transportLoadedWithUnit1 = aaaEngine.unitAfterLoadUnitType[emptyTransport][transportableUnitType1]
                transportableUnit2 = payloadTwo[1]
                transportableUnitType2 = transportableUnit2.unitType
                canLoadUnitType2 = transportUnitType.maxLand >= transportableUnitType1.weight + transportableUnitType2.weight
                transportLoadedWithUnit1.canLoadUnitType[transportableUnitType2] = canLoadUnitType2
                if canLoadUnitType2:
                    loadedTransport = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining)
                    aaaEngine.payload[loadedTransport] = payloadTwo
                    payloadTwoTransports.append(loadedTransport)
                    aaaEngine.unitAfterLoadUnitType[transportLoadedWithUnit1][transportableUnitType2] = loadedTransport
                    unloadingTransportBoth = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining)
                    aaaEngine.payload[unloadingTransportBoth] = payloadTwo
                    unloadingTransportBoth.unitAfterUnload = emptyTransport
                    unloadingTransportBoth.payloadPendingUnload = payloadTwo
                    loadedTransport.unitAfterUnloadBoth = unloadingTransportBoth
                    unloadingTransports.append(unloadingTransportBoth)
                    
                    unloadingTransport1 = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining)
                    aaaEngine.payload[unloadingTransport1] = payloadTwo
                    unloadingTransport1.unitAfterUnload = aaaEngine.unitAfterLoadUnitType[emptyTransport][transportableUnitType2]
                    unloadingTransport1.payloadPendingUnload = payloadOneDict[transportableUnit1]
                    loadedTransport.unitAfterUnload1 = unloadingTransport1
                    unloadingTransports.append(unloadingTransport1)
                    
                    unloadingTransport2 = DetailedUnit(unitType=transportUnitType, movesRemaining=emptyTransport.movesRemaining, hitsRemaining=emptyTransport.hitsRemaining)
                    aaaEngine.payload[unloadingTransport2] = payloadTwo
                    unloadingTransport2.unitAfterUnload = aaaEngine.unitAfterLoadUnitType[emptyTransport][transportableUnitType1]
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
        if detailedUnit2.unitType == detailedUnit.unitType and aaaEngine.payload[detailedUnit] == aaaEngine.payload[detailedUnit2]:
            if detailedUnit2.movesRemaining == detailedUnit.movesRemaining:
                if detailedUnit2.hitsRemaining == detailedUnit.hitsRemaining - 1:
                    detailedUnit.unitAfterHit = detailedUnit2
            elif detailedUnit2.movesRemaining == detailedUnit.movesRemaining - 1 and detailedUnit2.hitsRemaining == detailedUnit.hitsRemaining:
                detailedUnit.unitAfterMove = detailedUnit2
            if detailedUnit2.movesRemaining == detailedUnit.unitType.maxMoves and detailedUnit2.hitsRemaining == detailedUnit.unitType.maxHits:
                detailedUnit.unitAfterTurn = detailedUnit2

for detailedUnit in payloadTwoTransports:
    for detailedUnit2 in payloadTwoTransports:
        if detailedUnit2.unitType == detailedUnit.unitType and aaaEngine.payload[detailedUnit] == aaaEngine.payload[detailedUnit2]:
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

aaaEngine.allTerritoryUnits = allTerritoryUnits
rusTer = aaaEngine.createLand(name='Russia', landValue=10, owner=rusPlayer)
aaaEngine.capital[rusPlayer] = rusTer
gerTer = aaaEngine.createLand(name='Germany', landValue=10, owner=gerPlayer)
aaaEngine.capital[gerPlayer] = gerTer
engTer = aaaEngine.createLand(name='England', landValue=10, owner=engPlayer)
aaaEngine.capital[engPlayer] = engTer
japTer = aaaEngine.createLand(name='Japan', landValue=10, owner=japPlayer)
aaaEngine.capital[japPlayer] = japTer

aaaEngine.buildFactory(rusTer)
aaaEngine.buildFactory(gerTer)
aaaEngine.buildFactory(engTer)
aaaEngine.buildFactory(japTer)

rusSea = aaaEngine.createSea(name='Russia Sea')
gerSea = aaaEngine.createSea(name='Germany Sea')
engSea = aaaEngine.createSea(name='England Sea')
japSea = aaaEngine.createSea(name='Japan Sea')

gamedata = aaaEngine.gamedata

aaaEngine.connectTerritories(territoryFrom=rusTer, territoryTo=gerTer)
aaaEngine.connectTerritories(territoryFrom=engTer, territoryTo=gerTer)
aaaEngine.connectTerritories(territoryFrom=rusTer, territoryTo=japTer)
aaaEngine.connectTerritories(territoryFrom=engTer, territoryTo=japTer)

aaaEngine.connectTerritories(territoryFrom=rusTer, territoryTo=rusSea, unloadingTransports=unloadingTransports)
aaaEngine.connectTerritories(territoryFrom=gerSea, territoryTo=gerTer, unloadingTransports=unloadingTransports)
aaaEngine.connectTerritories(territoryFrom=japSea, territoryTo=japTer, unloadingTransports=unloadingTransports)
aaaEngine.connectTerritories(territoryFrom=engTer, territoryTo=engSea, unloadingTransports=unloadingTransports)

aaaEngine.connectTerritories(territoryFrom=rusSea, territoryTo=gerSea)
aaaEngine.connectTerritories(territoryFrom=engSea, territoryTo=gerSea)
aaaEngine.connectTerritories(territoryFrom=rusSea, territoryTo=japSea)
aaaEngine.connectTerritories(territoryFrom=engSea, territoryTo=japSea)

#territories = [rusTer, rusSea, gerTer, gerSea, engTer, engSea, japTer, japSea]
aaaEngine.completeSetup()
originalGameState = bytes(aaaEngine.gamedata.rawByteArray)

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
#rusTer.addUnit(rusInfantryFull)
stateAfterTurn = []
stateAfterCombatMove = []
stateAfterCombatResolved = []
stateAfterSecondMove = []
stateAfterPurchase = []

currentGameState = aaaEngine.backupGameState()
result = aaaEngine.simulateGameToEnd(currentGameState)
print(result)

allieswins = open("allieswins.txt", "w")
allieswins.write('[')
axiswins = open("axiswins.txt", "w")
axiswins.write('[')

totalstates = 0
while(True):
    reward = 0
    stateHistory = []
    aaaEngine.restoreGameState(currentGameState)
    originalPlayer = aaaEngine.currentPlayer
    while(not aaaEngine.isTerminal()):
        currentPlayer = aaaEngine.currentPlayer
        if aaaEngine.currentPhase == 0:
            while(True):
                movesAvailable = aaaEngine.getAllAvailableMoveOrders(combatAllowed=True)
                totalMoves = len(movesAvailable)
                if totalMoves > 0:
                    if random.random() < (1.0 / (totalMoves * totalMoves)):
                        break
                    moveAvailable = random.choice(movesAvailable)
                    aaaEngine.moveUnit(moveAvailable.moveFrom, moveAvailable.selectedUnit, moveAvailable.moveTo)
                else:
                    break
                stateHistory.append(aaaEngine.backupGameState())
            aaaEngine.currentPhase = 1
            stateHistory.append(aaaEngine.backupGameState())
        elif aaaEngine.currentPhase == 1:
            aaaEngine.resolveSeaCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
            aaaEngine.resolveBombards() # rand select unit Casulaty
            aaaEngine.unloadTransports2() # no options here...
            aaaEngine.resolveLandCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
            aaaEngine.currentPhase = 2
            stateHistory.append(aaaEngine.backupGameState())
        elif aaaEngine.currentPhase == 2:
            while(True):
                movesAvailable = aaaEngine.getAllAvailableMoveOrders(combatAllowed=False)
                totalMoves = len(movesAvailable)
                if totalMoves > 0:
                    if random.random() < (1.0 / (totalMoves * totalMoves)):
                        break
                    moveAvailable = random.choice(movesAvailable)
                    aaaEngine.moveUnit(moveAvailable.moveFrom, moveAvailable.selectedUnit, moveAvailable.moveTo)
                else:
                    break
                stateHistory.append(aaaEngine.backupGameState())
            aaaEngine.currentPhase = 3
            stateHistory.append(aaaEngine.backupGameState())
        elif aaaEngine.currentPhase == 3:
            while(True):
                purchasesAvailable = aaaEngine.getAllBuildOptions()
                if len(purchasesAvailable) > 0:
                    buildOption = random.choice(purchasesAvailable)
                    buildFrom = buildOption.buildFrom
                    buildTo = buildOption.buildTo
                    unitSelected = buildOption.detailedUnit
                    aaaEngine.currentPlayer.money -= unitSelected.unitType.cost
                    if unitSelected == aaaEngine.factoryUnit:
                        buildFrom.buildFactory()
                        buildFrom.constructionRemaining = 0
                    elif unitSelected == aaaEngine.repairUnit:
                        buildFrom.factoryHealth += 1
                        buildFrom.constructionRemaining += 1
                    else:
                        buildFrom.constructionRemaining -= 1
                        aaaEngine.addUnit(buildTo, unitSelected)
                else:
                    break
                stateHistory.append(aaaEngine.backupGameState())
            aaaEngine.crashPlanes()
            aaaEngine.resetUnitsFully()
            aaaEngine.resetConstruction()
            aaaEngine.collectMoney()
            aaaEngine.advanceTurn()
            aaaEngine.currentPhase = 0
            stateHistory.append(aaaEngine.backupGameState())
    jstring = ""
    for i, gameState in enumerate(stateHistory):
        jstring += '{"steps":' + str(len(stateHistory) - i - 1) + ', "data":' + json.dumps(list(gameState)) + '},'
    totalstates += len(stateHistory)
    if aaaEngine.capital[aaaEngine.currentPlayer].owner.team == 1:
        allieswins.write(jstring)
        print(str(totalstates) + " allies win " + str(len(stateHistory)))
    else:
        axiswins.write(jstring)
        print(str(totalstates) + " axis win " + str(len(stateHistory)))
    stateHistory.clear()

mcts = mcts(rolloutPolicy=aaaEngine.simulateGameToEnd, terminalPolicy=aaaEngine.isStateTerminal, 
    getNextStates=aaaEngine.lookAheadSmall, timeLimit=100)
action = mcts.search(initialState=currentGameState)
while(True):
    bestState = action.state
    aaaEngine.restoreGameState(bestState)
#    print(str(action.totalReward) + "/" + str(action.numVisits))
#    print(aaaEngine.readableStatus())
    if aaaEngine.currentPhase == 1:
        aaaEngine.resolveSeaCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
        aaaEngine.resolveBombards() # rand select unit Casulaty
        aaaEngine.unloadTransports2() # no options here...
        aaaEngine.resolveLandCombat() # rand retreat, rand bombers, ect... also using high luck # rand select unit Casulaty
        aaaEngine.currentPhase = 2
        bestState = aaaEngine.backupGameState()
#        print(str(action.totalReward) + "/" + str(action.numVisits))
#        print(aaaEngine.readableStatus())
    stateHistory.append(bestState)
    if aaaEngine.isStateTerminal(bestState):
        jstring = ""
        for i, gameState in enumerate(stateHistory):
            jstring += '{"steps":' + str(len(stateHistory) - i - 1) + ', "data":' + json.dumps(list(gameState)) + '},'
        if aaaEngine.capital[aaaEngine.currentPlayer].owner.team == 1:
            allieswins.write(jstring)
            print("allies win " + str(len(stateHistory)))
        else:
            axiswins.write(jstring)
            print("axis win " + str(len(stateHistory)))
        bestState = currentGameState
        aaaEngine.restoreGameState(currentGameState)
        stateHistory.clear()
    action = mcts.search(initialState=bestState)
