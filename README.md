# KnowBeforeBuy

A Chrome extension that scans the Amazon product page you're viewing and
answers questions about it using Llama 3 70B (via Groq), grounded in the
actual scraped page data.

```
You browse Amazon  ─►  Extension popup  ─►  Flask backend (localhost)
                                                   │
                                       Selenium scrapes the live page
                                                   │
                                          BeautifulSoup extracts fields
                                                   │
                                    Groq (Llama3-70B) answers, grounded
                                       in the scraped product data
```

## What's been tested vs. what you need to verify yourself

I built and tested this without live internet access, so here's exactly
what's been verified vs. not:

**Verified (real code, actually executed):**
- BeautifulSoup selector logic against Amazon-shaped HTML — correctly
  extracts title, price, rating, review count, feature bullets
- Flask routes (`/api/scrape`, `/api/chat`, `/api/health`) — request
  validation, error handling (400s on missing fields), JSON responses
- The LLM prompt-grounding logic — confirmed the product context
  (title/price/rating/bullets) gets correctly assembled into the prompt
  sent to Llama3
- The popup UI — rendered and screenshotted, chat bubbles/chips/composer
  all display correctly

**Not verified here (needs your machine + real internet):**
- Actually running Selenium against a live amazon.com page (Amazon's
  bot-detection may show a CAPTCHA — see Troubleshooting below)
- Actually calling the real Groq API (needs your API key)
- Loading the extension in real Chrome and clicking through it

## Setup

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

You'll also need Chrome installed locally (Selenium drives real Chrome,
`webdriver-manager` auto-downloads the matching driver — this step
needs internet the first time it runs).

### 2. Get a free Groq API key

1. Go to https://console.groq.com/keys
2. Sign up (free), create an API key
3. Copy `.env.example` to `.env` and paste your key:

```bash
cp .env.example .env
# edit .env: GROQ_API_KEY=gsk_your_actual_key_here
```

### 3. Run the backend

```bash
python app.py
```

You should see Flask start on `http://127.0.0.1:5000`. Leave this running.

### 4. Load the extension in Chrome

1. Open `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `extension/` folder
5. The KnowBeforeBuy icon should appear in your toolbar

### 5. Try it

1. Go to any Amazon product page, e.g. `https://www.amazon.com/dp/B0B6WFPJ8P`
2. Click the KnowBeforeBuy extension icon
3. It should scrape the page (takes a few seconds — real headless Chrome
   is launching) and show a product summary card
4. Ask a question: "Is this worth it?", "What's the battery life?", etc.

## Troubleshooting

**"Couldn't reach the backend"** — make sure `python app.py` is still
running in a terminal and nothing else is using port 5000.

**Scrape returns `scrape_ok: false` / fields missing** — the most likely
cause is Amazon showing a CAPTCHA or bot-check page instead of the real
product page. This is common with automated Amazon scraping and is
exactly why the original project's scraper design has multiple selector
fallbacks — Amazon changes layout/tests frequently. If it happens
consistently:
- Try a different product URL
- Try increasing the wait/sleep times in `scraper.py`
- Consider testing against a less aggressively bot-protected site first
  to confirm the rest of the pipeline (backend, LLM, extension) works,
  then return to hardening the Amazon scraper specifically

**GROQ_API_KEY error** — double check `.env` is in the `backend/` folder
(not the project root) and has no quotes around the key.

**CORS errors in the extension's console** — the backend already allows
all origins on `/api/*` for local dev. If you still see CORS errors,
confirm you're hitting `http://127.0.0.1:5000` and not `https://`.

## Project structure

```
knowbeforebuy/
├── backend/
│   ├── app.py              # Flask routes
│   ├── scraper.py          # Selenium + BeautifulSoup Amazon scraper
│   ├── llm.py               # Groq/Llama3 client + prompt grounding
│   ├── requirements.txt
│   └── .env.example
└── extension/
    ├── manifest.json        # Manifest V3
    ├── popup.html/css/js    # Extension popup UI
    └── icons/
```

## Known limitations (be upfront about these in an interview)

- **Amazon-specific**: selectors are tuned to Amazon's DOM. Other sites
  need their own selector sets (this is exactly why the original project
  claimed "4 major e-commerce platforms" — each needs its own scraper
  module following the same pattern as `scraper.py`).
- **Scraping fragility**: e-commerce sites change layouts and actively
  fight bots. Production-grade scraping usually needs proxy rotation,
  CAPTCHA-solving services, or official APIs — out of scope for a demo.
- **No persistent chat history** — history resets when the popup closes
  (kept in-memory in `popup.js`). Easy extension: `chrome.storage.local`.
- **Local-only backend** — for a real deployed version, you'd containerize
  `backend/` (Docker) and deploy it, then point `BACKEND_URL` in
  `popup.js` at the real endpoint instead of `127.0.0.1`. This is also
  your natural next step toward a cloud-computing-flavored resume bullet.
