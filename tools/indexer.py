WIDTH = 32
HEIGHT = 96
LEDS_PER_PANEL = 512

def map_xy_to_led_index(x: int, y: int) -> int:
    panel_y = y // 16
    local_y = y % 16
    panel_index = panel_y

    led_index = panel_index * LEDS_PER_PANEL

    if local_y < 8:
        # Top half of the panel
        if x % 2 == 0:
            # Even columns go down
            led_index += x * 8 + local_y
        else:
            # Odd columns go up
            led_index += x * 8 + (7 - local_y)
    else:
        # Bottom half of the panel
        if x % 2 == 0:
            # Even columns go down
            led_index += 256 + x * 8 + (local_y - 8)
        else:
            # Odd columns go up
            led_index += 256 + x * 8 + (15 - local_y)

    return led_index

if __name__ == "__main__":
    print(map_xy_to_led_index(0, 0))  # Should print 0
    print(map_xy_to_led_index(1, 0))  # Should print 7
    print(map_xy_to_led_index(0, 1))  # Should print 1
    print(map_xy_to_led_index(1, 1))  # Should print 6
    print(map_xy_to_led_index(31,0))  # Should print 255
    print(map_xy_to_led_index(0,8))  # Should print 256
    print(map_xy_to_led_index(0,9))  # Should print 257
