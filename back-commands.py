f = open('commands.txt', 'r')
lines = f.readlines()


w = open('backwards.txt','w')
for i in range(511,-1,-1):
    w.write(lines[i])
    print(i)
