import subprocess, os, librosa, Dir, shlex, pickle, stat, shutil
from multiprocessing import Process
from multiprocessing import sharedctypes
import numpy as np
from Config import save_file_array_count
from Tempogram import TempogramImg


def instrument_decomposition_subprocess(audio_path, mp_array, second_per_frame, fps_offset):
    y, sr = librosa.load(audio_path)
    o_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset = librosa.onset.onset_detect(onset_envelope=o_env, backtrack=False)
    onset_secs = librosa.frames_to_time(onset)
    onset_frames = (onset_secs / second_per_frame).astype(np.uint16)
    non_overlapping_hits = np.argwhere(np.diff(onset_frames) > 3).flatten()

    all_hits = np.hstack((onset_frames[non_overlapping_hits], onset_frames[non_overlapping_hits] + 3)) + fps_offset
    all_hits_length = all_hits.shape[0]
    mp_array._obj[0:all_hits_length] = all_hits[0:]
    mp_array._obj[-1] = all_hits_length

def save_instrument_song_data(audio_folder_paths, tempogram_fps, fps_offset):
    instrument_path_ends = ('bass.wav', 'drums.wav', 'vocals.wav', 'other.wav')
    tempogram_final_data, tempogram_data_count, tempogram_str_count = [], 1, 1
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
            processes.append(Process(target=instrument_decomposition_subprocess, args=(instrument_path, shared_instrument_data_mp[audio_i], second_per_frame, fps_offset)))
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

        if tempogram_data_count == save_file_array_count or tempogram_data_count == song_lengths:
            data_dir = f'{Dir.audio_data_directory}/data_{tempogram_str_count}.pkl'
            with open(data_dir, 'wb') as save_file:
                pickle.dump(tempogram_final_data, save_file, pickle.HIGHEST_PROTOCOL)

            tempogram_final_data.clear()
            tempogram_data_count = 1
            tempogram_str_count += 1
        else:
            tempogram_data_count += 1

def spleeter_decompose(audio_file_paths):
    print('Starting spleeter decomposition')
    spleeter_subcommand = shlex.split(f'spleeter separate -p spleeter:4stems -o {Dir.temp_audio_directory}')
    for audio_path in audio_file_paths:
        spleeter_subcommand.append(audio_path)

    spleeter_subprocess = subprocess.Popen(spleeter_subcommand, stdout=subprocess.PIPE, universal_newlines=True)
    while not spleeter_subprocess.poll():
        if spleeter_subprocess.poll() == 0:
            break
    print('Spleeter decomposition finished')

def remove_temp_files(temp_audio_paths):
    def remove_permission_error(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        os.remove(path)

    for temp_audio_path in temp_audio_paths:
        shutil.rmtree(temp_audio_path, onerror=remove_permission_error)


def main():
    tempogram = TempogramImg()
    audio_file_names = os.listdir(Dir.audio_files)
    audio_file_paths = [f'{Dir.audio_files}/{audio_path}' for audio_path in os.listdir(Dir.audio_files) if audio_path != '.gitkeep']
    temp_audio_paths = [f'{Dir.temp_audio_directory}/{audio_file_name[0:-4]}' for audio_file_name in audio_file_names if audio_file_name != '.gitkeep']

    spleeter_decompose(audio_file_paths)
    save_instrument_song_data(temp_audio_paths, tempogram.fps, tempogram.tempogram_halfway_idx)
    remove_temp_files(temp_audio_paths)


if __name__ == '__main__':
    main()


