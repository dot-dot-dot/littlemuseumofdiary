import sys
import time
import spidev
import argparse
import socket
from sh import aplay

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("name", help="name of the diary")
parser.add_argument("address", help="ip address of server")
parser.add_argument("port", help="port of server", type=int)
args = parser.parse_args()

AUDIO_NAME = args.name + ".wav"

ADDR = args.address
PORT = args.port

# rear sensor
R_SENSOR_ID = 1
# value when near
R_SENSOR_MIN = 7
# value when far
R_SENSOR_MAX = 28

AUDIO_STARTED = False

NUM_CAMP = 5

# read SPI data from MCP3008 chip, 8 possible adc's (0 thru 7)
def readadc(adcnum):
  if ((adcnum > 7) or (adcnum < 0)):
    return -1
  r = spi.xfer2([1,(8+adcnum)<<4,0])
  adcout = ((r[1]&3) << 8) + r[2]
  val = (int)(4800/(adcout - 20))
  return val

def sendUDP(value):
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  #print('sendUDP ', value)
  sock.sendto(value, (ADDR, PORT))

# open communication with distance sensor
spi = spidev.SpiDev()
spi.open(0,0)

# open communication with distance sensor
spi = spidev.SpiDev()
spi.open(0,0)

i = 0
r_acc = 0

while True:  
  try:

    r_sensor_value = readadc(R_SENSOR_ID)

    if i == NUM_CAMP:

      r_sensor_value = r_acc / NUM_CAMP

      i = 0
      r_acc = 0

      if r_sensor_value >= R_SENSOR_MAX:
        if AUDIO_STARTED == False:
          print("Starting audio...")
          print("read ", r_sensor_value)
          sendUDP('1') # open
          AUDIO_STARTED = True
          run_audio = aplay(AUDIO_NAME, _bg=True)
          R_SENSOR_MAX = R_SENSOR_MAX - 4

      elif r_sensor_value <= R_SENSOR_MIN:
        sendUDP('0') # closed

      else:
        sendUDP('2') # motion
   
        if AUDIO_STARTED == True:
          AUDIO_STARTED = False
          R_SENSOR_MAX = R_SENSOR_MAX + 4 
          print("Stopping audio...")
          print("read ", r_sensor_value)	
          run_audio.kill()

    else:
      i += 1
      r_acc += r_sensor_value


    time.sleep(.1)

  except KeyboardInterrupt:

    if AUDIO_STARTED == True:
      run_audio.kill()
    sys.exit()
