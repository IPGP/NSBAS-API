#!/usr/bin/env python
""" print / save sar image as jpeg"""

import re
import argparse
import numpy as np
import matplotlib.pyplot as plt
#import scipy.misc

def read_width(file_name, field_re="WIDTH\s+(\d+)"):
    """ read the image width from file_name

    :file_name: (str) file name that contains the with field
    :field: (str, default WIDTH (\d+)) regex that matches the field
    :returns: the with  of the image (int)
    """
    re_comp = re.compile(field_re)
    with open(file_name, "r")as  _handle:
        for line in _handle:
            re_match = re_comp.search(line)
            if re_match:
                return int(re_match.groups()[0])
    return None

class FactoryImageViewver(object):
    """ factory class to build an image viewer out of
    different kind of sar images
    """

    __array__ = None

    def __init__(self, img, data_type=np.float32):
        """ initialize the Factory using a image name
        :img: (str) an image name
        :dtype: (numpy type, default=np.float32): the type of the data
        """
        self.__file_name__ = img
        self.__array__ = np.fromfile(img, dtype=data_type)

    def __str__(self):
        """ return the string reprensenting the shape of the internal array
        """
        if self.__array__ is None:
            return "None"
        else:
            return "internal array shape is {}".format(self.__array__.shape)

    def reshape(self, width):
        """reshape the array according to shape
            :width: the width of the image.
        """
        self.__array__ = np.reshape(self.__array__, (-1,width))


    def select_band(self, band_nb, interleave_type='BIL'):
        """ selects a band of the image.

        :band_nb: (int) the band to select
        :interleave_type: the type of interleave. Should be one
        of 'BIL', 'BIP', 'BSQ'. Default "BIL"
        """
        if interleave_type == 'BIL':
            self.__array__ = self.__array__[band_nb::2]

    def data(self):
        """Returns the internal array
        :returns: the internal array (numpy array)
        """
        return self.__array__


    def build(self, copy=False):
        """ Actually builds the ImageViewer
        :returns: an ImageViewer object
        """
        if copy:
            return ImageViewer(np.copy(self.__array__))
        return ImageViewer(self.__array__)

class ImageViewer(object):

    """A class for viewving image generated from sar processing.
    """

    __array__ = None

    def __init__(self, arr):
        """ Initialize  the _array__ field, which should
            be a numpy ndarray
        :param arr: the data
        :type arr: numpy array
        """
        self.__array__ = arr

    def __str__(self):
        """ return the string reprensenting the shape of the internal array
        """
        if self.__array__ is None:
            return "None"
        else:
            return "internal array shape is {}".format(self.__array__.shape)


    def min_max_norm(self, copy=False):
        """
         Does a min/max normalization of the data.
         If copy is False: do it "in place", else return a new
         ImageViewer object
        """
        a_min = np.min(self.__array__)
        a_max = np.max(self.__array__)
        if copy:
            temp_arr = np.copy(self.__array__)
            temp_arr = temp_arr -  a_min
            temp_arr /= a_max
            return ImageViewer(np.copy(temp_arr))

        self.__array__ -= a_min
        self.__array__ /= a_max
        return self

    def auto_clip(self, threshold, copy=False):
        """clip the data, computing automatically the thresholds.
        Compute threshold using percentile. A "perhaps" better way
        to do it would be to use MAD (Median Absolute Dev)....
        :threshold: threshold on the "amount of data to keep"
        :copy: (boolean, default False) if true copy the data and
               returns  a new ImageViewer
        """
        diff = (100 - threshold) / 2.0
        minval, maxval = np.percentile(self.__array__, [diff, 100 - diff])
        self.clip(minval, maxval, copy)

    def clip(self, minval, maxval, copy=False):
        """ clip the data using min an max values
        :drange: (tuple) the data range (minimum, maximum) value
        :copy: (boolean, default False) if true copy the data and
               returns  a new ImageViewer
        """
        if copy:
            temp_arr = np.copy(self.__array__)
            np.clip(temp_arr, minval, maxval, out=temp_arr)
            return ImageViewer(temp_arr)
        np.clip(self.__array__, minval, maxval, out=self.__array__)
        return self

    def plot(self, cmap='winter', color_bar=False, plot=False, save=None):
        """ Show the image.
        :cmap: (str) the color map to use (default=summer)
        :color_bar: (boolean) if true, add a color map to show the data
        """
        fig = plt.figure()
        plt_img = plt.imshow(self.__array__, cmap)
        if color_bar:
            plt.colorbar(plt_img, orientation='horizontal')
        if plot:
            plt.show()
        if save is not None:
            fig.savefig(save)


    def save(self, file_name):
        """save the file. Compatible format are the one managed by scipy.misc.imsave
        :file_name: (str) the out file name
        """
        scipy.misc.imsave(file_name, self.__array__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="show and/or save sar image")
    parser.add_argument("-i", type=str, help="input file name")
    parser.add_argument("-c", type=str, default="summer", help="color map to use, default = summer")
    parser.add_argument("-w", type=int, default=None, help="width of the image. If not provided, search for the width in the rsc file")
    parser.add_argument("-b", type=str, help="the band to a for amplitude p for phase")
    parser.add_argument("-n", action='store_true', default=None, help="normalization (default minmax)")
    parser.add_argument("-C", type=int, default=None, help="auto clip (percentil based) default) value for parameter is 95")
    parser.add_argument("-m", type=float, default=None, help="min value for clipping")
    parser.add_argument("-M", type=float, default=None, help="max value for clipping")
    parser.add_argument("-s", type=str, help="where to save the data")
    parser.add_argument("-S", action='store_true', default=None, help="show the figure")
    parser.add_argument("-I", action='store_true', default=None, help="become interactive at the end of the script")


    args = parser.parse_args()

    imv_b = FactoryImageViewver(args.i)

    # managing SHAPE: get the width
    img_width = None
    if args.w:
        img_width = args.w
    else:
        img_width = read_width(args.i + ".rsc")
    imv_b.reshape(img_width)

    # extracting relevant part
    if args.b == "p":
        imv_b.select_band(1)
    else:
        imv_b.select_band(0)

    imv = imv_b.build(copy=False)
    if args.C is None:
        if args.m or args.M:
            minval = np.min(imv.__array__) if args.m is None else args.m
            maxval = np.max(imv.__array__) if args.M is None else args.M
            imv.clip(minval, maxval)
    else:
        imv.auto_clip(args.C)

    if args.n:
        imv.min_max_norm()

    imv.plot(cmap=args.c, color_bar=True, save="plt_" + args.s, plot=args.S)

    #if args.s:
    #    imv.save(args.s)

    if args.I:
        arr = imv.__array__
        print "*" * 50
        print ("**  your data are in the arr variable. Let's play with it\n"
               "**  modules already imported:\n**\n"
               "**  import numpy as np\n"
               "**  import matplotlib.pyplot as plt\n"
               "**  import scipy.misc")
        print "*" * 50
        import pdb
        pdb.set_trace()
