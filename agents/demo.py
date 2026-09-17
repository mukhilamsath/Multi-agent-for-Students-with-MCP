
def freq(numbers):

    f = {}

    for i in numbers:
       
       f[i] = f.get(i)+1

    highest = 0
    res = -1

    for key,value in f.items():

        if value > highest:
            highest = value
            res = key

    print("most frequent : ",res)  

n = [1,2,2,3,4]
freq(n) 
