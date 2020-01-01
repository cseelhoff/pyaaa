
import time
import math
import random


class treeNode():
    def __init__(self, state, isTerminal, parent):
        self.state = state
        self.isTerminal = isTerminal
        self.isFullyExpanded = isTerminal
        self.parent = parent
        self.numVisits = 0
        self.totalReward = 0
        self.children = {}


class mcts():
    def __init__(self, rolloutPolicy, terminalPolicy, getNextStates, timeLimit=None, iterationLimit=None, explorationConstant=1 / math.sqrt(2)):
        if timeLimit != None:
            if iterationLimit != None:
                raise ValueError("Cannot have both a time limit and an iteration limit")
            # time taken for each MCTS search in milliseconds
            self.timeLimit = timeLimit
            self.limitType = 'time'
        else:
            if iterationLimit == None:
                raise ValueError("Must have either a time limit or an iteration limit")
            # number of iterations of the search
            if iterationLimit < 1:
                raise ValueError("Iteration limit must be greater than one")
            self.searchLimit = iterationLimit
            self.limitType = 'iterations'
        self.explorationConstant = explorationConstant
        self.rollout = rolloutPolicy
        self.terminalPolicy = terminalPolicy
        self.getNextStates = getNextStates

    def search(self, initialState):
        self.root = treeNode(initialState, self.terminalPolicy(initialState), None)

        if self.limitType == 'time':
            timeLimit = time.time() + self.timeLimit / 1000
            while time.time() < timeLimit:
                self.executeRound()
        else:
            for _ in range(self.searchLimit):
                self.executeRound()

        bestChild = self.getBestChild(self.root, 0)
        return bestChild

    def executeRound(self):
        node = self.selectNode(self.root)
        reward = self.rollout(node.state)
        self.backpropogate(node, reward)

    def selectNode(self, node):
        while not node.isTerminal:
            if node.isFullyExpanded:
                node = self.getBestChild(node, self.explorationConstant)
            else:
                return self.expand(node)
        return node

    def expand(self, node):
        futureStates = self.getNextStates(node.state)
        for futureState in futureStates:
            if futureState not in node.children:
                newNode = treeNode(state=futureState, isTerminal=self.terminalPolicy(futureState), parent=node)
                node.children[futureState] = newNode
                if len(futureStates) == len(node.children):
                    node.isFullyExpanded = True
                return newNode

        #node.isFullyExpanded = True
        #newNode = self.getBestChild(node, self.explorationConstant)
        #return newNode

        raise Exception("Should never reach here")

    def backpropogate(self, node, reward):
        while node is not None:
            node.numVisits += 1
            node.totalReward += reward
            node = node.parent

    def getBestChild(self, node, explorationValue):
        bestValue = float("-inf")
        bestNodes = []
        for child in node.children.values():
            nodeValue = child.totalReward / child.numVisits + explorationValue * math.sqrt(
                2 * math.log(node.numVisits) / child.numVisits)
            if nodeValue > bestValue:
                bestValue = nodeValue
                bestNodes = [child]
            elif nodeValue == bestValue:
                bestNodes.append(child)
        return random.choice(bestNodes)
