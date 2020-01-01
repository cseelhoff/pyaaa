from typing import List
from gamedata import GameData

class Player:
    def __init__(self, gamedata: GameData, name: str, money: int=0, team: int=0, isHuman: bool=False):
        self.gamedata: GameData = gamedata
        self.moneyIndex: int = gamedata.allocateAndGetIndex()
        self.money: int = money
        self.reservedMoneyIndex: int = gamedata.allocateAndGetIndex()
        self.reservedMoney: int = 0
        self.name: str = name
        self.team: int = team
        self.isHuman: bool = isHuman

    @property
    def money(self) -> int:
        return self.gamedata.rawByteArray[self.moneyIndex]

    @money.setter
    def money(self, money: int) -> None:
        if money > 255:
            self.gamedata.rawByteArray[self.moneyIndex] = 255
        elif money < 0:
            self.gamedata.rawByteArray[self.moneyIndex] = 0
        else:
            self.gamedata.rawByteArray[self.moneyIndex] = money

    @property
    def reservedMoney(self) -> int:
        return self.gamedata.rawByteArray[self.reservedMoneyIndex]

    @reservedMoney.setter
    def reservedMoney(self, reservedMoney: int) -> None:
        if reservedMoney > 255:
            self.gamedata.rawByteArray[self.reservedMoneyIndex] = 255
        elif reservedMoney < 0:
            self.gamedata.rawByteArray[self.reservedMoneyIndex] = 0
        else:
            self.gamedata.rawByteArray[self.reservedMoneyIndex] = reservedMoney

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)
        