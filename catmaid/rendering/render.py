#!/usr/bin/env python
"""
Input is:
    skeletons to render (as csv or string or wildcard):
        connOriApiList.csv [c0 = pre, c1 = post] (render each row)
        connOri... [c0 = pre, c1 = post] (render each row)
        convApiList... [c0 = pre, c1 = post]
            (render all posts that have >1 unique pre)
        multiHitList... [c0 = pre, c1 = post] (render each row)
    skeleton repo
        could be server (requires local fetching)
        or file source (don't assume has trees and conns.p)
    attrs csv and attrsheader [optional]
    options file [optional]
    materials file [optional]
"""

import csv
import logging
import os
import subprocess

from . import converter
from .. import source


def prepare_source(s, sids=None, force=True):
    if isinstance(s, source.ServerSource):
        # need to fetch locally and then create a file source
        pass
    if not isinstance(s, source.FileSource):
        raise ValueError("Source should be a FileSource")
    tree_dir = os.path.join(s._skel_source, 'trees')
    conn_fn = os.path.join(tree_dir, 'conns.p')
    # check if conn.p exists
    # check if trees exist
    if force or (not os.path.exists(tree_dir)) or (
            not os.path.exists(conn_fn)):
        _, _, fails = converter.convert_source(s, tree_dir, report_fails=True)
    else:
        fails = None
    if not os.path.exists(tree_dir):
        raise IOError(
            "Failed to build trees in {} from source {}[{}]".format(
                tree_dir, s, s._skel_source))
    if not os.path.exists(conn_fn):
        raise IOError(
            "Failed to build conns.p[{}] from source {}[{}]".format(
                conn_fn, s, s._skel_source))
    return tree_dir, conn_fn, fails


def get_data_dir():
    return os.path.join(
        os.path.dirname(
            os.path.abspath(
                os.path.expanduser(__file__))), 'data')


def get_template_filename():
    return os.path.join(get_data_dir(), 'template.blend')


def get_blender_render_filename():
    return os.path.join(get_data_dir(), 'blender.py')


def get_groups_from_csv(filename, columns=None, group_by=None):
    """
    Get groups of skeleton ids from a csv file

    if columns is None, defaults to (0, 1), using columns 0 and 1
    if group_by is None, each row is considered a group
    if group_by is a number, than that column is used to create groups
    """
    if columns is None:
        columns = (0, 1)
    with open(filename, 'r') as f:
        rows = [row for row in csv.reader(f)]
    if group_by is not None:
        # regroup by column
        key_groups = {}
        for r in rows:
            k = r[group_by]
            if k not in key_groups:
                key_groups[k] = []
            key_groups[k] += [r[c] for c in columns]
        groups = [list(set(key_groups[k])) for k in key_groups]
    else:
        groups = []
        for r in rows:
            groups.append([r[c] for c in columns])
    return groups


def call_blender(
        skel_fns, conns_fn=None, attrs_fn=None, attrs_header=None,
        options_fn=None, materials_fn=None, save_fn=None, render_fn=None,
        template_fn=None, background=True, tree_dir=None):
    env_vars = {}
    if isinstance(skel_fns, (list, tuple)):
        skel_fns = ','.join(skel_fns)
    env_vars['BR_SKELS'] = skel_fns
    if tree_dir is not None:
        env_vars['BR_TREE_DIR'] = tree_dir
    if conns_fn is not None:
        env_vars['BR_CONNS'] = conns_fn
    if attrs_fn is not None:
        env_vars['BR_ATTRS'] = attrs_fn
    if isinstance(attrs_header, (list, tuple)):
        attrs_header = ','.join(attrs_header)
    if attrs_header is not None:
        env_vars['BR_ATTRS_HEADER'] = attrs_header
    if options_fn is not None:
        env_vars['BR_OPTIONS'] = options_fn
    if materials_fn is not None:
        env_vars['BR_MATERIALS'] = materials_fn
    if save_fn is not None:
        env_vars['BR_SAVE'] = save_fn
    if render_fn is not None:
        env_vars['BR_RENDER'] = render_fn
    if template_fn is None:
        tfn = get_template_filename()
    else:
        tfn = template_fn
    if not background:
        env_vars['DISPLAY'] = '0:0'
    cmd = "blender {} -P {}".format(tfn, get_blender_render_filename())
    if background:
        cmd += " -b"
    subprocess.check_call(cmd.split(), env=env_vars)
