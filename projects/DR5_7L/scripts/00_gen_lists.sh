#!/bin/bash

mkdir -p ../results/lists/

# TODO need ../../results/lists/functional.txt [can this be computed??]
cd gen_lists
python gen_lists.py
