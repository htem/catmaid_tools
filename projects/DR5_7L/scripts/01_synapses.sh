#!/bin/bash

cd synapses
echo "Running hasudorff.py"
python hausdorff.py
echo "Running verbose_synapses.py"
python verbose_synapses.py
echo "Running synapses.py"
python synapses.py
