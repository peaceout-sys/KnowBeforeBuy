"""
app.py
------
Flask backend for the KnowBeforeBuy extension.

Endpoints:
  POST /api/scrape  {url}                          -> scraped product data
  POST /api/chat     {product, question, history}   -> LLM answer
  GET  /api/health                                  -> {"status": "ok"}

Run:
  python app.py
Then load the extension/ folder as an unpacked Chrome extension and
visit an Amazon product page.
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from scraper import scrape_amazon_product
from llm import ask_about_product

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("knowbeforebuy")

app = Flask(__name__)
# Chrome extensions call this from a chrome-extension:// origin, not http(s),
# so we allow all origins for this local dev server. Do not do this in a
# public-facing production deployment.
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Simple in-memory cache so re-asking about the same tab doesn't
# re-trigger a full Selenium scrape every time.
_scrape_cache: dict[str, dict] = {}


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/scrape", methods=["POST"])
def scrape():
    data = request.get_json(force=True)
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400

    if url in _scrape_cache:
        logger.info(f"Cache hit for {url}")
        return jsonify(_scrape_cache[url])

    try:
        logger.info(f"Scraping {url}")
        product = scrape_amazon_product(url)
        _scrape_cache[url] = product
        return jsonify(product)
    except Exception as e:
        logger.exception("Scrape failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    product = data.get("product")
    question = data.get("question")
    history = data.get("history", [])

    if not product or not question:
        return jsonify({"error": "Missing 'product' or 'question'"}), 400

    try:
        answer = ask_about_product(product, question, history)
        return jsonify({"answer": answer})
    except Exception as e:
        logger.exception("Chat failed")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
