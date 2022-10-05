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
color_styles = {'segmented':np.array([0], dtype=np.uint8),
                'dispersed':np.array([1], dtype=np.uint8)}


mc_1 = {'name': 'Silicon Labs',
        'led_colors': (np.array([255, 0, 0], dtype=np.uint8), np.array([255, 0, 0], dtype=np.uint8), np.array([255, 0, 0], dtype=np.uint8), np.array([255, 0, 0], dtype=np.uint8)),
        'color_style': (color_styles['segmented'], ),
        'instrument_idxs': (np.array([0, 1, 2, 3], dtype=np.uint8), ),
        'id': 0}

mc_2 = None

mc_3 = None

mc_4 = None

microcontroller_settings = [mc_1, mc_2, mc_3, mc_4]

def config_check(mc_config, key):
    error_msgs = ''
    if key in mc_config:
        if type(key) != type(mc_format[key]):
            error_msgs += f'Expected type {type(mc_format[key])} for key:{key}. Received type {type(mc_config[key])} \n'
            pass
        else:
            if key == 'name':
                if len(mc_config[key]) == 0:
                    error_msgs += f'String is empty for key:{key}, length must be a minimum of 1 \n'
            elif key == 'data_pins':
                for comparison_key in ('led_count', 'color_style'):
                    if len(mc_config[key]) != len(mc_config[comparison_key]):
                        error_msgs += f'Key:{key} length({len(mc_config[key])}) does not match does not match led_count length ({len(mc_config[comparison_key])} \n'
            elif key == 'colors':
                pass
            elif key == 'color_style':
                pass
            elif key == 'instrument_idxs':
                pass
            elif key == 'led_count':
                pass
            elif key == 'id':
                pass



        pass
    else:
        error_msgs += f'Key:{key} not found'

    print('b')
