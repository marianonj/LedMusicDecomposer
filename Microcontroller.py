import struct
import time, serial, serial.tools.list_ports, serial.tools.list_ports_common, sys
from struct import unpack
import numpy as np
from config import microcontroller_settings
from contextlib import suppress


class Microcontroller:
    time_out, byte_instruction_wait = 2, .25
    microcontroller_count = 4
    baud_rate = 115200
    # Top_Left,
    lc_pixel_locations = None
    byte_order: str = sys.byteorder
    byte_commands = {
        'trigger_instrument': b'\x01',
        'query_id': b'\x02',
        'set_led_count': b'\x03',
        'end_of_transmission': b'\x04',
        'set_led_light_type': b'\x05',
        'set_led_data_lines': b'\x06',
        'setup_complete': b'\x07'
    }

    # Byte commands - Lights
    # b'\0x0' - Trigger LC Read (0 - TL, 1 - TR, 2 - BL, 3 - BR)
    # b'\0x1' - Light LED
    # b'\0x2' - Return ID (0 - TL, 1 - TR, 2 - BL, 3 - BR)

    # b'\0x1' - LC 1
    # b'\0x1' - Light led
    # b'\0x2' - Lc 2

    # Byte commands - Camera Trigger
    # b'\0x3' - str 'lr' - both
    # b'\0x4' - str 'l' - left
    # b'\0x5' - str 'r', right

    # Byte Commands - LC Trigger
    # b'\0x6' - Triggers LC Read

    def __init__(self, com_port):
        self.lc_offset = 0
        self.com_port = com_port
        self.mc = serial.Serial(self.com_port, Microcontroller.baud_rate, timeout=Microcontroller.time_out)

        # self.top_offset, self.bottom_offset = return_calibration_offsets()

    def trigger_led(self, instrument_id):
        self.send_instructions(bytearray(self.byte_commands['trigger_led'] + instrument_id.to_bytes(instrument_id, 1, self.byte_order)))

    def query_id(self) -> int:
        id = None
        self.send_instructions(self.byte_commands[self.query_id.__name__])
        time.sleep(self.byte_instruction_wait)

        with suppress(struct.error):
            id = int(unpack('f', b''.join([self.mc.read(4)]))[0])

        return id

    def set_led_count(self, count):
        self.send_instructions(bytearray(self.byte_commands[self.set_led_count.__name__] + count.to_bytes(count, 1, self.byte_order)))
        pass

    def set_led_light_type(self, type_i):
        self.send_instructions(bytearray(self.byte_commands[self.set_led_light_type.__name__] + type_i.to_bytes(type_i, 1, self.byte_order)))
        pass

    def set_led_colors(self, color: np.ndarray):
        self.send_instructions(bytearray(self.byte_commands[self.set_led_colors.__name__] + color.tobytes()))

    def setup_complete(self):
        self.send_instructions([self.setup_complete.__name__])

    def send_instructions(self, instruction_bytes: bytearray or bytes):
        self.mc.write(instruction_bytes), self.mc.write(self.byte_commands['end_of_transmission'])
        time.sleep(self.byte_instruction_wait)


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
            return f'No microcontroller matching the name {microcontroller_setting_dict["name"]} was found'
        else:
            return f'Ports with device name {microcontroller_setting_dict["name"]} are already designated to a previous arduino device'

    valid_mc_id = False
    for com_port in com_ports:
        mc_temp: Microcontroller
        with Microcontroller(com_port) as mc_temp:
            mc_id = mc_temp.query_id()
            if mc_id == microcontroller_setting_dict['id']:
                occupied_ports.append(com_port)
                valid_mc_id = True
                break

    if not valid_mc_id:
        return f'The id returned by the microcontrollers did not match the id in the config.py.\n Ensure the arduino script id matches the mc dictionary id'


def return_microcontrollers() -> [Microcontroller, ...]:
    ports = serial.tools.list_ports.comports()
    microcontrollers, currently_used_ports = [], []
    from config import microcontroller_settings

    for mc_i, settings in enumerate(microcontroller_settings):
        if settings is not None:
            ret = return_microcontroller_class_instance(ports, currently_used_ports, settings)
            if ret is str:
                print(f'Microcontroller {mc_i + 1} failed to setup. Please check mc_{mc_i + 1} settings in config.py')
                print(f'Error message: {ret}')
                break
            else:
                microcontrollers.append(ret)
        else:
            break

    return


if __name__ == '__main__':
    t = return_microcontrollers()
