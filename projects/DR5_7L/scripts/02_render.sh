#!/bin/bash

AF="../results/physio/EMidOriRGBneuronIDSFTFspeed.csv"
AH="skeleton_id,ori,r,g,b,neuron_id,sf,tf,speed"
#AF="EMidOriRGBSFTFspeed.csv"
#AH="skeleton_id,ori,r,g,b,sf,tf,speed"
SK="../data/skeletons"


FILES=`ls ../results/groups`

mkdir -p ../results/render

function render_csv() {
    catmaid_render.py -a $AF -A $AH -s $SK -r ../results/render/ -S ../results/render/ -i $@
}

echo "rendering"

# group column (g) is 0-based
echo "connApList"
render_csv ../results/groups/connApList.csv
echo "connNonApList"
render_csv ../results/groups/connNonApList.csv
echo "convApList"
render_csv ../results/groups/convApList.csv -g 1
echo "convNonApList"
render_csv ../results/groups/convNonApList.csv -g 1
echo "multiHitApList"
render_csv ../results/groups/multiHitApList.csv
echo "multiHitNonApList"
render_csv ../results/groups/multiHitNonApList.csv
echo "testfig"
render_csv ../results/groups/testFig1.csv -g 0

echo "functional_sids"
catmaid_render.py -a $AF -A $AH -s $SK -r ../results/render/render/ -S ../results/render/save/ -i ../results/lists/functional_sids.txt -N "funct_sids"
echo "wired_sids"
catmaid_render.py -a $AF -A $AH -s $SK -r ../results/render/render/ -S ../results/render/save/ -i ../results/lists/wired_sids.txt -o render/wiredopts.json -m render/wiredmats.json -N "wired_sids"
echo "all_sids"
catmaid_render.py -a $AF -A $AH -s $SK -r ../results/render/render/ -S ../results/render/save/ -i ../results/lists/all_sids.txt -N "all_sids"
