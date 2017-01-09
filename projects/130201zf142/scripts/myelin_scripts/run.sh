#!/bin/bash

SOURCE=`find source_me.sh`

if [ -f $SOURCE ];
then
  . $SOURCE
fi

python fishmyelin.py
python myelinresults.py
