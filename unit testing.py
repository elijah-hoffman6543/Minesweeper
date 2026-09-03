import unittest

# Copy method from main.py to this module for testing purposes (brightness parameter was added)
def calculate_rgb_method(brightness: int, colour: tuple[int, int, int]) -> tuple:
    return tuple(map(lambda x: x * brightness // 255, colour))

class TestCalculateRGBMethod(unittest.TestCase):

    def test_extremes(self):
        # Run the following tests for 6 varying brightnesses ranging from 0 to 255
        for brightness in range(0, 256, 51):
            # Test boundary conditions / extreme colours (white and black):
            self.assertEqual(calculate_rgb_method(brightness, (0, 0, 0)), (0, 0, 0))
            self.assertEqual(calculate_rgb_method(brightness, (255, 255, 255)), (brightness, brightness, brightness))

    def test_unexpected(self):
        # Test unexpected input values:
        self.assertEqual(calculate_rgb_method(81, (-10, 150, 300)), (-4, 47, 95))

    def test_common(self):
        # Test typical / common cases:
        self.assertEqual(calculate_rgb_method(50, (255, 131, 212)), (50, 25, 41))
        self.assertEqual(calculate_rgb_method(67, (143, 112, 77)), (37, 29, 20))
        self.assertEqual(calculate_rgb_method(199, (107, 255, 118)), (83, 199, 92))

    def test_error(self):
        # Test error:
        with self.assertRaises(TypeError):
            calculate_rgb_method('23', 'ffad80')  # type: ignore

if __name__ == '__main__':
    unittest.main()