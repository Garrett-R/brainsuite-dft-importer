#####################################################################
#  This takes a BrainSuite .dft file and imports the 3D model (of the curves)
#  into Blender
#
#  To use it, just copy and paste this whole thing into Blender's text editor,
#  edit the parameters below, then hit "Run Script".
#
#  by: Garrett R
#
#####################################################################

# path to .dft file
dft_file = "/home/garrett/Desktop/corticospinal.dft"

# (integer) setting curve_step to a number higher than 1 causes the program to
# skip over tracts, so setting to 2 will give you half the number of tracts
# the most curves I've done is 5000 and it takes about an hour to import.
curve_step = 5
# (integer) setting vertex_step to a number higher than 1 causes the program to
# skip over vertices, so setting to 2 will give you half the number of vertices
vertex_step = 1

# res_length: (integer) the resolution along the length of the fiber.
# If using auto_color and colors get a bit funky, then it's because
# rectangles aren't long enough.  Turn this down or increase res_circum.
res_length = 5

# res_circum: (integer) the resolution around the circumference of tube
res_circum = 1

# radius of the tubes (float)
radius = 0.2

# color the curve according to its direction, R,G,B for x,y,z-directions
# Setting this also converts it from NURBS/poly curve to mesh
auto_color = True

# moves curves to be near center (ie global origin)
center_curves = True

verbose = True

#######################################
#       don't edit beyond here        #
#######################################

import bpy


def main():

    # if there's already a nurbs circle in existence, it could cause problems
    if bpy.data.objects.get('NurbsCircle') is not None:
        print("WARNING: A 'NurbsCircle' object already existed!"
              "The script will use that instead of generating a new one... "
              "I hope that's what you wanted.")

    # start timer
    if verbose:
        import time
        tic = time.time()

    curves, colors = dft_read(dft_file)

    # initiate list of curves, used at the end to move them all to
    # the global origin
    curve_list = []

    num_curves = len(curves)

    # loop through all curves, but only create the curve in Blender for
    # every (curve_step)-th curve.
    for i in range(num_curves):
        if i % curve_step == 0:
            verts = curves[i][::vertex_step, :]
            color = colors[i]
            curve = make_curve(verts, radius=radius, res_length=res_length,
                               res_circum=res_circum,
                               color=color, auto_color=auto_color)
            curve_list.append(curve)
            if verbose:
                print("Finished curve " + str(i) + "/" + str(num_curves))

    # after the brain is imported, move it near the global origin
    if center_curves:
        # Move all curves based on 1st curve's displacement from origin
        trans_vector = -curve_list[0].location
        for curve in curve_list:
            curve.location += trans_vector

    print("Done")
    if verbose:
        toc = time.time()
        print("That took", toc-tic, "seconds.")


def dft_read(dft_filename, verbose=False):
    """Simple reader for BrainSuite's .dft files.

    This reads a .dft file and outputs a the vertices corresponding to the
    curves and the color of each curve.

    Note: if using Python 2, you must do
    "from __future__ import print_function" before calling this function.

    EXAMPLE USAGE
        list_curves, list_colors = dft_read("subj1_curves.dft")

    INPUT:
        > dft_filename: string of the file to be read.
        > verbose: Boolean, set to True if you want verbose output

    OUTPUT:
        > list_curves: list with each element representing one curve using a
            (N x 3) NumPy array where each row is a vertex.
        > list_color: list where n-th element is the a 3-element list of ints
            in the form [R,G,B] corresponding to color of the n-th curve"""
    import struct
    import xml.etree.ElementTree as ET
    import numpy as np

    # list of curves to return,
    list_curves = []

    # if verbose is set, we'll time how long it takes to finish
    if verbose:
        import time
        tic = time.time()

    # open the file to be read in binary mode
    with open(dft_filename, "rb") as fo:

        # for now, I just discard the first 8 bytes which are the text label
        # for the file version
        _ = fo.read(8)[0]
        # discard the next 4 bytes corresponding to the version code.
        _ = fo.read(4)[0]
        # read in as an integer the header size  (4 bytes)
        hdrsize = struct.unpack('i', fo.read(4))[0]
        # start of data of the curve vertices
        dataStart = struct.unpack('i', fo.read(4))[0]
        # start of XML data which gives the color of each curve
        mdoffset = struct.unpack('i', fo.read(4))[0]
        # Discard the next 4 bytes ("pdoffset") since I'm not sure what they do
        _ = struct.unpack('i', fo.read(4))[0]
        # Number of curves (read in as an unsigned int32)
        nContours = struct.unpack('I', fo.read(4))[0]

        if verbose:
            print("the number of curves is: ", nContours)

        # move current file reading position to start of xml block
        fo.seek(mdoffset)

        # calculate size of the XML block
        xml_block_size = dataStart - mdoffset
        # read in XML block
        xml_block = fo.read(xml_block_size)

        # get root element of XML block
        root = ET.fromstring(xml_block)
        # list of all the colors.  Each color is represented by a
        # list of 3 elements corresponding to RGB.
        list_colors = []

        for child in root:
            temp_color = child.attrib['color']
            # convert to float
            temp_color = [float(x) for x in temp_color.split(" ")]
            list_colors.append(temp_color)

        # move current file reading position to start of curve vertex data
        fo.seek(dataStart)

        # loop through every curve
        for curve in range(nContours):
            # number of points in current curve
            num_points = struct.unpack('i', fo.read(4))[0]

            if verbose:
                print("Number of points in current curve:", num_points)

            # in order to read off all the points of a curve in one fell swoop,
            # we need to know the number of (4 byte) floats to read off
            num_floats = num_points*3
            points = struct.unpack('f'*num_floats, fo.read(4*num_floats))

            # make NumPy array from the points.  We reshape it to be a
            # Nx3 array.
            points_arr = np.array(points).reshape((-1, 3))

            # add to the list of curves
            list_curves.append(points_arr)

        if verbose:
            toc = time.time()
            print("Finished processing", nContours,
                  "curves in", toc-tic, "seconds.")

        return list_curves, list_colors


def color_tube(obj):
    """Given a long tube, whose sides are made of long, skinny rectangles and
    whose caps are made of triangles, this colors the tube based on its
    directions, so red for x-direction, green for y-direction,
    blue for z-direction."""

    mesh = obj.data
    scn = bpy.context.scene
    num_verts = len(mesh.vertices)

    # check if our mesh already has Vertex Colors, and if not add some...
    # (first we need to make sure it's the active object)
    scn.objects.active = obj
    obj.select = True
    if len(mesh.vertex_colors) == 0:
        bpy.ops.mesh.vertex_color_add()

    # for each polygon calculate the direction then assign
    # that direction to the four vertices (only doing it for rectangles).
    # This will create some redundancy,
    # so we average later on.
    # First, create a list of N empty lists, where N is the number vertices
    all_vert_colors = [list([]) for _ in range(num_verts)]
    for poly in mesh.polygons:
        if len(poly.vertices) == 4:
            direction = long_edge_dir(mesh, poly)
            # make all elements of direction positive
            pos_direction = [abs(k) for k in direction]
            # scale this so that one of the three values is 1.0.
            # I'm not sure if this is the most sensible operation to perform...
            face_color = [k / max(pos_direction) for k in pos_direction]
            # save this color to the 4 vertices
            for vert in poly.vertices:
                all_vert_colors[vert].append(face_color)

    # now we loop through again to average out the color at each vertex
    # initialize the list of vertex colors
    final_vert_colors = [0]*num_verts

    for vert in range(num_verts):
        # print("vert=",vert)
        final_vert_colors[vert] = average_color(all_vert_colors[vert])

    i = 0
    for poly in mesh.polygons:
        for vert_side in poly.loop_indices:
            # find the vertex number as indexed by mesh.vertices,
            # ie. where each vertex has 1 unique number
            global_vert_num = poly.vertices[vert_side-min(poly.loop_indices)]

            mesh.vertex_colors[0].data[i].color = final_vert_colors[
                global_vert_num
                ]

            i += 1


def make_material(name, diffuse_color=(1.0, 1.0, 1.0), diffuse_intensity=0.8,
                  specular_color=(1.0, 1.0, 1.0), specular_intensity=0.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = diffuse_color
    mat.diffuse_intensity = diffuse_intensity
    mat.specular_color = specular_color
    mat.specular_intensity = specular_intensity
    return mat


def long_edge_dir(mesh, poly):
    """Given a rectangular polygon,
    it finds the direction of the longest edge"""

    # we now search through the 4 edge vectors, we record max length,
    # and also min length to make sure the rectangle is not too square
    current_max_length = 0.0
    # the value -99 just indicates that this variable hasn't been set yet.
    current_min_length = -99.0
    for edge in poly.edge_keys:
        # get the edge vector
        edge_vec = mesh.vertices[edge[0]].co - mesh.vertices[edge[1]].co
        length = edge_vec.length

        if length > current_max_length:
            direction = edge_vec
            current_max_length = length
        if length < current_min_length or current_min_length == -99.0:
            current_min_length = length

    # give warning for very square rectangles
    if (current_max_length - current_min_length) / current_min_length < 0.02:
        print("WARNGING: your rectangle is pretty square! Short side:",
              current_min_length, "and long side:", current_max_length)
        print("This could lead to incorrect coloring")
        print("if you're using the brainsuite to blender dft importer, "
              "try increasing res_circum")

    return direction


def average_color(list_of_colors):
    """given a list of colors (which themselves are 3 element lists, [R,G,B]),
    give the average color"""
    # initialize average color
    average_color = [0, 0, 0]

    num = len(list_of_colors)

    for color_j in range(3):
        average_color[color_j] = sum(
            [list_of_colors[i][color_j] for i in range(num)]
            ) / num

    return average_color


def remove_doubles(obj):
    """ Removes doubles using default settings"""
    bpy.ops.object.mode_set(mode='EDIT')
    # toggle select_all since objects are created with all vertices deselected
    bpy.ops.mesh.select_all(action='TOGGLE')
    bpy.ops.mesh.remove_doubles()
    bpy.ops.object.mode_set(mode='OBJECT')


def make_curve(verts, radius=0.5, spline_type='NURBS', res_length=5,
               res_circum=3, color=None, auto_color=False, curve_name='tract',
               curvedata_name='curve_data'):
    """ Given a list of vertices, this creates a tube-like object
    following the vertices.

    >INPUT:
        verts: Nx3 NumPy array where N is the number of vertices
        spline_type: 'POLY' or 'NURBS'
        color: there are 2 options, leave is as None or give it
        a color [R, G, B].  If auto_color is set, this argument is ignored
        res_length: the resolution along the length of the fiber.  If using
                    auto_color and colors get a bit funky, then it's because
                    rectangles aren't long enough.  Turn this down or
                    increase res_cross_section.
        res_circum: the resolution around the circumference of tube
        auto_color: color the curve according to its direction, R,G,B for
                    x,y,z-directions.
                    Setting this also converts it from NURBS/poly curve to mesh
    """
    scn = bpy.context.scene

    curve_data = bpy.data.curves.new(name=curvedata_name, type='CURVE')
    curve_data.dimensions = '3D'
    # fill in the end caps
    curve_data.use_fill_caps = True

    # if there's already a bezier circle in existence, it could cause problems
    if bpy.data.objects.get('NurbsCircle') is None:
        # Create the bevel object to give tube some width
        bpy.ops.curve.primitive_nurbs_circle_add(radius=radius)
        bevel_obj = bpy.data.objects['NurbsCircle']
        bevel_obj.data.resolution_u = res_circum
        # make this object invisible
        # (it would probably be better to delete it at the end...)
        bevel_obj.hide = True
        bevel_obj.hide_render = True
    else:
        bevel_obj = bpy.data.objects['NurbsCircle']

    curve_data.bevel_object = bevel_obj

    curve = bpy.data.objects.new(curve_name, curve_data)

    # create a material for curve
    if color is None or auto_color is True:
        mat = make_material('curve_material', diffuse_color=(0.8, 0.8, 0.8))
    elif type(color) == list and len(color) == 3:
        mat = make_material('curve_material', color)
    else:
        print("Warning: there was a problem with the color argument:", color)

    # set curve to have this material
    curve.active_material = mat

    # link the object to the scene
    scn.objects.link(curve)

    # create the curve
    spline = curve_data.splines.new(spline_type)

    # create all the control points of spline
    spline.points.add(len(verts)-1)
    for num in range(len(verts)):
        x, y, z = verts[num]
        spline.points[num].co = (x, y, z, 1)  # we just use weighting of 1 here

    # this must be after creating points since the funny things happen when
    # you mess with these properties before having control points
    if spline_type == 'NURBS':
        # make NURBS spline go right to the first and last vertices
        spline.use_endpoint_u = True
        # set preview resolution to minimum
        curve_data.resolution_u = 1
        curve_data.render_resolution_u = res_length
        # The default Order is 4 so I don't change spline.order_u

    # select only our tube and set to active object
    for obj in bpy.context.selected_objects:
        obj.select = False
    scn.objects.active = curve
    curve.select = True

    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')

    # In order to use the auto color, we have to convert the curve to a mesh
    if auto_color:
        # We convert it to a mesh, but first we need to set
        # the resolution_u back up
        # since it'll be converted at a low res otherwise
        if spline_type == 'NURBS':
            curve_data.resolution_u = curve_data.render_resolution_u
        bpy.ops.object.convert(target='MESH')
        # sometimes this conversion results in a bunch of doubles,
        # so I remove the doubles
        remove_doubles(curve)

        curve.active_material.use_vertex_color_paint = True

        # color the curve
        color_tube(curve)

    return curve
# end of make_curve(.)


if __name__ == '__main__':
    main()


##########################################################################
# NOTE: this function is not used, but I'm keeping it around as an alternative
# def color_tube_oldVersion(obj):
#    """
#    Given a long tube, whose sidees are made of long, skinny rectangles and
#    whose caps are made of triangles, this colors the tube based on its
#    directions, so red for x-direction, green for y-direction, etc."""
#    mesh = obj.data
#    scn = bpy.context.scene
#
#    # check if our mesh already has Vertex Colors, and if not add some...
#    # (first we need to make sure it's the active object)
#    scn.objects.active = obj
#    obj.select = True
#    if len(mesh.vertex_colors) == 0:
#        bpy.ops.mesh.vertex_color_add()
#
#    i=0
#    for poly in mesh.polygons
#        # if face is a triangle, then we know it is on the end,
#        # and we therefore color it using its normal
#        if len(poly.vertices) == 3:
#            direction = poly.normal
#
#        #if face is a rectangle, it means that the long edge is pointing
#        #along the direction of our tubes, so we
#        #find that direction and set it to be our color
#        if len(poly.vertices) ==4:
#            direction = long_edge_dir( mesh, poly )
#
#        # make all elements of direction positive
#        pos_direction=[abs(k) for k in direction]
#        #scale this so that one of the three values is 1.0.
#        #I'm not sure if this is the most sensible operation to perform...
#        face_color = [k / max(pos_direction) for k in pos_direction]
#
#        for vert_side in poly.loop_indices:
#            mesh.vertex_colors[0].data[i].color = face_color
#            i += 1
