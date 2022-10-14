# MC Data types are as follows
# Name - M
# Color - Desired Color
# Data_
# instrument_segmentation_style : 'Segmented, Interlaced'
# Data_
import numpy as np
from enum import Enum

save_file_array_count = 10

mc_format = {
    'name': str,
    'led_colors': (np.ndarray, ...),
    'color_style': (str, ...),
    'data_pins': ((int, ...), ...),
    'instrument_idxs': ((int, ...), ...),
    'led_count': ((int, ...), ...),
    'id': int
}
color_styles = {'segmented': np.array([0], dtype=np.uint8),
                'dispersed': np.array([1], dtype=np.uint8)}

#BGR
instrument_colors = np.array([[255, 255, 0],
                              [0, 255, 0],
                              [255, 0, 255],
                              [0, 0, 255]], dtype=np.uint8)


mc_1 = {'name': 'Silicon Labs',
        'id': 0,
        'instrument_idxs': (np.array([0, 1, 2, 3], dtype=np.uint8), ),
        'color_style_per_data_line': (color_styles['dispersed'], ),
        'instrument_count_per_data_line': (np.array([4], dtype=np.uint8), )
        }

mc_2 = None

mc_3 = None

mc_4 = None

microcontroller_settings = [mc_1, mc_2, mc_3, mc_4]
microcontroller_count = 0
for mc in microcontroller_settings:
    if mc is not None:
        microcontroller_count += 1
