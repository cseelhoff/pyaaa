import os

with open("allieswins.txt", 'rb+') as filehandle:
    filehandle.seek(-1, os.SEEK_END)
    filehandle.truncate()

with open("axiswins.txt", 'rb+') as filehandle:
    filehandle.seek(-1, os.SEEK_END)
    filehandle.truncate()

allieswins = open("allieswins.txt", "a")
allieswins.write(']')

axiswins = open("axiswins.txt", "a")
axiswins.write(']')