import struct
import time, serial, serial.tools.list_ports, serial.tools.list_ports_common, sys
from struct import unpack
import numpy as np
import multiprocessing as mp
from threading import Thread
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
        'end_transmission': b'\x07'
    }

    def __init__(self, com_port):
        self.lc_offset = 0
        self.com_port = com_port
        self.mc = serial.Serial(self.com_port, Microcontroller.baud_rate, timeout=Microcontroller.time_out)
        time.sleep(2)
        self.instrument_idxs = None
        # self.top_offset, self.bottom_offset = return_calibration_offsets()

    def trigger_led(self, trigger_idxs):
        instrument_relative_idxs = np.argwhere(np.isin(self.instrument_idxs, trigger_idxs, assume_unique=True)).astype(np.uint8).flatten()

        if instrument_relative_idxs.shape[0] != 0:
            self.send_instructions(self.trigger_led.__name__, instrument_relative_idxs.tobytes(), wait=False)
            self.send_instructions('end_transmission', wait=False)

    def query_id(self) -> int:
        mc_id = None
        self.send_instructions('query_id')
        with suppress(struct.error):
            mc_id = unpack('b', self.mc.read(1))[0]

        return mc_id

    def send_instructions(self, instruction_cmd, arg_bytes=None, wait=True):
        self.mc.write(self.byte_commands[instruction_cmd])
        if arg_bytes is not None:
            self.mc.write(arg_bytes)
        if wait:
            time.sleep(self.byte_instruction_wait)

    def setup(self, mc_settings):
        self.instrument_idxs = mc_settings['instrument_idxs']



        for settings_tuple, command in zip((mc_settings['led_colors'], mc_settings['color_style_per_data_line'], mc_settings['instrument_count_per_data_line']),
                                     ('set_led_colors', 'set_color_style', 'set_instrument_count')):
            setting_values = np.hstack(settings_tuple).tobytes()
            self.send_instructions(command, setting_values)
            self.send_instructions('end_transmission')

        self.send_instructions('setup_complete')










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
    mc_count = 0

    for mc_i, settings in enumerate(microcontroller_settings):
        if settings is not None:
            mc_count += 1
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

    return microcontrollers, mc_count





def write_led_trigger_thread(mc_dict):
    mc: Microcontroller
    for mc, byte in zip(mc_dict['mcs'], mc_dict['bytes']):
        mc.send_instructions(mc.byte_commands['trigger_led'], byte)


def mc_child_process(mp_shared_array: mp.Array, mp_child_is_ready: mp.Value, main_process_is_running: mp.Value):
    def main():
        led_trigger_view = np.ndarray(5, buffer=mp_shared_array._obj, dtype=np.uint8)
        mp_child_is_ready.value = 1
        while main_process_is_running.value:
            if led_trigger_view[-1] == 1:
                threads = []
                led_triggers = np.argwhere(led_trigger_view[0:-1] == 1).flatten()
                for mc in mcs:
                    thread = Thread(target=mc.trigger_led, args=(led_triggers, ))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()
                led_trigger_view[led_triggers] = 0
                led_trigger_view[-1] = 0

    mcs, mc_count = return_microcontrollers()
    if len(mcs) == mc_count:
        main()
    else:
        print('Valid Microcontrollers did not match the settings count in config.py')
        print('Exiting the program')
        main_process_is_running.value = 0
        mp_child_is_ready.value = 1