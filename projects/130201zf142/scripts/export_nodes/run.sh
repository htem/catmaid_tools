#!/bin/bash

SOURCE=`find source_me.sh`

if [ -f $SOURCE ];
then
  . $SOURCE
fi

export DATE=$(date +%y%m%dT%H%M)

echo "exporting 130201zf142 data"

mkdir -p  ../../results/exports/

echo "Outputting all zf points in raw coordinates"

SAVEFILE=../../results/exports/${DATE}_130201zf142_ALLNODE_dump_RAWcoord.txt

python export_affine_nodes_to_raw.py ${SAVEFILE}
gzip ${SAVEFILE}
