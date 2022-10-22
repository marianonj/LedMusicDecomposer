import numpy as np
from Errors import *
import sys
sys.tracebacklimit = 0
save_file_array_count = 10

'''MC Config Formatting
{'name': The name of your microcontroller. You can get a list of usb names using PrintUsbNames.py. 
         You do not need to have the full name of the device, only a str of sufficient length to be unique relative to your other usb names.

'id': The device id in the Arduino script. Make sure these match.

'instruments_per_data_line': A tuple(tuple(int, ...), ) . These represent the instruments and their order for a given data line.
                             One data line : Tuple((int, ...), )
                             Mulitple data lines : Tuple((int, ...), (int, ...) )

'color_style_per_data_line': A tuple(str, ...). These represent the fill logic used to color in the lights. Use the str value for 
                             One data line: Tuple(int, )
                             Multiple data lines : Tuple(int, )
}'''

# BGR color formatting for each instrument, range 0-255
instrument_colors = np.array([[255, 255, 0],
                              [0, 255, 0],
                              [255, 0, 255],
                              [0, 0, 255]], dtype=np.uint8)

fill_styles = {'segmented': 0,
               'dispersed': 1}
bass, drum, voice, other = 0, 1, 2, 3

mc_config_0 = {'name': 'Silicon Labs',
               'id': 0,
               'instruments_per_data_line': ((bass, drum, voice, other),),
               'color_style_per_data_line': ('segmented',)
               }
mc_config_1 = None
mc_config_2 = None
mc_config_3 = None
microcontroller_settings = (mc_config_0, mc_config_1, mc_config_2, mc_config_3)


def raise_errors(errors):
    if not errors:
        return
    try:
        raise errors.pop()
    finally:
        raise_errors(errors)


def config_type_check(errors: list, ):
    mc_types = {'name': str,
                'id': int,
                'instruments_per_data_line': (tuple, int),
                'color_style_per_data_line': (tuple, str),
                }

    for setting_i, setting in enumerate(microcontroller_settings):
        if setting is not None:
            if not isinstance(setting, dict):
                errors.append(TypeError(f'Expected type {dict} for mc_{setting_i} settings, got {type(setting)}'))
                continue

            for dict_key in mc_types.keys():
                if dict_key not in setting:
                    errors.append(KeyError(f'Key<{dict_key}> missing for mc_{setting_i} settings'))
                    continue

                if isinstance(mc_types[dict_key], tuple):
                    if not isinstance(setting[dict_key], tuple):
                        errors.append(TypeError(f'Expected tuple for key <{dict_key}> in MC_{setting_i} settings, got {type(setting[dict_key])}'))
                        continue
                    for setting_tuple_i, setting_value, in enumerate(setting[dict_key]):
                        if isinstance(setting_value, tuple):
                            if not setting_value:
                                errors.append(ValueError(f'Empty tuple for key <{dict_key}> at idx {setting_tuple_i} in MC_{setting_i} settings'))
                                continue
                            else:
                                for setting_tuple_value_i, setting_tuple_value in enumerate(setting_value):
                                    if not isinstance(setting_tuple_value, mc_types[dict_key][1]):
                                        errors.append(ValueError(f'Expected type <{mc_types[dict_key][1]}> for key <{dict_key}> at tuple_idx [{setting_tuple_i}][{setting_tuple_value_i}], got {type(setting_tuple_value)}'))
                                        continue
                        else:
                            if not isinstance(setting_value, mc_types[dict_key][1]):
                                errors.append(ValueError(f'Expected type <{mc_types[dict_key][1]}> for key <{dict_key}> at idx [{setting_tuple_i}], got {type(setting_tuple_value)}'))

                    if not isinstance(setting[dict_key], mc_types[dict_key]):
                        errors.append(TypeError(f'Expected {mc_types[dict_key]} for key <{dict_key}> in MC_{setting_i} settings, got {type(setting[dict_key])}'))
                        continue


def config_value_check(errors):
    valid_instrument_idxs = [bass, drum, voice, other]
    for setting_i, setting in enumerate(microcontroller_settings):
        if setting is None:
            continue

        if len(setting['instruments_per_data_line']) != len(setting['color_style_per_data_line']):
            errors.append(InvalidConfig(f'Key <instruments_per_data_line> and key <color_style_per_data_line> are different lengths for MC_{setting_i} settings'))

        for instrument_tuple_i, instrument_tuple_value in enumerate(setting['instruments_per_data_line']):
            if isinstance(instrument_tuple_value, tuple):
                for instrument_i, instrument in enumerate(instrument_tuple_value):
                    if instrument not in valid_instrument_idxs:
                        errors.append(
                            InvalidInstrument(f'Expected instrument idx to be one of values {valid_instrument_idxs} for key <instruments_per_data_line> at idx <[{instrument_tuple_i}][{instrument_i}]> in MC_{setting_i} settings, got {instrument}. Ensure you are using the #Instrument idx variables'))
            elif instrument_tuple_value > 3:
                errors.append(InvalidInstrument(f'Expected instrument idx be one of values {valid_instrument_idxs} for key <instruments_per_data_line> at idx <[{instrument_tuple_i}]> in MC_{setting_i} settings, got {instrument_tuple_value}. Ensure you are using the Instrument idx variables'))

        for fill_type in setting['color_style_per_data_line']:
            if fill_type not in fill_styles:
                errors.append(InvalidFillType(f'Expected fill value to be one of values {valid_instrument_idxs} for key <instruments_per_data_line> at idx <[{instrument_tuple_i}][{instrument_i}]> in MC_{setting_i} settings, got {instrument}. Ensure you are using the #Instrument idx variables'))


def config_check():
    errors = []
    for check in (config_type_check, config_value_check):
        check(errors)
        if errors:
            raise_errors(errors)
    for config_i, setting in enumerate(microcontroller_settings):
        if setting is not None:
            setting_lengths = np.array([len(setting[key]) for key in ('instruments_per_data_line', 'color_style_per_data_line')])
            # All three of the data_line_param_tuples must be the same length
            if np.unique(setting_lengths).shape[0] != 1:
                errors.append(InvalidConfig(f'Mc_{config_i} has invalid config keys for {("instruments_per_data_line", "color_style_per_data_line")}. \n All the above keys must have a tuple of the same length.'))
