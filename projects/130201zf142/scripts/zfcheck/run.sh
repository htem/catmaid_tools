#!/bin/bash

SOURCE=`find source_me.sh`

if [ -f $SOURCE ];
then
  . $SOURCE
fi

echo "Running zf tracing validation"

python zfcheck.py

echo "finished running zf scripts"
