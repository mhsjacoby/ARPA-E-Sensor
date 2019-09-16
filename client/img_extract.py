# Modified 9/12

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from PIL import Image
import pickle
import gzip
import collections
import json
import cProfile
import re
import itertools

NewImage = collections.namedtuple('NewImage', 'day time data')


"""
This class takes a list of pickled objects and extracts the raw images.
The pickled objects are organized by hour.
Change the path at the end to match your stored location,
and where the new images should be saved to. 

This file extracts images that were pickled with 'img_save.py'
"""

class ImageExtract():
    def __init__(self, root_dir, store_dir):
        self.root_dir = root_dir
        self.store_location = store_dir

    def unpickle(self, pickled_file):
        f = gzip.open(pickled_file, 'rb')
        unpickled_obj = pickle.load(f)
        f.close()
        return unpickled_obj

    def mylistdir(self, directory):
        filelist = os.listdir(directory)
        return [x for x in filelist if not (x.startswith('.') or 'Icon' in x)]

    def extract_images(self, img_data):
        im_data = np.asarray(img_data)
        new_im = Image.new('L', (112, 112))
        flat_data = list(itertools.chain(*im_data))
        new_im.putdata(flat_data)
        return new_im

    def main(self):
        pickled_days = sorted(self.mylistdir(self.root_dir))
        for day in pickled_days:
            pickled_files = sorted(self.mylistdir(os.path.join(self.root_dir, day)))

            for f in pickled_files:
                print('time is: {}'.format(datetime.now().strftime('%H:%M:%S')))
                print('unpickling file: {}'.format(f))
                pickleName = f.strip('.pklz')
                Names = pickleName.split('_')
                day, hour, sensor, home = Names[0], Names[1], Names[2], Names[3]

                new_store_dir = os.path.join(self.store_location, home, sensor, 'img', day)
                hour_fdata = self.unpickle(os.path.join(self.root_dir, day, f))

                for entry in [x for x in hour_fdata if len(hour_fdata) > 0]:
                    print(len(entry.data))
                    if entry.data != 0:
                        new_image = self.extract_images(entry.data)
                        full_img_dir = os.path.join(new_store_dir, str(entry.time)[0:4])
                        if not os.path.isdir(full_img_dir):
                            os.makedirs(full_img_dir)

                        fname = str(entry.day + '_' + entry.time + '_' + sensor + '_' + home + '.png')
                        if not os.path.exists(os.path.join(full_img_dir, fname)):
                            new_image.save(os.path.join(full_img_dir, fname))
                        else:
                            print('Image exists: {}'.format(fname))



if __name__ == '__main__':
    pickle_location = sys.argv[1] if len(sys.argv) > 1 else '/Users/maggie/Desktop/HPD_mobile_data/HPD_mobile-H1/pickled_images'
    new_image_location = '/Users/maggie/Desktop/Unpickled_Images'
    if not os.path.isdir(new_image_location):
        os.mkdir(new_image_location)
    P = ImageExtract(pickle_location, new_image_location)
    P.main()


    