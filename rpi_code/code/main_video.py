import sys
import time
import re
import argparse
import socket
import pygame
from sh import omxplayer, aplay
import RPi.GPIO as GPIO

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("name", help="name of the diary")
parser.add_argument("address", help="ip address of server")
parser.add_argument("port", help="port of server", type=int)
args = parser.parse_args()

VIDEO_NAME = args.name + ".mp4"
AUDIO_NAME = args.name + ".wav"
IMAGE_NAME = args.name + ".jpg"

IMAGE_WIDTH = 1600
IMAGE_HEIGHT = 900

VIDEO_CURR_REXP = re.compile(r'V :\s*([\d.]+).*')
VIDEO_TOTAL_REXP = re.compile(r'Length : *([\d.]+)*')

ADDR = args.address
PORT = args.port

GPIO_SENSORS = [4, 25, 24]

GPIO_PIN = 23

VIDEO_STARTED = False
VIDEO_PAUSED = False

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

# send data to server over UDP protocol
def sendUDP(value):
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  #print('sendUDP ', value)
  sock.sendto(value, (ADDR, PORT))

def setup_buttons():
  GPIO.setmode(GPIO.BCM)
  [GPIO.setup(x, GPIO.IN) for x in GPIO_SENSORS]
  GPIO.setup(GPIO_PIN,GPIO.IN)

def read_buttons(): # get index of button pressed
  button = [x for x in GPIO_SENSORS if not(GPIO.input(x))]
  return 0 if not button else GPIO_SENSORS.index(button[0])+1

# interact with omxplayer STDIN and STDOUT 
def interact(line, stdin, process):
  global tot_sec
  global VIDEO_PAUSED
  global omx_stdin
  global omx_process

  omx_stdin = stdin
  omx_process = process

  # get current video time
  curr = VIDEO_CURR_REXP.search(line)

  if curr and tot_sec:
    pts = curr.group(1)
    sec = int(pts.split(".")[0]) / 1000000

    # stop video to last seconds
    if tot_sec == sec and VIDEO_PAUSED == False:
      VIDEO_PAUSED = True
      stdin.put('p')
      print("---- PAUSE ----")

  else:
    len = VIDEO_TOTAL_REXP.search(line)

    if len:
      tot_pts = len.group(1)
      tot_sec = (int(tot_pts) / 1000) - 13
      # set tot_len to 2 sec before end because of omxplayer buffer

print_intro(args.name)

setup_buttons()

pygame.init()
pygame.mouse.set_visible(False)

# init rendering screen
displaymode = (IMAGE_WIDTH , IMAGE_HEIGHT)
screen = pygame.display.set_mode(displaymode)

# load cover image
cover = pygame.image.load(IMAGE_NAME).convert()

# set cover position
position = pygame.Rect((0, 0, IMAGE_WIDTH, IMAGE_HEIGHT))
screen.blit(cover, position)

pygame.display.update()

while True:  
  try:

    if VIDEO_STARTED == False:
      if (not(GPIO.input(GPIO_PIN))):
        print("Starting video...")
        sendUDP('1') # open
        VIDEO_STARTED = True
        VIDEO_PAUSED = False
        time.sleep(.5)
        run = omxplayer('-s', VIDEO_NAME, _bg=True, _out=interact, _out_bufsize=250)
        time.sleep(1)
        run_audio = aplay(AUDIO_NAME, _bg=True)
        screen.fill((0,0,0))
        pygame.display.update()

    else:

      # check if chapter button is pressed
      if omx_stdin:
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

      # check if is closed
      if GPIO.input(GPIO_PIN):
        sendUDP('0') # closed
        VIDEO_STARTED = False
        print("Stopping video...")
        omx_stdin = None
        omx_process.kill()
        omx_process.wait()

        run_audio.kill()

        screen.blit(cover, position)        
        pygame.display.update()

    pygame.time.delay(100)

  except KeyboardInterrupt:

    if VIDEO_STARTED == True:
      omx_process.kill()
      omx_process.wait()
      run_audio.kill()

    pygame.quit()
    GPIO.cleanup()
    #time.sleep(1)
    sys.exit()
