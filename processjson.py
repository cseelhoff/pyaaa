import json
import numpy as np

gamma = 0.999
train_data_list = []
train_labels_list = []
with open("allieswins.txt") as allieswins:
    allieswinsdata = json.load(allieswins)
with open("axiswins.txt") as axiswins:
    axiswinsdata = json.load(axiswins)
for dataset in allieswinsdata:
    train_data_list.append(dataset['data'])
    train_labels_list.append(gamma ** dataset['steps'])
for dataset in axiswinsdata:
    train_data_list.append(dataset['data'])
    train_labels_list.append((gamma ** dataset['steps']) * -1)

train_data = np.asarray(train_data_list)
train_labels = np.asarray(train_labels_list)

np.save('train_data.npy', train_data) 
np.save('train_labels.npy', train_labels) 
