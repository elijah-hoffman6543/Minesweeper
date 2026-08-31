# Minesweeper game for ESP32 microcontroller and mini joystick i2c

import random
import time
import neopixel
from machine import Pin, I2C
from mini_joystick_i2c import MiniJoyStickI2C

# Constants
MATRIX_PIN = Pin(26, Pin.OUT)
I2C_BUS = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
PIXELS_X = 16
PIXELS_Y = 16
JOYSTICK_DEBOUNCE_DURATION = 0.3e9
CURSOR_FADE_SPEED = 10
CURSOR_MIN_BRIGHTNESS = 20
MAX_BRIGHTNESS = 50
UNREVEALED_COLOUR = (255, 255, 255)
FLAGGED_COLOUR = (255, 67, 67)
MINE_COLOUR = (255, 0, 0)
EMPTYSQUARE_COLOUR = (67, 67, 67)
NUMBERSQUARE_COLOURS = {1: (106, 218, 255),  # Light Blue
                        2: (107, 255, 118),  # Green
                        3: (160, 117, 209),  # Purple
                        4: (252, 240, 62),  # Yellow
                        5: (255, 141, 66),  # Orange
                        6: (255, 131, 212),  # Pink
                        7: (143, 112, 77),  # Brown
                        8: (42, 34, 217)}  # Dark Blue
NUMBER_OF_MINES = 50

class PanelManager:
    """Panel Manager class -- controls / manages all LED objects and interaction with the neopixel matrix, acts as a facade class for handling the LEDs individually"""
    def __init__(self, pixels_x: int, pixels_y: int, matrix_pin: Pin):
        """Initialises panel manager object with the LED pixels and matrix as attributes."""
        self._led_matrix = neopixel.NeoPixel(matrix_pin, pixels_x * pixels_y)
        self._led_list = [LED((x, y), UNREVEALED_COLOUR) for x in range(PIXELS_X) for y in range(PIXELS_Y)]  # List containing each LED object
        self._mine_coords = []  # List containing just the tuple coordinates of each mine
        # Creates a 2 dimensional array using grid coordinates as the indexes to retrieve the index appropriate for LED matrix
        # that is in a serpantine array format. This is done by counting up if the row index is odd and otherwise counting down
        self._index_converter = [[x for x in (range(pixels_x * y, pixels_x * (y + 1), 1) if y % 2 != 0 else range(pixels_x * (y + 1) - 1, pixels_x * y - 1, -1))] for y in range(pixels_y)]
        self._cursor_brightness = 100  # Cursor brightness is used as a percentage value (from 0 to 100) of the maximum brightness
        self._cursor_fade_down = True

    def wipe_pixels(self):
        """Method that wipes all of the pixels."""
        del self._led_list

    def update_pixel(self, grid_pos: tuple[int, int], rgb: tuple[int, int, int]):
        """Public method called by pixels to update status the status of the LED matrix."""
        # The index converter is used to turn the LED grid coordinates into the appropriate index in the serpentine array
        self._led_matrix[self._index_converter[grid_pos[1]][grid_pos[0]]] = rgb

    def get_pixel(self, coordinate: tuple[int, int] | list[int]) -> LED:
        """Public method called by the joystick object to return the pixel at its location."""
        # Returns the first (and only) value / LED from the list that has a matching position or coordinate
        return next(filter(lambda led: led.get_pos() == tuple(coordinate), self._led_list))

    def draw_pixels(self):
        """Method that calls the draw method on each of the LEDs (using message passing) and publishes the changes to the matrix panel."""
        # Using type polymorphism to treat each pixel in the list as the parent, LED object rather than their specific subclasses to access 'draw' method
        for pixel in self._led_list:
            pixel.draw(self)
        self._led_matrix.write()

    def _surrounding_mines(self, grid_pos: tuple[int, int]) -> int:
        """Non-public (protected) method used to determine number of mines surrounding a given coordinate."""
        mine_count = 0
        for a in range(-1, 2):
            for b in range(-1, 2):
                if (grid_pos[0] + a, grid_pos[1] + b) in self._mine_coords:
                    mine_count += 1
        return mine_count

    def setup_game(self, starting_pos: list[int]):
        """Method that generates the map of mines randomly and the remaining pixels accordingly."""
        while len(self._mine_coords) < NUMBER_OF_MINES:
            # Generate random coordinate in grid but only create mine if not already created
            random_coord = (random.randint(0, PIXELS_X - 1), random.randint(0, PIXELS_Y - 1))
            if random_coord not in self._mine_coords and not (-1 <= random_coord[0] -  starting_pos[0] <= 1 and -1 <= random_coord[1] -  starting_pos[1] <= 1):
                self._mine_coords.append(random_coord)

        self._led_list = []
        for y in range(PIXELS_Y):
            for x in range(PIXELS_X):
                if (x, y) not in self._mine_coords:
                    mine_count = self._surrounding_mines((x, y))
                    if mine_count == 0:
                        self._led_list.append(EmptySquare((x, y)))
                    else:
                        self._led_list.append(NumberSquare((x, y), mine_count))
                else:
                    self._led_list.append(Mine((x, y)))

    def flash_cursor(self, joystick: Joystick):
        """Method that fluctuates the brightness of the selected pixel to show the location of the joystick cursor."""
        cursor_led = self.get_pixel(joystick.get_pos())
        cursor_led.set_brightness(MAX_BRIGHTNESS * self._cursor_brightness // 100)
        if self._cursor_fade_down:
            self._cursor_brightness -= CURSOR_FADE_SPEED
            if self._cursor_brightness <= CURSOR_MIN_BRIGHTNESS:
                self._cursor_fade_down = False
        else:
            self._cursor_brightness += CURSOR_FADE_SPEED
            if self._cursor_brightness >= 100:
                self._cursor_fade_down = True

class LED:
    """LED class -- used for each pixel in the matrix"""
    def __init__(self, grid_pos: tuple[int, int], colour: tuple[int, int, int]):
        """Instantiates an LED pixel object with the appropriate attributes."""
        self._grid_pos = grid_pos
        self._colour = colour
        self._brightness = MAX_BRIGHTNESS
        self._revealed = False
        self._flagged = False

    def get_pos(self) -> tuple[int, int]:
        """Accessor for the grid position attribute of the LED."""
        return self._grid_pos

    def is_revealed(self) -> bool:
        """Accessor for the revealed attribute of the LED."""
        return self._revealed

    def set_colour(self, colour: tuple[int, int, int]):
        """Mutator for the colour attribute of the LED pixel."""
        self._colour = colour

    def set_brightness(self, brightness: int, increment: bool=False):
        """Mutator for the brightness attribute and has the option to increment brightness instead of set it to a new value."""
        if increment:
            self._brightness += brightness
        else:
            self._brightness = brightness

    def _calculate_rgb(self, colour) -> tuple:
        """Non-public method returning the appropriate rgb for the pixel given its colour and brightness."""
        # Generates an rgb tuple by mapping each colour value (red, green and blue) to a lambda function that transforms the integer into the
        # appropriate range according to the ratio between the pixel brightness and 255.
        return tuple(map(lambda x: x * self._brightness // 255, colour))

    def flag(self):
        """Method (mutator) called when pixel is flagged as a mine (whether it is or not)."""
        if not self._revealed:
            self._flagged = True

    def reveal(self, panel: PanelManager):
        """Method (mutator) called when the pixel is selected and / or revealed."""
        self._flagged = False
        self._revealed = True

    def draw(self, panel_manager: PanelManager):
        """Public method called to update the LED pixel colour in the panel matrix depending on its state (using message passing)."""
        if self._revealed:
            panel_manager.update_pixel(self._grid_pos, self._calculate_rgb(self._colour))
        elif self._flagged:
            panel_manager.update_pixel(self._grid_pos, self._calculate_rgb(FLAGGED_COLOUR))
        else:
            panel_manager.update_pixel(self._grid_pos, self._calculate_rgb(UNREVEALED_COLOUR))

class Mine(LED):
    """Mine subclass of LED -- type of pixel user should avoid in the game"""
    # hit class attribute to determine whether any mine has been hit
    hit = False

    def __init__(self, grid_pos: tuple[int, int]):
        """Creates an instance of a mine LED using the parent constructor."""
        super().__init__(grid_pos, MINE_COLOUR)

    def reveal(self, panel: PanelManager):
        """Overrides the reveal method from the parent class and update the hit class attribute."""
        Mine.hit = True
        # Trigger the game ending sequence

class EmptySquare(LED):
    """EmptySquare subclass of LED -- type of pixel with no mine or number, reveals all pixels next it"""
    def __init__(self, grid_pos: tuple[int, int]):
        """Creates an instance of an empty square LED using the parent constructor."""
        super().__init__(grid_pos, EMPTYSQUARE_COLOUR)

    def reveal(self, panel: PanelManager):
        """Overrides the reveal method from the parent class and triggers reveal for surrounding LEDs."""
        super().reveal(panel)
        for a in range(-1, 2):
            for b in range(-1, 2):
                new_pos = (self._grid_pos[0] + a, self._grid_pos[1] + b)
                if 0 <= new_pos[0] < PIXELS_X and 0 <= new_pos[1] < PIXELS_Y and new_pos != self._grid_pos:
                    led = panel.get_pixel(new_pos)
                    if not led.is_revealed() and not isinstance(led, Mine):
                        led.reveal(panel)

class NumberSquare(LED):
    """NumberSquare subclass of LED -- type of pixel displaying specific colour depending on number of surrounding mines"""
    def __init__(self, grid_pos: tuple[int, int], num: int):
        """Creates an instance of a number square LED using the parent constructor."""
        super().__init__(grid_pos, NUMBERSQUARE_COLOURS[num])

class Joystick(MiniJoyStickI2C):
    """Joystick subclass of MiniJoyStickI2C from the given module -- manages and interprets joystick input"""
    game_started = False  # Boolean class attribute to determine whether game has started, i.e. board is setup

    def __init__(self, i2c: I2C):
        """Instantiates a joystick object, calling the parent constructor and then creates additional attributes"""
        super().__init__(i2c)
        self._prev_time = time.time_ns()
        self._pos = [PIXELS_X // 2, PIXELS_Y // 2]

    def get_pos(self) -> list[int]:
        """Accessor method for joystick cursor position."""
        return self._pos

    def _get_direction(self, t: int) -> str | None:
        """Non-public method that returns the direction the joystick is pointed towards, outside of debouncing time."""
        # t is used to represent the current time (number of nanoseconds) while avoiding confusion with the time module name
        if t - self._prev_time > JOYSTICK_DEBOUNCE_DURATION:
            x_value = super().analog_read_x()
            y_value = super().analog_read_y()
            if x_value == 0:
                self._prev_time = t
                return 'left'
            elif x_value == 255:
                self._prev_time = t
                return 'right'
            elif y_value == 0:
                self._prev_time = t
                return 'down'
            elif y_value == 255:
                self._prev_time = t
                return 'up'
        return None

    def _b_pressed(self, t: int) -> bool:
        """Non-public method to check whether the 'B' button is pressed, outside of debouncing time."""
        if super().button_pressed(super().BUTTON_B) and t - self._prev_time > JOYSTICK_DEBOUNCE_DURATION:
            self._prev_time = t
            return True
        else:
            return False

    def _c_pressed(self, t: int) -> bool:
        """Non-public method to check whether the 'C' button is pressed, outside of debouncing time."""
        if super().button_pressed(super().BUTTON_C) and t - self._prev_time > JOYSTICK_DEBOUNCE_DURATION:
            self._prev_time = t
            return True
        else:
            return False

    def check_joystick(self, panel: PanelManager):
        """Public method that calls the private methods to check the state of the joystick and take the appropriate actions.
        It utilises the 'facade pattern' to simplify the the function (method) as well as message passing to call methods on other objects.
        """
        current_time = time.time_ns()
        led = panel.get_pixel(self._pos)
        # Move joystick position depending on direction of joystick
        direction = self._get_direction(current_time)
        if direction is not None:
            led.set_brightness(MAX_BRIGHTNESS)
            if direction == 'left':
                self._pos[0] = max(self._pos[0] - 1, 0)
            elif direction == 'right':
                self._pos[0] = min(self._pos[0] + 1, PIXELS_X - 1)
            elif direction == 'up':
                self._pos[1] = max(self._pos[1] - 1, 0)
            elif direction == 'down':
                self._pos[1] = min(self._pos[1] + 1, PIXELS_Y - 1)
        # Reveals or flags the LED if buttons are pressed
        if self._b_pressed(current_time):
            if not self.game_started:
                panel.setup_game(self._pos)
                self.game_started = True
                led = panel.get_pixel(self._pos)
            led.reveal(panel)
        elif self.game_started and self._c_pressed(current_time):
            led.flag()

joystick = Joystick(I2C_BUS)
panel_manager = PanelManager(PIXELS_X, PIXELS_Y, MATRIX_PIN)

while not joystick.button_pressed(MiniJoyStickI2C.BUTTON_D):
    joystick.check_joystick(panel_manager)
    panel_manager.flash_cursor(joystick)
    panel_manager.draw_pixels()