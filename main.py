# Minesweeper game for ESP32 microcontroller and mini joystick i2c
# Import standard MicroPython libraries and the mini joystick module
import random
import time
import neopixel
from machine import Pin, I2C
from mini_joystick_i2c import MiniJoyStickI2C

# CONSTANTS:
# Input and output machine objects
MATRIX_PIN = Pin(2, Pin.OUT)
I2C_BUS = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
# Matrix dimensions
PIXELS_X = 16
PIXELS_Y = 16
# Joystick and cursor timing constants
JOYSTICK_DEBOUNCE_DURATION = 0.4e9
CURSOR_FADE_SPEED = 10
CURSOR_MIN_BRIGHTNESS = 20  # Used as a percentage; out of 100
# Colours and brightness
MAX_BRIGHTNESS = 30
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
GAME_WON_COLOUR = (0, 255, 0)
GAME_LOST_COLOUR = (255, 0, 0)
# Number of mines to be generated (essentially the difficulty) -- Note: if too low (less than 20-30) the program will reach max. recursive depth
NUMBER_OF_MINES = 50
# Game over animation timing constants
MINE_REVEAL_INTERVAL = 0.1
GAME_OVER_DURATION = 3

class PanelManager:
    """Panel Manager class -- controls / manages all LED objects and interaction with the neopixel matrix, acts as a facade class for handling the LEDs
    The class also manages game functions such as flashing the cursor, generating the mine map and controlling the game over animation.
    """
    def __init__(self, pixels_x: int, pixels_y: int, matrix_pin: Pin):
        """Initialises panel manager object with the LED pixels and matrix as attributes."""
        self._game_over = False  # True when game is over, win or lose
        self._game_won = False  # True when game was won, used do determine whether to track score
        self._led_matrix = neopixel.NeoPixel(matrix_pin, pixels_x * pixels_y)
        self._led_list = [LED((x, y), UNREVEALED_COLOUR) for x in range(PIXELS_X) for y in range(PIXELS_Y)]  # List containing each LED object
        self._mine_coords = []  # List containing just the tuple coordinates of each mine
        # The index_converter creates a 2 dimensional array using grid coordinates as the indexes to retrieve the index appropriate for LED matrix
        # that is in a serpentine array format. This is done by counting up if the row index is odd and otherwise counting down.
        self._index_converter = [[x for x in (range(pixels_x * y, pixels_x * (y + 1), 1) if y % 2 != 0 else range(pixels_x * (y + 1) - 1, pixels_x * y - 1, -1))] for y in range(pixels_y)]
        self._cursor_brightness = 100  # Cursor brightness is used as a percentage value (from 0 to 100) of the maximum brightness
        self._cursor_fade_down = True  # Determines whether the cursor is increasing / decreasing in brightness
        self._reveal_counter = 0  # Used for counting the number of non-mines revealed so far

    def is_game_over(self) -> bool:
        """Accessor method for the protected game over attribute."""
        return self._game_over

    def is_game_won(self) -> bool:
        """Accessor method for the protected game won attribute"""
        return self._game_won

    def update_pixel(self, grid_pos: tuple[int, int], rgb: tuple[int, int, int]):
        """Public mutator method called by pixels to update status the status of the LED matrix."""
        # The index converter is used to turn the LED grid coordinates into the appropriate index in the serpentine array
        self._led_matrix[self._index_converter[grid_pos[1]][grid_pos[0]]] = rgb

    def get_pixel(self, coordinate: tuple[int, int] | list[int]) -> LED:
        """Public method called by the joystick object to return the pixel at its location."""
        # Returns the first (and only) value / LED from the list that has a matching position or coordinate
        return next(filter(lambda led: led.get_pos() == tuple(coordinate), self._led_list))

    def draw_pixels(self):
        """Method that calls the draw method on each of the LEDs (using message passing) and publishes the changes to the matrix panel."""
        # Using type polymorphism to treat each pixel in the list as their parent, LED object rather than their specific subclass objects in order to access 'draw' method
        for pixel in self._led_list:
            pixel.draw(self)
        self._led_matrix.write()  # Update the neopixel display with the new colours and brightnesses

    def _surrounding_mines(self, grid_pos: tuple[int, int]) -> int:
        """Non-public (protected) method used to determine number of mines surrounding a given coordinate."""
        mine_count = 0
        # Loops through the nine grid coordinates surrounding the coordinate with adjusting modifiers
        for a in range(-1, 2):
            for b in range(-1, 2):
                if (grid_pos[0] + a, grid_pos[1] + b) in self._mine_coords:
                    mine_count += 1
        return mine_count

    def setup_game(self, starting_pos: list[int]):
        """Method that generates the map of mines randomly and the remaining pixels accordingly."""
        while len(self._mine_coords) < NUMBER_OF_MINES:
            # Generate random coordinate in grid but only add to the mine list if it is not on or next to the selected coordinate
            random_coord = (random.randint(0, PIXELS_X - 1), random.randint(0, PIXELS_Y - 1))
            if not (-1 <= random_coord[0] -  starting_pos[0] <= 1 and -1 <= random_coord[1] -  starting_pos[1] <= 1):
                self._mine_coords.append(random_coord)
        # Create each specific type of LED object in the grid, depending on whether it is on or next to a mine
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
        """Method that fluctuates the brightness of the selected pixel to show the location of the joystick cursor (obtained using message passing)."""
        # Set the modulated brightness of LED at the joystick position
        cursor_led = self.get_pixel(joystick.get_pos())
        cursor_led.set_brightness(MAX_BRIGHTNESS * self._cursor_brightness // 100)
        # Fade up or down between 100% and and the minimum cursor brightness (defined earlier)
        if self._cursor_fade_down:
            self._cursor_brightness -= CURSOR_FADE_SPEED
            if self._cursor_brightness <= CURSOR_MIN_BRIGHTNESS:
                self._cursor_fade_down = False
        else:
            self._cursor_brightness += CURSOR_FADE_SPEED
            if self._cursor_brightness >= 100:
                self._cursor_fade_down = True

    def increment_reveal_counter(self):
        """Public mutator method that adds one to the counter each time a non-mine LED is revealed."""
        self._reveal_counter += 1

    def get_reveal_counter(self) -> int:
        """Public accessor method for the reveal counter attribute."""
        return self._reveal_counter

    def end_game(self, last_pos: tuple[int, int], won: bool):
        """Method called when the game is over, i.e. mine hit or all mines avoided."""
        # Update the game-ending colour depending on whether the game was won or lost.
        if won:
            game_finish_colour = GAME_WON_COLOUR
            self._game_won = True
        else:
            game_finish_colour = GAME_LOST_COLOUR
        # Reset the fading cursor pixel to maximum brightness
        self.get_pixel(last_pos).set_brightness(MAX_BRIGHTNESS)
        # Reveal each mine, one by one with a time delay interval
        for led in self._led_list:
            if isinstance(led, Mine):
                led.set_colour(game_finish_colour)
                led.show()
                self.draw_pixels()
                time.sleep(MINE_REVEAL_INTERVAL)
        # Show every LED and set their colour to the game_finish_colour
        for led in self._led_list:
            led.show()
            led.set_colour(game_finish_colour)
        self.draw_pixels()
        time.sleep(GAME_OVER_DURATION)
        # Reset all pixels to black to prevent ongoing power output requirements
        for led in self._led_list:
            led.set_colour((0, 0, 0))
        self._game_over = True

class LED:
    """LED class -- used for each pixel in the matrix"""
    def __init__(self, grid_pos: tuple[int, int], colour: tuple[int, int, int]):
        """Instantiates an LED pixel object with the appropriate attributes."""
        # While the following attributes could be private (two leading underscores) to prevent their use anywhere outside this specific class,
        # they need to be accessed by the following subclasses for full functionality. Thus they have been declared as 'protected' (one leading underscore).
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
        """Public mutator method called when pixel is flagged as a mine (whether it is or not)."""
        self._flagged = not self._flagged

    def reveal(self, panel: PanelManager):
        """Public mutator method called when the pixel is selected and / or revealed."""
        if not self._revealed:
            self._flagged = False
            self._revealed = True
            # Increment reveal counter and check winning condition, whether all non-mine LEDs have been revealed
            panel.increment_reveal_counter()
            if panel.get_reveal_counter() == PIXELS_X * PIXELS_Y - NUMBER_OF_MINES:
                panel.end_game(self._grid_pos, True)

    def show(self):
        """Public mutator method with same functionality as the reveal method; used for game ending sequence."""
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
    """Mine subclass of LED -- type of pixel user should avoid in the game to win"""
    def __init__(self, grid_pos: tuple[int, int]):
        """Creates an instance of a mine LED by overriding and using the parent constructor."""
        super().__init__(grid_pos, MINE_COLOUR)

    def reveal(self, panel: PanelManager):
        """Overrides the reveal method from the parent class and triggers the (losing) end_game method from the PanelManager."""
        panel.end_game(self._grid_pos, False)

class EmptySquare(LED):
    """EmptySquare subclass of LED -- type of pixel with no mine or number, reveals all pixels next it"""
    def __init__(self, grid_pos: tuple[int, int]):
        """Creates an instance of an empty square LED by overriding and using the parent constructor."""
        super().__init__(grid_pos, EMPTYSQUARE_COLOUR)

    def reveal(self, panel: PanelManager):
        """Overrides the reveal method from the parent class and triggers reveal method for surrounding LEDs (recursion)."""
        super().reveal(panel)
        for a in range(-1, 2):
            for b in range(-1, 2):
                new_pos = (self._grid_pos[0] + a, self._grid_pos[1] + b)
                # Only reveal surrounding pixels if they are within the grid, not the current pixel and not a mine
                if 0 <= new_pos[0] < PIXELS_X and 0 <= new_pos[1] < PIXELS_Y and new_pos != self._grid_pos:
                    led = panel.get_pixel(new_pos)
                    if not led.is_revealed() and not isinstance(led, Mine):
                        led.reveal(panel)

class NumberSquare(LED):
    """NumberSquare subclass of LED -- type of pixel displaying specific colour depending on number of surrounding mines"""
    def __init__(self, grid_pos: tuple[int, int], num: int):
        """Creates an instance of a number square LED by overriding and using the parent constructor."""
        super().__init__(grid_pos, NUMBERSQUARE_COLOURS[num])

class Joystick(MiniJoyStickI2C):
    """Joystick subclass of MiniJoyStickI2C from the given module -- manages and interprets joystick input"""
    def __init__(self, i2c: I2C):
        """Instantiates a joystick object, calling the parent constructor and then creates additional attributes"""
        super().__init__(i2c)  # Call the parent constructor for basic joystick functionality
        self._game_started = False  # Boolean attribute to determine whether game has started, i.e. board is setup
        self._prev_time = time.time_ns()  # Used to track the last time the joystick was used
        self._pos = [PIXELS_X // 2, PIXELS_Y // 2]  # Position tracker, initially at the centre of the board

    def get_pos(self) -> list[int]:
        """Accessor method for joystick cursor position."""
        return self._pos

    def _get_direction(self, current_time: int) -> str | None:
        """Non-public method that returns the direction the joystick is pointed towards, outside of debouncing time."""
        # current_time is used to represent the current time (number of nanoseconds) while avoiding confusion with the time module name
        if current_time - self._prev_time > JOYSTICK_DEBOUNCE_DURATION:
            x_value = super().analog_read_x()
            y_value = super().analog_read_y()
            if x_value == 0:
                self._prev_time = current_time
                return 'left'
            elif x_value == 255:
                self._prev_time = current_time
                return 'right'
            elif y_value == 0:
                self._prev_time = current_time
                return 'down'
            elif y_value == 255:
                self._prev_time = current_time
                return 'up'
        return None

    def _b_pressed(self, current_time: int) -> bool:
        """Non-public method to check whether the 'B' button is pressed, outside of debouncing time."""
        if current_time - self._prev_time > JOYSTICK_DEBOUNCE_DURATION and super().button_pressed(super().BUTTON_B):
            self._prev_time = current_time
            return True
        else:
            return False

    def _c_pressed(self, current_time: int) -> bool:
        """Non-public method to check whether the 'C' button is pressed, outside of debouncing time."""
        if current_time - self._prev_time > JOYSTICK_DEBOUNCE_DURATION and super().button_pressed(super().BUTTON_C):
            self._prev_time = current_time
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
            if not self._game_started:
                panel.setup_game(self._pos)
                self._game_started = True
                led = panel.get_pixel(self._pos)
            led.reveal(panel)
        elif self._game_started and self._c_pressed(current_time):
            led.flag()

# Instantiate joystick and panel_manager objects
joystick = Joystick(I2C_BUS)
panel_manager = PanelManager(PIXELS_X, PIXELS_Y, MATRIX_PIN)

# Store the starting time of the game for score tracking purposes.
start_time = int(time.time())

# Game loop (runs until user wins, loses or presses blue exit button)
while not panel_manager.is_game_over() and not joystick.button_pressed(MiniJoyStickI2C.BUTTON_D):
    # Call the three main facade methods to run the game
    joystick.check_joystick(panel_manager)
    panel_manager.flash_cursor(joystick)
    panel_manager.draw_pixels()

# Store the ending time of the game for score tracking purposes.
end_time = int(time.time())
# The "high score.txt" file must be downloaded to the microcontroller with first line "HIGH SCORES:"
if panel_manager.is_game_won():
    with open("high score.txt", "r+") as f:
        last_line = f.readlines()[-1]
        current_score = end_time - start_time
        # Only add to the file if there is no best time score or it beats the previous one
        if last_line == "HIGH SCORES:":
            f.write(f"\nTime: {current_score//60} min {current_score%60} sec | Mines: {NUMBER_OF_MINES}")  # converts seconds to minutes and seconds
        else:
            last_line = last_line.strip("Time: ").split()
            previous_score = int(last_line[0])*60 + int(last_line[2])  # Combine minutes and seconds
            if current_score < previous_score:
                f.write(f"\nTime: {current_score//60} min {current_score%60} sec | Mines: {NUMBER_OF_MINES}")