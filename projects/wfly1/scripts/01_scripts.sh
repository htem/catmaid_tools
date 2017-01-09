#!/bin/bash

echo "running wfly1 scripts"

#Scripts to run before rendering go below.
cd scripts

mkdir ../../results/scripts
python gen_annotation_map.py
python check_npl_list.py
python near_path_lengths.py

echo "finished running scripts"
