# Raspberry Pi Setup Guide — AiTrading Bot

Complete step-by-step guide to get the AI trading bot running on a Raspberry Pi.

---

## Part 1: Getting Your API Keys

You need **two types of keys**: one for your AI provider, and one for Alpaca (the broker).

---

### Alpaca API Keys (Broker — Free Paper Trading)

1. Go to [https://alpaca.markets](https://alpaca.markets)
2. Click **Sign Up** and create a free account with your email
3. Verify your email via the link sent to your inbox
4. Log in to the **Alpaca Dashboard**
5. Click **Paper Trading** (toggle or section in the dashboard)
6. Go to **API Keys** in the sidebar (under Settings or Developer)
7. Click **Generate New Key**
8. You'll see two values:
   - **API Key ID** — this is your `ALPACA_API_KEY`
   - **Secret Key** — this is your `ALPACA_SECRET_KEY`
9. **Copy both immediately** — the secret key is only shown once!
10. Store them somewhere safe (password manager, note on your phone, etc.)

> **Note:** Paper trading is completely free. No credit card required.
> The paper trading base URL is `https://paper-api.alpaca.markets` (handled automatically by the bot).

---

### Gemini API Key (Google — Recommended for Pi)

1. Go to [https://aistudio.google.com](https://aistudio.google.com)
2. Sign in with your **Google account**
3. Look for **"Get API Key"** or go to **API Keys** in the sidebar
4. Click **"Create API Key"**
5. Select or create a Google Cloud project when prompted
6. Your API key will be generated — **copy it immediately**
7. Store it securely

> **Pricing:** Gemini 2.5 Flash is ~$0.30/M input tokens, ~$2.50/M output tokens.
> Estimated cost: **$3–10/month** for this bot.
> Google also offers a **free tier** with limited daily requests — enough for testing.

---

### Claude API Key (Anthropic — Best Quality)

1. Go to [https://console.anthropic.com](https://console.anthropic.com)
2. Click **Sign Up** and create an account with your email
3. Verify your email and phone number
4. Go to **Settings → Billing** and add a credit card
   - Recommended: set a **monthly spending limit** (e.g., $50) to avoid surprises
5. Click **API Keys** in the sidebar
6. Click **+ Create Key**
7. Name it (e.g., "AiTrading Bot")
8. **Copy the key immediately** — it's only shown once
9. Store it securely

> **Pricing:** Claude Sonnet is ~$3/M input, ~$15/M output.
> Estimated cost: **$30–90/month**.

---

### ChatGPT API Key (OpenAI)

1. Go to [https://platform.openai.com](https://platform.openai.com)
2. Click **Sign Up** or **Log In**
3. Verify your email and set up two-factor authentication if prompted
4. Go to **Settings → Billing** and add a payment method
5. Navigate to **API Keys** (top-right profile menu → API Keys)
   - Or go directly to: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
6. Click **"+ Create new secret key"**
7. Name it and click **Create**
8. **Copy the key immediately** — it's only shown once
9. Store it securely

> **Pricing:** GPT-4.1 is ~$2/M input, ~$8/M output.
> Estimated cost: **$20–60/month**.

---

### Grok API Key (xAI)

1. You need an **X Premium subscription** ($8/month) at [x.com](https://x.com)
   - Go to Premium in the sidebar and subscribe
   - Wait **24–48 hours** for API access to activate
2. Go to [https://console.x.ai](https://console.x.ai)
3. Sign in with your **X account**
4. Complete the developer onboarding (name, use case, agree to terms)
5. Go to **Billing** and add a payment method
6. Go to **API Keys** in the sidebar
7. Click **"Create New Key"**
8. Name it, set permissions, and click **Create**
9. **Copy the key immediately** — it's only shown once
10. Store it securely

> **Pricing:** Grok-3 Mini is ~$0.30/M input, ~$0.50/M output.
> Estimated cost: **$1–5/month** (cheapest option).
> However, requires X Premium subscription ($8/month) on top.

---

## Part 2: Raspberry Pi Setup

### Prerequisites

- Raspberry Pi (any model with WiFi — even a Pi Zero W works)
- Raspberry Pi OS installed (Bookworm recommended — comes with Python 3.11)
- Pi connected to WiFi and accessible via SSH
- Your API keys from Part 1

---

### Step 1: Copy the Project to the Pi

**Option A — From your Windows/WSL terminal via SCP:**
```bash
scp -r /path/to/AiTrading pi@<PI_IP_ADDRESS>:~/AiTrading
```

**Option B — From a GitHub repo:**
```bash
# On the Pi:
git clone https://github.com/your-username/AiTrading.git ~/AiTrading
```

**Option C — USB stick:**
Copy the `AiTrading` folder to a USB drive, plug into Pi, and copy to `~/AiTrading`.

> **Find your Pi's IP address:** On the Pi, run `hostname -I`, or check your router's connected devices.

---

### Step 2: SSH into the Pi

```bash
ssh pi@<PI_IP_ADDRESS>
```

Default password is usually `raspberry` (change it with `passwd` if you haven't).

---

### Step 3: Install Python and Create Virtual Environment

```bash
# Check Python version (need 3.10+, Bookworm has 3.11)
python3 --version

# Go to the project folder
cd ~/AiTrading

# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install base dependencies
pip install -r requirements.txt

# Install your chosen AI provider SDK:
pip install google-generativeai    # For Gemini (recommended)
# pip install anthropic            # For Claude
# pip install openai               # For ChatGPT or Grok
```

> **Note:** On a Pi Zero, `pip install` may take 5–10 minutes. Be patient.

---

### Step 4: Configure Your .env File

```bash
# Copy the template
cp .env.example .env

# Edit it
nano .env
```

Fill in your values (example for Gemini):
```
AI_PROVIDER=gemini
AI_API_KEY=your-actual-gemini-api-key-here
AI_MODEL=

ALPACA_API_KEY=your-alpaca-api-key
ALPACA_SECRET_KEY=your-alpaca-secret-key
ALPACA_PAPER=true
```

Save with **Ctrl+O** then **Enter**, exit with **Ctrl+X**.

---

### Step 5: Test Run

```bash
# Make sure venv is active
source venv/bin/activate

# Run the bot
python3 run.py
```

**Expected output:**
- If market is closed: `Market is closed (HH:MM ET, DayName). Skipping.`  — this is correct!
- If market is open: The bot will run through its analysis cycle and log everything.

**To test outside market hours** (temporarily), edit `run.py`:
```bash
nano run.py
```
Comment out lines 46-48 (the market hours check):
```python
    # if not is_market_open():
    #     now = get_eastern_time()
    #     log(log_file, f"Market is closed ...")
    #     return
```
Run the test, then **uncomment the lines** when done.

---

### Step 6: Set the Pi's Timezone

This ensures cron runs at the correct hours relative to US market time.

```bash
# Check current timezone
timedatectl

# Set to US Eastern (recommended — cron hours match market hours directly)
sudo timedatectl set-timezone America/New_York
```

If you prefer to keep your local timezone, adjust the cron hours accordingly (see Step 7).

---

### Step 7: Set Up the Cron Job

```bash
crontab -e
```

If asked to choose an editor, pick **nano** (option 1).

Add this line at the bottom of the file:

**If timezone is set to America/New_York (Eastern Time):**
```
*/5 9-15 * * 1-5 cd /home/pi/AiTrading && /home/pi/AiTrading/venv/bin/python run.py >> /home/pi/AiTrading/logs/cron.log 2>&1
```

**If timezone is CET/CEST (Central European Time, UTC+1/+2):**
```
*/5 15-22 * * 1-5 cd /home/pi/AiTrading && /home/pi/AiTrading/venv/bin/python run.py >> /home/pi/AiTrading/logs/cron.log 2>&1
```

Save with **Ctrl+O** then **Enter**, exit with **Ctrl+X**.

Verify the cron job was saved:
```bash
crontab -l
```

> **What this does:** Runs `run.py` every 5 minutes, Monday–Friday, during market hours.
> The bot itself also checks if the market is actually open (handles holidays, half-days, etc.).

---

### Step 8: Ensure Cron Starts on Boot

This should be the default, but verify:
```bash
sudo systemctl enable cron
sudo systemctl status cron
```

You should see `Active: active (running)`.

---

### Step 9: Verify It's Working

After the next market open (or the next cron trigger):

```bash
# Check today's log
cat ~/AiTrading/logs/$(date +%Y-%m-%d).log

# Watch the log live (Ctrl+C to stop watching)
tail -f ~/AiTrading/logs/cron.log

# Check state file
cat ~/AiTrading/state.json
```

---

### Step 10: Keep the Pi Running Reliably

```bash
# Optional: auto-reboot weekly (Sunday 3 AM) to keep things clean
sudo crontab -e
# Add this line:
0 3 * * 0 /sbin/reboot
```

**Prevent SD card wear** (optional but recommended for longevity):
```bash
# Reduce log writes — logs are small, but good practice
# Create a tmpfs for temporary files
echo "tmpfs /tmp tmpfs defaults,noatime,nosuid,size=100m 0 0" | sudo tee -a /etc/fstab
```

---

## Part 3: Ongoing Management

### Check Logs Remotely
```bash
ssh pi@<PI_IP_ADDRESS> "tail -30 ~/AiTrading/logs/\$(date +%Y-%m-%d).log"
```

### Switch AI Provider
```bash
ssh pi@<PI_IP_ADDRESS>
nano ~/AiTrading/.env
# Change AI_PROVIDER and AI_API_KEY
# Install the new SDK if needed: pip install openai / anthropic / google-generativeai
```

### Update the Strategy
```bash
ssh pi@<PI_IP_ADDRESS>
nano ~/AiTrading/prompts/strategy.md
# Edit the strategy — takes effect on the very next run
```

### Go Live (After Extensive Paper Testing!)
```bash
ssh pi@<PI_IP_ADDRESS>
nano ~/AiTrading/.env
# Change: ALPACA_PAPER=false
# Use your LIVE Alpaca API keys (different from paper keys!)
```

> **Warning:** Only do this after at least 1-2 weeks of successful paper trading
> and careful review of the bot's decision logs.

---

## Troubleshooting

### "Market is closed" even during market hours
- Check timezone: `timedatectl`
- US market hours are 9:30 AM – 4:00 PM Eastern Time (ET)
- The bot adds a 5-min buffer: 9:35 AM – 3:45 PM ET

### "Missing required environment variable"
- Check your `.env` file: `cat ~/AiTrading/.env`
- Make sure there are no extra spaces around the `=` sign
- Make sure the venv is activated: `source ~/AiTrading/venv/bin/activate`

### "ModuleNotFoundError: No module named 'google.generativeai'"
- Install the SDK: `pip install google-generativeai`
- Make sure you're in the venv: `source ~/AiTrading/venv/bin/activate`

### "Another run is already in progress"
- A previous run didn't finish. Check if it's still running: `ps aux | grep run.py`
- If stuck, remove the lock: `rm ~/AiTrading/.run.lock`

### Pi loses WiFi
- Set up WiFi reconnection:
  ```bash
  sudo nano /etc/cron.d/wifi-check
  # Add: */5 * * * * root /sbin/iwconfig wlan0 | grep -q "Not-Associated" && sudo systemctl restart networking
  ```

### Check if cron is running
```bash
sudo systemctl status cron
grep -i cron /var/log/syslog | tail -20
```
