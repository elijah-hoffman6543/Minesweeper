# Minesweeper game for ESP32 microcontroller and mini joystick i2c

import neopixel
from machine import Pin, I2C, Timer
from mini_joystick_i2c import MiniJoyStickI2C

# Constants
MATRIX_PIN = Pin(26, Pin.OUT)
PIXELS_X = 16
PIXELS_Y = 16

class PanelManager:
    """Panel Manager class -- controls / manages all LED objects and interaction with the neopixel matrix"""
    def __init__(self, pixels_x: int, pixels_y: int, matrix_pin: Pin):
        """Initialises panel manager object with the LED pixels and matrix as attributes."""
        self._led_matrix = neopixel.Neopixel(matrix_pin, pixels_x * pixels_y)
        # Generic values used here for LED objects, list will ultimately be generated in setup method using appropriate LED subclass
        self._led_list = list(LED((x, y), (255, 255, 255), 20) for y in range(pixels_y) for x in range(pixels_x))
        # Creates a 2 dimensional array using grid coordinates as the indexes to retrieve the index appropriate for LED matrix
        # that is in a serpantine array format. This is done by counting up if the row index is odd and otherwise counting down
        self._index_converter = [[x for x in (range(pixels_x * y, pixels_x * (y + 1), 1) if y % 2 != 0 else range(pixels_x * (y + 1) - 1, pixels_x * y - 1, -1))] for y in range(pixels_y)]

    def wipe_pixels(self):
        """Method that wipes all of the pixels."""
        del self._led_list

    def update_pixel(self, grid_pos: tuple[int, int], rgb: tuple[int, int, int]):
        """Public method called by pixels to update status the status of the LED matrix."""
        # The index converter is used to turn the LED grid coordinates into the appropriate index in the serpentine array
        self._led_matrix[self._index_converter[grid_pos[0]][grid_pos[1]]] = rgb

    def draw_pixels(self):
        """Method that calls the draw method on each of the LEDs (using message passing) and publishes the changes to the matrix panel."""
        for pixel in self._led_list:
            pixel.draw(self)
        self._led_matrix.write()

    def setup_game(self):
        """Method that generates the map of mines randomly and the remaining pixels accordingly."""
        pass

class LED:
    """LED class -- used for each pixel in the matrix"""
    def __init__(self, grid_pos: tuple[int, int], colour: tuple[int, int, int], brightness: int):
        """Instantiates an LED pixel object with the appropriate attributes."""
        self._grid_pos = grid_pos
        self._colour = colour
        self._brightness = brightness
        self._is_on = False

    def set_colour(self, colour: tuple[int, int, int]):
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
        return tuple(map(lambda x: x * self._brightness // 255, self._colour))

    def reveal(self):
        """Method called when the pixel is selected and / or revealed."""
        pass

    def draw(self, panel_manager: PanelManager):
        """Public method called to update the LED pixel colour in the panel matrix using message passing."""
        panel_manager.update_pixel(self._grid_pos, self._calculate_rgb())