int red_pin = 2;
int green_pin = 3;
int blue_pin = 4;

int pwm_pin = 6;

void setup()
{
  // imposta i pin come input / output
  pinMode(red_pin, OUTPUT);
  pinMode(green_pin, OUTPUT);
  pinMode(blue_pin, OUTPUT);
  pinMode(pwm_pin, OUTPUT); 

  digitalWrite(red_pin, LOW);
  digitalWrite(green_pin, LOW);
  digitalWrite(blue_pin, LOW);

}

void loop()
{
  digitalWrite(pwm_pin, HIGH);

  for(int i = 0; i<3 ; i++)
  {
    digitalWrite(i+2, HIGH);
    delay(300);
    digitalWrite(i+2, LOW);
    delay(1);
  }

  digitalWrite(pwm_pin, LOW);
  delay(99);
}