#!/usr/bin/env python
"""
Load a tree(s) from file and render it

Options are:
    - Inputs:
        - tree file(s)
        - options/materials file
        - connector(s) file
        - attributes (physio) file
    - Options:
        - attributes file header/options


Options file
    'default': {
        'curves': {
            'axon': {
                'material': str
                'options':
"""

import copy
import csv
import glob
import json
import math
import os
import pickle
import warnings
import random
import time

try:
    import bpy
    in_blender = True
except ImportError:
    in_blender = False


def layers(*args):
    l = [False] * 20
    for a in args:
        l[a] = True
    return l


# -------------- defaults ------------
default_options = {
    'world': {
        'scale': 1E-5,
        'center': (0., 0., 0.),
        'relationship_lines': False,
        'lighting': {
            'use_environment_light': True,
            'environment_energy': 0.2,
        },
        'smooth': True
    },
    'axon': {
        'material': 'axon',
        'options': {
            'bevel_depth': 0.004,  # size
            'fill_mode': 'FULL',
            'dimensions': '3D',
            'layers': layers(0, 2),
        },
    },
    'dendrite': {
        'material': 'dendrite',
        'options': {
            'bevel_depth': 0.010,
            'fill_mode': 'FULL',
            'dimensions': '3D',
            'layers': layers(0, 3),
        },
    },
    'apical': {
        'material': 'apical',
        'options': {
            'bevel_depth': 0.018,
            'fill_mode': 'FULL',
            'dimensions': '3D',
            'layers': layers(0, 4),
        },
    },
    'soma': {
        'material': 'soma',
        'options': {
            #'size': 0.075,
            'size': "E:ifnan((float(skeleton['attrs']['speed']) - 4) / (60 - 4) * 0.03 + 0.05, 0.04):0.075",
            'layers': layers(0, 1),
        },
    },
    'synapse.pre.within': {
        'material': 'synapse.pre.within',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.016 + 0.016, 0.01):0.024",
            'layers': layers(0, 5),
        },
    },
    'synapse.pre.outside': {
        'material': 'synapse.pre.outside',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.016 + 0.016, 0.01):0.024",
            'hide': True,
            'layers': layers(0, 6),
        },
    },
    'synapse.post.within': {
        'material': 'synapse.post.within',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.016 + 0.016, 0.01):0.024",
            'layers': layers(0, 7),
        },
    },
    'synapse.post.outside': {
        'material': 'synapse.post.outside',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.016 + 0.016, 0.01):0.024",
            'hide': True,
            'layers': layers(0, 8),
        },
    },
    'synapse.auto.within': {
        'material': 'synapse.auto.within',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.016 + 0.016, 0.01):0.024",
            'layers': layers(0, 9),
        },
    },
    'synapse.auto.outside': {
        'material': 'synapse.auto.outside',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.016 + 0.016, 0.01):0.024",
            'hide': True,
            'layers': layers(0, 10),
        },
    },
}

default_materials = {
    # 'default' gets applied to all materials first
    'default': {
        'diffuse_color': (1., 0., 0.),
        'diffuse_shader': 'LAMBERT',
        'diffuse_intensity': 1.,
        'specular_color': (1., 1., 1.),
        'specular_shader': 'COOKTORR',
        'specular_intensity': 0.0,
        'emit': 0.,
        'use_transparency': False,
        'alpha': 1.,
        'ambient': 1.,
    },
    'axon': {
        'specular_intensity': 1.,
        'emit': 1.,
        #'diffuse_color': (.6, .6, .6),
        #'use_transparency': True,
        #'alpha': 0.5,
        'diffuse_color': "E:(float(skeleton['attrs']['r'])/255., float(skeleton['attrs']['g'])/255., float(skeleton['attrs']['b'])/255.):(0.6, 0.6, 0.6)",
        #'use_transparency': False,
        #'alpha': 1.0,
        'use_transparency': True,
        #'use_transparency': "E:ifnan(float(skeleton['attrs']['r']),True,False):True",
        'alpha': "E:ifnan(float(skeleton['attrs']['r']),0.05,1.):0.05",
    },
    'dendrite': {
        #'specular_intensity': 0.5,
        #'diffuse_color': (.6, .6, .6),
        #'use_transparency': True,
        #'alpha': 0.5,
        'diffuse_color': "E:(float(skeleton['attrs']['r'])/255., float(skeleton['attrs']['g'])/255., float(skeleton['attrs']['b'])/255.):(0.6, 0.6, 0.6)",
        #'use_transparency': False,
        #'alpha': 1.0,
        'use_transparency': True,
        #'use_transparency': "E:ifnan(float(skeleton['attrs']['r']),True,False):True",
        'alpha': "E:ifnan(float(skeleton['attrs']['r']),0.05,1.):0.05",
    },
    'soma': {
        #'specular_intensity': 0.5,
        #'diffuse_color': (.6, .6, .6),
        #'use_transparency': True,
        #'alpha': 0.5,
        'diffuse_color': "E:(float(skeleton['attrs']['r'])/255., float(skeleton['attrs']['g'])/255., float(skeleton['attrs']['b'])/255.):(0.6, 0.6, 0.6)",
        'use_transparency': True,
        #'use_transparency': "E:ifnan(float(skeleton['attrs']['r']),True,False):True",
        'alpha': "E:ifnan(float(skeleton['attrs']['r']),0.3,1.):0.3",
        #'use_transparency': False,
        #'alpha': 1.0,
    },
    'apical': {
        #'specular_intensity': 0.5,
        #'diffuse_color': (.6, .6, .6),
        #'use_transparency': True,
        #'alpha': 0.5,
        'diffuse_color': "E:(float(skeleton['attrs']['r'])/255., float(skeleton['attrs']['g'])/255., float(skeleton['attrs']['b'])/255.):(0.6, 0.6, 0.6)",
        #'use_transparency': False,
        #'alpha': 1.0,
        'use_transparency': True,
        #'use_transparency': "E:ifnan(float(skeleton['attrs']['r']),True,False):True",
        'alpha': "E:ifnan(float(skeleton['attrs']['r']),0.05,1.):0.05",
    },
    'synapse.pre.within': {
        #'diffuse_color': (0., 1., 1.),
        'diffuse_color': "E:(float(pre['attrs']['r'])/255., float(pre['attrs']['g'])/255., float(pre['attrs']['b'])/255.):(0., 1., 1.)",
    },
    'synapse.pre.outside': {
        'diffuse_color': (0., 1., 1.),
        'use_transparency': True,
        'use_raytrace': False,
        'alpha': 0.05,
    },
    'synapse.post.within': {
        #'diffuse_color': (1., 0., 0.),
        'diffuse_color': "E:(float(post['attrs']['r'])/255., float(post['attrs']['g'])/255., float(post['attrs']['b'])/255.):(1., 0., 0.)",
    },
    'synapse.post.outside': {
        'diffuse_color': (1., 0., 0.),
        'use_transparency': True,
        'use_raytrace': False,
        'alpha': 0.05,
    },
    'synapse.auto.within': {
        #'diffuse_color': (0., 1., 1.),
        'diffuse_color': "E:(float(pre['attrs']['r'])/255., float(pre['attrs']['g'])/255., float(pre['attrs']['b'])/255.):(0., 1., 1.)",
    },
    'synapse.auto.outside': {
        'diffuse_color': (0., 1., 0.),
        'use_transparency': True,
        'use_raytrace': False,
        'alpha': 0.05,
    },

    # any other custom ...
}


def update(a, b):
    c = copy.deepcopy(a)
    for k in b:
        if isinstance(b[k], dict) and k in a:
            c[k] = update(a[k], b[k])
        else:
            c[k] = b[k]
    return c


class Timer(object):
    def __init__(self, status):
        if status:
            self.enable()
        else:
            self.disable()
        self.times = {}
        self.max_dts = {}

    def nothing(self, *args, **kwargs):
        pass

    def _tick(self, key):
        self.times[key] = time.time()

    def _tock(self, key):
        if key in self.times:
            dt = time.time() - self.times[key]
            print("Timer: %0.6f, %s" % (dt, key))
            self.max_dts[key] = max(dt, self.max_dts.get(key, float('-inf')))

    def disable(self):
        self.tick = self.nothing
        self.tock = self.nothing
        self.summarize = self.nothing
        self.decorate = lambda f: f

    def enable(self):
        self.tick = self._tick
        self.tock = self._tock
        self.decorate = self._decorate
        self.summarize = self._summarize

    def _decorate(self, f):
        def w(*args, **kwargs):
            self.tick(f.__name__)
            r = f(*args, **kwargs)
            self.tock(f.__name__)
            return r
        return w

    def _summarize(self):
        print("Max dts")
        for k in self.max_dts:
            print("\t%0.6f, %s" % (self.max_dts[k], k))


# to enable timing, use:
# timer = Timer(True)
# to disable timing, use:
timer = Timer(False)


# -------------- options loading ---------------
options_var = 'BR_OPTIONS'
attrs_header_var = 'BR_ATTRS_HEADER'
attrs_var = 'BR_ATTRS'
conns_var = 'BR_CONNS'
skels_var = 'BR_SKELS'
mat_var = 'BR_MATERIALS'
save_var = 'BR_SAVE'
render_var = 'BR_RENDER'
tree_dir_var = 'BR_TREE_DIR'

# for var in (options_var, attrs_header_var, attrs_var, conns_var, skels_var):
for var in (skels_var, conns_var):
    if var not in os.environ:
        raise ValueError("Missing {} in os.environ".format(var))

abs_fn = lambda fn: os.path.abspath(os.path.expanduser(fn))

tree_dir = os.environ.get(tree_dir_var, None)
# load skel files (env)
skelfns = os.environ[skels_var].strip().split(',')
# expand any wildcards
for fn in skelfns[:]:
    if '*' in fn:
        skelfns.remove(fn)
        skelfns.extend(glob.glob(fn))
    if '.txt' in fn:
        skelfns.remove(fn)
        d = os.path.dirname(fn)
        if tree_dir is not None:
            d = tree_dir
        with open(fn, 'r') as f:
            for l in f:
                fn = l.strip()
                if os.path.splitext(fn)[1].lower() != '.p':
                    # this looks like just a id, not a path
                    skelfns.append(os.path.join(d, fn) + '.p')
                else:
                    skelfns.append(os.path.join(d, l.strip()))
skels = {}  # keys = skeleton ids
for fn in skelfns:
    with open(abs_fn(fn), 'rb') as f:
        s = pickle.load(f)
    sid = s['skeleton_id']
    s['attrs'] = {}  # placeholder for attributes
    skels[sid] = s


# load connectors file (pickle)
with open(abs_fn(os.environ[conns_var]), 'rb') as f:
    conns = pickle.load(f)
for cid in conns:
    in_group_skeletons = 0
    conns[cid]['type'] = 'outside'
    for sid in conns[cid]['pre']:
        if sid in skels:
            for sid in conns[cid]['post']:
                if sid in skels:
                    conns[cid]['type'] = 'within'
    #for sid in conns[cid]['pre'] + conns[cid]['post']:
    #    if sid in skels:
    #        # a skeleton that uses this connector is visible
    #        in_group_skeletons += 1
    #if in_group_skeletons > 1:
    #    conns[cid]['type'] = 'within'
    #else:
    #    conns[cid]['type'] = 'outside'

if attrs_header_var in os.environ:
    # load attributes header (env)
    attrs_header = os.environ[attrs_header_var].strip().split(',')
else:
    attrs_header = None

if attrs_var in os.environ:
    if attrs_header is None:
        warnings.warn(
            "{} was not set, reading first line of {} as header".format(
                attrs_header_var, os.environ[attrs_var]))
    # load attributes file (csv)
    with open(abs_fn(os.environ[attrs_var]), 'r') as f:
        attrs = [i for i in csv.DictReader(f, attrs_header)]
    # add attrs to skeletons
    for r in attrs:
        sid = int(float(r['skeleton_id']))
        if sid in skels:
            skels[sid]['attrs'] = r

# load options file (json), and cascade with defaults
if options_var in os.environ:
    with open(abs_fn(os.environ[options_var]), 'r') as f:
        options = update(default_options, json.load(f))
else:
    options = default_options

# load materials file (json) and cascade with defaults
if mat_var in os.environ:
    with open(abs_fn(os.environ[mat_var]), 'r') as f:
        materials = update(default_materials, json.load(f))
else:
    materials = default_materials

# build styles (materials & options) for each object
for sid in skels:
    if sid in options:
        # cascade custom style with defaults
        style = update(options, options[sid])
    else:
        style = options
    skels[sid]['style'] = style

# save filename
save_fn = os.environ.get(save_var, None)
render_fn = os.environ.get(render_var, None)


# -------------- object building ---------------

def is_dynamic_option(opt):
    return (
        isinstance(opt, str) and
        len(opt) > 2 and opt[0] == 'E' and opt[1] == ':')


def has_dynamic_option(opts):
    for k in opts:
        if is_dynamic_option(opts[k]):
            return True
    return False


def has_label(label, labels, v, d, match=None):
    if match is None:
        match = 'loose'
    if match == 'loose':
        label = label.lower()
        for l in labels:
            if label in l.lower():
                return v
        return d
    if match == 'case':
        for l in labels:
            if label in l:
                return v
        return d
    if match == 'strict':
        if label in labels:
            return v
        return d


def ifnan(v, d, e=None):
    if math.isnan(v):
        return d
    if e is None:
        return v
    return e


def in_list(l, item, if_yes, if_no):
    if item in l:
        return if_yes
    else:
        return if_no


def evaluate_option(opt, context):
    """Evaluate an option string (i.e. "E:...")

    Examples:
    E:(pre.r, pre.g, pre.b) -> (r, g, b) of pre
    E:pre.speed * 0.2 + 5 -> speed of pre * 0.2 + 5
    """
    es, ds = opt[2:].split(':')
    # print(context['skeleton']['attrs'])
    try:
        return eval(es, None, context)
    except Exception:
        return eval(ds, None, context)


# make_material
def make_material(name, **opts):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    for k in opts:
        setattr(mat, k, opts[k])
    return mat


def resolve_options(opts, context):
    r = {}
    for k in opts:
        opt = opts[k]
        if is_dynamic_option(opt):
            v = evaluate_option(opt, context)
            # print("{} -> {}".format(k, v))
            r[k] = v
            # r[k] = evaluate_option(opt, context)
        else:
            r[k] = opt
    return r


def resolve_material(mat, context):
    if mat is None:
        name = 'default'
    else:
        name = mat
    opts = update(context['materials']['default'], context['materials'][name])
    # opts = context['materials'][name]
    if has_dynamic_option(opts):
        name = '{}.{}'.format(context['skeleton']['skeleton_id'], name)
        opts = resolve_options(opts, context)
    return make_material(name, **opts)


@timer.decorate
def resolve_style(style, context):
    # print(style)
    opts = resolve_options(style.get('options', {}), context)
    mat = resolve_material(style.get('material', None), context)
    return opts, mat


@timer.decorate
def make_root(sk, context):
    opts = {}
    opts['size'] = 0.1
    # opts['location'] = (
    #    sk['root'][0] * context['scale'],
    #    sk['root'][1] * context['scale'],
    #    sk['root'][2] * context['scale'],
    # )
    opts['location'] = (0., 0., 0.)
    root = make_sphere(sk['neuron_id'], opts, resolve_material(None, context))
    root.hide = True
    root.hide_render = True
    root.layers = [True] * 20
    return root


def make_soma(sk, context):
    # name, location, size, mat
    opts, mat = resolve_style(sk['style']['soma'], context)
    opts['location'] = (
        sk['soma'][0] * context['scale'],
        sk['soma'][1] * context['scale'],
        sk['soma'][2] * context['scale'])
    return make_sphere('{}.soma'.format(sk['neuron_id']), opts, mat)


# make_sphere
@timer.decorate
def make_sphere(name, opts=None, mat=None):
    if opts is None:
        opts = dict(size=0.075, location=(0, 0, 0))
    kwargs = {}
    for k in ('size', 'location'):
        if k in opts:
            kwargs[k] = opts.pop(k)
    bpy.ops.mesh.primitive_uv_sphere_add(**kwargs)
    sphere = bpy.context.object
    sphere.name = name
    for k in opts:
        setattr(sphere, k, opts[k])
    if mat is not None:
        sphere.data.materials.append(mat)
    return sphere


@timer.decorate
def make_curve(name, opts=None, mat=None):
    if opts is None:
        opts = dict(dimensions='3D', fill_mode='FULL', bevel_depth=0.004)
    # print(opts)
    curve = bpy.data.curves.new(name=name, type='CURVE')
    for k in opts:
        # for some reason fill_mode doesn't have 'FULL' here
        if k == 'fill_mode':
            continue
        if k == 'layers':
            continue
        setattr(curve, k, opts[k])
    return curve


@timer.decorate
def finish_curve(curve, opts=None, mat=None):
    if opts is None:
        opts = dict(dimensions='3D', fill_mode='FULL', bevel_depth=0.004)
    obj = bpy.data.objects.new(curve.name, curve)
    for k in opts:
        if k == 'layers':
            continue
        setattr(obj.data, k, opts[k])
    # print("Curve layers 1: %s" % str([l for l in obj.layers]))
    bpy.context.scene.objects.link(obj)
    if mat is not None:
        obj.data.materials.append(mat)
    # layers have to be set AFTER linking
    if 'layers' in opts:
        obj.layers = opts['layers']
    return obj


# add_poly
@timer.decorate
def add_poly(curve, verts, scale):
    p = curve.splines.new('POLY')
    p.points.add(len(verts) - 1)
    for i in range(len(verts)):
        v = verts[i]
        p.points[i].co = (v[0] * scale, v[1] * scale, v[2] * scale, 1.)
    return p


@timer.decorate
def make_curves(sk, context):
    scale = context['scale']
    style = sk['style']
    curves = []
    for ck in sk['curves']:
        # get style
        opts, mat = resolve_style(style.get(ck, {}), context)
        # make curve
        curve = make_curve(
            "{}.{}".format(sk['skeleton_id'], ck), opts, mat)
        # make poly(s)
        for pl in sk['curves'][ck]:
            add_poly(curve, pl, scale)
        # link curve
        obj = finish_curve(curve, opts, mat)
        # return objects (for setting of parent)
        curves.append(obj)
    return curves


@timer.decorate
def make_synapses(sk, context):
    sid = sk['skeleton_id']
    syns = sk['synapses']
    conns = context['connectors']
    skels = context['skeletons']
    synapses = []
    # for cid in syns:
    for syn in syns:
        # print("SYNAPSE: %s" % (syn,))
        cid, loc, labels = syn
        # check if connector in conns
        if cid not in conns:
            raise ValueError(
                "Found conn {} in skeleton {} that was not in conns".format(
                    cid, sid))
        conn = conns[cid]
        context['labels'] = labels
        ctype = "synapse."
        # is skel pre or post synaptic?
        if sid in conn['pre']:
            if sid in conn['post']:
                # deal with auto synapses
                context['pre'] = sk
                context['post'] = sk
                ctype += "auto.{}".format(conn['type'])
            else:
                context['pre'] = sk
                # find post cell
                context['post'] = None
                for psid in conn['post']:
                    if psid in skels:
                        context['post'] = skels[psid]
                    # TODO what to do when >1 post?
                ctype += "pre.{}".format(conn['type'])
        elif sid in conn['post']:
            context['post'] = sk
            # find pre cell
            context['pre'] = None
            for psid in conn['pre']:
                if psid in skels:
                    context['pre'] = skels[psid]
                # TODO what to do when >1 pre?
            ctype += "post.{}".format(conn['type'])
        else:
            raise ValueError(
                "Skeleton {} contains conn {} but conn "
                "doesn't contain skeleton".format(sid, cid))
        opts, mat = resolve_style(sk['style'].get(ctype, {}), context)
        opts['location'] = (
            loc[0] * context['scale'],
            loc[1] * context['scale'],
            loc[2] * context['scale'],
        )
        name = '{}.{}'.format(sid, cid)
        synapses.append(make_sphere(name, opts, mat))

        # clean up context
        del context['labels']
        del context['pre']
        del context['post']
    return synapses


@timer.decorate
def add_skeleton(sk, context):
    # default_layers = [True] + [False] * 19
    context['skeleton'] = sk
    root = make_root(sk, context)
    # soma
    if 'soma' in sk:
        soma = make_soma(sk, context)
        soma.parent = root
    # curves [axon, dendrite, apical, etc...]
    curves = make_curves(sk, context)
    # synapses
    synapses = make_synapses(sk, context)
    # set soma as parent to all (doesn't have to be visible)
    for c in curves:
        c.parent = root
    for s in synapses:
        s.parent = root
    del context['skeleton']
    return root


# ------------- world stuff -------------

# disable relationship lines
def disable_relationship_lines():
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces[0].show_relationship_lines = False


# smooth objects
def smooth_objects():
    # sometimes getting
    # RuntimeError: Operator bpy.ops.object.shade_smooth.poll() failed,
    #   context is incorrect
    bpy.ops.object.select_all(action='DESELECT')
    hidden = []
    for o in bpy.data.objects:
        if o.hide:
            hidden.append(o)
            o.hide = False
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.shade_smooth()
    bpy.ops.object.select_all(action='DESELECT')
    for h in hidden:
        h.hide = True


def random_color():
    r, g, b = [random.random() for i in range(3)]
    return r, g, b


# set lighting
def set_lighting(**kwargs):
    l = bpy.data.worlds[0].light_settings
    for k in kwargs:
        setattr(l, k, kwargs[k])


@timer.decorate
def process():
    # setup world
    wopts = options['world']
    # do some setup...
    # turn off relationship lines
    if not wopts.get('relationship_lines', False):
        disable_relationship_lines()

    # setup context
    context = {}
    context['ifnan'] = ifnan
    context['has_label'] = has_label
    context['scale'] = options['world'].get('scale', 1.0)
    context['options'] = options
    context['materials'] = materials
    context['skeletons'] = skels
    context['connectors'] = conns
    context['random_color'] = random_color
    context['in_list'] = in_list

    # add skeletons
    for sid in skels:
        add_skeleton(skels[sid], context)

    # finish setup...
    # smooth objects?
    if wopts.get('smooth', True):
        smooth_objects()
    # set lighting?
    set_lighting(**wopts.get('lighting', {}))
    if save_fn is not None:
        save_file(save_fn)
    # TODO render
    if render_fn is not None:
        render_to_file(render_fn)


# -------------- general settings ---------------

# scale (to_vertex?)

# save files
def save_file(fn):
    bpy.ops.wm.save_as_mainfile(filepath=fn)


@timer.decorate
def render_to_file(fn):
    # remove extension
    bfn, ext = os.path.splitext(fn)
    # don't parse extension, expect that the template is setup
    bpy.context.scene.render.filepath = bfn
    bpy.ops.render.render(write_still=True)


def test():
    pass

if __name__ == '__main__':
    if in_blender:
        process()
    else:
        test()
    timer.summarize()
