/*
 * UDPSendReceiveStrings
 * This sketch receives UDP message strings, prints them to the serial port
 * and sends an "acknowledge" string back to the sender
 * Use with Arduino 1.0
 *
 */

#include <SPI.h>         // needed for Arduino versions later than 0018
#include <Ethernet.h>
#include <EthernetUdp.h> // Arduino 1.0 UDP library

byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED }; // MAC address to use
byte ip[] = {192, 168, 2, 201 };    // Arduino's IP address

unsigned int localPort = 8888;      // local port to listen on

const int analogOutPins[] = { 3,5,6 };  // pins 10 and 11 used by ethernet shield

// buffers for receiving and sending data
char packetBuffer[UDP_TX_PACKET_MAX_SIZE]; //buffer to hold incoming packet,
char replyBuffer[] = "acknowledged";       // a string to send back

// A UDP instance to let us send and receive packets over UDP
EthernetUDP Udp;

void setup() {
    // start the Ethernet and UDP:
  Ethernet.begin(mac,ip);
  Udp.begin(localPort);
  pinMode(analogOutPins[0], OUTPUT);
  pinMode(analogOutPins[1], OUTPUT);
  pinMode(analogOutPins[2], OUTPUT);

  Serial.begin(9600);
}

void loop() {
  // if there's data available, read a packet
  int packetSize =  Udp.parsePacket(); 
  int i = 0;
  if(packetSize)
  {
  //  Serial.print("Received packet of size ");
  //  Serial.println(packetSize);

    // read packet into packetBuffer and get sender's IP addr and port number
    Udp.read(packetBuffer,UDP_TX_PACKET_MAX_SIZE);
   // Serial.println("Contents:");
   // Serial.println(packetBuffer);

    int pin = packetBuffer[0]-48;
    int value = packetBuffer[2]-48;
    Serial.println(pin);
    Serial.println(value);

    if (pin < 2) {
      if (value == 0) {
        analogWrite(analogOutPins[pin], 0);
      }else if (value == 2) {
        for (i = 0; i < 256; i++) {
          analogWrite(analogOutPins[pin], i);
          delay(10);
        }
      }
    }
    //  analogWrite(analogOutPins[packetBuffer], value); 
    
    // send a string back to the sender
    //Udp.beginPacket(Udp.remoteIP(), Udp.remotePort());
    //Udp.write(replyBuffer);
    //Udp.endPacket();
  }
  delay(10);
}
