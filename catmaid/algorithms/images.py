#!/usr/bin/env python

import numpy
import math

from .. import errors


def get_web_montage(conn, vertex_length, vertex_height, z_index, stack_id=None,
                    tiletype=4, shp=(1024, 1024)):
    """This function takes a range of catmaid tiles on one index (l, h, z) and
       stiches those tiles together into one image."""
    vslices = []
    for i in range(vertex_length[0], vertex_height[0] + 1):
        hslices = []
        for j in range(vertex_length[1], vertex_height[1] + 1):
            try:
                img = conn.fetch_tile(row=i, column=j, z_index=z_index,
                                      stack_id=stack_id, tiletype=tiletype)
                if img.shape != shp:
                    raise ValueError(
                        "invalid tile shape %s does not match actual tile"
                        "shape %s" % (img.shape, shp))
            except errors.InvalidUrl as e:
                img = numpy.zeros(shp)
            hslices.append(img)
        vslices.append(numpy.hstack(hslices))
    full_img = numpy.vstack(vslices)
    return full_img


def img_from_catmaid(conn, ctr_x_px, ctr_y_px, z_index,
                     tiletype=4, tile_shape=(1024, 1024),
                     imgshape=(3072, 3072), points=None, colors=None,
                     stack_id=None, add_points=False, image_copy=False):
    """
    Inputs:
        ctr_x_px -- x coordinate in catmaid pixel space used for centering of
                   output image
        ctr_y_px -- y coordinate in catmaid pixel space used for centering of
                   output image
        z_index -- z index of desired slices
        tile_shape -- the (x, y) shape of a catmaid tile (usually 1024)
        imgshape -- the desired shape of output image
        points -- a list or array of points to be used when adding indicators
                  to the resulting image
        colors -- a list or array of colors(in RGB) to be used when adding
                  indicators to the resulting image
        add_points -- a boolean toggle used to add point indicators for nodes
                      positions on the image
        image_copy = a boolean toggle used to return a second cropped image
                     without the node points
    ----------
    Outputs:
        img -- an image that is cropped from a full image of
               multiple catmaid tiles using the desired imgshape.
        copy -- the cropped image without any points added.
    ----------
    Terms:
        left, right, top, bottom -- denotes pixel coords for each edge
                                    of desired image
        tilespace -- the column, row grid used by catmaid to reference images
        in -- refers to inside image taken from tilespace
        out -- refers to the outside image taken from the tilespace
        inout -- the x or y difference between the inside edge and outside edge
        crop -- the parameters to select the desired image from the full
                image of the catmaid tiles
    """
    left = ctr_x_px - imgshape[0]/2
    right = ctr_x_px + imgshape[0]
    top = ctr_y_px - imgshape[1]/2
    bottom = ctr_y_px + imgshape[1]
    in_left_tilespace = left / float(tile_shape[0])
    in_top_tilespace = top / float(tile_shape[1])
    in_right_tilespace = right / float(tile_shape[0])
    in_bot_tilespace = bottom / float(tile_shape[1])
    out_left_tilespace = int(math.floor(in_left_tilespace))
    out_top_tilespace = int(math.floor(in_top_tilespace))
    out_right_tilespace = int(math.ceil(in_right_tilespace))
    out_bot_tilespace = int(math.ceil(in_bot_tilespace))
    inout_xoff = int(round(
        (in_left_tilespace - out_left_tilespace) * tile_shape[0]))
    inout_yoff = int(round(
        (in_top_tilespace - out_top_tilespace) * tile_shape[1]))
    crop_x_min = inout_xoff
    crop_x_max = inout_xoff + imgshape[0]
    crop_y_min = inout_yoff
    crop_y_max = inout_yoff + imgshape[1]
    full_img = get_web_montage(conn,
                               (out_top_tilespace, out_left_tilespace),
                               (out_bot_tilespace, out_right_tilespace),
                               z_index, stack_id, tiletype, tile_shape)
    img = full_img[crop_y_min:crop_y_max, crop_x_min:crop_x_max]
    if image_copy:
        copy = img
    else:
        copy = None
    if add_points:
        img = add_points_to_image(points, img, imgshape, (left, top), z_index,
                                  radius=8., colors=colors)
    return img, copy


# Makes an image have 3 layers for R, G, and B
def add_depth_to_image(arr, depth=3):
    return numpy.dstack([arr for i in range(depth)])


# Takes an image from catmaid as input, and places circles at node positions
# On the image
def add_points_to_image(points, image, imgshape, top_left_corner, z_index,
                        radius=8., colors=None):
    """
    This function add location indicators for nodes on an image pulled from
    catmaid. This script requires the top left point position of the tilespace
    along with the crop minimums for x and y. This ensures proper placement
    of the circle indicator on the image.
    ---------------
    Inputs:
        points - a list of (x, y) points
        image - a numpy array(image) pulled from catmaid
        imgshape - the resolution of the image
        top_left_corner = the top left corner (x, y) of the image in pixel
                          coordinates
        radius - size of circle (node indicator)
        colors - a list of colors to represent different skeletons (Will be
                 a default color for all nodes if left as None)
    ---------------
    Outputs:
        img - a numpy array(image) that has node positions indicated on a
              catmaid image.
    """
    img = add_depth_to_image(image, depth=3)
    if colors is not None:
        for pt, col in zip(points, colors):
            x_point = pt[1] - top_left_corner[0]
            y_point = pt[2] - top_left_corner[1]
            pts = numpy.array([pt[0], x_point, y_point])
            img = addcircle(img, z_index, radius, pts, col)
        return img
    else:
        for pt in points:
            x_point = pt[1] - top_left_corner[0]
            y_point = pt[2] - top_left_corner[1]
            pts = numpy.array([pt[0], x_point, y_point])
            img = addcircle(img, z_index, radius, pts)
        return img


def addcircle(arr, z_index, r, position=None, color=(232, 96, 28)):
    """
    This function adds a circle to an image by creating a boolean mask where
    the circle will be placed, and adding the node to the image with the
    correct color.
    """
    if position is None:
        position = [i/2 for i in arr.shape]
    y, x = numpy.ogrid[-position[2]:(arr.shape[0]-position[2]),
                       -position[1]:(arr.shape[1]-position[1])]
    circle = (x**2 + y**2) <= r**2
    try:
        arr[circle] = numpy.vstack([numpy.array(color) for i in
                                    range(arr[circle].shape[0])])
    except:
        print ("Skeleton {} will be out of bounds for specified image area on"
               " section {}".format(int(position[0]), z_index))
    return arr
