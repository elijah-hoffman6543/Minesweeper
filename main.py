# Minesweeper game for ESP32 microcontroller and mini joystick i2c

import neopixel
from machine import Pin, I2C, Timer
from mini_joystick_i2c import MiniJoyStickI2C

# Initialise LED Matrix
matrix_pin = Pin(26, Pin.OUT)
PIXELS_X = 16
PIXELS_Y = 16
NUM_PIXELS = PIXELS_X * PIXELS_Y
np = neopixel.NeoPixel(matrix_pin, NUM_PIXELS)

# Create a 2 dimensional array mapping grid indexes to the matrix in snake format
# by counting up if the row index is odd, otherwise counting down
index_converter = [[x for x in (range(PIXELS_X * y, PIXELS_X * (y + 1), 1) if y % 2 != 0 else range(PIXELS_X * (y + 1) - 1, PIXELS_X * y - 1, -1))] for y in range(PIXELS_Y)]