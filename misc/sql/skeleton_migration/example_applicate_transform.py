'''
example of simple transformation for z-shifted catmaid data.
Expects c2z.py json in working directory
'''
import json

dumpfn = './20160503_export_FromDB.json'  # TODO maybe make this date based?
outfn = './20160503_newnodedump.txt'
c2zfile = './c2z.json'


with open(c2zfile, 'r') as j:
    c2z = json.load(j)
c2z = {int(k): int(v) for k, v in c2z.items()}

with open(dumpfn, 'r') as f:
    proj = json.load(f)

outputs = []
for sid in proj['reconstructions']['skeletons'].keys():
    for nid in proj['reconstructions']['skeletons'][sid]['trace'].keys():
        nidps = proj['reconstructions']['skeletons'][sid]['trace'][nid]
        x = nidps['xpix']
        y = nidps['ypix']
        z = c2z[int(float(nidps['zpix']))]
        outputs.append('{} {} {} {} {} {}\n'.format(sid, nid, 'root', x, y, z))

for cid in proj['reconstructions']['connectors'].keys():
    connps = proj['reconstructions']['connectors'][cid]
    x = connps['xpix']
    y = connps['ypix']
    z = c2z[int(float(connps['zpix']))]
    outputs.append('{} {} {} {} {} {}\n'.format(
        'connector', cid, 'root', x, y, z))

with open(outfn, 'w') as f:
    for ln in outputs:
        f.write(ln)
