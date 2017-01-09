#!/usr/bin/env python
"""

usage : mat_to_csv <infile> [<outfile>] -c columns -s sep -d dtype
"""

import argparse

from catmaid.utils.mattocsv import mat_to_csv


def parse_arguments(args=None):
    p = argparse.ArgumentParser()
    p.add_argument('infile')
    p.add_argument('outfile', default=None, nargs="?")
    p.add_argument('-c', '--columns', default=None, nargs="+", type=int)
    p.add_argument('-s', '--separator', default=',')
    p.add_argument('-d', '--dtype', default=None, nargs="+", type=str)
    args = p.parse_args()
    return args


def run():
    args = parse_arguments()
    mat_to_csv(args.infile, args.outfile)

if __name__ == '__main__':
    run()
