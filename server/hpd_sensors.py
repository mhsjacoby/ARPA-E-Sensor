import smbus
import board
import busio
import adafruit_sgp30
import VL53L1X
import Adafruit_DHT
import threading
from datetime import datetime
import time

class HPD_APDS9301():
    def __init__(self):
        # Module variables
        self.i2c_ch = 1
        self.bus = smbus.SMBus(self.i2c_ch)

        # APDS-9301 address on the I2C bus
        self.apds9301_addr = 0x39

        # Register addresses
        self.apds9301_control_reg = 0x80
        self.apds9301_timing_reg = 0x81
        self.apds9301_data0low_reg = 0x8C
        self.apds9301_data1low_reg = 0x8E

        # Read the CONTROL register (1 byte)
        val = self.bus.read_i2c_block_data(self.apds9301_addr, self.apds9301_control_reg, 1)
        
        # Set POWER to on in the CONTROL register
        val[0] = val[0] & 0b11111100
        val[0] = val[0] | 0b11

        # Enable the APDS-9301 by writing back to CONTROL register
        self.bus.write_i2c_block_data(self.apds9301_addr, self.apds9301_control_reg, val)

    # Read light data from sensor and calculate lux
    def read(self):

        # Read channel 0 light value and combine 2 bytes into 1 number
        val = self.bus.read_i2c_block_data(self.apds9301_addr, self.apds9301_data0low_reg, 2)
        ch0 = (val[1] << 8) | val[0]

        # Read channel 1 light value and combine 2 bytes into 1 number
        val = self.bus.read_i2c_block_data(self.apds9301_addr, self.apds9301_data1low_reg, 2)
        ch1 = (val[1] << 8) | val[0]

        # Make sure we don't divide by 0
        if ch0 == 0.0:
            return 0.0

        # Calculate ratio of ch1 and ch0
        ratio = ch1 / ch0

        # Assume we are using the default 13.7 ms integration time on the sensor
        # So, scale raw light values by 1/0.034 as per the datasheet
        ch0 *= 1 / 0.034
        ch1 *= 1 / 0.034

        # Assume we are using the default low gain setting
        # So, scale raw light values by 16 as per the datasheet
        ch0 *= 16;
        ch1 *= 16;

        # Calculate lux based on the ratio as per the datasheet
        if ratio <= 0.5:
            return int((0.0304 * ch0) - ((0.062 * ch0) * ((ch1/ch0) ** 1.4)))
        elif ratio <= 0.61:
            return int((0.0224 * ch0) - (0.031 * ch1))
        elif ratio <= 0.8:
            return int((0.0128 * ch0) - (0.0153 * ch1))
        elif ratio <= 1.3:
            return int((0.00146 * ch0) - (0.00112*ch1))
        else:
            return int(0.0)


class HPD_SGP30():
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
        self.sensor = adafruit_sgp30.Adafruit_SGP30(self.i2c)
        self.sensor.iaq_init()
        self.sensor.set_iaq_baseline(0x8973, 0x8aae)

    def read(self):
        return((self.sensor.co2eq, self.sensor.tvoc))

    def read_baseline(self):
        return((self.sensor.baseline_co2eq, self.sensor.baseline_tvoc))
    

class HPD_VL53L1X():
    def __init__(self):
        self.sensor = VL53L1X.VL53L1X(i2c_bus=1, i2c_address=0x29)
        self.sensor.open()

    def read(self):
        self.sensor.start_ranging(1)
        distance = self.sensor.get_distance()
        self.sensor.stop_ranging()
        return distance


class HPD_DHT22():
    def __init__(self):
        self.sensor = Adafruit_DHT.DHT22
        self.pin = 17

    def to_f(self, t):
        return t * 9/5.0 + 32
    
    def read(self):
        h, t = Adafruit_DHT.read_retry(self.sensor, self.pin)
        return((h, t))


class Sensors(threading.Thread):
# class Sensors():
    def __init__(self, read_interval):
        threading.Thread.__init__(self)
        self.gas = HPD_SGP30()
        self.light = HPD_APDS9301()
        self.temp_humid = HPD_DHT22()
        self.dist = HPD_VL53L1X()
        self.read_interval = read_interval
        self.readings = []

    def run(self):
        while True:
            if datetime.now().second % self.read_interval == 0:
                (h, t) = self.temp_humid.read()
                (co2, tvoc) = self.gas.read()
                (co2_base, tvoc_base) = self.gas.read_baseline()
                self.readings.append({"time": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                                      "light_lux": self.light.read(),
                                      "temp_c": t,
                                      "rh": h,
                                      "dist_in": self.dist.read(),
                                      "co2eq_ppm": co2,
                                      "tvoc_ppb": tvoc,
                                      "co2eq_base_ppm": co2_base,
                                      "tvoc_base": tvoc_base})

                if len(self.readings) % 2 == 0:
                    print("{} readings in the Queue\n\tMin timestamp: {}\n\tMax timestamp: {}".format(len(self.readings),
                                                                                                  self.readings[0]["time"],
                                                                                                  self.readings[-1]["time"]))
                time.sleep(1)