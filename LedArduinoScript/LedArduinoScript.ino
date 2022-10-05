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
uint8_t instrument_counts[4] = {}, instrument_data_line_idx[4][2] = {}, leds_on[4] = {}, led_fill_type[4] = {};
int instrument_colors_bgr[4][3] = {};




void set_instrument_idxs(){
  for (int data_line_i = 0; data_line_i <=3; data_line_i++){
    uint16_t led_start_i = 0;
    int led_count = data_pins_and_lengths[data_line_i][1];
    uint16_t led_per_instrument = led_count / instrument_counts[data_line_i], led_remaining = led_count % instrument_counts[data_line_i];
    int current_instrument_i = 0;
    if (instrument_counts[data_line_i]) {
      for (uint16_t i = 0; i < instrument_counts[data_line_i]; i++){
        instrument_data_line_idx[current_instrument_i][0] = instrument_counts[data_line_i] - i;
        instrument_data_line_idx[current_instrument_i][1] = data_line_i;
        if (instrument_counts[data_line_i] > 1){
          led_start_stop_idxs[current_instrument_i][0] = led_start_i;
          led_start_stop_idxs[current_instrument_i][1] = led_start_i + led_per_instrument;
          if (led_remaining != 0){
            led_start_stop_idxs[1][current_instrument_i] += 1;
            led_remaining -= 1;
          } 
          led_start_i = led_start_stop_idxs[current_instrument_i][1];
        } else {
          led_start_stop_idxs[0][current_instrument_i] = 0;
          led_start_stop_idxs[1][current_instrument_i] = led_count;
        }
       current_instrument_i += 1;}
    }else{
      break;
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

    case 1:
      break;
    case 2:

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
  binaryintarr_16 incoming_bytes;
  Serial.readBytes(incoming_bytes.binary, 4);
  for (uint16_t i = 0; i < sizeof(incoming_bytes.value); i++){
    if (incoming_bytes.value[i] != 0){
      data_array[i] = incoming_bytes.value[i];
    }else{ 
      return;} 
  }
}

void set_data_arrays(uint16_t data_array[]){
  binaryintarr_16 incoming_bytes;
  Serial.readBytes(incoming_bytes.binary, 4);
  for (uint16_t i = 0; i < sizeof(incoming_bytes.value); i++){
    if (incoming_bytes.value[i] != 0){
      data_array[i] = incoming_bytes.value[i];
    }else{ 
      return;} 
  }
}



int get_led_counts(){
  int count = 0;
  for (int i = 0; i <= 3; i++){
    if (instrument_counts[i] != 0){
      count += 1;
    };
  }
  return count;
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
}

void set_led_arrays(){
FastLED.addLeds<WS2812B, DATA_PIN_1>(leds_1, NUM_LEDS_1);
if (DATA_PIN_2 != 0){FastLED.addLeds<WS2812B, DATA_PIN_2>(leds_2, NUM_LEDS_2);}
if (DATA_PIN_3 != 0){FastLED.addLeds<WS2812B, DATA_PIN_3>(leds_3, NUM_LEDS_3);}
if (DATA_PIN_4 != 0){FastLED.addLeds<WS2812B, DATA_PIN_4>(leds_4, NUM_LEDS_4);} 
}

void set_led_colors(){
  binaryintarr_8 incoming_bytes;
  Serial.readBytes(incoming_bytes.binary, 4);
  uint8_t color_i = incoming_bytes.value[0];
  for (uint8_t i = 0; i < 3; i++){
    instrument_colors_bgr[color_i][i] = int(incoming_bytes.binary[i]);
  }
}

void fill_leds(CRGB leds[], int instrument_idx, int led_count){
  int fill_color[3] = {0, 0, 0};
  if (leds_on[instrument_idx] == 0){
    for(int i = 0; i <=2; i++){
      fill_color[i] = instrument_colors_bgr[instrument_idx][i];
      leds_on[instrument_idx] = 1;
     }
  }else{leds_on[instrument_idx] = 0;}


  //Fills segmented
  if (led_fill_type == 0){
    uint16_t start_i = led_start_stop_idxs[instrument_idx][0], end_i = led_start_stop_idxs[instrument_idx][1];
    for (uint16_t led_i = start_i; led_i <= end_i; led_i++){
      leds[led_i].b = fill_color[0];
      leds[led_i].g = fill_color[1];
      leds[led_i].g = fill_color[2];


    }

  }
  // Fills dispersed
  else{
    int increment = int(instrument_counts[instrument_idx]);
    for (int led_i = instrument_idx; led_i <= led_count; led_i = led_i + increment){
      leds[led_i].b = fill_color[0];
      leds[led_i].g = fill_color[1];
      leds[led_i].g = fill_color[2];
    }
  }
}


void loop() {
  byte incoming_bytes[5] = {};
  char end_instruction_byte = 5;
  while (1)
  {
  if (Serial.available() > 0){
    byte instruction_byte = Serial.read();
    if (instruction_byte == 1){
        int read_length = Serial.readBytesUntil(end_instruction_byte, incoming_bytes, 5);
        for (int i = 1; i < read_length; i++){
          int instrument_idx = incoming_bytes[i];
          int data_line_idx = instrument_data_line_idx[instrument_idx][1];
          switch(data_line_idx){
            case 0:
            fill_leds(leds_1, instrument_idx, NUM_LEDS_1);
            break;
            case 1:
            fill_leds(leds_2, instrument_idx, NUM_LEDS_2);
            break;
            case 2:
            fill_leds(leds_3, instrument_idx, NUM_LEDS_3);
            break;
            case 3:
            fill_leds(leds_4, instrument_idx, NUM_LEDS_4);
            break;
          }
        }
      FastLED.show();
      }
    }
  }
}     
