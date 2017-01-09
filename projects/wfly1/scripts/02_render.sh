#!/bin/bash

SK="../data/skeletons"
TE="render/wfly1template.blend"
MAT="render/flymaterials.json"
OPT="render/flyoptions.json"


function render_csv() {
    catmaid_render.py -a $AF -A $AH -s $SK -t $TE -r ../results/render/render/ -S ../results/render/save/ -i $@
}

echo "rendering"

echo "ORNs and PNs"
catmaid_render.py -s $SK -m $MAT -o $OPT -t $TE -r ../results/render/render/ -S ../results/render/save/ -i ../results/lists/PNs_ORNs.txt -N "PNs_ORNs"

#echo "all_sids"
#catmaid_render.py -s $SK -m $MAT -o $OPT -t $TE -r ../results/render/render/ -S ../results/render/save/ -i ../results/lists/all_sids.txt -N "all_sids"
