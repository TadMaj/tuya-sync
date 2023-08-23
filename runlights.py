import numpy
import cv2
import mss
import time
import json
import tinytuya
import _thread
import math
import signal
import sys

from frame_color_lib import FrameColorLib
FRAME_COLOR_LIB = FrameColorLib()

refresh_rate = 4 ## higher is slower

input_image_reduced_size = 50
channels_min_threshold = 50
channels_max_threshold = 180
dim_brightness = 3
starting_brightness = 110
min_non_zero_count = 0.2
max_non_zero_count = 20
number_of_k_means_clusters = 8
color_spread_threshold = 0.4
color_skip_sensitivity = 30
result_color = None
light_update_wait = .250 * refresh_rate
screen_update_wait = .200 * refresh_rate
skip_frame = False
percentage_from_top = 20
stop = False

def signal_handler(signal, frame):
    global stop
    stop = True

signal.signal(signal.SIGINT, signal_handler)

def bulb_update(name, id, ip, localkey):
        global skip_frame
        b = tinytuya.BulbDevice(
                dev_id=id,
                address=ip,      
                local_key=localkey, 
                version=3.3)
        
        b.turn_on()

        while(True):
                if (stop):
                        b.turn_off()
                        break
                try:
                        if not skip_frame:
                                b.set_colour(result_color.color[2],result_color.color[1],result_color.color[0])
                except:
                        print(name, " failed to update.")
                time.sleep(light_update_wait)
                
def screen_color():
        global result_color
        global skip_frame
        prev_color = None
        
        with mss.mss() as sct:
                
                while(True):
                        if (stop):
                                break   
                        last_time = time.time()

                        monitor = sct.monitors[1]
                        left = monitor["left"]
                        top = monitor["top"] + monitor["height"] * percentage_from_top // 100  # 5% from the top
                        right = monitor["width"]  # 400px width
                        lower = monitor["height"] * (100 - percentage_from_top) // 100  # 400px height
                        box = (left, top, right, lower)
                                
                                    
                        # Get raw pixels from the screen, save it to a Numpy array
                        img = numpy.array(sct.grab(box))
                        
                        # Shrink image for performance sake
                        current_frame = FRAME_COLOR_LIB.shrink_image(img, input_image_reduced_size)
                        
                        # Apply dark color threshold and compute mask
                        masked_frame = FRAME_COLOR_LIB.apply_frame_mask(current_frame, channels_min_threshold)
                        
                        # Calculate relevant color for this frame
                        result_color = FRAME_COLOR_LIB.calculate_hue_color(masked_frame, (number_of_k_means_clusters), color_spread_threshold, channels_min_threshold, channels_max_threshold)
                        

                        if prev_color is not None:
                                skip_frame = True
                                for j in range (0,3):
                                        ch_diff = math.fabs(int(prev_color.color[j]) - int(result_color.color[j]))
                                if ch_diff > color_skip_sensitivity:
                                        print("rgb: ",result_color.color[0]," ",result_color.color[1]," ",result_color.color[2])
                                        skip_frame = False
                        prev_color = result_color
                        
                        
                        time.sleep(screen_update_wait)

_thread.start_new_thread(screen_color,())

f = open("devices.json", "r")
config = json.loads(f.read())
_thread.start_new_thread(bulb_update,("Main",config[0]['id'],"Auto",config[0]['key']))

while not stop:
        pass
#sleep to allow time for light to turn off
time.sleep(light_update_wait)