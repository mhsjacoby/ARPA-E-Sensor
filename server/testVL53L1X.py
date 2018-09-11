import hpd_sensors
import sys
from datetime import datetime
import os

def main(id):
    size = 1
    test = hpd_sensors.HPD_VL53L1X()
    d = {}
    while size <= 60:
        if datetime.now().microsecond == 0:
            d[size] = test.read()
            size += 1
    
    fname = os.path.join('tests','VL53L1X_{}.txt'.format(id))
    with open(fname, 'w+') as f:
        for k, v in d.items():
            f.write("{},{}".format(k,v))


if __name__=="__main__":
    id = sys.argv[1]
    print("Sampling VL53L1X id: {}")
    main(id)
