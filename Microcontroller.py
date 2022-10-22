import struct
import time, serial, serial.tools.list_ports, serial.tools.list_ports_common, sys
from struct import unpack
import numpy as np
import multiprocessing as mp
from threading import Thread
import warnings
import Config
from Config import microcontroller_settings
from contextlib import suppress
from Errors import *


class Microcontroller:
    led_minimum_count = 4
    time_out, post_instruction_wait_time = 2, .5
    baud_rate = 115200
    already_used_ids = []
    # Top_Left,
    lc_pixel_locations = None
    byte_order: str = sys.byteorder
    all_instrument_idxs = np.array([Config.bass, Config.drum, Config.voice, Config.other], dtype=np.uint8)
    byte_commands = {
        'query_id': b'\x00',
        'query_num_leds': b'\x01',
        'set_instruments': b'\x02',
        'set_color_style': b'\x03',
        'set_instrument_count': b'\x04',
        'set_led_colors': b'\x05',
        'setup_complete': b'\x06',
        'end_transmission': b'\x07',
        'trigger_led': b'\x08'
    }
    all_configs = Config.microcontroller_settings
    instrument_colors = Config.instrument_colors
    def __init__(self, com_port, name):
        self.com_port, self.name = com_port, name
        try:
            self.mc = serial.Serial(self.com_port, Microcontroller.baud_rate, timeout=Microcontroller.time_out)
        except serial.SerialException:
            raise(PortAccessDenied(f'{self.com_port} denied access. Check to see if it in use by another program.'))


        #Set in Setup - Config Check
        self.mc_settings = self.data_line_count = self.instrument_idxs = None, None, None
        time.sleep(2)
        self.setup()


        # self.top_offset, self.bottom_offset = return_calibration_offsets()

    def trigger_led(self, trigger_idxs):
        instrument_triggers = np.intersect1d(trigger_idxs, self.instrument_idxs).astype(np.uint8)
        if instrument_triggers.shape[0] != 0:
            self.send_instructions(self.trigger_led.__name__, instrument_triggers.tobytes() + self.byte_commands['end_transmission'], wait=False)

    def query_arduino(self) -> (int, list):
        mc_id, led_counts = None, []
        self.send_instructions('query_id')
        with suppress(struct.error):
            mc_id = unpack('b', self.mc.read(1))[0]

        for _ in range(len(self.mc_settings['color_style_per_data_line'])):
            self.send_instructions('query_num_leds')
            led_counts.append(unpack('H', self.mc.read(1))[0])

        return mc_id, led_counts

    def send_instructions(self, instruction_cmd, arg_bytes=None, wait=True):
        self.mc.write(self.byte_commands[instruction_cmd])
        if arg_bytes is not None:
            self.mc.write(arg_bytes)
        if wait:
            time.sleep(self.post_instruction_wait_time)

    def set_instrument_idxs(self):
        if len(self.mc_settings['instruments_per_data_line']) == 1:
            idxs = np.array([self.mc_settings['instruments_per_data_line']], dtype=np.uint8)
        else:
            idxs = np.hstack((self.mc_settings['instruments_per_data_line'])).astype(np.uint8)

        self.instrument_idxs = np.unique(idxs)

    def arduino_config_check(self):
        self.send_instructions('query_id')
        with suppress(struct.error):
            mc_id = unpack('b', self.mc.read(1))[0]
            for mc_setting in self.all_configs:
                if mc_setting['id'] == mc_id and mc_setting['name'] == self.name:
                    self.mc_settings = mc_setting
                    if mc_id in self.already_used_ids:
                        warnings.warn(f'Duplicate Microcontroller_ID {mc_id}')
                    self.already_used_ids.append(mc_id)
                    break
            else:
                raise MicrocontrollerNotFound(f'MC config not found for {self.name}, check configs and that their ids match')
        self.instrument_idxs = np.array([self.mc_settings['instruments_per_data_line']], dtype=np.uint8) if len(self.mc_settings['instruments_per_data_line']) == 1 else np.hstack((self.mc_settings['instruments_per_data_line']))
        self.data_line_count = len(self.mc_settings['instruments_per_data_line'])

        with suppress(struct.error):
            self.send_instructions('query_num_leds')
            led_counts = np.frombuffer(self.mc.read(8), dtype=np.uint16)
            non_zeros_idxs = np.argwhere(led_counts).flatten()
            if (data_line_count := non_zeros_idxs.shape[0]) != self.data_line_count:
                raise LedCountNotSet(f'MC_{mc_id} has {self.data_line_count} data_lines, but only {np.count_nonzero(data_line_count)} has led_counts set. \n'
                                     f'Adjust the led_counts in the Arduino file or the settings in settings.py')
            else:
                counts = led_counts[non_zeros_idxs]
                less_than_minimum = np.argwhere(counts < 4).flatten()
                if less_than_minimum.shape[0] != 0:
                    raise LedCountLessThanMinimum(f'MC_{mc_id} has led count(s) that are less than the minimum of {self.led_minimum_count} at led_idx(s) {non_zeros_idxs[less_than_minimum]}.')



    def setup(self):
        self.arduino_config_check()
        self.set_instrument_idxs()
        instrument_counts = np.array([len(instruments) for instruments in self.mc_settings['instruments_per_data_line']], dtype=np.uint8)
        color_style_per_line = np.array([Config.ColorStyles[fill_style_str].value for fill_style_str in self.mc_settings['color_style_per_data_line']], dtype=np.uint8)

        for instruments in self.mc_settings['instruments_per_data_line']:
            self.send_instructions('set_instruments', np.array(instruments, dtype=np.uint8).tobytes() + self.byte_commands['end_transmission'])

        for settings_value, command in zip((instrument_counts, self.instrument_colors, color_style_per_line), ('set_instrument_count', 'set_led_colors', 'set_color_style', )):
            self.send_instructions(command, settings_value.tobytes() + self.byte_commands['end_transmission'])

            print('b')
        self.send_instructions('setup_complete')
        time.sleep(.5)


def return_microcontroller_class_instance(ports: list, occupied_ports: list, microcontroller_setting_dict: dict) -> Microcontroller or str:
    # If the fields in the setting_dict are all valid, and the microcontroller is found within the valid usb ports, return the microcontroller
    # Otherwise return an error message
    com_port, device_name, mc_name_match = None, None, False
    for port in ports:
        port: serial.tools.list_ports_common.ListPortInfo
        device_name = port.description[0:len(microcontroller_setting_dict['name'])]
        if device_name == microcontroller_setting_dict['name']:
            mc_name_match = True
            if port.name not in occupied_ports:
                occupied_ports.append(port.device)
                com_port = port.device
                break

    if not com_port:
        if mc_name_match:
            raise MicrocontrollerNotFound(f'Ports with device name {microcontroller_setting_dict["name"]} are already designated to a previous arduino device')
        else:
            return MicrocontrollerNotFound(f'No microcontroller matching the name {microcontroller_setting_dict["name"]} was found')
    else:
        try:
            return Microcontroller(com_port, device_name)
        except Exception:
            raise



def return_microcontrollers() -> [Microcontroller, ...]:
    ports = serial.tools.list_ports.comports()
    microcontrollers, currently_used_ports = [], []
    from Config import microcontroller_settings
    mc_count = 0

    for mc_i, settings in enumerate(microcontroller_settings):
        if settings is not None:
            mc_count += 1
            ret = return_microcontroller_class_instance(ports, currently_used_ports, settings)
            if isinstance(ret, str):
                print(f'Microcontroller {mc_i + 1} failed to setup. Please check mc_{mc_i + 1} settings in Config.py')
                print(f'Error message: {ret}')
                break
            else:
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
        print('Valid Microcontrollers did not match the settings count in Config.py')
        print('Exiting the program')
        mp_child_is_ready.value, main_process_is_running.value = 1, 0
