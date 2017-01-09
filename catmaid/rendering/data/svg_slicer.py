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
                'maeterial': str
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


import svgwrite


class Canvas(object):
    """Draw onto a stack of svgs"""
    def __init__(self, z_height, xy_scale, z_offset=0, attribs=None):
        self.z_height = z_height
        self.z_offset = z_offset
        self.xy_scale = xy_scale
        self.slices = {}  # indexed by z
        if attribs is None:
            self.attribs = {}
        else:
            self.attribs = attribs

    def z_to_slice_index(self, z):
        return int(round((z - self.z_offset) / self.z_height))

    def from_slice_index_to_z(self, i):
        return i * float(self.z_height) + self.z_offset

    def scale_xy(self, x, y):
        return self.xy_scale * x, self.xy_scale * y

    def get_slices(self, z_start, z_end=None):
        z_index = self.z_to_slice_index(z_start)
        if z_index not in self.slices:
            self.slices[z_index] = svgwrite.Drawing()
            self.slices[z_index].z = self.from_slice_index_to_z(z_index)
        if z_end is None:
            return self.slices[z_index]
        if z_end < z_start:
            return self.get_slices(z_end, z_start)
        z_end_index = self.z_to_slice_index(z_end)
        for z in xrange(z_index, z_end_index + 1):
            if z not in self.slices:
                self.slices[z] = svgwrite.Drawing()
                self.slices[z].z = self.from_slice_index_to_z(z)
        return [self.slices[z] for z in xrange(z_index, z_end_index + 1)]

    def make_material(self, name, **opts):
        # TODO
        pass

    def draw_sphere(self, location, radius, material=None):
        # TODO material
        # TODO options
        x, y, z = location
        sx, sy = self.scale_xy(x, y)
        slices = self.get_slices(z - radius, z + radius)
        for s in slices:
            # scale radius by dz
            dz = abs(z - s.z)
            sr = math.cos(dz / radius * math.pi / 2.) * radius
            s.add(svgwrite.shapes.Circle(
                (sx, sy), sr, fill='black', stroke='none'))

    def draw_curve(self, curve, material=None):
        # TODO material
        # TODO options [stroke!]
        for pl in curve:
            s = None
            p = None
            px, py = None, None
            for v in pl:
                x, y, z = v
                sx, sy = self.scale_xy(x, y)
                ts = self.get_slices(z)
                if s is None or ts != s:
                    p = svgwrite.path.Path()
                    p.attribs['stroke'] = 'black'
                    p.attribs['stroke-width'] = '0.181px'
                    p.attribs['fill'] = 'none'
                    s = ts
                    s.add(p)
                    if px is not None:
                        p.push(('M', px, py))
                        p.push(('L', sx, sy))
                    else:
                        p.push(('M', sx, sy))
                else:
                    p.push(('L', sx, sy))
                px, py = sx, sy

    def save_files(self, directory, border=True):
        if not os.path.exists(directory):
            os.makedirs(directory)
        # TODO parallelize this
        # TODO alignment holes
        for sk in self.slices:
            s = self.slices[sk]
            s.attribs.update(self.attribs)
            if border:
                h = self.attribs.get('height', 90)
                w = self.attribs.get('width', 90)
                rect = svgwrite.shapes.Rect(
                    (0, 0), (w, h), stroke='red', fill='none')
                rect.attribs['stroke-width'] = '0.09px'
                s.add(rect)
            f = s.filename
            s.filename = os.path.join(directory, '{:04d}.svg'.format(sk))
            s.save()
            s.filename = f


def layers(*args):
    l = [False] * 20
    for a in args:
        l[a] = True
    return l


# -------------- defaults ------------
default_options = {
    'world': {
        'scale': 1.,
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
            'size': "E:ifnan((float(skeleton['attrs']['speed']) - 4) / (60 - 4) * 0.45 + 0.75, 0.6):1.125",
            'layers': layers(0, 1),
        },
    },
    'synapse.pre.within': {
        'material': 'synapse.pre.within',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.24 + 0.24, 0.15):0.36",
            'layers': layers(0, 5),
        },
    },
    'synapse.pre.outside': {
        'material': 'synapse.pre.outside',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.24 + 0.24, 0.15):0.36",
            'hide': True,
            'layers': layers(0, 6),
        },
    },
    'synapse.post.within': {
        'material': 'synapse.post.within',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.24 + 0.24, 0.15):0.36",
            'layers': layers(0, 7),
        },
    },
    'synapse.post.outside': {
        'material': 'synapse.post.outside',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.24 + 0.24, 0.15):0.36",
            'hide': True,
            'layers': layers(0, 8),
        },
    },
    'synapse.auto.within': {
        'material': 'synapse.auto.within',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.24 + 0.24, 0.15):0.36",
            'layers': layers(0, 9),
        },
    },
    'synapse.auto.outside': {
        'material': 'synapse.auto.outside',
        'options': {
            #'size': 0.024,
            'size': "E:ifnan((float(pre['attrs']['speed']) - 4) / (60 - 4) * 0.24 + 0.24, 0.15):0.36",
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


# -------------- options loading ---------------
def load_options():
    options_var = 'BR_OPTIONS'
    attrs_header_var = 'BR_ATTRS_HEADER'
    attrs_var = 'BR_ATTRS'
    conns_var = 'BR_CONNS'
    skels_var = 'BR_SKELS'
    mat_var = 'BR_MATERIALS'
    save_var = 'BR_SAVE'
    render_var = 'BR_RENDER'
    for var in (skels_var, conns_var):
        if var not in os.environ:
            raise ValueError("Missing {} in os.environ".format(var))

    abs_fn = lambda fn: os.path.abspath(os.path.expanduser(fn))

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
            with open(fn, 'r') as f:
                for l in f:
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
        for sid in conns[cid]['pre'] + conns[cid]['post']:
            if sid in skels:
                # a skeleton that uses this connector is visible
                in_group_skeletons += 1
        if in_group_skeletons > 1:
            conns[cid]['type'] = 'within'
        else:
            conns[cid]['type'] = 'outside'

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
    #save_fn = os.environ.get(save_var, None)
    #render_fn = os.environ.get(render_var, None)
    return options, materials, skels, conns


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


def ifnan(v, d, e=None):
    if math.isnan(v):
        return d
    if e is None:
        return v
    return e


def evaluate_option(opt, context):
    """Evaluate an option string (i.e. "E:...")

    Examples:
    E:(pre.r, pre.g, pre.b) -> (r, g, b) of pre
    E:pre.speed * 0.2 + 5 -> speed of pre * 0.2 + 5
    """
    es, ds = opt[2:].split(':')
    #print(context['skeleton']['attrs'])
    try:
        return eval(es, None, context)
    except Exception:
        return eval(ds, None, context)


# make_material
def make_material(name, **opts):
    warnings.warn("Materials are not yet supported")
    #if name in bpy.data.materials:
    #    return bpy.data.materials[name]
    #mat = bpy.data.materials.new(name)
    #for k in opts:
    #    setattr(mat, k, opts[k])
    #return mat


def resolve_options(opts, context):
    r = {}
    for k in opts:
        opt = opts[k]
        if is_dynamic_option(opt):
            v = evaluate_option(opt, context)
            print("{} -> {}".format(k, v))
            r[k] = v
            #r[k] = evaluate_option(opt, context)
        else:
            r[k] = opt
    return r


def resolve_material(mat, context):
    if mat is None:
        name = 'default'
    else:
        name = mat
    opts = update(context['materials']['default'], context['materials'][name])
    #opts = context['materials'][name]
    if has_dynamic_option(opts):
        name = '{}.{}'.format(context['skeleton']['skeleton_id'], name)
        opts = resolve_options(opts, context)
    return make_material(name, **opts)


def resolve_style(style, context):
    #print(style)
    opts = resolve_options(style.get('options', {}), context)
    mat = resolve_material(style.get('material', None), context)
    return opts, mat


def make_soma(sk, context):
    # name, location, size, mat
    opts, mat = resolve_style(sk['style']['soma'], context)
    opts['location'] = (sk['soma'][0], sk['soma'][1], sk['soma'][2])
    context['canvas'].draw_sphere(
        opts['location'], opts.get('size', 2.625), mat)


def make_curves(sk, context):
    style = sk['style']
    for ck in sk['curves']:
        # get style
        opts, mat = resolve_style(style.get(ck, {}), context)
        # make curve
        context['canvas'].draw_curve(sk['curves'][ck], mat)


def make_synapses(sk, context):
    sid = sk['skeleton_id']
    syns = sk['synapses']
    conns = context['connectors']
    skels = context['skeletons']
    #for cid in syns:
    for syn in syns:
        print("SYNAPSE: %s" % (syn,))
        cid, loc = syn
        # check if connector in conns
        if cid not in conns:
            raise ValueError(
                "Found conn {} in skeleton {} that was not in conns".format(
                    cid, sid))
        conn = conns[cid]
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
        opts['location'] = (loc[0], loc[1], loc[2])
        context['canvas'].draw_sphere(
            opts['location'], opts.get('size', 0.45), mat)

        # clean up context
        del context['pre']
        del context['post']


def add_skeleton(sk, context):
    #default_layers = [True] + [False] * 19
    context['skeleton'] = sk
    # soma
    if 'soma' in sk:
        make_soma(sk, context)
        #soma.parent = root
    # curves [axon, dendrite, apical, etc...]
    make_curves(sk, context)
    # synapses
    make_synapses(sk, context)
    # set soma as parent to all (doesn't have to be visible)
    #for c in curves:
    #    c.parent = root
    #for s in synapses:
    #    s.parent = root
    del context['skeleton']
    #return root


# ------------- world stuff -------------

## disable relationship lines
#def disable_relationship_lines():
#    for area in bpy.context.screen.areas:
#        if area.type == 'VIEW_3D':
#            area.spaces[0].show_relationship_lines = False


## smooth objects
#def smooth_objects():
#    # sometimes getting
#    # RuntimeError: Operator bpy.ops.object.shade_smooth.poll() failed,
#    #   context is incorrect
#    bpy.ops.object.select_all(action='DESELECT')
#    hidden = []
#    for o in bpy.data.objects:
#        if o.hide:
#            hidden.append(o)
#            o.hide = False
#    bpy.ops.object.select_all(action='SELECT')
#    bpy.ops.object.shade_smooth()
#    bpy.ops.object.select_all(action='DESELECT')
#    for h in hidden:
#        h.hide = True


## set lighting
#def set_lighting(**kwargs):
#    l = bpy.data.worlds[0].light_settings
#    for k in kwargs:
#        setattr(l, k, kwargs[k])


def process():
    options, materials, skels, conns = load_options()
    # setup world
    #wopts = options['world']
    # do some setup...
    # turn off relationship lines
    #if not wopts.get('relationship_lines', False):
    #    disable_relationship_lines()

    # setup context
    context = {}
    context['ifnan'] = ifnan
    context['scale'] = options['world'].get('scale', 1.0)
    context['canvas'] = Canvas(
        2000, 0.000135, attribs={'width': '90px', 'height': '90px'})
    context['options'] = options
    context['materials'] = materials
    context['skeletons'] = skels
    context['connectors'] = conns

    # add skeletons
    for sid in skels:
        add_skeleton(skels[sid], context)

    # finish setup...
    # smooth objects?
    #if wopts.get('smooth', True):
    #    smooth_objects()
    # set lighting?
    #set_lighting(**wopts.get('lighting', {}))
    #if save_fn is not None:
    #    save_file(save_fn)
    #if render_fn is not None:
    #    render_to_file(render_fn)
    context['canvas'].save_files('svgs')


if __name__ == '__main__':
    process()
