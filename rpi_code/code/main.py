import pygame
import sys
import spidev
import time
import re
import argparse
import socket
from sh import omxplayer, aplay
import RPi.GPIO as GPIO

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("name", help="name of the diary")
parser.add_argument("address", help="ip address of server")
parser.add_argument("port", help="port of server", type=int)
args = parser.parse_args()

# media files
VIDEO_NAME = args.name + ".mp4"
AUDIO_NAME = args.name + ".wav"
IMAGE_NAME = args.name + ".jpg"

# server address
ADDR = args.address
PORT = args.port

# screen
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 768

# buttons input
GPIO_SENSORS = [4, 25, 24]

# rear sensor
R_SENSOR_ID = 1
# value when near
#R_SENSOR_MIN = 700
R_SENSOR_MIN = 24
# value when far
#R_SENSOR_MAX = 300
R_SENSOR_MAX = 36

VIDEO_STARTED = False
VIDEO_PAUSED = False

# number of samples for filtering
NUM_CAMP = 5

omx_stdin = None
omx_process = None
tot_sec = None

# print splash screen
def print_intro(name):
  print("""        __...--~~~~~-._   _.-~~~~~--...__
      //               `V'               \\\ 
     //                 |                 \\\ 
    //__...--~~~~~~-._  |  _.-~~~~~~--...__\\\ 
   //__.....----~~~~._\ | /_.~~~~----.....__\\\ 
  ====================\\\|//====================
                      `---`""")
  print("\t[[[[ Diario: " + name.upper() + " ]]]]\n")


def sendUDP(value):
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#  print('sendUDP ', value)
  sock.sendto(value, (ADDR, PORT))

def setup_buttons():
  GPIO.setmode(GPIO.BCM)
  [GPIO.setup(x, GPIO.IN) for x in GPIO_SENSORS]

def read_buttons(): # get index of button pressed
  button = [x for x in GPIO_SENSORS if not(GPIO.input(x))]
  return 0 if not button else GPIO_SENSORS.index(button[0])+1

# read SPI data from MCP3008 chip, 8 possible adc's (0 thru 7)
def readadc(adcnum):
  if ((adcnum > 7) or (adcnum < 0)):
    return -1
  r = spi.xfer2([1,(8+adcnum)<<4,0])
  adcout = ((r[1]&3) << 8) + r[2]
  return adcout

# interact with omxplayer STDIN and STDOUT 
def interact(line, stdin, process):
  global tot_sec
  global VIDEO_PAUSED
  global omx_stdin
  global omx_process

  omx_stdin = stdin
  omx_process = process

  # video regexp
  video_curr_rexp = re.compile(r'V :\s*([\d.]+).*')
  video_total_rexp = re.compile(r'Length : *([\d.]+)*')

  # get current video time
  curr = video_curr_rexp.search(line)

  if curr and tot_sec:
    pts = curr.group(1)
    sec = int(pts.split(".")[0]) / 1000000
    print(sec, tot_sec)
    # stop video to last seconds
    if tot_sec == sec and VIDEO_PAUSED == False:
      VIDEO_PAUSED = True
      stdin.put('p')
      print("---- PAUSE ----")

  else:
    len = video_total_rexp.search(line)

    if len:
      tot_pts = len.group(1)
      tot_sec = (int(tot_pts) / 1000) - 11
      #print(tot_sec)
      # stops 2 seconds before end

print_intro(args.name)

# open communication with distance sensor
spi = spidev.SpiDev()
spi.open(0,0)

setup_buttons()

pygame.init()
pygame.mouse.set_visible(False)

# init rendering screen
displaymode = (IMAGE_WIDTH , IMAGE_HEIGHT)
screen = pygame.display.set_mode(displaymode)

# load cover image
cover = pygame.image.load(IMAGE_NAME).convert()

# set cover position
position = pygame.Rect((0, -IMAGE_HEIGHT, IMAGE_WIDTH, IMAGE_HEIGHT))
screen.blit(cover, position)

i = 0
r_acc = 0

while True:  
  try:
    # read rear sensor value
    # r_sensor_value = readadc(R_SENSOR_ID)
    r_val = readadc(R_SENSOR_ID)
    r_sensor_value = 4800.0/(r_val - 18)


    if i == NUM_CAMP:

      if VIDEO_STARTED == True and omx_stdin:
        chapter = read_buttons()
      
        if chapter > 0:      
          if VIDEO_PAUSED == True:
            omx_stdin.put('p')
            print("--- PLAY ---")
            time.sleep(.3)

          run_audio.kill()
          omx_stdin.put("\027[B")
          print('Rewind')
          time.sleep(1)
        
          if chapter > 1:
            print('sendOMX ' + repr(chapter))
            omx_stdin.put(repr(chapter))
          else:
            run_audio = aplay(AUDIO_NAME, _bg=True)

          VIDEO_PAUSED = False


      r_sensor_value = r_acc / NUM_CAMP

      i = 0
      r_acc = 0

      #print('R: ', r_sensor_value)

      if r_sensor_value >= R_SENSOR_MAX:

        if VIDEO_STARTED == False:
          print("Starting video...")
          sendUDP('1') # open
          VIDEO_STARTED = True
          VIDEO_PAUSED = False
          run = omxplayer('-s', VIDEO_NAME, _bg=True, _out=interact, _out_bufsize=250)
          time.sleep(1)
          run_audio = aplay(AUDIO_NAME, _bg=True)
          screen.fill((0,0,0))
          pygame.display.update()
          R_SENSOR_MAX = R_SENSOR_MAX - 3 
      
      elif r_sensor_value <= R_SENSOR_MIN:
        sendUDP('0') # closed

      else:
        sendUDP('2') # motion

        if VIDEO_STARTED == True:
          VIDEO_STARTED = False
          R_SENSOR_MAX = R_SENSOR_MAX + 3
          print("Stopping video...")
          omx_stdin = None
          omx_process.kill()
          omx_process.wait()
          run_audio.kill()

        else:
          # redraw background
          screen.fill((0,0,0))
          new_value = ((R_SENSOR_MAX - r_sensor_value) * (-IMAGE_HEIGHT))/(R_SENSOR_MAX-R_SENSOR_MIN)
          cover_position = pygame.Rect(0, new_value, IMAGE_WIDTH, IMAGE_HEIGHT)
          screen.blit(cover, cover_position)
          pygame.display.update()

    else:
      i += 1
      r_acc += r_sensor_value

    pygame.time.delay(100/NUM_CAMP)

  except KeyboardInterrupt:

    if VIDEO_STARTED == True:
      omx_process.kill()
      omx_process.wait()
      run_audio.kill()
    pygame.quit()
    GPIO.cleanup()
    #time.sleep(1)
    sys.exit()
