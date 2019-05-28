from hashlib import sha256
from time import time
from random import randint

x = randint(0,10000)
y = 0
t1 =time()
while(sha256(f'{x*y}'.encode()).hexdigest()[:4] != '1234'):
    y +=1

print("x = {}".format(x))
print("y = {}".format(y))
print(sha256(f'{x*y}'.encode()).hexdigest())

t2= time()
print(t2-t1)
