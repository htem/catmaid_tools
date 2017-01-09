#!/bin/bash

. source_me.sh

mkdir -p logs
mkdir -p data
mkdir -p results

# fetch skeletons
echo "fetching skeletons for $CATMAID_PROJECT from $CATMAID_SERVER to data/skeletons"
catmaid_fetch.py -o data/skeletons &> logs/fetch

# run scripts (in alphabetical order)
for SCRIPT in `find scripts/ -maxdepth 1 -type f | sort`
do
    cd scripts
    SCRIPT_FILENAME=`basename $SCRIPT`
    SCRIPT_NAME="${SCRIPT_FILENAME%.*}"
    echo "running $SCRIPT_NAME from $SCRIPT"
    bash $SCRIPT_FILENAME &> ../logs/$SCRIPT_NAME
    cd ../
done
