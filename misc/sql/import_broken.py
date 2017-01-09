'''
This script imports a list of broken sections into a catmaid db
   input:
       catmaid server connection options
       stacks to modify140
       List of broken sections:
           Format:
               0
               1
               2
               3
               .
               .
               .

list can be generated with, e.g.:
    brokens = range(0, 12000).extend(missingsections)
    with open(SectionFile, 'w') as f:
        for sect in brokens:
            f.write(sect)
'''

import json
import psycopg2

#user inputs
stacks = [1,2]
SectionFile = 'BrokenSections.txt'
dbfile = 'catmaiddb.json'

with open(SectionFile, 'r') as f:
    brokensects = [(ln.replace('\n','')) for ln in f.readlines()]

# connect to catmaid db using catmaid file
with open(dbfile, 'r') as f:
    dbinfo = json.load(f)
conn = psycopg2.connect(**dbinfo)
curs = conn.cursor()

sqlstr = 'INSERT INTO broken_slice (stack_id, index) SELECT %s, %s '
         'WHERE NOT EXISTS (SELECT id FROM broken_slice '
         'WHERE stack_id = %s AND index = %s);'
for sect in brokensects:
    for stack in stacks:
        curs.execute(sqlstr, (stack, sect, stack, sect, ))

# push changes
conn.commit()
conn.close()
