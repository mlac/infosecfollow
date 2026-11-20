# PaperS3 reader

`PaperS3_InfosecFollow/` is an Arduino sketch for the M5Stack PaperS3
(ESP32-S3, 4.7-inch 540x960 e-ink). Press the side power button and it fetches
`https://infosecfollow.com/paper.txt` over verified HTTPS, shows one story per
screen, and powers off after 90 seconds without a tap. Tap the right half of
the screen for the next story, the left half to go back.

`engine/paper.py` writes `paper.txt` and trims each story on the server until
it fits one screen, using the same fonts, geometry, and word-wrap rule as the
sketch. If you change the fonts, margins, or line spacing in the sketch, change
`engine/paper.py` to match.

## Flashing

1. Arduino IDE 2: add
   `https://static-cdn.m5stack.com/resource/arduino/package_m5stack_index.json`
   under Settings > Additional boards manager URLs, then install the M5Stack
   board package.
2. Library Manager: install M5Unified (0.2.5 or later) and M5GFX (0.2.7 or later).
3. Open `PaperS3_InfosecFollow/PaperS3_InfosecFollow.ino`; `root_ca.h` opens as
   a second tab. Set `WIFI_SSID` and `WIFI_PASS` (a 2.4 GHz network). Do not
   commit your credentials.
4. Tools > Board > M5Stack > M5PaperS3. Connect USB-C, hold the power button
   until the back LED blinks red, choose the `/dev/cu.usbmodem...` port, and
   upload.

`root_ca.h` holds nine public root certificates (Let's Encrypt, Google Trust
Services, Amazon, DigiCert, Sectigo, SSL.com). If the screen shows a TLS error,
the site's certificate chains to a root that is not in the bundle; add it.
