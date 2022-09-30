# MC Data types are as follows
# Name - M
# Color - Desired Color
# Data_
# instrument_segmentation_style : 'Segmented, Interlaced'
# Data_
import numpy as np
mc_format = {
    'name': str,
    'led_colors': ((np.ndarray[np.uint8, np.uint8, np.uint8]), ...),
    'segmented_instruments': (bool, ...),
    'data_pins': (int, ...),
    'instrument_idxs': ((int, ...), ...),
    'led_count': (int, ...),
    'id': int
}

mc_1 = {'name': 'Silicon Labs',
        'led_colors': ((np.array([255, 0, 0], dtype=np.uint8)), ),
        'color_style': ('Segmented', ),
        'data_pins': (0, ),
        'instrument_idxs': ((0, 1, 2, 3), ),
        'led_count': (10,),
        'id': 0}

mc_2 = None

mc_3 = None

mc_4 = None

microcontroller_settings = [mc_1, mc_2, mc_3, mc_4]
