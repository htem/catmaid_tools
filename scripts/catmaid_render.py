#!/usr/bin/env python
"""
Render some catmaid skeletons using blender

Required options:
    -i, -g, -C: csv file or skeleton ids
    -s: source (usually file source)
Optional:
    -c:  conns file
    -a, -A: attrs file and header
    -o: options file
    -m: materials file
    -S: save file
    -r: render file
    -f: background (usually True)
    -t: blender template file
"""

import argparse
import logging
import os
import subprocess

import catmaid

has_joblib = False
try:
    import joblib.parallel
    has_joblib = True
except ImportError:
    has_joblib = False


def full_path(fn):
    if fn is None:
        return fn
    return os.path.abspath(os.path.expanduser(fn))

parser = argparse.ArgumentParser()

# ---- required ----
parser.add_argument(
    '-i', '--input', required=True,
    help="Input file or list of skeleton ids")

# ---- optional ----
parser.add_argument(
    '-a', '--attrs', default=None,
    help="Attributes csv file")
parser.add_argument(
    '-A', '--attrs_header', default=None,
    help="Attributes csv file header")
parser.add_argument(
    '-c', '--conns', default=None,
    help="Connections pickle file")
parser.add_argument(
    '-C', '--columns', default=None,
    help="Input file columns that contain skeleton ids")
parser.add_argument(
    '-f', '--foreground', default=False, action='store_true',
    help="Run blender in foreground")
parser.add_argument(
    '-F', '--format', default='{}')
parser.add_argument(
    '-g', '--group_by', default=None,
    help="Input file grouping column")
parser.add_argument(
    '-m', '--materials', default=None,
    help="Materials json file")
parser.add_argument(
    '-N', '--name', default=None,
    help="Output file name (overrides groups)")
parser.add_argument(
    '-o', '--options', default=None,
    help="Options json file")
parser.add_argument(
    '-p', '--parallel', default=False, action='store_true',
    help="Render in parallel (requires joblib)")
parser.add_argument(
    '-P', '--parallel_jobs', default=-1, type=int,
    help="Number of renderings to run in parallel")
parser.add_argument(
    '-r', '--render', default=None,
    help="Where to save renders")
parser.add_argument(
    '-s', '--source', default=None,
    help="Catmaid source that contains skeletons")
parser.add_argument(
    '-S', '--save', default=None,
    help="Where to save blend files")
parser.add_argument(
    '-t', '--template', default=None,
    help="Blender template file")
parser.add_argument(
    '-v', '--verbose', default=False, action='store_true',
    help="Enable verbose logging")

# parse command line options
opts = parser.parse_args()

if opts.verbose:
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Options: %s", opts)

if opts.parallel and (not has_joblib):
    raise Exception("parallel rendering requires joblib")

# parse input file for sids (and groups)
iext = os.path.splitext(opts.input)[1].lower()
if iext == '.csv':
    logging.debug("Loading input from csv file: %s", opts.input)
    if opts.columns is None:
        cols = opts.columns
    else:
        cols = map(int, opts.columns.split(','))
    if opts.group_by is not None:
        group_by = int(opts.group_by)
    else:
        group_by = opts.group_by
    groups = catmaid.rendering.render.get_groups_from_csv(
        opts.input, cols, group_by)
    bn = os.path.splitext(os.path.basename(opts.input))[0]
elif iext == '.txt':
    logging.debug("Loading input from text file: %s", opts.input)
    # assuming this is 1 skeleton id per line and all 1 group
    #groups = [[]]
    #with open(opts.input, 'r') as f:
    #    for l in f:
    #        sl = l.strip()
    #        if len(sl):
    #            groups[0].append(sl)
    #bn = os.path.splitext(os.path.basename(opts.input))[0]
    groups = [[opts.input]]
    if opts.name is None:
        opts.name = os.path.splitext(opts.input)[1]
    bn = None
else:  # assuming opts.input is a list of skeleton ids all 1 group
    logging.debug("Loading input from string: %s", opts.input)
    groups = [opts.input.split(',')]
    bn = None
logging.debug("Found %s groups", len(groups))

all_sids = []
for g in groups:
    all_sids += g

# prepare source
logging.debug("Getting source: %s", opts.source)
s = catmaid.get_source(opts.source)
logging.debug("Preparing source: %s", s)
# TODO figure out a way to check the source to see if conversion is needed
tree_dir, conn_fn, fails = catmaid.rendering.render.prepare_source(s, all_sids)
#tree_dir = opts.source + '/trees'
#conn_fn = opts.source + '/trees/conns.p'
#fails = None
logging.debug("Trees are in %s, conn file is %s", tree_dir, conn_fn)
if opts.conns is not None:
    # TODO figure out what to do here
    assert opts.conns == conn_fn

# make general kwargs
kwargs = {
    'conns_fn': conn_fn,
    'attrs_fn': full_path(opts.attrs),
    'attrs_header': opts.attrs_header,
    'options_fn': full_path(opts.options),
    'materials_fn': full_path(opts.materials),
    'template_fn': full_path(opts.template),
    'background': not opts.foreground,
}

if bn is None:
    if opts.save is None:
        opts.save = "saves"
    if opts.render is None:
        opts.render = "renders"
else:
    if opts.save is None:
        opts.save = os.path.join(bn, "saves")
    else:
        opts.save = os.path.join(opts.save, bn, "saves")
    if opts.render is None:
        opts.render = os.path.join(bn, "renders")
    else:
        opts.render = os.path.join(opts.render, bn, "renders")
save_dir = full_path(opts.save)
if not os.path.exists(save_dir):
    os.makedirs(save_dir)
render_dir = full_path(opts.render)
if not os.path.exists(render_dir):
    os.makedirs(render_dir)

# resolve all arguments (skel_fns and gkwargs)
rendering_args = []
for g in groups:
    skel_fns = []
    for sid in g:
        if os.path.splitext(sid)[1].lower() == '.txt':
            skel_fns.append(sid)
        else:
            skel_fns.append(os.path.join(tree_dir, '{}.p'.format(sid)))
    # make specific kwargs [save_fn, render_fn]
    gkwargs = {}
    for k in kwargs:
        gkwargs[k] = kwargs[k]
    if opts.name is None:
        bn = opts.format.format('_'.join(g))
    else:
        bn = opts.name
    gkwargs['tree_dir'] = tree_dir
    gkwargs['save_fn'] = os.path.join(save_dir, bn)
    gkwargs['render_fn'] = os.path.join(render_dir, bn)
    rendering_args.append((skel_fns, gkwargs))


def render(skel_fns, kwargs):
    logging.debug("Rendering %s with %s", skel_fns, kwargs)
    catmaid.rendering.render.call_blender(skel_fns, **kwargs)


if opts.parallel:
    # render each group in parallel
    logging.debug(
        "Parallel rendering %s jobs with %s cores",
        len(rendering_args), opts.parallel_jobs)
    #joblib.Parallel(n_jobs=opts.parallel_jobs, verbose=int(opts.verbose))(
    #    joblib.delayed(catmaid.rendering.render.call_blender)(a[0], **a[1])
    #    for a in rendering_args)
    joblib.Parallel(n_jobs=opts.parallel_jobs, verbose=50)(
        joblib.delayed(render)(a[0], a[1])
        for a in rendering_args)
else:
    for args in rendering_args:
        render(args[0], args[1])
        #skel_fns, gkwargs = args
        #logging.debug("Rendering %s with %s", skel_fns, gkwargs)
        ## render
        #catmaid.rendering.render.call_blender(skel_fns, **gkwargs)

if fails is None:
    print("Unknown number of failed conversions, used existing trees")
else:
    if len(fails):
        print("Failed to convert skeletons: %s" % fails)
    else:
        print("No failed conversions")
