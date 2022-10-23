#include <FastLED.h>
// Data pin the strip is connected to
#define DATA_PIN_1 2

// Number of LEDS, minimum value of 4
#define NUM_LEDS_1 10

// FASTLED strip type, supported types: NEOPIXEL, SM16703, TM1829, TM1812, TM1809, TM1804, TM1803, UCS1903, UCS1903B, UCS1904, 
// UCS2903, WS2812, WS2852, WS2812B, GS1903, SK6812, SK6822, APA106, PL9823, SK6822
#define LED_STRIP_TYPE_1 WS2812B

// Color order depending on your specific strip. Check your datasheet or just try random combinations until you find the right one :). 
#define LED_COLOR_ORDER_1 GRB


// Adjust below if more than one data line is being used
#define DATA_PIN_2 0
#define NUM_LEDS_2 0
#define LED_STRIP_TYPE_2 null
#define LED_COLOR_ORDER_2 GRB

#define DATA_PIN_3 0
#define NUM_LEDS_3 0
#define LED_STRIP_TYPE_3 null
#define LED_COLOR_ORDER_3 GRB

#define DATA_PIN_4 0
#define NUM_LEDS_4 0
#define LED_STRIP_TYPE_4 null
#define LED_COLOR_ORDER_4 GRB

CRGB leds_1[NUM_LEDS_1],  leds_2[NUM_LEDS_2], leds_3[NUM_LEDS_3], leds_4[NUM_LEDS_4];
uint8_t mc_id = 0, data_line_count = 0;

struct color {
  int r;
  int g;
  int b;
};

typedef union {
  uint8_t value;
  byte binary;
} binaryint_8;

typedef union {
  uint8_t value[4];
  byte binary[4];
} binaryintarr_8;

typedef union {
  uint16_t value[4];
  byte binary[8];
} binaryintarr_16;

uint16_t led_start_stop_idxs[4][8] = {};
int data_pins_and_lengths[4][2] = { { DATA_PIN_1, NUM_LEDS_1 }, { DATA_PIN_2, NUM_LEDS_2 }, { DATA_PIN_3, NUM_LEDS_3 }, { DATA_PIN_4, NUM_LEDS_4 }}, instrument_colors_bgr[4][3];
uint8_t instrument_counts[4], data_line_instruments[4][4] = {{4, 4, 4, 4}, {4, 4, 4, 4}, {4, 4, 4, 4}, {4, 4, 4, 4}}, leds_on[4] = {0, 0, 0, 0}, led_fill_type[4];
char end_transmission_character = 7, led_trigger_char = 8;

void set_instrument_idxs() {
  for (int data_line_i = 0; data_line_i < data_line_count; data_line_i++) {
    uint16_t led_per_instrument = data_pins_and_lengths[data_line_i][1] / instrument_counts[data_line_i];
    uint16_t led_remaining = data_pins_and_lengths[data_line_i][1] % instrument_counts[data_line_i];
    int instrument_count = instrument_counts[data_line_i];
    uint16_t start_i = 0, end_i = 0;

    for (int instrument_idx = 0; instrument_idx < instrument_count; instrument_idx++) {
      end_i = start_i + led_per_instrument;
      if (led_remaining != 0) {
        end_i++;
        led_remaining--;
      }
      led_start_stop_idxs[data_line_i][instrument_idx * 2] = start_i;
      led_start_stop_idxs[data_line_i][instrument_idx * 2 + 1] = end_i;
      start_i = end_i;
    }
  }
}

int setup_instruction_handler() {
  int setup_complete = 0;

  byte instruction_byte = Serial.read();
  switch (instruction_byte) {
    case 0:
      write_id();
      break;
    case 1:
      write_led_count();
      break;
    case 2:
      set_data_arrays(data_line_instruments[data_line_count]);
      data_line_count += 1;
      break;
    case 3:
      set_data_arrays(led_fill_type);
      break;
    case 4:
      set_data_arrays(instrument_counts);
      break;
    case 5:
      set_led_colors();
      break;
    case 6:
      setup_complete = 1;
      break;
  }
  return setup_complete;
}

void write_id() {
  binaryint_8 id;
  id.value = mc_id;
  Serial.write(id.binary);
}


void write_led_count() {
  binaryintarr_16 led_counts;
  for (int i = 0; i < 4; i++) {
    led_counts.value[i] = data_pins_and_lengths[i][1];
  }
  Serial.write(led_counts.binary, 8);
}


void set_data_arrays(uint8_t data_array[]) {
  binaryintarr_8 incoming_bytes;
  int length = Serial.readBytesUntil(end_transmission_character, incoming_bytes.binary, 4);
  // Serial.println(length);
  for (int i = 0; i < length; i++) {
    data_array[i] = incoming_bytes.value[i];
  }
}


void set_led_arrays() {
  FastLED.addLeds<LED_STRIP_TYPE_1, DATA_PIN_1, LED_COLOR_ORDER_1>(leds_1, NUM_LEDS_1);
  if (DATA_PIN_2 != 0) { FastLED.addLeds<WS2812B, DATA_PIN_2, LED_COLOR_ORDER_2>(leds_2, NUM_LEDS_2); }
  if (DATA_PIN_3 != 0) { FastLED.addLeds<WS2812B, DATA_PIN_3, LED_COLOR_ORDER_3>(leds_3, NUM_LEDS_3); }
  if (DATA_PIN_4 != 0) { FastLED.addLeds<WS2812B, DATA_PIN_4, LED_COLOR_ORDER_4>(leds_4, NUM_LEDS_4); }
}

void set_led_colors() {
  byte incoming_bytes[12] = {};
  int length = Serial.readBytesUntil(end_transmission_character, incoming_bytes, 12);
  int count = length / 3;
  for (int instrument_i_relative = 0; instrument_i_relative < count; instrument_i_relative++) {
    for (int color_i = 0; color_i < 3; color_i++) {
      int byte_i = (instrument_i_relative * 3) + color_i;
      binaryint_8 color;
      color.binary = incoming_bytes[byte_i];
      instrument_colors_bgr[instrument_i_relative][color_i] = color.value;
    }
  }
}

void fill_leds(CRGB leds[], int fill_color[], int data_line_column_i, int data_line_row_i) {

  int fill_type = led_fill_type[data_line_row_i];
  switch (fill_type) {
    case 0:
      {
        int start_i = int(led_start_stop_idxs[data_line_row_i][data_line_column_i * 2]), end_i = int(led_start_stop_idxs[data_line_row_i][data_line_column_i * 2 + 1]);
        for (int led_i = start_i; led_i < end_i; led_i++) {
          leds[led_i].b = fill_color[0];
          leds[led_i].g = fill_color[1];
          leds[led_i].r = fill_color[2];
        }
        break;
      }

    case 1:
      int increment = instrument_counts[data_line_row_i];
      int led_count = data_pins_and_lengths[data_line_row_i][1];
      for (int led_i = data_line_column_i; led_i < led_count; led_i = led_i + increment) {
        leds[led_i].b = fill_color[0];
        leds[led_i].g = fill_color[1];
        leds[led_i].r = fill_color[2];
      }
      break;
  }
}


void trigger_leds(uint8_t instrument_idxs[], int instrument_count) {
  int fill_color[instrument_count][3] = {};
  for (int row_i = 0; row_i < instrument_count; row_i++) {
    int instrument_idx = instrument_idxs[row_i];
    switch (leds_on[instrument_idx]) {
      case 0:
        for (int column_i = 0; column_i < 3; column_i++) {
          fill_color[row_i][column_i] = instrument_colors_bgr[instrument_idx][column_i];
        }
        leds_on[instrument_idx] = 1;
        break;
      case 1:
        for (int column_i = 0; column_i < 3; column_i++) {
          fill_color[row_i][column_i] = 0;
        }
        leds_on[instrument_idx] = 0;
        break;
    }
  }

  for (uint8_t data_line_row_i = 0; data_line_row_i < data_line_count; data_line_row_i++) {
    for (uint8_t data_line_column_i = 0; data_line_column_i < 4; data_line_column_i++) {

      if (data_line_instruments[data_line_row_i][data_line_column_i] == 4){break;} 

      for (uint8_t trigger_idx = 0; trigger_idx < instrument_count; trigger_idx++) {
        uint8_t instrument_trigger_value = instrument_idxs[trigger_idx];
        if (instrument_trigger_value == data_line_instruments[data_line_row_i][data_line_column_i]) {
          switch (data_line_row_i) {
  
            case 0:
              fill_leds(leds_1, fill_color[trigger_idx], data_line_column_i,  data_line_row_i);
              break;
            case 1:
              fill_leds(leds_2, fill_color[trigger_idx], data_line_column_i, data_line_row_i);
              break;
            case 2:
              fill_leds(leds_3, fill_color[trigger_idx], data_line_column_i, data_line_row_i);
              break;
            case 3:
              fill_leds(leds_4, fill_color[trigger_idx], data_line_column_i, data_line_row_i);
              break;
          }
        }
      }
    }
  }
}


void setup() {
  Serial.begin(115200);
  while (!Serial)
    ;

  int setup_finished = 0;
  while (setup_finished == 0) {
    if (Serial.available() > 0) {
      setup_finished = setup_instruction_handler();
    }
  }
  set_instrument_idxs();
  set_led_arrays();

  for (int i = 0; i < NUM_LEDS_1; i++) {
    leds_1[i].b = 128;
    leds_1[i].g = 128;
    leds_1[i].r = 128;
  }
  FastLED.show();
  delay(.5);
  FastLED.clear();
  }



void loop() {
  while (1) {
    if (Serial.available() > 0) {
      byte instruction_byte = Serial.read();
      if (instruction_byte == led_trigger_char) {
        binaryintarr_8 instrument_triggers;
        int instrument_length = Serial.readBytesUntil(end_transmission_character, instrument_triggers.binary, 4);
        trigger_leds(instrument_triggers.binary, instrument_length);
        FastLED.show();
      }
    }
  }
}