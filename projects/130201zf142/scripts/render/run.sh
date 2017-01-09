#!/bin/bash

SOURCE=`find source_me.sh`

if [ -f $SOURCE ];
then
  . $SOURCE
fi

SK="../../data/skeletons"
MAT="./zfmaterials.json"
OPT="./zfoptions.json"
TEMPLATE="./zf_template.blend"


function render_csv() {
    catmaid_render.py -a $AF -A $AH -s $SK -t $TEMPLATE -r ../../results/render/render/ -S ../../results/render/save/ -i $@
}

echo "rendering"

echo "all_sids"
catmaid_render.py -s $SK -m $MAT -o $OPT -t $TEMPLATE -r ../../results/render/render/ -S ../../results/render/save/ -i ../../results/lists/all_sids.txt -N "all_sids"
