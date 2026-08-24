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

class LED:
    """LED class -- used for each pixel"""
    def __init__(self, grid_pos: tuple, colour: tuple, brightness: int):
        """Initialises an LED pixel object with the appropriate attributes."""
        self._grid_pos = grid_pos
        self._colour = colour
        self._brightness = brightness
        self._is_on = False

    def set_colour(self, colour: tuple):
        """Mutator for the colour attribute of the LED pixel."""
        self._colour = colour

    def set_brightness(self, brightness: int, increment: bool=False):
        """Mutator for the brightness attribute and has the option to increment brightness instead of set it to a new value."""
        if increment:
            self._brightness += brightness
        else:
            self._brightness = brightness

    def _calculate_rgb(self) -> tuple:
        """Non-public method returning the appropriate rgb for the pixel given its colour and brightness."""
        # Generates an rgb tuple by mapping each colour value to a lambda function that transforms the integer into the appropriate
        # range according to the ratio between the pixel brightness and 255.
        return tuple(map(lambda x: x * self._brightness // 255, self.colour))

    def reveal(self):
        """Method called when the pixel is selected and / or revealed."""
        pass

    def draw(self, panel_manager: 'PanelManager'):
        """Public method called to update the LED pixel colour in the panel matrix using message passing."""
        panel_manager.update_pixel(self._grid_pos, self._calculate_rgb)