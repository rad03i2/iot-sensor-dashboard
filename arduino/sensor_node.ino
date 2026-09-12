const int lightPin = A0;
const int ledPin = 13;

void setup() {
  Serial.begin(9600);
  pinMode(ledPin, OUTPUT);
}

void loop() {
  int light = analogRead(lightPin);
  int temperature = 24 + (light % 7);

  Serial.print("{\"light\":");
  Serial.print(light);
  Serial.print(",\"temperature\":");
  Serial.print(temperature);
  Serial.println("}");

  digitalWrite(ledPin, light < 400 ? HIGH : LOW);
  delay(1000);
}
