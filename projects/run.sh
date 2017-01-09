#!/bin/bash

function print_usage(){
  echo "
  This script iterates through all projects and executes the run.sh within
  that project. This script also takes an optional argument that specifies the
  running of a single project.

  If optional scripts or arguments are to be passed through to other run.sh
  scripts, there needs to be two dashes, --, after the indicated project
  argument. An example of this would be:

  bash run.sh -p project -- -f script1 script2 script3

  Note the lack of quotes on the optional scripts, and the -f to disable
  skeleton fetching if necessary.

  Options:

  -p   project   An argument with the name of desired project to be run.

  -h             Prints help message. Exits script.

  Arguments:

  Following any options called ( -p or -h ) you can pass through arguments to
  the corresponding project run.sh. For example, if project 130201zf142
  is called with option -p, any arguments for that project's run.sh would
  follow the -p 130201zf142/ with two dashes ( -- ) separating the project
  option from the arguments for the next script.

  The possible arguments to pass through to a projects run.sh script are:

  -f             An option with no argument to disable skeleton fetching.

  -s             An option with no argument to enable skeleton smoothing

  -h             An option with no argument that will display a help message
                 and exit the script.

  script         The name of a desired script to be run. Can list multiple
                 scripts but must have spaces between scripts and no quotation
                 marks surrounding script names. If one or multiple scripts are
                 passed through, any scripts not called will not be run.
  "
}

# set USER env in case running as cron
USER="`id -un`"
# get directory of this file and change to it
BASEDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)
cd $BASEDIR

# source bash rc (to load any per-user env vars)
RCFILE="source_me.sh"
if [ -e $RCFILE ]
then
    . $RCFILE
fi

# activate any venv
VENV_ACTIVATE="/home/$USER/.virtualenvs/catmaid_tools/bin/activate"
if [ -e $VENV_ACTIVATE ]
then
    echo "Activating virtual environment: $VENV_ACTIVATE"
    . $VENV_ACTIVATE
else
    echo "Virtual environment not found: $VENV_ACTIVATE"
fi

# find list of projects
PROJECTS=`ls -d */`

while getopts ":p:hf" opt; do
  case $opt in
    p)
      echo "Project Specified: $OPTARG" >&2
      PROJECTS=$OPTARG
      ;;
    h)
      print_usage
      exit 1
      ;;
    ?)
      echo "Invalid option: -$OPTARG" >&2
      print_usage
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      print_usage
      exit 1
      ;;
  esac
done

shift $((OPTIND-1))

for PROJECT in ${PROJECTS[*]}
do
    # test if project is disabled by looking for a file named "disable"
    if [ -e "$PROJECT/disable" ]
    then
        echo "Skipping $PROJECT"
        continue
    fi

    cd $PROJECT

    echo "Processing $PROJECT [`date`]"

    bash run.sh "$@"

    echo "Finished processing $PROJECT [`date`]"

    # cd back to directory of this file
    cd $BASEDIR
done
