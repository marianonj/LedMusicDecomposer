# LedMusicDecomposer
A python and c++ program that uses FASTLED, Spleeter, and Librosa to decompose songs and send instrument timings to LED strips
<video src="https://user-images.githubusercontent.com/83613942/197366009-708d8ef7-c574-4348-a960-b75f6436b11c.mp4"></video>

How to run:
  1. Clone repository and install requirements using cmd pip install -r requirements.txt
  2. Place audio files into the Audio directory and run AudioDecomposer.py. This part of the process will take a little while. 
  3. Go to config.py and edit the setting dictionaries to match your individual config parameters (instructions in config.py).
  4. Go to the Arduino script and change the following:
     A. Set the mc_id (line 23) to its corresponding id in config.py. 
     B. Set DATA_PIN_1, NUM_LEDS_1, LED_STRIP_TYPE_1, and LED_COLOR_ORDER_2 to your respective mc/strip values. Led_count must be > 4. 
     C. If you have additional data lines (max 4), repeat step B as needed.
  5. Run AudioPlayer.py. Press q to exit the program at any time.
  
