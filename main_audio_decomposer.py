import subprocess, os, librosa, dir, shlex
from multiprocessing import Process
from multiprocessing import sharedctypes
import numpy as np


def instrument_decomposition_subprocess(audio_path, mp_array, second_per_frame):
    y, sr = librosa.load(audio_path)
    o_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_bt = librosa.onset.onset_detect(onset_envelope=o_env, backtrack=True)
    onset = librosa.onset.onset_detect(onset_envelope=o_env, backtrack=False)
    diffs = onset - onset_bt
    higher_than_zero = np.argwhere(diffs > 0).flatten()
    onset_bt_secs, onset_secs = librosa.frames_to_time(onset_bt[higher_than_zero]), librosa.frames_to_time(onset[higher_than_zero])
    onset_bt_frames, onset_frames = (onset_bt_secs / second_per_frame).astype(np.uint16), (onset_secs / second_per_frame).astype(np.uint16)
    valid_hits = np.argwhere((onset_frames - onset_bt_frames) > 0).flatten()
    all_hits = np.hstack((onset_bt_frames[valid_hits], onset_frames[valid_hits]))
    all_hits_length = all_hits.shape[0]
    mp_array._obj[0:all_hits_length] = all_hits[0:]
    mp_array._obj[-1] = all_hits_length


def return_instrument_song_data(audio_folder_paths, tempogram_fps):
    instrument_path_ends = ('bass.wav', 'drums.wav', 'other.wav', 'vocals.wav')
    tempogram_final_data = []
    second_per_frame = 1 / tempogram_fps
    max_instrument_data_points = 4000
    shared_instrument_data_mp = [sharedctypes.Array('H', max_instrument_data_points) for _ in range(0, 4)]
    shared_instrument_data_np_view = [np.ndarray(max_instrument_data_points, buffer=mp_array._obj, dtype=np.uint16) for mp_array in shared_instrument_data_mp]
    song_lengths = len(audio_folder_paths)

    print('Starting instrument beat analysis')
    for i, audio_folder_path in enumerate(audio_folder_paths):
        processes, tempogram_data_pre_sort = [], []
        instrument_paths = [f'{audio_folder_path}/{instrument_path}' for instrument_path in instrument_path_ends]
        for audio_i, instrument_path in enumerate(instrument_paths):
            processes.append(Process(target=instrument_decomposition_subprocess, args=(instrument_path, shared_instrument_data_mp[audio_i], second_per_frame)))
        for process in processes:
            process.start()
        for process in processes:
            process.join()

        for audio_i, np_view in enumerate(shared_instrument_data_np_view):
            max_i = np_view[-1]
            tempogram_data_pre_sort.append(np.column_stack((np_view[0:max_i], np.full(max_i, audio_i))))
        tempogram_data_pre_sort = np.vstack(tempogram_data_pre_sort)
        lex_sort = np.lexsort((tempogram_data_pre_sort[:, 1], tempogram_data_pre_sort[:, 0]))
        tempogram_final_data.append(tempogram_data_pre_sort[lex_sort])
        print(f'Finished analyzing song {i + 1} of {song_lengths}')

    return tempogram_final_data



def spleeter_decompose(audio_file_paths):
    print('Starting spleeter decomposition')
    spleeter_subcommand = shlex.split(f'spleeter separate -p spleeter:4stems -o {dir.temp_audio_directory}')
    for audio_path in audio_file_paths:
        spleeter_subcommand.append(audio_path)

    spleeter_subprocess = subprocess.Popen(spleeter_subcommand, stdout=subprocess.PIPE, universal_newlines=True)
    while not spleeter_subprocess.poll():
        if spleeter_subprocess.poll() == 0:
            break
    print('Spleeter decomposition finished')


def main():
    tempogram_fps = 24
    audio_file_paths = os.listdir(dir.audio_files)
    # spleeter_decompose([f'{dir.audio_files}/{audio_path}' for audio_path in audio_folder_paths])
    instrument_data = return_instrument_song_data([f'{dir.temp_audio_directory}/{audio_file_path[0:-4]}' for audio_file_path in audio_file_paths], tempogram_fps)

    print('b')

    pass


if __name__ == '__main__':
    main()
