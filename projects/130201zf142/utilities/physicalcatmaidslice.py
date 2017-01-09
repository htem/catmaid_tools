import csv
""" example infile: infile = ('c2z.csv')"""


def catmaid_physical_dict(filename):
    mydict = {}
    with open(filename, 'r') as infile:
        reader = csv.reader(infile)
        for row in reader:
            k = int(row[0])
            v = int(row[1])
            if ((k in mydict) and (v != mydict[k])):
                raise Exception("Key: {} does not Map 1:1".format(k))
            if (v in mydict.values()):
                raise Exception("Value: {} does not Map 1:1".format(v))
            else:
                mydict[k] = v
        return mydict


def catmaid_to_physical(number):
    if int(number) in c2z:
        return c2z[int(number)]
    else:
        return None


def physical_to_catmaid(number):
    if int(number) in c2z.values():
        d = [key for key, val in c2z.items() if val == int(number)][0]
        return d
    else:
        return None

infile = 'c2z.csv'
c2z = catmaid_physical_dict(infile)
