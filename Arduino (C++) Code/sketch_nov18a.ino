#include <LiquidCrystal.h>

// LCD pins
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

// Pin assignments
const int greenLED = 9;
const int redLED1 = 13;
const int redLED2 = 10;
const int buzzer = 8;

const int togglePin = 6;
const int pushButtonPin = 7;

void setup() {
  Serial.begin(9600);

  // LCD
  lcd.begin(16, 2);
  lcd.clear();

  // LEDs
  pinMode(greenLED, OUTPUT);
  pinMode(redLED1, OUTPUT);
  pinMode(redLED2, OUTPUT);

  // Buzzer
  pinMode(buzzer, OUTPUT);

  // Switches
  pinMode(togglePin, INPUT_PULLUP);     // toggle wired to GND → use pull-up
  pinMode(pushButtonPin, INPUT_PULLUP); // button wired to GND

  // Start with everything off
  digitalWrite(greenLED, LOW);
  digitalWrite(redLED1, LOW);
  digitalWrite(redLED2, LOW);
  digitalWrite(buzzer, LOW);

  lcd.print("System Ready");
}

void loop() {
  int toggleState = digitalRead(togglePin);       // HIGH = OFF, LOW = ON
  int buttonState = digitalRead(pushButtonPin);   // LOW when pressed

  // Toggle OFF → system disabled
  if (toggleState == HIGH) {
    lcd.clear();
    lcd.print("System Off");

    digitalWrite(greenLED, LOW);
    digitalWrite(redLED1, LOW);
    digitalWrite(redLED2, LOW);
    digitalWrite(buzzer, LOW);
    return;
  }

  // Toggle ON → system ready
  digitalWrite(greenLED, HIGH);
  lcd.clear();
  lcd.print("System Active");

  // Optional debug
  // Serial.println("alarm ");

  // Check alarm trigger
  if (buttonState == LOW) {
    triggerAlarm();
  }
}

void triggerAlarm() {
  lcd.clear();
  lcd.print("!!! ALARM !!!");

  // Tell Python: alarm has started
  Serial.println("ALARM_TRIGGERED");

  // Blink red LEDs + buzzer for as long as button is pressed
  while (digitalRead(pushButtonPin) == LOW) {
    digitalWrite(redLED1, HIGH);
    digitalWrite(redLED2, HIGH);
    digitalWrite(buzzer, HIGH);
    delay(150);

    digitalWrite(redLED1, LOW);
    digitalWrite(redLED2, LOW);
    digitalWrite(buzzer, LOW);
    delay(150);
  }

  // After alarm stops
  lcd.clear();
  lcd.print("System Active");

  // Tell Python: alarm ended, safe again
  Serial.println("ALARM_CLEARED");
}
