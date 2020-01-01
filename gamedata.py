
class GameData:
    def __init__(self):
        self.rawByteArray = [0, 0]
    
    def allocateAndGetIndex(self) -> int:
        self.rawByteArray.append(0)
        return len(self.rawByteArray) - 1
