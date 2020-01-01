a = [0, 1, 2, 3]
c = a[:]
for b in c:
    print(b)
    if a[2] == 2:
        a.remove(2)
        a.append(4)
