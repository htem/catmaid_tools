#!/bin/bash

mkdir -p logs
mkdir -p data
mkdir -p data/skeletons_smooth/
mkdir -p results

SOURCE=`find source_me.sh`

if [ -f $SOURCE ];
then
  . $SOURCE
fi


function print_usage(){
  echo "
  This script iterates through all subprojects and executes the run.sh within
  that subproject. This script also takes an optional argument that
  disables skeleton fetching.

  Arguemnts:

  -f             Turns off skeleton fecthing when called. No argument after -f.

  -h             Prints help message and exits script. No argument after -h.

  -s             Turns on skeleton smoothing when called. No argument after -s.

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

FETCH=1
SMOOTHING=0

while getopts "hfs" opt; do
  case $opt in
    h)
      print_usage
      exit 1
      ;;
    f)
      FETCH=0
      ;;
    s)
      SMOOTHING=1
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

if [ $OPTIND -gt 0 ]; then
  shift $((OPTIND-1))
fi

if [ $FETCH == 1 ]; then
  echo "removing previous skeletons"
  rm -rf data/skeletons
  echo "fetching skeletons for $CATMAID_PROJECT from $CATMAID_SERVER to data/skeletons"
  catmaid_fetch.py -o data/skeletons &> logs/fetch
else
  echo "Skeleton fetching successfully disabled"
fi

if [ $SMOOTHING == 1 ]; then
    echo "Removing previously Smoothed Skeletons"
    rm -rf data/skeletons_smooth/
    mkdir data/skeletons_smooth/
    echo "Smoothing Skeletons"
    python ../../catmaid/algorithms/smoothing.py -s data/skeletons -d data/skeletons_smooth/
    export CATMAID_FILESOURCE="data/skeletons_smooth"
    export CATMAID_SMOOTHING=1
    echo "Finished Smoothing Skeletons"
fi

# run scripts
cd scripts

bash run.sh "$@"
