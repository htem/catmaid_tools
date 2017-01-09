#!/bin/bash

SOURCE=`find source_me.sh`

if [ -f $SOURCE ];
then
  . $SOURCE
fi

mkdir -p ../../results/lists/

python gen_zf_lists.py
