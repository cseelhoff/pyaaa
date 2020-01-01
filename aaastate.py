from gamestate import GameState

class AAAstate():
    def __init__(self, gameState: GameState, rawByteArray: bytes):
        self.gameState = gameState
        self.rawByteArray = rawByteArray[:]

    def takeAction(self, action):
        return action

    def isTerminal(self):
        return True

    def getReward(self):
        return 0
