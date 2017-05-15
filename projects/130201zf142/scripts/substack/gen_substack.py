import argparse
import catmaid
import catmaid.algorithms.images as IM
import os
import scipy.misc


conn = catmaid.connect()
s = catmaid.get_source(conn)


def gen_images(connection, zrange, center, outdir,
               imgshape=(1024, 1024)):
    if not isinstance(zrange, tuple):
        raise Exception("Must pass in a tuple for the image range!")
    if not isinstance(center, tuple):
        raise Exception("Must pass in a tuple for the center position")
    for z in range(zrange[0], zrange[1]):
        print "Outputting image for z: {}".format(z)
        fn = '{}_sub.png'.format(str(int(z)).zfill(5))
        image, no_overlay = IM.img_from_catmaid(connection, center[0],
                                                center[1], int(z),
                                                imgshape=imgshape,
                                                stack_id=6, tiletype=4,
                                                add_points=False,
                                                image_copy=False)
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        scipy.misc.imsave((outdir + fn), image)


def directory(path):
    if not os.path.isdir(path):
        err_msg = "path is not a directory(%s)"
        raise Exception(err_msg)
    return path


parser = argparse.ArgumentParser()
parser.add_argument(
        '-o', '--output_dir', type=str, required=True)
parser.add_argument(
        '-r', '--range', type=int, required=True, nargs=2)
parser.add_argument(
        '-c', '--center', type=int, required=True, nargs=2)
parser.add_argument(
        '-i', '--imgshape', type=int, required=False, nargs=2)

opts = parser.parse_args()

output = directory(opts.output_dir)
zrange = tuple(opts.range)
center = tuple(opts.center)
if opts.imgshape is not None:
    imgshape = tuple(opts.imgshape)
else:
    imgshape = (1024, 1024)

if __name__ == '__main__':
    gen_images(conn, zrange, center, output, imgshape=imgshape)
