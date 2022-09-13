# SPDX-FileCopyrightText: 2021 Division of Intelligent Medical Systems, DKFZ
# SPDX-FileCopyrightText: 2021 Janek Groehl
# SPDX-License-Identifier: MIT


import numpy as np
from scipy.interpolate import interp1d
import torch
import itertools

def calculate_oxygenation(molecule_list):
    """
    :return: an oxygenation value between 0 and 1 if possible, or None, if not computable.
    """
    hb = None
    hbO2 = None

    for molecule in molecule_list:
        if molecule.spectrum.spectrum_name == "Deoxyhemoglobin":
            hb = molecule.volume_fraction
        if molecule.spectrum.spectrum_name == "Oxyhemoglobin":
            hbO2 = molecule.volume_fraction

    if hb is None and hbO2 is None:
        return None

    if hb is None:
        hb = 0
    elif hbO2 is None:
        hbO2 = 0

    if hb + hbO2 < 1e-10:  # negative values are not allowed and division by (approx) zero
        return None        # will lead to negative side effects.

    return hbO2 / (hb + hbO2)


def create_spline_for_range(xmin_mm=0, xmax_mm=10, maximum_y_elevation_mm=1, spacing=0.1):
    """
    Creates a functional that simulates distortion along the y position
    between the minimum and maximum x positions. The elevation can never be
    smaller than 0 or bigger than maximum_y_elevation_mm.

    :param xmin_mm: the minimum x axis value the return functional is defined in
    :param xmax_mm: the maximum x axis value the return functional is defined in
    :param maximum_y_elevation_mm: the maximum y axis value the return functional will yield
    :return: a functional that describes a distortion field along the y axis

    """
    # Convert units from mm spacing to voxel spacing.
    xmax_voxels = xmax_mm / spacing
    maximum_y_elevation_mm = -maximum_y_elevation_mm

    # Create initial guesses left and right position
    left_boundary = np.random.random() * maximum_y_elevation_mm
    right_boundary = np.random.random() * maximum_y_elevation_mm

    # Define the number of division knots
    divisions = np.random.randint(1, 5)
    order = divisions
    if order > 3:
        order = 3

    # Create x and y value pairs that should be fit by the spline (needs to be division knots + 2)
    locations = np.linspace(xmin_mm, xmax_mm, divisions + 1)
    constraints = np.linspace(left_boundary, right_boundary, divisions + 1)

    # Add random permutations to the y-axis of the division knots
    for i in range(0, divisions + 1):
        scaling_value = np.sqrt(2 - ((i - (divisions / 2)) / (divisions / 2)) ** 2)

        constraints[i] = np.random.normal(scaling_value, 0.2) * constraints[i]
        if constraints[i] < maximum_y_elevation_mm:
            constraints[i] = maximum_y_elevation_mm
        if constraints[i] > 0:
            constraints[i] = 0

    constraints = constraints - np.max(constraints)

    spline = interp1d(locations, constraints, order)

    max_el = np.min(spline(np.arange(0, int(round(xmax_voxels)), 1) * spacing))

    return spline, max_el


def spline_evaluator2d_voxel(x, y, spline, offset_voxel, thickness_voxel):
    elevation = spline[x]
    y_value = np.round(elevation + offset_voxel)
    if y_value <= y < thickness_voxel + y_value:
        return True
    else:
        return False


def calculate_gruneisen_parameter_from_temperature(temperature_in_celcius):
    """
    This function returns the dimensionless gruneisen parameter based on a heuristic formula that
    was determined experimentally::

        @book{wang2012biomedical,
            title={Biomedical optics: principles and imaging},
            author={Wang, Lihong V and Wu, Hsin-i},
            year={2012},
            publisher={John Wiley & Sons}
        }

    :param temperature_in_celcius: the temperature in degrees celcius
    :return: a floating point number, if temperature_in_celcius is a number or a float array, if temperature_in_celcius
        is an array

    """
    return 0.0043 + 0.0053 * temperature_in_celcius


def randomize_uniform(min_value: float, max_value: float):
    """
    returns a uniformly drawn random number in [min_value, max_value[

    :param min_value: minimum value
    :param max_value: maximum value
    :return: random number in [min_value, max_value[

    """
    return (np.random.random() * (max_value-min_value)) + min_value


def rotation_x(theta):
    """
    Rotation matrix around the x-axis with angle theta.

    :param theta: Angle through which the matrix is supposed to rotate.
    :return: rotation matrix
    """
    return np.array([[1, 0, 0],
                    [0, np.cos(theta), -np.sin(theta)],
                    [0, np.sin(theta), np.cos(theta)]])


def rotation_y(theta):
    """
    Rotation matrix around the y-axis with angle theta.

    :param theta: Angle through which the matrix is supposed to rotate.
    :return: rotation matrix
    """
    return np.array([[np.cos(theta), 0, np.sin(theta)],
                    [0, 1, 0],
                    [-np.sin(theta), 0, np.cos(theta)]])


def rotation_z(theta):
    """
    Rotation matrix around the z-axis with angle theta.

    :param theta: Angle through which the matrix is supposed to rotate.
    :return: rotation matrix
    """
    return np.array([[np.cos(theta), -np.sin(theta), 0],
                    [np.sin(theta), np.cos(theta), 0],
                    [0, 0, 1]])


def rotation(angles):
    """
    Rotation matrix around the x-, y-, and z-axis with angles [theta_x, theta_y, theta_z].

    :param angles: Angles through which the matrix is supposed to rotate in the form of [theta_x, theta_y, theta_z].
    :return: rotation matrix
    """
    return rotation_x(angles[0]) * rotation_y(angles[1]) * rotation_z(angles[2])


def rotation_matrix_between_vectors(a, b):
    """
    Returns the rotation matrix from a to b

    :param a: 3D vector to rotate
    :param b: 3D target vector
    :return: rotation matrix
    """
    a_norm, b_norm = (a / np.linalg.norm(a)).reshape(3), (b / np.linalg.norm(b)).reshape(3)
    cross_product = np.cross(a_norm, b_norm)
    if np.abs(cross_product.all()) < 1e-10:
        return np.zeros([3, 3])
    dot_product = np.dot(a_norm, b_norm)
    s = np.linalg.norm(cross_product)
    mat = np.array([[0, -cross_product[2], cross_product[1]],
                    [cross_product[2], 0, -cross_product[0]],
                    [-cross_product[1], cross_product[0], 0]])
    rotation_matrix = np.eye(3) + mat + mat.dot(mat) * ((1 - dot_product) / (s ** 2))
    return rotation_matrix


def min_max_normalization(data: np.ndarray = None) -> np.ndarray:
    """
    Normalizes the given data by applying min max normalization.
    The resulting array has values between 0 and 1 inclusive.

    :param data: (numpy array) data to be normalized
    :return: (numpy array) normalized array
    """

    if data is None:
        raise AttributeError("Data must not be none in order to normalize it.")

    _min = np.min(data)
    _max = np.max(data)
    output = (data - _min) / (_max - _min)

    return output


def positive_gauss(mean, std) -> float:
    """
    Generates a non-negative random sample (scalar) from a normal (Gaussian) distribution.

    :param mean : float defining the mean ("centre") of the distribution. 
    :param std: float defining the standard deviation (spread or "width") of the distribution. Must be non-negative.
    :return: non-negative random sample from a normal (Gaussian) distribution.
    """
    random_value = np.random.normal(mean, std)
    if random_value <= 0:
        return positive_gauss(mean, std)
    else: 
        return random_value

def bilinear_interpolation(image: torch.tensor, x: torch.tensor, y: torch.tensor, z: torch.tensor = None) -> torch.tensor:
    """
    Returns interpolated values of an 2 dimensional or 3 dimensional map/image at the positions (x,y) or (x,y,z) respectively.
    For this bilinear interpolation (in every dimension) is used.
    This function is based on https://gist.github.com/peteflorence/a1da2c759ca1ac2b74af9a83f69ce20e.
    If the sample point is outside the image, one uses the next nearest 2 or 3 neighbors for interpolation!
    
    :param image: 2-dim./3-dim image which values shall be interpolated
    :type image: torch.tensor
    :param x: pixel positions in x-direction
    :type x: torch.tensor
    :param y: pixel positions in y-direction
    :type y: torch.tensor
    :param z: pixel positions in z-direction
    :type z: torch.tensor
    
    :return: interpolated values of the input image at given positions
    :rtype: torch.tensor
    """
    dtype = torch.float64
    dtype_long = torch.long
    
    if image.ndim < 3 or z == None: # 2dim case

        """
        MEMORY EXPENSIVE
        
        # compute the indices of the neighbors            
        x0 = torch.floor(x).type(dtype_long)
        x1 = x0 + 1

        y0 = torch.floor(y).type(dtype_long)
        y1 = y0 + 1

        x0 = torch.clamp(x0, 0, image.shape[0]-2)
        x1 = torch.clamp(x1, 1, image.shape[0]-1)
        y0 = torch.clamp(y0, 0, image.shape[1]-2)
        y1 = torch.clamp(y1, 1, image.shape[1]-1)

        # ensures, that at the boundary the nearest boundary values are taken into account
        x = torch.clamp(x, 0, image.shape[0]-1)
        y = torch.clamp(y, 0, image.shape[1]-1)
        
 

        # read out the neighboring values
        f_tl = image[x0, y0] # top left neighbor value
        f_bl = image[x0, y1] # bottom left neighbor value
        f_tr = image[x1, y0] # top right neighbor value
        f_br = image[x1, y1] # bottom right neighbor value

        # calculate the weights
        w_tl = (x1.type(dtype)-x) * (y1.type(dtype)-y)
        w_bl = (x1.type(dtype)-x) * (y-y0.type(dtype))
        w_tr = (x-x0.type(dtype)) * (y1.type(dtype)-y)
        w_br = (x-x0.type(dtype)) * (y-y0.type(dtype))
        return f_tl*w_tl + f_bl*w_bl + f_tr*w_tr + f_br*w_br"""

        x_int = torch.empty([2]+list(x.shape), dtype=dtype_long, device=x.device)
        y_int = torch.empty([2]+list(y.shape), dtype=dtype_long, device=y.device)
        # compute the indices of the neighbors
        # for x dimension           
        x_int[0] = torch.floor(x)
        x_int[1] = x_int[0] + 1
        # for y dimension
        y_int[0] = torch.floor(y)
        y_int[1] = y_int[0] + 1

        # for lower indices clamp at 0 and image.shape[*]-2
        # for higher indices clamp at 1 and image.shape[*]-1
        for i in range(2):
            x_int[i] = torch.clamp(x_int[i], i, image.shape[0]-2+i)
            y_int[i] = torch.clamp(y_int[i], i, image.shape[1]-2+i)

        # ensures, that at the boundary the nearest boundary values are taken into account
        x = torch.clamp(x, 0, image.shape[0]-1)
        y = torch.clamp(y, 0, image.shape[1]-1)
        
        # in order to reduce needed memory loop over 4 neigbours (i,j) \in {(0,0), (1,0), (0,1), (1,1)} 
        # and sum the weighted image values of the neighbors up
        f_int = 0
        for i,j in zip(itertools.product(range(2),repeat=2), itertools.product(range(1,-1,-1),repeat=2)):
            f_int += image[x_int[i[0]], y_int[i[1]]] * torch.abs((x_int[j[0]].type(dtype)-x) * (y_int[j[1]].type(dtype)-y))

        return f_int

    
    elif image.ndim == 3: # 3dim case #TODO: NOT TESTED YET
        # in the 3dim case one has 8 neighbors that are the corners of a cube 
        
        # compute the indices of the neighbors            
        x0 = torch.floor(x).type(dtype_long)
        x1 = x0 + 1

        y0 = torch.floor(y).type(dtype_long)
        y1 = y0 + 1
        
        z0 = torch.floor(z).type(dtype_long)
        z1 = z0 + 1

        x0 = torch.clamp(x0, 0, image.shape[0]-2)
        x1 = torch.clamp(x1, 1, image.shape[0]-1)
        y0 = torch.clamp(y0, 0, image.shape[1]-2)
        y1 = torch.clamp(y1, 1, image.shape[1]-1)
        z0 = torch.clamp(z0, 0, image.shape[2]-2)
        z1 = torch.clamp(z1, 1, image.shape[2]-1)

        # ensures, that at the boundary the nearest boundary values are taken into account
        x = torch.clamp(x, 0, image.shape[0]-1)
        y = torch.clamp(y, 0, image.shape[1]-1)
        z = torch.clamp(z, 0, image.shape[2]-1)
        
        # read out the neighboring values
        # front plane
        f_tlf = image[x0, y0, z0] # top left front neighbor value
        f_blf = image[x0, y1, z0] # bottom left front neighbor value
        f_trf = image[x1, y0, z0] # top right front neighbor value
        f_brf = image[x1, y1, z0] # bottom right front neighbor value
        # back plane
        f_tlb = image[x0, y0, z1] # top left front neighbor value
        f_blb = image[x0, y1, z1] # bottom left front neighbor value
        f_trb = image[x1, y0, z1] # top right front neighbor value
        f_brb = image[x1, y1, z1] # bottom right front neighbor value

        # calculate the weights
        # front plane
        w_tlf = (x1.type(dtype)-x) * (y1.type(dtype)-y) * (z1.type(dtype)-z)
        w_blf = (x1.type(dtype)-x) * (y-y0.type(dtype)) * (z1.type(dtype)-z)
        w_trf = (x-x0.type(dtype)) * (y1.type(dtype)-y) * (z1.type(dtype)-z)
        w_brf = (x-x0.type(dtype)) * (y-y0.type(dtype)) * (z1.type(dtype)-z)
        # back plane
        w_tlb = (x1.type(dtype)-x) * (y1.type(dtype)-y) * (z-z0.type(dtype))
        w_blb = (x1.type(dtype)-x) * (y-y0.type(dtype)) * (z-z0.type(dtype))
        w_trb = (x-x0.type(dtype)) * (y1.type(dtype)-y) * (z-z0.type(dtype))
        w_brb = (x-x0.type(dtype)) * (y-y0.type(dtype)) * (z-z0.type(dtype))

        return f_tlf*w_tlf + f_blf*w_blf + f_trf*w_trf + f_brf*w_brf + f_tlb*w_tlb + f_blb*w_blb + f_trb*w_trb + f_brb*w_brb
        
    else:
        return None

def print_memory_stats(unit="kiB"):
           
    t = torch.cuda.get_device_properties(0).total_memory
    r = torch.cuda.memory_reserved(0)
    a = torch.cuda.memory_allocated(0)
    if unit=="kiB":
        t /= 2**10
        r /= 2**10
        a /= 2**10
    elif unit=="MiB":
        t /= 1048576 #2**20
        r /= 1048576
        a /= 1048576
    else:
        unit = "B"
    print(f"""##########GPU-Memory-Stats##########
Allocated : {a:20.3f} {unit}
Theo. Free: {t-a:20.3f} {unit}
(Total-allocated)
Reserved  : {r:20.3f} {unit}
Free Cache: {r-a:20.3f} {unit}
(Not used in reserved)
Total     : {t:20.3f} {unit}
####################################""")