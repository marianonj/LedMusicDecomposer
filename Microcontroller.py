import struct
import time, serial, serial.tools.list_ports, serial.tools.list_ports_common, sys
from struct import unpack
import numpy as np
from config import microcontroller_settings
from contextlib import suppress


class Microcontroller:
    time_out, byte_instruction_wait = 2, .5
    microcontroller_count = 4
    baud_rate = 115200
    # Top_Left,
    lc_pixel_locations = None
    byte_order: str = sys.byteorder
    byte_commands = {
        'query_id': b'\x00',
        'trigger_led': b'\x01',
        'set_color_style': b'\x03',
        'set_instrument_count': b'\x04',
        'set_led_colors': b'\x05',
        'setup_complete': b'\x06',
        'end_led_transmission': b'\x07'
    }


    def __init__(self, com_port):
        self.lc_offset = 0
        self.com_port = com_port
        self.mc = serial.Serial(self.com_port, Microcontroller.baud_rate, timeout=Microcontroller.time_out)
        time.sleep(2)

        # self.top_offset, self.bottom_offset = return_calibration_offsets()

    def __enter__(self):
        print('b')
        return self.mc

    def __exit__(self):
        self.mc.close()

    def trigger_led(self, instrument_ids):
        self.send_instructions(self.byte_commands[self.trigger_led.__name__], instrument_ids.astype(np.uint8).tobytes())
        self.send_instructions(self.byte_commands['end_led_transmission'])

    def query_id(self) -> int:
        mc_id = None
        self.send_instructions(self.byte_commands['query_id'])
        with suppress(struct.error):
            mc_id = unpack('b', self.mc.read(1))[0]


        return mc_id

    def set_led_count(self, count):
        self.send_instructions(bytearray(self.byte_commands[self.set_led_count.__name__] + count.to_bytes(count, 1, self.byte_order)))
        pass

    def set_led_light_type(self, type_i):
        self.send_instructions(bytearray(self.byte_commands[self.set_led_light_type.__name__] + type_i.to_bytes(type_i, 1, self.byte_order)))
        pass

    def setup_complete(self):
        self.send_instructions([self.setup_complete.__name__])

    def send_instructions(self, instruction_byte, arg_bytes= None):
        self.mc.write(instruction_byte)
        if arg_bytes is not None:
            self.mc.write(arg_bytes)
        time.sleep(self.byte_instruction_wait)

    def setup(self, mc_settings):
        for instrument_i, color in enumerate(mc_settings['led_colors']):
            self.send_instructions(self.byte_commands['set_led_colors'], np.hstack((instrument_i, color)))

        for color_style, instrument_idxs in zip(mc_settings['color_style'], mc_settings['instrument_idxs']):
            self.send_instructions(self.byte_commands['set_color_style'], color_style.tobytes())
            self.send_instructions(self.byte_commands['set_instrument_count'], np.array([instrument_idxs.shape[0]], dtype=np.uint8).tobytes())













def microcontroller_config_is_properly_setup() -> None or str:
    error_msg = None


def return_microcontroller_class_instance(ports: list, occupied_ports: list, microcontroller_setting_dict: dict) -> Microcontroller or str:
    # If the fields in the setting_dict are all valid, and the microcontroller is found within the valid usb ports, return the microcontroller
    # Otherwise return an error message
    com_ports = []
    mc_name_match = False
    for port in ports:
        port: serial.tools.list_ports_common.ListPortInfo
        if port.description[0:len(microcontroller_setting_dict['name'])] == microcontroller_setting_dict['name']:
            mc_name_match = True
            if port.name not in occupied_ports:
                com_ports.append(port.device)

    if len(com_ports) == 0:
        if mc_name_match:
            return f'Ports with device name {microcontroller_setting_dict["name"]} are already designated to a previous arduino device'
        else:
            return f'No microcontroller matching the name {microcontroller_setting_dict["name"]} was found'

    for com_port in com_ports:
        try:
            mc = Microcontroller(com_port)
            mc_id = mc.query_id()
            if mc_id is not None:
                occupied_ports.append(com_port)
                return mc
        except serial.SerialException:
            return f'{com_port} is already in use by another program'

    return f'The id returned by the microcontrollers did not match the id in the config.py.\n Ensure the arduino script id matches the mc dictionary id'

def return_microcontrollers() -> [Microcontroller, ...]:
    ports = serial.tools.list_ports.comports()
    microcontrollers, currently_used_ports = [], []
    from config import microcontroller_settings

    for mc_i, settings in enumerate(microcontroller_settings):
        if settings is not None:
            ret = return_microcontroller_class_instance(ports, currently_used_ports, settings)
            if isinstance(ret, str):
                print(f'Microcontroller {mc_i + 1} failed to setup. Please check mc_{mc_i + 1} settings in config.py')
                print(f'Error message: {ret}')
                break
            else:
                ret.setup(settings)
                microcontrollers.append(ret)

        else:
            break

    return microcontrollers

def mc_child_process():
    pass


if __name__ == '__main__':
    t = return_microcontrollers()
    print('b')
