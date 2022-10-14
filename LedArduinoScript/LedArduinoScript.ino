#include <FastLED.h>
#define DATA_PIN_1 2
#define NUM_LEDS_1 10
CRGB leds_1[NUM_LEDS_1];

// Adjust below if more than one data pin is being used 
#define DATA_PIN_2 0
#define NUM_LEDS_2 0
CRGB leds_2[NUM_LEDS_2];
#define DATA_PIN_3 0
#define NUM_LEDS_3 0
CRGB leds_3[NUM_LEDS_3];
#define DATA_PIN_4 0
#define NUM_LEDS_4 0
CRGB leds_4[NUM_LEDS_4];


struct color {
  int r;
  int g;
  int b;
};

uint8_t mc_id = 0;

typedef union{
  uint8_t value;
  byte binary;
  } binaryint_8;

typedef union{
  uint8_t value[4];
  byte binary[4];
  } binaryintarr_8;


typedef union{
  uint16_t value;
  byte binary[2];
  } binaryint_16;

typedef union {
  uint16_t value[4];
  byte binary[8];
  } binaryintarr_16;

uint16_t led_start_stop_idxs[4][2] = {};
int data_pins_and_lengths[4][2] = {{DATA_PIN_1, NUM_LEDS_1}, {DATA_PIN_2, NUM_LEDS_2}, {DATA_PIN_3, NUM_LEDS_3}, {DATA_PIN_4, NUM_LEDS_4}};
uint8_t instrument_counts[4] = {}, instrument_relative_i_data_line_i[4][2] = {}, leds_on[4] = {}, led_fill_type[4] = {};
int instrument_colors_bgr[4][3] = {};
char end_transmission_character = 7;


void set_instrument_idxs(){
  for (int data_line_i = 0; data_line_i < 4; data_line_i++){
    if (instrument_counts[data_line_i] != 0){
      uint16_t led_per_instrument = data_pins_and_lengths[data_line_i][1] / instrument_counts[data_line_i];
      uint16_t led_remaining = data_pins_and_lengths[data_line_i][1] % instrument_counts[data_line_i];
      int instrument_count = instrument_counts[data_line_i];
      uint16_t start_i = 0, end_i = 0;
      int instrument_idx = -1;
      uint8_t instrument_i_relative = 0;

      for (int i = 0; i < instrument_count; i++){
        instrument_idx = instrument_idx + 1;
        instrument_relative_i_data_line_i[instrument_idx][0] = instrument_i_relative;
        instrument_relative_i_data_line_i[instrument_idx][1] = data_line_i;
        end_i = start_i + led_per_instrument;
        if (led_remaining != 0){
          end_i++;
          led_remaining--;
        }
        led_start_stop_idxs[instrument_idx][0] = start_i;
        led_start_stop_idxs[instrument_idx][1] = end_i;
        start_i = led_start_stop_idxs[instrument_idx][1];
        instrument_i_relative = instrument_i_relative + 1;
      }


    } else {
      return;
    }

  }


}

int setup_instruction_handler(){
  int setup_complete = 0;
  byte instruction_byte = Serial.read();

  switch (instruction_byte)
  {
    case 0:
      write_id();
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

void write_id(){
  binaryint_8 id;
  id.value = mc_id;
  Serial.write(id.binary);
}

void set_data_arrays(uint8_t data_array[]){
  binaryintarr_8 incoming_bytes;
  int length = Serial.readBytesUntil(end_transmission_character, incoming_bytes.binary, 4);
  // Serial.println(length);
  for (int i = 0; i < length; i++){
      data_array[i] = incoming_bytes.value[i];
  }
}





void set_led_arrays(){
FastLED.addLeds<WS2812B, DATA_PIN_1>(leds_1, NUM_LEDS_1);
if (DATA_PIN_2 != 0){FastLED.addLeds<WS2812B, DATA_PIN_2>(leds_2, NUM_LEDS_2);}
if (DATA_PIN_3 != 0){FastLED.addLeds<WS2812B, DATA_PIN_3>(leds_3, NUM_LEDS_3);}
if (DATA_PIN_4 != 0){FastLED.addLeds<WS2812B, DATA_PIN_4>(leds_4, NUM_LEDS_4);} 
}

void set_led_colors(){
  byte incoming_bytes[12] = {};
  binaryint_8 color;
  int length =  Serial.readBytesUntil(end_transmission_character, incoming_bytes, 13);
  int count = length / 3;
  for (int instrument_i_relative = 0; instrument_i_relative < count; instrument_i_relative++){
    for (int color_i = 0; color_i < 3; color_i++){
      int byte_i = (instrument_i_relative * 3) + color_i;
      color.binary = incoming_bytes[byte_i];
      instrument_colors_bgr[instrument_i_relative][color_i] = color.value;
    }
  }
}

void fill_leds(CRGB leds[], int instrument_idx, int led_count, int data_line_idx){
  int fill_color[3] = {0, 0, 0};
  if (leds_on[instrument_idx] == 0){
    for(int i = 0; i <=2; i++){
      fill_color[i] = instrument_colors_bgr[instrument_idx][i];
     }
    leds_on[instrument_idx] = 1;
  }else{leds_on[instrument_idx] = 0;}

  uint8_t instrument_idx_relative = instrument_relative_i_data_line_i[instrument_idx][0];


  //Fills segmented
  if (led_fill_type[data_line_idx] == 0){
    int start_i = int(led_start_stop_idxs[instrument_idx_relative][0]), end_i = int(led_start_stop_idxs[instrument_idx_relative][1]);
    for (int led_i = start_i; led_i < end_i; led_i++){
      leds[led_i].b = fill_color[0];
      leds[led_i].g = fill_color[1];
      leds[led_i].r = fill_color[2];
    }

  }
  // Fills dispersed`
  else{
    int increment = int(instrument_counts[data_line_idx]);
    int start_i = instrument_idx_relative;
    for (int led_i = start_i; led_i < led_count; led_i = led_i + increment){
      leds[led_i].b = fill_color[0];
      leds[led_i].g = fill_color[1];
      leds[led_i].r = fill_color[2];
    }
  }
}

void setup() {
  Serial.begin(115200);
  while(!Serial);

  int setup_finished = 0;
  while (setup_finished == 0){
    if (Serial.available() > 0){
      setup_finished = setup_instruction_handler();
    }
  }
  set_instrument_idxs();
  set_led_arrays();

  for (int i = 0; i < NUM_LEDS_1; i++){
    leds_1[i].b = 255;
    leds_1[i].g = 255;
    leds_1[i].r = 255;
  }
  FastLED.show();
  delay(1);
  FastLED.clear();
  
}


void loop() {
  while (1)
  {
  if (Serial.available() > 0){
    byte instruction_byte = Serial.read();
    if (instruction_byte == 1){
        while (1){
          instruction_byte = Serial.read();
          if (instruction_byte == end_transmission_character){break;}
          Serial.println(instruction_byte);
          uint8_t data_line_idx = instrument_relative_i_data_line_i[instruction_byte][1];
          switch(data_line_idx){
            case 0:
            fill_leds(leds_1, instruction_byte, NUM_LEDS_1, data_line_idx);
            break;
            case 1:
            fill_leds(leds_2, instruction_byte, NUM_LEDS_2, data_line_idx);
            break;
            case 2:
            fill_leds(leds_3, instruction_byte, NUM_LEDS_3, data_line_idx);
            break;
            case 3:
            fill_leds(leds_4, instruction_byte, NUM_LEDS_4, data_line_idx);
            break;
          }
          }
          FastLED.show();
        }
      }
    }
} 
