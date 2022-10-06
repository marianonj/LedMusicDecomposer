import os, dir, vlc, pickle, time, cv2
import pickle

import numpy as np

import config
from tempogram import TempogramImg
from Microcontroller import mc_child_process
import multiprocessing as mp
from multiprocessing import Process, Array, Value

import Microcontroller


def return_instrument_data(directory_count) -> (list, int, 0):
    data_dir = f'{dir.audio_data_directory}/data_{directory_count}.pkl'
    with open(data_dir, 'rb') as data_file:
        data = pickle.load(data_file)
    return data, directory_count + 1, 0


def apply_synchronization_delay(desired_end_time, end_time, fps_time_deficit) -> float:
    if end_time > desired_end_time:
        fps_time_deficit += end_time - desired_end_time
    else:
        if fps_time_deficit > 0:

            if fps_time_deficit >= desired_end_time - end_time:
                fps_time_deficit -= desired_end_time - end_time
            else:
                while time.perf_counter() <= desired_end_time - fps_time_deficit:
                    pass
                fps_time_deficit = 0
                print(f'time deficit is {fps_time_deficit}')
        else:
            while time.perf_counter() - desired_end_time <= 0:
                pass
        # print(f'fps is {1 / (time.perf_counter() - start_time)}')
    return fps_time_deficit

def start_and_return_led_child(led_data_mp, led_child_ready_mp, main_process_running_mp):
    child = mp.Process(target=mc_child_process, args=(led_data_mp, led_child_ready_mp, main_process_running_mp))
    child.start()
    while led_child_ready_mp.value == 0:
        pass
    return child

def end_program(main_process_running_mp, child_process):
    cv2.destroyAllWindows()
    main_process_running_mp.value = 0
    child_process.join()


def main():
    tempogram = TempogramImg()
    led_child_ready_mp, main_process_running_mp = mp.Value('B', 0), mp.Value('B', 1)
    child_process = start_and_return_led_child(tempogram.led_shared_memory, led_child_ready_mp, main_process_running_mp)

    media_player = vlc.MediaPlayer()
    song_dirs = tuple([f'{dir.audio_files}/{audio_file_path}' for audio_file_path in os.listdir(dir.audio_files) if audio_file_path != '.gitkeep'])
    song_i, song_count, directory_count, time_per_frame = 0, 0, 1, 1 / tempogram.fps
    song_frame, song_final_frame, fps_time_deficit = 0, 0, 0.0
    instrument_data_list = []
    cv2.namedWindow('frame', cv2.WINDOW_AUTOSIZE)

    while song_count != len(song_dirs):
        if song_count % (config.save_file_array_count - 1) == 0:
            instrument_data_list, directory_count, song_count = return_instrument_data(directory_count)

        instrument_data, tempogram_final_frame = instrument_data_list[song_count], instrument_data_list[song_count][-1, 0]
        media_player.set_media(vlc.Media(song_dirs[song_i]))

        while song_frame < tempogram_final_frame + tempogram.tempogram_halfway_idx:
            start_time = time.perf_counter()
            desired_end_time = start_time + time_per_frame
            tempogram.draw_tempogram(instrument_data, song_frame)

            if song_frame == tempogram.tempogram_frame_play_music:
                media_player.play()
                print(f'time elapsed is {time.perf_counter() - st}')

            song_frame += 1
            cv2.imshow('frame', tempogram.frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break
            fps_time_deficit = apply_synchronization_delay(desired_end_time, time.perf_counter(), fps_time_deficit)

        song_i, song_count, song_frame = song_i + 1, song_count + 1, 0
        tempogram.tempogram_current_hit_idx, tempogram.tempogram_future_hit_idx = 0, 0

    end_program(main_process_running_mp, child_process)


if __name__ == '__main__':
    main()
