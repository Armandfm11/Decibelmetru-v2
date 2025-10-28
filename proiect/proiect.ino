
////////////////////////////////////////// Macro DEBUG

                                          #define DEBUG

////////////////////////////////////////// Macro DEBUG


  // Librarii

//Standard Input/Output
#include <stdio.h>

// Comunicare I2C - display
#include <Wire.h>           
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Librarii comunicatie WiFi
#include <WiFi.h>
#include <WiFiUdp.h>


// Parametrii display OLED
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET     -1 // Acelasi pin ca si pin-ul de reset Arduino
#define SCREEN_ADDRESS 0x3C
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);




  // Initializare

// Credentialele
#include "network.h"

// Stare initiala
int status        = WL_IDLE_STATUS;

// Declarare obiect udp - folosit pentru transferul prin UDP
WiFiUDP udp;

char buffer[255];



  // Variabile globale

// Tensiune de alimentare - 5v sau 3.3v 
float ref_v   = 5.0;

// Offset MAX9814
float offset  = (1.25 * 1023) / ref_v ;

// Valoare maxima inregistrata pe durata intervalului
int peak      = 0;

// Valoare temp. inregistrata
int temp      = 0;

// Timpul la care incepe perioada curenta de achizitie
int start     = 0;

// Peak senzor, in V
float volts   = 0;

// Valoare senzor in dB
float dB      = 0;

// Flag pentru efect-ul de blink al display-ului
int flag      = 0;

// Intervalul de achizitie
int interval  = 200;



void setup()
{
  // Push-Button
  pinMode(10, INPUT);

  // Pentru debug
  Serial.begin(9600);

  // Initializare display - daca esueaza, programul nu ruleaza
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS))
  {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;);
  }
  display.display();
  delay(1000);
  display.clearDisplay();

  // Initializare modul WiFi - acelasi caz ca la display
    if (WiFi.status() == WL_NO_SHIELD)
    {
    Serial.println("WiFi shield not present");
    // don't continue:
    while (true);
    }   

  // Conectare folosind credentialele - acelasi caz ca la display
  while (status != WL_CONNECTED)
  {
    Serial.print("Attempting to connect to SSID: ");
    Serial.println(ssid);
    status = WiFi.begin(ssid, pass);

    // wait 4 seconds for connection:
    delay(4000);
  }

  // Conectarea a reusit
  Serial.println("Connected to wifi");
  Serial.println("\nStarting connection to server...");
  udp.begin(port);
}


void loop()
{
  // Nou ciclu de achizitie date
  peak = 0;
  temp = 0;
  //count = 0;

  // Se inregistreaza timpul cand incepe achizitia
  start = millis();

  // Cat timp a trecut mai putin timp de la start-ul achizitiei
  // decat este definit prin "interval"
  while(millis() - start < interval)
  {
    // Temp primeste o noua valoare, corectata cu offset-ul.
    // Se face abs(valoare) pentru ca semnalul are forma de unda, cu mijlocul = offset.
    // Daca este cea mai mare valoare inregistrata, se salveaza

    temp = abs(analogRead(1) - offset);
    if(peak < temp)
    {
      peak = temp;
    }
    //count++;
  }

  // Achizitia este gata - incepem conversia
  // Conversie semnal analog > volti > decibeli
  // Rezolutie default - 10 biti => 1024 valori posibile

  volts = ( ref_v / 1023.0 ) * peak;
  dB = 20 * log(volts) + 56.0; //calibrare

  #ifdef DEBUG
  Serial.println(dB);
  #endif

  // Pregatire packet pentru transmitere
  int len = snprintf(buffer, sizeof(buffer), "%.2f", dB);

  // Trimitere packet spre IP-ul si portul specificat
  udp.beginPacket(pcIP, port);
  udp.write((uint8_t*)buffer, len);
  udp.endPacket();
  Serial.println("Sent packet.");
  Serial.println();

  // Daca push-button-ul este apasat, reseteaza graficul din aplicatie
  if(digitalRead(10) == HIGH)
  {
    udp.beginPacket(pcIP, port);
    udp.write("reset");
    udp.endPacket();
    Serial.println("Requested reset.");
  }


  //Serial.print("  -- analog > ");   //DEBUG
  //Serial.println(peak);             //DEBUG

  // Functie display
  show(dB);
}

// Functie display
void show(float val)
{
  // Reseteaza ecranul pentru a evita overlapping de caractere
  display.clearDisplay();

  // Afiseaza valoarea in dB a zgomotului
  display.setTextColor(WHITE);
  display.setCursor(8, 28);
  display.setTextSize(1);
  display.println("Sound:");
  display.setCursor(16, 40);
  display.setTextSize(2);
  display.print(val);
  display.print(" dB");

  // Pentru fiecare 10dB, o bara va aparea pe display
  for( int i = 0; i <= (int(val) / 10 - 1); i++)
  {
    display.fillRect(2 + i*17, 1, 15, 11, WHITE);
  }

  // La minim 50dB
  if(val >= 50) blink();

  // Display-ul este gata pentru actualizare cu noile date
  display.display();
}

void blink()
{
  flag++;

  if(flag / 3)
  {
    flag = 0;
    display.fillRect(0, 1, 124, 39, BLACK);
  }
  // La fiecare 3 achizitii cu valori finale peste 50
  // ecranul va clipi, semnaland o valoare de zgomot mare
}
