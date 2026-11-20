// PaperS3_InfosecFollow.ino -- one story per screen.
//
// Press the side power button: the PaperS3 boots, fetches
// https://infosecfollow.com/paper.txt over verified HTTPS, and shows one
// story per screen in Smart Brevity form (kicker, headline, lede, "Why it
// matters", labeled details, sources). Tap the right half for the next story,
// the left half to go back. After IDLE_TIMEOUT_MS without a tap it powers
// off; the e-ink panel keeps the last story on screen with no power.
//
// The layout below (fonts, margins, line pitches, the word-wrap rule, the 1 px
// fake-bold allowance) mirrors engine/paper.py, which trims every story on the
// server until it fits this screen. Change the two together.

#include <M5Unified.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <time.h>
#include <vector>
#include "root_ca.h"

// --- User configuration ---
const char* WIFI_SSID = "YOUR_WIFI_SSID";       // must be a 2.4 GHz network
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
const char* PAPER_URL = "https://infosecfollow.com/paper.txt";
const char* TZ_INFO   = "EST5EDT,M3.2.0,M11.1.0";  // US Eastern

const uint32_t IDLE_TIMEOUT_MS = 90000;  // power off after 90 s without a tap
const uint32_t FAST_CONNECT_MS = 4000;   // cached channel/BSSID attempt
const uint32_t FULL_CONNECT_MS = 12000;  // full scan fallback
const uint32_t CPU_ACTIVE_MHZ  = 240;
const uint32_t CPU_IDLE_MHZ    = 80;

// --- Layout: keep in step with engine/paper.py ---
const GFXfont* CHROME_FONT = &fonts::DejaVu18;            // header, footer
const GFXfont* KICKER_FONT = &fonts::DejaVu18;
const GFXfont* HEAD_FONT   = &fonts::FreeSansBold18pt7b;
const GFXfont* BODY_FONT   = &fonts::DejaVu24;
const int MARGIN_X    = 18;
const int HEADER_H    = 48;
const int FOOTER_H    = 40;
const int TOP_PAD     = 6;
const int BOTTOM_PAD  = 4;
const int KICKER_GAP  = 8;
const int HEAD_GAP    = 8;
const int BODY_LEADING = 4;
const int PARA_GAP    = 10;

struct Story {
  String kicker;
  String headline;
  std::vector<String> paras;
};

std::vector<Story> stories;
int currentStory = 0;
String stampStr  = "";

// ---------------------------------------------------------------------------
// Wi-Fi: cached channel and BSSID first (skips the scan), then a full connect.
// ---------------------------------------------------------------------------
bool waitForWiFi(uint32_t timeoutMs) {
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeoutMs) delay(50);
  return WiFi.status() == WL_CONNECTED;
}

bool connectWiFi() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  Preferences prefs;
  prefs.begin("wifi", false);
  int32_t channel = prefs.getInt("ch", 0);
  uint8_t bssid[6];
  bool haveCache = channel > 0 && prefs.getBytes("bssid", bssid, 6) == 6;
  if (haveCache) {
    WiFi.begin(WIFI_SSID, WIFI_PASS, channel, bssid);
    if (waitForWiFi(FAST_CONNECT_MS)) {
      prefs.end();
      return true;
    }
    WiFi.disconnect();
    delay(100);
  }
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  bool ok = waitForWiFi(FULL_CONNECT_MS);
  if (ok) {
    prefs.putInt("ch", WiFi.channel());
    prefs.putBytes("bssid", WiFi.BSSID(), 6);
  }
  prefs.end();
  return ok;
}

// ---------------------------------------------------------------------------
// Timestamp from the HTTP response ("Fri, 20 Nov 2026 17:05:00 GMT").
// ---------------------------------------------------------------------------
int64_t daysFromCivil(int y, int m, int d) {
  y -= (m <= 2);
  const int era = (y >= 0 ? y : y - 399) / 400;
  const int yoe = y - era * 400;
  const int doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const int doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  return (int64_t)era * 146097 + doe - 719468;
}

bool parseHttpDate(const String& s, time_t& out) {
  static const char* MONTHS = "JanFebMarAprMayJunJulAugSepOctNovDec";
  int d, y, hh, mm, ss;
  char mon[4] = {0};
  if (sscanf(s.c_str(), "%*3s, %d %3s %d %d:%d:%d", &d, mon, &y, &hh, &mm, &ss) != 6) return false;
  const char* p = strstr(MONTHS, mon);
  if (p == nullptr) return false;
  int m = (p - MONTHS) / 3 + 1;
  out = (time_t)(daysFromCivil(y, m, d) * 86400 + hh * 3600 + mm * 60 + ss);
  return true;
}

String formatLocal(time_t t) {
  setenv("TZ", TZ_INFO, 1);
  tzset();
  struct tm lt;
  localtime_r(&t, &lt);
  char buf[24];
  strftime(buf, sizeof(buf), "%b %d %H:%M", &lt);
  return String(buf);
}

// ---------------------------------------------------------------------------
// HTTPS fetch, verified against root_ca.h.
// ---------------------------------------------------------------------------
bool fetchPaper(String& payload) {
  WiFiClientSecure client;
  client.setCACert(ROOT_CA_BUNDLE);
  HTTPClient http;
  http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
  http.setTimeout(12000);
  http.setUserAgent("PaperS3-InfosecFollow/2.0");
  const char* keys[] = {"Last-Modified", "Date"};
  http.collectHeaders(keys, 2);

  if (!http.begin(client, PAPER_URL)) {
    payload = "Could not start the HTTPS request.";
    return false;
  }
  int code = http.GET();
  if (code == HTTP_CODE_OK) {
    payload = http.getString();
    time_t t;
    if (parseHttpDate(http.header("Last-Modified"), t)) {
      stampStr = "Ed. " + formatLocal(t);
    } else if (parseHttpDate(http.header("Date"), t)) {
      stampStr = "Got " + formatLocal(t);
    }
    http.end();
    return payload.length() > 0;
  }
  char tlsErr[100] = {0};
  client.lastError(tlsErr, sizeof(tlsErr));
  payload = "HTTP error " + String(code) + ": " + HTTPClient::errorToString(code) + ".";
  if (tlsErr[0] != '\0') payload += " TLS: " + String(tlsErr);
  http.end();
  return false;
}

// ---------------------------------------------------------------------------
// paper.txt parsing: stories separated by form feeds; in each story, line 1 is
// the kicker, line 2 the headline, and every later non-blank line a paragraph.
// ---------------------------------------------------------------------------
String asciiOnly(const String& in) {
  String out;
  out.reserve(in.length());
  for (size_t i = 0; i < in.length(); ++i) {
    uint8_t c = static_cast<uint8_t>(in[i]);
    if (c == '\n' || c == '\f' || (c >= 32 && c <= 126)) out += static_cast<char>(c);
  }
  return out;
}

void parsePaper(const String& raw) {
  stories.clear();
  String text = asciiOnly(raw);
  int pos = 0;
  int len = text.length();
  while (pos < len) {
    int ff = text.indexOf('\f', pos);
    if (ff == -1) ff = len;
    String block = text.substring(pos, ff);
    pos = ff + 1;

    Story s;
    int lineNo = 0;
    int bp = 0;
    int blen = block.length();
    while (bp <= blen) {
      int nl = block.indexOf('\n', bp);
      if (nl == -1) nl = blen;
      String line = block.substring(bp, nl);
      bp = nl + 1;
      line.trim();
      if (line.length() == 0) {
        if (nl == blen) break;
        continue;
      }
      if (lineNo == 0) s.kicker = line;
      else if (lineNo == 1) s.headline = line;
      else s.paras.push_back(line);
      lineNo++;
      if (nl == blen) break;
    }
    if (s.headline.length() > 0) stories.push_back(s);
  }
}

void setMessage(const String& headline, const String& body) {
  stories.clear();
  Story s;
  s.kicker = "INFOSECFOLLOW";
  s.headline = headline;
  s.paras.push_back(body);
  stories.push_back(s);
}

// ---------------------------------------------------------------------------
// Layout, identical to engine/paper.py wrap() and layout().
// ---------------------------------------------------------------------------
// "*Label:* rest" -> label "Label:", rest "rest". Mirrors _LABEL_RE.
bool splitLabel(const String& para, String& label, String& rest) {
  if (para.length() < 4 || para[0] != '*') return false;
  int close = para.indexOf(":*", 1);
  if (close < 1 || close > 40) return false;
  String inner = para.substring(1, close + 1);
  if (inner.indexOf('*') != -1) return false;
  label = inner;
  rest = para.substring(close + 2);
  while (rest.length() > 0 && isspace((unsigned char)rest[0])) rest.remove(0, 1);
  return true;
}

std::vector<String> wrap(const String& text, int boldChars, int maxW) {
  std::vector<String> lines;
  String line;
  int pos = 0;
  int len = text.length();
  while (pos < len) {
    int sp = text.indexOf(' ', pos);
    if (sp == -1) sp = len;
    String word = text.substring(pos, sp);
    pos = sp + 1;
    if (word.length() == 0) continue;
    String candidate = line.isEmpty() ? word : (line + " " + word);
    int extra = (boldChars > 0 && lines.empty()) ? 1 : 0;
    if (M5.Display.textWidth(candidate) + extra <= maxW) {
      line = candidate;
      continue;
    }
    if (!line.isEmpty()) {
      lines.push_back(line);
      line = "";
    }
    while (M5.Display.textWidth(word) > maxW && word.length() > 1) {
      int cut = word.length() - 1;
      while (cut > 1 && M5.Display.textWidth(word.substring(0, cut)) > maxW) cut--;
      lines.push_back(word.substring(0, cut));
      word = word.substring(cut);
    }
    line = word;
  }
  if (!line.isEmpty()) lines.push_back(line);
  return lines;
}

void drawChrome(int w, int h) {
  M5.Display.setFont(CHROME_FONT);
  M5.Display.setCursor(MARGIN_X, 14);
  M5.Display.print("INFOSECFOLLOW");
  String status = stampStr;
  if (status.length() > 0) status += "   ";
  status += String(M5.Power.getBatteryLevel()) + "%";
  M5.Display.setCursor(w - MARGIN_X - M5.Display.textWidth(status), 14);
  M5.Display.print(status);
  M5.Display.drawFastHLine(MARGIN_X, HEADER_H - 8, w - 2 * MARGIN_X, TFT_BLACK);

  M5.Display.drawFastHLine(MARGIN_X, h - FOOTER_H, w - 2 * MARGIN_X, TFT_BLACK);
  String pageStr = String(currentStory + 1) + " / " + String((int)stories.size());
  M5.Display.setCursor(MARGIN_X, h - FOOTER_H + 12);
  M5.Display.print(pageStr);
  const char* hint = "< back | next >";
  M5.Display.setCursor(w - MARGIN_X - M5.Display.textWidth(hint), h - FOOTER_H + 12);
  M5.Display.print(hint);
}

void renderStory(int idx, epd_mode_t mode) {
  const int w = M5.Display.width();
  const int h = M5.Display.height();
  const int textW = w - 2 * MARGIN_X;
  const int bottom = h - FOOTER_H - BOTTOM_PAD;
  const Story& s = stories[idx];

  M5.Display.setEpdMode(mode);
  M5.Display.startWrite();
  M5.Display.fillScreen(TFT_WHITE);
  M5.Display.setTextColor(TFT_BLACK, TFT_WHITE);
  drawChrome(w, h);

  int y = HEADER_H + TOP_PAD;

  M5.Display.setFont(KICKER_FONT);
  M5.Display.setCursor(MARGIN_X, y);
  M5.Display.print(s.kicker);
  y += M5.Display.fontHeight() + KICKER_GAP;

  M5.Display.setFont(HEAD_FONT);
  int headPitch = M5.Display.fontHeight();
  for (const String& line : wrap(s.headline, 0, textW)) {
    M5.Display.setCursor(MARGIN_X, y);
    M5.Display.print(line);
    y += headPitch;
  }
  y += HEAD_GAP;

  M5.Display.setFont(BODY_FONT);
  int pitch = M5.Display.fontHeight() + BODY_LEADING;
  for (size_t n = 0; n < s.paras.size(); ++n) {
    if (n) y += PARA_GAP;
    String label, rest, shown;
    int boldChars = 0;
    if (splitLabel(s.paras[n], label, rest)) {
      shown = rest.length() ? (label + " " + rest) : label;
      boldChars = label.length();
    } else {
      shown = s.paras[n];
    }
    std::vector<String> lines = wrap(shown, boldChars, textW);
    for (size_t i = 0; i < lines.size(); ++i) {
      if (y + pitch > bottom + BODY_LEADING) break;  // never draw into the footer
      if (i == 0 && boldChars > 0) {
        int k = min((int)lines[0].length(), boldChars);
        String bold = lines[0].substring(0, k);
        M5.Display.setCursor(MARGIN_X + 1, y);    // fake bold: draw twice, 1 px apart
        M5.Display.print(bold);
        M5.Display.setCursor(MARGIN_X, y);
        M5.Display.print(bold);
        M5.Display.print(lines[0].substring(k));
      } else {
        M5.Display.setCursor(MARGIN_X, y);
        M5.Display.print(lines[i]);
      }
      y += pitch;
    }
  }

  M5.Display.endWrite();
  M5.Display.display();
  M5.Display.waitDisplay();   // finish the refresh before sleeping or powering off
}

// ---------------------------------------------------------------------------
void setup() {
  auto cfg = M5.config();
  cfg.internal_imu = false;   // keep unused peripherals off
  cfg.internal_spk = false;
  M5.begin(cfg);
  setCpuFrequencyMhz(CPU_ACTIVE_MHZ);
  M5.Display.setRotation(0);  // portrait, 540 x 960; paper.py assumes this

  String payload;
  if (connectWiFi()) {
    if (fetchPaper(payload)) {
      parsePaper(payload);
      if (stories.empty()) setMessage("Nothing to Show", "paper.txt held no stories.");
    } else {
      setMessage("Fetch Failed", payload);
    }
  } else {
    setMessage("Wi-Fi Failed", "Check the 2.4 GHz network name and password in the sketch.");
  }
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);

  renderStory(currentStory, epd_mode_t::epd_quality);   // full refresh clears ghosting
  setCpuFrequencyMhz(CPU_IDLE_MHZ);

  uint32_t lastTouch = millis();
  while (millis() - lastTouch < IDLE_TIMEOUT_MS) {
    M5.update();
    auto t = M5.Touch.getDetail();
    if (t.wasClicked()) {
      lastTouch = millis();
      int next = currentStory;
      if (t.x > M5.Display.width() / 2) {
        if (currentStory < (int)stories.size() - 1) next++;
      } else if (currentStory > 0) {
        next--;
      }
      if (next != currentStory) {
        currentStory = next;
        setCpuFrequencyMhz(CPU_ACTIVE_MHZ);
        renderStory(currentStory, epd_mode_t::epd_text);
        setCpuFrequencyMhz(CPU_IDLE_MHZ);
      }
    }
    delay(25);
  }

  M5.Power.powerOff();   // on battery: power cut, the panel keeps the story
  M5.Power.deepSleep();  // on USB: sleep; a tap on the screen restarts the sketch
}

void loop() {}
