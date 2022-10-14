import numpy as np
import cv2, os, Config
from multiprocessing.sharedctypes import Array


class TempogramImg:
    element_padding = 5
    fps = 30
    font_face = cv2.FONT_HERSHEY_COMPLEX_SMALL
    font_scale_thickness = .75, 1
    text_color = (255, 255, 255)
    size_yx = (720, 1080)
    tempogram_led_current_colors = Config.instrument_colors

    def __init__(self):
        self.frame = np.zeros((self.size_yx[0], self.size_yx[1], 3), dtype=np.uint8)

        self.tempogram_y_axis_text_padding, self.element_padding = int(.025 * self.size_yx[0]), int(.015 * self.size_yx[0])
        self.tempogram_icon_templates, self.tempogram_template_non_zero_indicies, self.tempogram_template_non_zero_points, self.tempogram_icon_bbox, self.tempogram_y_str_stop = self.return_tempogram_icons()
        self.tempogram_lines_x_start_stop, self.tempogram_lines_y_start_stop, self.x_graph_labels_start_y = self.return_tempogram_line_idxs(('-2.00', '0.00', '+2.00'))
        self.tempogram_hit_width, self.tempogram_halfway_idx, self.tempogram_adjusted_time = self.return_tempogram_hit_width(1.5)
        self.draw_graph_axes(self.tempogram_adjusted_time)
        self.font_scale_thickness = self.return_text_scale_thickness()
        self.leds_are_on, self.led_shared_memory = np.zeros((2, 4), dtype=bool), Array('B', 5)
        self.led_shared_memory_view = np.ndarray(5, buffer=self.led_shared_memory._obj, dtype=np.uint8)
        self.tempogram_first_draw_index, self.tempogram_mid_draw_index, self.tempogram_frame_play_music = 0, 0, int(self.tempogram_adjusted_time * self.fps)
        self.now_playing_bbox = (self.element_padding, self.element_padding + self.tempogram_y_axis_text_padding, self.tempogram_lines_x_start_stop[0], self.tempogram_lines_x_start_stop[1])
        self.tempogram_future_hit_idx, self.tempogram_current_hit_idx = 0, 0

    def return_tempogram_icons(self) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        img_directory = 'TempogramIcons'

        y_lin_space = np.linspace(self.tempogram_y_axis_text_padding + self.element_padding * 2, self.frame.shape[0] - self.tempogram_y_axis_text_padding - self.element_padding * 2, num=9, endpoint=True, dtype=np.uint16)
        tempogram_icons = os.listdir(img_directory)
        icon_spacing = 5
        icon_dimension = y_lin_space[2] - y_lin_space[0] - icon_spacing
        icon_index_ranges = np.zeros((4, 2), dtype=np.uint16)
        icon_templates = np.zeros([4, 2, icon_dimension, icon_dimension, 3], dtype=np.uint8)

        def unsharp_mask(image, kernel_size=(5, 5), sigma=1.0, amount=50.0, threshold=0):
            """Return a sharpened version of the image, using an unsharp mask."""
            blurred = cv2.GaussianBlur(image, kernel_size, sigma)
            sharpened = float(amount + 1) * image - float(amount) * blurred
            sharpened = np.maximum(sharpened, np.zeros(sharpened.shape))
            sharpened = np.minimum(sharpened, 255 * np.ones(sharpened.shape))
            sharpened = sharpened.round().astype(np.uint8)
            if threshold > 0:
                low_contrast_mask = np.absolute(image - blurred) < threshold
                np.copyto(sharpened, image, where=low_contrast_mask)
            return sharpened

        for idx, icon_dir in enumerate(tempogram_icons):
            icon = cv2.imread(f'{img_directory}/{icon_dir}')
            icon_reshape = cv2.resize(icon, (icon_dimension, icon_dimension), cv2.INTER_NEAREST_EXACT)
            icon_sharpened = unsharp_mask(icon_reshape)
            non_zero = np.nonzero(icon_sharpened)
            icon_activated = icon_sharpened.copy()
            icon_activated[non_zero[0], non_zero[1]] = self.tempogram_led_current_colors[idx]
            if idx == 0:
                icon_index_ranges[idx] = (0, non_zero[0].shape[0])
                icon_non_zero_points = np.column_stack((non_zero[0], non_zero[1]))
            else:
                icon_index_ranges[idx] = icon_index_ranges[idx - 1, 1], icon_index_ranges[idx - 1, 1] + non_zero[0].shape[0]
                icon_non_zero_points = np.vstack((icon_non_zero_points, np.column_stack((non_zero[0], non_zero[1]))))
            icon_templates[idx, 0] = icon_activated.copy()
            icon_templates[idx, 1] = icon_sharpened.copy()
        icon_range_indicies = np.column_stack((y_lin_space[0:-1:2], y_lin_space[0:-1:2] + icon_dimension, np.full(4, self.element_padding), np.full(4, self.element_padding + icon_dimension)))

        for indicies, template in zip(icon_range_indicies, icon_templates):
            self.frame[indicies[0]:indicies[1], indicies[2]:indicies[3]] = template[1]

        tempogram_pixel_draw_height = .75 * y_lin_space[0]
        tempogram_y_mps = np.mean(icon_range_indicies[:, 0:2], axis=1)

        tempogram_y_str_stop = np.column_stack((tempogram_y_mps - tempogram_pixel_draw_height / 2, tempogram_y_mps + tempogram_pixel_draw_height / 2)).astype(np.uint16)

        return icon_templates, icon_index_ranges, icon_non_zero_points, icon_range_indicies, tempogram_y_str_stop

    def return_tempogram_hit_width(self, desired_time) -> (np.ndarray, np.ndarray, np.ndarray):
        pixel_diff = (self.tempogram_lines_x_start_stop[1] - self.tempogram_lines_x_start_stop[0]) // 2
        pixel_per_frame = pixel_diff // (desired_time * self.fps) + 1
        adjusted_time = pixel_diff / (self.fps * pixel_per_frame)
        truncated_time = '%.2f' % (adjusted_time)
        tempogram_half_point = (self.tempogram_lines_x_start_stop[1] - self.tempogram_lines_x_start_stop[0]) // (pixel_per_frame * 2)
        return int(pixel_per_frame), int(tempogram_half_point), float(truncated_time)

    def return_tempogram_line_idxs(self, times) -> ((int, int), np.ndarray, int):
        text_widths, text_heights = [], []
        for text in times:
            text_size = cv2.getTextSize(text, self.font_face, self.font_scale_thickness[0], self.font_scale_thickness[1])
            text_widths.append(text_size[0][0])
            text_heights.append(text_size[0][1])
        max_w, max_h = max(text_widths), max(text_heights)

        top_left_y_start = ((self.tempogram_icon_bbox[-1, 1] + self.frame.shape[0]) // 2) - max_h
        tempogram_line_x_end = self.frame.shape[1] - self.element_padding - max_w // 2
        tempogram_line_x_start = self.tempogram_icon_bbox[0, 3] + self.element_padding + max_h // 2
        tempogram_line_x_mp = (tempogram_line_x_start + tempogram_line_x_end) // 2 - max_w // 2

        tempogram_line_y_start_stop = np.zeros((4, 2), dtype=np.uint16)
        for idx, indicies in enumerate(self.tempogram_icon_bbox):
            mp_y = np.mean(indicies[0:2], dtype=int)
            tempogram_line_y_start_stop[idx] = mp_y - 2, mp_y + 2

            self.frame[tempogram_line_y_start_stop[idx, 0]:tempogram_line_y_start_stop[idx, 1], tempogram_line_x_start:tempogram_line_x_end] = (255, 255, 255)

        return (tempogram_line_x_start, tempogram_line_x_end), tempogram_line_y_start_stop, top_left_y_start

    def return_text_scale_thickness(self) -> (float, int):
        font_scale, font_thickness = self.font_scale_thickness[0], self.font_scale_thickness[1]
        text_height = cv2.getTextSize('M', self.font_face, font_scale, font_thickness)[0][1]
        if text_height < self.tempogram_y_axis_text_padding:
            while text_height <= self.tempogram_y_axis_text_padding:
                font_scale += .01
                text_height = cv2.getTextSize('M', self.font_face, font_scale, font_thickness)[0][1]
        else:
            while text_height >= self.tempogram_y_axis_text_padding:
                font_scale -= .01
                text_height = cv2.getTextSize('M', self.font_face, font_scale, font_thickness)[0][1]

        return font_scale, font_thickness

    def draw_graph_axes(self, time):
        times = (f'-{"%.2f" % time}', ('0.00'), f'+{"%.2f" % time}')
        text_bbox_y = self.tempogram_icon_bbox[-1, 1] + self.element_padding, self.tempogram_icon_bbox[-1, 1] + self.element_padding + self.tempogram_y_axis_text_padding
        for i, time in enumerate(times):
            text_size = cv2.getTextSize(time, self.font_face, self.font_scale_thickness[0], self.font_scale_thickness[1])
            if i == 0:
                text_bbox_x = np.array([self.tempogram_lines_x_start_stop[0] - text_size[0][0] // 2,
                                        self.tempogram_lines_x_start_stop[0] - text_size[0][0] // 2 + text_size[0][0]], dtype=np.uint16)
            elif i == 1:
                text_bbox_x = np.array([np.sum(self.tempogram_lines_x_start_stop) // 2 - text_size[0][0] // 2,
                                        np.sum(self.tempogram_lines_x_start_stop) // 2 - text_size[0][0] // 2 + text_size[0][0]], dtype=np.uint16)
            else:
                text_bbox_x = np.array([self.tempogram_lines_x_start_stop[1] - text_size[0][0],
                                        self.tempogram_lines_x_start_stop[1] - text_size[0][0] // 2 + text_size[0][0]], dtype=np.uint16)
            self.draw_centered_text(self.frame, time, np.hstack((text_bbox_y, text_bbox_x)), self.text_color)

    def draw_centered_text(self, img, text, bbox, text_color, fill_color=None, return_bbox=False) -> np.ndarray or None:
        img[bbox[0]:bbox[1], bbox[2]:bbox[3]] = 0, 0, 0

        text_size = cv2.getTextSize(text, self.font_face, self.font_scale_thickness[0], self.font_scale_thickness[1])
        mp_xy = (bbox[3] + bbox[2] - text_size[0][0]) // 2, ((bbox[0] + bbox[1]) + text_size[0][1] - text_size[1] // 2) // 2
        bbox = np.array([mp_xy[1] - text_size[0][1] - text_size[1] // 2, mp_xy[1] + text_size[1] // 2, mp_xy[0], mp_xy[0] + text_size[0][0]], dtype=np.uint16)
        if fill_color is not None:
            img[bbox[0]:bbox[1], bbox[2]:bbox[3]] = fill_color

        cv2.putText(img, text, mp_xy, self.font_face, self.font_scale_thickness[0], (int(text_color[0]), int(text_color[1]), int(text_color[2])), self.font_scale_thickness[1], lineType=cv2.LINE_AA)

        if return_bbox:
            return bbox

    def draw_tempogram(self, instrument_data, frame):
        if self.tempogram_current_hit_idx != instrument_data.shape[0]:
            self.draw_current_hits(instrument_data, frame)
        if self.tempogram_future_hit_idx != instrument_data.shape[0]:
            self.draw_future_hits(instrument_data, frame)
        self.animate_step()

    def draw_current_hits(self, instrument_data, frame):
        end_i = 0

        try:
            while instrument_data[self.tempogram_current_hit_idx + end_i, 0] == frame:
                end_i += 1
        except IndexError:
            pass

        if end_i != 0:
            # MC subprocess will set the last idx back to 0 to indicate that the data has been transferred to the MCS
            while self.led_shared_memory_view[-1] != 0:
                pass

            draw_idxs = instrument_data[self.tempogram_current_hit_idx:self.tempogram_current_hit_idx + end_i][:, 1]
            leds_are_on_idxs = self.leds_are_on[0][draw_idxs].astype(np.uint0)

            for draw_i, led_on_i in zip(draw_idxs, leds_are_on_idxs):
                self.frame[self.tempogram_icon_bbox[draw_i, 0]: self.tempogram_icon_bbox[draw_i, 1], self.tempogram_icon_bbox[draw_i, 2]: self.tempogram_icon_bbox[draw_i, 3]] = self.tempogram_icon_templates[draw_i, led_on_i]
            self.leds_are_on[0][draw_idxs] = np.invert(self.leds_are_on[0][draw_idxs])
            self.tempogram_current_hit_idx += end_i

            self.led_shared_memory_view[draw_idxs] = 1
            self.led_shared_memory_view[-1] = 1

    def draw_future_hits(self, instrument_data, frame):
        end_i = 0

        try:
            while instrument_data[self.tempogram_future_hit_idx + end_i, 0] == (frame + self.tempogram_halfway_idx):
                end_i += 1
        except IndexError:
            pass

        if end_i != 0:
            draw_idxs = instrument_data[self.tempogram_future_hit_idx:self.tempogram_future_hit_idx + end_i][:, 1]
            leds_are_on_idxs = self.leds_are_on[1][draw_idxs].astype(np.uint0)
            # MC subprocess will set the last idx back to 0 to indicate that the data has been transferred to the MCS
            for draw_i, future_led_on in zip(draw_idxs, leds_are_on_idxs):
                if future_led_on:
                    self.frame[self.tempogram_y_str_stop[draw_i, 0]:self.tempogram_y_str_stop[draw_i, 1],
                    self.tempogram_lines_x_start_stop[1] - self.tempogram_hit_width: self.tempogram_lines_x_start_stop[1]] = (0, 0, 0)
                    self.frame[self.tempogram_lines_y_start_stop[draw_i, 0]:self.tempogram_lines_y_start_stop[draw_i, 1],
                    self.tempogram_lines_x_start_stop[1] - self.tempogram_hit_width: self.tempogram_lines_x_start_stop[1]] = (255, 255, 255)
                else:
                    self.frame[self.tempogram_y_str_stop[draw_i, 0]:self.tempogram_y_str_stop[draw_i, 1],
                    self.tempogram_lines_x_start_stop[1] - self.tempogram_hit_width: self.tempogram_lines_x_start_stop[1]] = self.tempogram_led_current_colors[draw_i]
            self.leds_are_on[1][draw_idxs] = np.invert(self.leds_are_on[1][draw_idxs])
            self.tempogram_future_hit_idx += end_i

    def animate_step(self):
        self.frame[self.tempogram_icon_bbox[0, 0]: self.tempogram_icon_bbox[3, 1], self.tempogram_lines_x_start_stop[0]:self.tempogram_lines_x_start_stop[1] - self.tempogram_hit_width] = \
            self.frame[self.tempogram_icon_bbox[0, 0]: self.tempogram_icon_bbox[3, 1], self.tempogram_lines_x_start_stop[0] + self.tempogram_hit_width:self.tempogram_lines_x_start_stop[1]].copy()





