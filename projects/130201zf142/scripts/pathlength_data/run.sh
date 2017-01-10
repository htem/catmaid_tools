#!/bin/bash

export DATETIME=$(date +%y%m%dt%H%M)

echo "fetching skeletons"

rm -rf ../../data/skeletons
mkdir -p ../../data/skeletons

catmaid_fetch.py -o ../../data/skeletons

rm -rf ../../data/skeletons_smooth*/
#rm -rf ../../data/skeletons_smooth_kalman_unmasked_fixed
#rm -rf ../../data/skeletons_smooth_kalman_unmasked_not_fixed
#rm -rf ../../data/skeletons_smooth_kalman_masked_fixed
#rm -rf ../../data/skeletons_smooth_kalman_masked_not_fixed
#rm -rf ../../data/skeletons_smooth_gaussian_not_fixed
#rm -rf ../../data/skeletons_smooth_gaussian_fixed

mkdir -p ../../data/skeletons_smooth_kalman_unmasked_fixed
mkdir -p ../../data/skeletons_smooth_kalman_unmasked_not_fixed
mkdir -p ../../data/skeletons_smooth_kalman_masked_fixed
mkdir -p ../../data/skeletons_smooth_kalman_masked_not_fixed
mkdir -p ../../data/skeletons_smooth_gaussian_not_fixed
mkdir -p ../../data/skeletons_smooth_gaussian_fixed

echo "smoothing skeletons"

python ../../../../catmaid/algorithms/smoothing.py -s ../../data/skeletons -d ../../data/ -t 2

mkdir -p ../../results/stats_${DATETIME}/

python ./calculate_pathlength_data.py -s ../../data/ -d ../../results/stats_${DATETIME}/ -a stats -e stats_blacklist blacklist marker not_neuronal
