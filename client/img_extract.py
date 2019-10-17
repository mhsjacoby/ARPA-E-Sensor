# Updated 10/17/2019

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

Run this program by specifying the path to the picked files, and the 
target save directory. 

eg:
python3 ARPA-E-Sensor/client/img_extract.py /Volumes/SEAGATE-9/h3-black
/RS1/H3-RS1-img-pkl/ /Users/maggie/Desktop/HPD_mobile_data/HPD_mobile-H3/H3-black/RS1/img


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
        return [x for x in filelist if x.startswith('2019-')]

    def extract_images(self, img_data):
        im_data = np.asarray(img_data)
        new_im = Image.new('L', (112, 112))
        flat_data = list(itertools.chain(*im_data))
        new_im.putdata(flat_data)
        return new_im

    def main(self):
        pickled_days = sorted(self.mylistdir(self.root_dir))
        for dayF in pickled_days:
            pickled_files = sorted(self.mylistdir(os.path.join(self.root_dir, dayF)))

            for f in pickled_files:
                print('time is: {}'.format(datetime.now().strftime('%H:%M:%S')))
                print('unpickling file: {}'.format(f))
                pickleName = f.strip('.pklz')
                Names = pickleName.split('_')
                day, hour, sensor, home = Names[0], Names[1], Names[2], Names[3]
                if day != dayF:
                    print(f'{pickleName} is in the wrong folder ({dayF})')
                new_store_dir = os.path.join(self.store_location, sensor, 'img', day)
                hour_fdata = self.unpickle(os.path.join(self.root_dir, dayF, f))

                for entry in [x for x in hour_fdata if len(hour_fdata) > 0]:
                    if entry.data != 0:
                        new_image = self.extract_images(entry.data)
                        full_img_dir = os.path.join(new_store_dir, str(entry.time)[0:4])
                        if not os.path.isdir(full_img_dir):
                            os.makedirs(full_img_dir)

                        fname = str(entry.day + '_' + entry.time + '_' + sensor + '_' + home + '.png')
                        if not os.path.exists(os.path.join(full_img_dir, fname)):
                            new_image.save(os.path.join(full_img_dir, fname))
                        # else:
                        #     print('Image exists: {}'.format(fname))



if __name__ == '__main__':
    pickle_location = sys.argv[1] #if len(sys.argv) > 1 else '/Users/maggie/Desktop/HPD_mobile_data/HPD_mobile-H1/pickled_images'
    new_image_location = sys.argv[2] # '/Users/maggie/Desktop/Unpickled_Images'
    

    P = ImageExtract(pickle_location, new_image_location)
    P.main()


    