#!/bin/bash

function print_usage(){
  echo "
  This script iterates through all subprojects and executes the run.sh within
  that subproject. This script takes one option argument (-h) and non-option
  arguments in the form of script names that will be passed through to the
  subproject run.sh.

  An example of this is:

  bash run.sh script

  Multiple scripts can be passed through at the same time.

  Arguemnts:

  -h             Prints help message and exits script. No argument after -h.

  script         The name of a desired script to be run. Can list multiple
                 scripts but must have spaces between scripts and no quotation
                 marks surrounding script names. If one or multiple scripts are
                 passed through, any scripts not called will not be run.
  "
}

# source bash rc (to load any per-user env vars)
RCFILE="source_me.sh"
if [ -e $RCFILE ]
then
    . $RCFILE
fi

SCRIPTS=`ls -d */`

while getopts "h" opt; do
  case $opt in
    h)
      print_usage
      exit 1
      ;;
    ?)
      echo "Invalid Option: -$OPTARG" >&2
      print_usage
      exit 1
      ;;
    :)
      echo "Option -$OPTARG reguires an argument." >&2
      print_usage
      exit 1
      ;;
  esac
done

if [ $# -gt 0 ]; then
  while [ $# -gt 0 ];
  do
    if [ -d ./$1 ]; then

      cd $1

      echo "Processing $1"

      bash run.sh

      echo "Finished processing $1"

      cd ../

      shift
    else
      echo "$1 is not a directory!"
      exit 1
    fi
  done
else
  for SCRIPT in $SCRIPTS
  do
    cd $SCRIPT

    echo "Processing $SCRIPT"

    bash run.sh

    echo "Finished processing $SCRIPT"

    cd ../

  done
fi
