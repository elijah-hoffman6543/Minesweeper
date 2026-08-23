# https://github.com/nulllaborg/mini-joystick-module
from machine import I2C

class MiniJoyStickI2C:
    # Constants converted from the header file
    # I2C addresses for multiple mini-joysticks
    #
    # From 0x24+0
    JOYSTICK_I2C_ADDR = 0x5A
    
    JOYSTICK_LEFT_X_REG = 0x10
    JOYSTICK_LEFT_Y_REG = 0x11
    JOYSTICK_RIGHT_X_REG = 0x12
    JOYSTICK_RIGHT_Y_REG = 0x13

    BUTTON_OK_REG = 0x20
    BUTTON_C_REG = 0x21
    BUTTON_A_REG = 0x22
    BUTTON_B_REG = 0x23
    BUTTON_D_REG = 0x24

    # Button States
    PRESS_DOWN = 0
    PRESS_UP = 1
    PRESS_REPEAT = 2
    SINGLE_CLICK = 3
    DOUBLE_CLICK = 4  
    LONG_PRESS_START = 5
    LONG_PRESS_HOLD = 6
    NONE_PRESS = 8

    # Button Identifiers (Mapping enum constants)
    BUTTON_A = 0
    BUTTON_B = 1
    BUTTON_C = 2
    BUTTON_D = 3
    BUTTON_OK = 4

    def __init__(self, i2c: I2C, addr: int = JOYSTICK_I2C_ADDR):
        """
        Initializes the joystick handle.
        :param i2c: An initialized machine.I2C object
        :param addr: The I2C address of the joystick board (defaults to 0x5A)
        """
        self.i2c = i2c
        self.board_addr = addr
        self.left_x = 0
        self.left_y = 0

    def _read_byte(self, reg: int) -> int:
        """Reads a single byte from a specified register over I2C."""
        try:
            # writeto then readfrom mimics WireReadDataArray
            self.i2c.writeto(self.board_addr, bytes([reg]), False)
            data = self.i2c.readfrom(self.board_addr, 1)
            return data[0]
        except Exception:
            return 0xFF  # Error fallback consistent with Arduino default

    def analog_read_x(self) -> int:
        """Read and return the analog value of the joystick X-axis."""
        self.left_x = self._read_byte(self.JOYSTICK_LEFT_X_REG)
        return self.left_x

    def analog_read_y(self) -> int:
        """Read and return the analog value of the joystick Y-axis."""
        self.left_y = self._read_byte(self.JOYSTICK_LEFT_Y_REG)
        return self.left_y

    def get_button_status(self, button: int) -> int:
        """Returns the specific event status of the requested button."""
        if button == self.BUTTON_A:
            return self._read_byte(self.BUTTON_A_REG)
        elif button == self.BUTTON_B:
            return self._read_byte(self.BUTTON_B_REG)
        elif button == self.BUTTON_C:
            return self._read_byte(self.BUTTON_C_REG)
        elif button == self.BUTTON_D:
            return self._read_byte(self.BUTTON_D_REG)
        elif button == self.BUTTON_OK:
            return self._read_byte(self.BUTTON_OK_REG)
        else:
            return 0xFF

    def button_pressed(self, button: int) -> bool:
        """Returns True if the button is currently interacting (not NONE or error)."""
        status = self.get_button_status(button)
        return status != self.NONE_PRESS and status != 0xFF

    def button_released(self, button: int) -> bool:
        """Returns True if the button is completely released."""
        return self.get_button_status(button) == self.NONE_PRESS