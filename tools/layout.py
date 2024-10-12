# main.py

# Constants
PANEL_WIDTH = 8       # Width of a single panel in pixels
PANEL_HEIGHT = 32     # Height of a single panel in pixels
NUM_COLUMNS = 5       # Number of panels horizontally
NUM_ROWS = 3          # Number of panels vertically

LEDS_PER_PANEL = PANEL_WIDTH * PANEL_HEIGHT

TOTAL_WIDTH = PANEL_WIDTH * NUM_COLUMNS
TOTAL_HEIGHT = PANEL_HEIGHT * NUM_ROWS

def led_index(x, y):
    """
    Calculate the LED index for the given (x, y) coordinate in the LED matrix.

    Parameters:
    x (int): The x-coordinate (horizontal position) of the LED.
    y (int): The y-coordinate (vertical position) of the LED.

    Returns:
    int: The LED index corresponding to the given (x, y) coordinate.
    """

    if not (0 <= x < TOTAL_WIDTH) or not (0 <= y < TOTAL_HEIGHT):
        raise ValueError("Coordinates out of bounds.")

    # Determine panel coordinates
    column = x // PANEL_WIDTH
    row = y // PANEL_HEIGHT

    # Local coordinates within the panel
    x_in_panel = x % PANEL_WIDTH
    y_in_panel = y % PANEL_HEIGHT

    # Determine panel index based on wiring sequence (snake pattern)
    if column % 2 == 0:
        # Even column: panels connected from top to bottom
        panel_index = column * NUM_ROWS + row
        orientation = 'normal'
    else:
        # Odd column: panels connected from bottom to top
        panel_index = column * NUM_ROWS + (NUM_ROWS - 1 - row)
        orientation = 'reversed'

    # Calculate LED index within the panel (serpentine pattern)
    if orientation == 'normal':
        if y_in_panel % 2 == 0:
            # Even row: right to left
            x_coord = (PANEL_WIDTH - 1) - x_in_panel
        else:
            # Odd row: left to right
            x_coord = x_in_panel
        led_index_within_panel = y_in_panel * PANEL_WIDTH + x_coord
    elif orientation == 'reversed':
        # Reversed panel orientation
        y_in_panel_reversed = (PANEL_HEIGHT - 1) - y_in_panel
        if y_in_panel_reversed % 2 == 0:
            # Even row in reversed panel
            x_coord = x_in_panel
        else:
            # Odd row in reversed panel
            x_coord = (PANEL_WIDTH - 1) - x_in_panel
        led_index_within_panel = y_in_panel_reversed * PANEL_WIDTH + x_coord
    else:
        raise ValueError("Invalid orientation.")

    # Calculate the total LED index
    total_led_index = panel_index * LEDS_PER_PANEL + led_index_within_panel

    return total_led_index

# Example usage:
if __name__ == "__main__":
    # Test coordinates
    test_coordinates = [
        (0, 0),             # Top-left corner of the entire matrix
        (8, 0),             # Start of second column, top row, should give 1535 ***
        (9, 0),             # Start of second column, top row, should give 1534
        (10, 0),             # Start of second column, top row, should give 1533
        (11, 0),             # Start of second column, top row, should give 1532
        (12, 0),             # Start of second column, top row, should give 1531
        (13, 0),             # Start of second column, top row, should give 1530
        (14, 0),             # Start of second column, top row, should give 1529
        (15, 0),             # Start of second column, top row, should give 1528
        (16, 0),             #  should give 1543  ***
        (17, 0),             #  should give 1542  ***
        (18, 0),             #  should give 1541  ***
        (19, 0),             #  should give 1540  ***
        (20, 0),             #  should give 1539  ***
        (21, 0),             #  should give 1538  ***
    ]

    for x, y in test_coordinates:
        index = led_index(x, y)
        print(f"LED index at coordinate ({x}, {y}): {index}")
