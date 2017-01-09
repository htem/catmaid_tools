#!/bin/bash

SOURCE=`find source_me.sh`

if [ -f $SOURCE ];
then
  . $SOURCE
fi


export DATE=$(date +%y%m%dt%H%M)

ANNOTATION="stats"
ANNOTATIONIGN="blacklist stats_blacklist marker not_neuronal"
#ANNOTATION="reticulospinal vestibulospinal"
#ANNOTATIONIGN="blacklist render_blacklist"
#ANNOTATION="render"
#ANNOTATIONIGN="blacklist render_blacklist marker not_neuronal"
#ANNOTATION="symmetry"
#ANNOTATIONIGN="blacklist symmetry_blacklist marker not_neuronal"
#TYPEEXP="ProjOrLngstLtL"
#TYPEEXP="LngstLeafToLeaf"
TYPEEXP="All"

ANNOTATIONFILE=`echo $ANNOTATION | sed  -e 's/_//g'`
ANNOTATIONFILE=`echo $ANNOTATIONFILE | sed  -e 's/ //g'`
ANNOTATIONIGNFILE=`echo $ANNOTATIONIGN | sed  -e 's/_//g'`
ANNOTATIONIGNFILE=`echo $ANNOTATIONIGNFILE | sed  -e 's/ //g'`

#LENGTHTHRESH=20000
LENGTHTHRESH=1000
if [ "$CATMAID_SMOOTHING" == 1 ]; then
    SUFF="smoothPHYScoord"
else
    SUFF="PHYScoord"
fi
OUTFILE=../../results/exports/${DATE}_130201zf142_160515SWiFT_${TYPEEXP}_ANNOT${ANNOTATIONFILE}_IGN${ANNOTATIONIGNFILE}_${LENGTHTHRESH}nmLenThresh_${SUFF}.txt

if [ -n "$CATMAID_FILESOURCE" ]; then
    FILESOURCE=../../${CATMAID_FILESOURCE}
    echo "Running with smoothed skeleton filesource: $FILESOURCE"
    if [ "$TYPEEXP" == "ProjOrLngstLtL" ]; then
        python export_nodes_from_annotation.py -p -u -a ${ANNOTATION} -i ${ANNOTATIONIGN} -t ${LENGTHTHRESH} -d ${OUTFILE} -f ${FILESOURCE}
    elif [ "$TYPEEXP" == "LngstLeafToLeaf" ]; then
        python export_nodes_from_annotation.py -l -u -a ${ANNOTATION} -i ${ANNOTATIONIGN} -t ${LENGTHTHRESH} -d ${OUTFILE} -f ${FILESOURCE}
    elif [ "$TYPEEXP" == "All" ]; then
        python export_nodes_from_annotation.py -u -a ${ANNOTATION} -i ${ANNOTATIONIGN} -t ${LENGTHTHRESH} -d ${OUTFILE} -f ${FILESOURCE}
    fi
else
    echo "Running export nodes from annotation on server source"
    if [ "$TYPEEXP" == "ProjOrLngstLtL" ]; then
        python export_nodes_from_annotation.py -p -u -a ${ANNOTATION} -i ${ANNOTATIONIGN} -t ${LENGTHTHRESH} -d ${OUTFILE}
    elif [ "$TYPEEXP" == "LngstLeafToLeaf" ]; then
        python export_nodes_from_annotation.py -l -u -a ${ANNOTATION} -i ${ANNOTATIONIGN} -t ${LENGTHTHRESH} -d ${OUTFILE}
    elif [ "$TYPEEXP" == "All" ]; then
        python export_nodes_from_annotation.py -u -a ${ANNOTATION} -i ${ANNOTATIONIGN} -t ${LENGTHTHRESH} -d ${OUTFILE}
    fi
fi
#python export_nodes_from_annotation.py -u -r -a ${ANNOTATION} -i ${ANNOTATIONIGN} -t ${LENGTHTHRESH} -d ${OUTFILE}
#python export_nodes_from_annotation.py -a ${ANNOTATION} -i ${ANNOTATION}_blacklist -s 10.63829787234043 10.63829787234043 10 -d ${OUTFILE}
#gzip ${OUTFILE}
