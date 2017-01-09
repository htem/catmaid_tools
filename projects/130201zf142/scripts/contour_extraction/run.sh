#!/bin/bash

SOURCE=`find source_me.sh`

if [ -f $SOURCE ];
then
  . $SOURCE
fi

echo "exporting backbone and projection contours"
mkdir -p  ../../results/exports/
python export_contours.py
