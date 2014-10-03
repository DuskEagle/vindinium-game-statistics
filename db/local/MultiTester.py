from multiprocessing import Process
import random
import time

def f(val):
    print(val)

def main():
    for i in range(1,100):
        p = Process(target=f, args=(i,))
        p.start()

if __name__=="__main__":
    main()