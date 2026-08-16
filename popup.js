const BACKEND_URL = "http://127.0.0.1:5000";

const productCard = document.getElementById("productCard");
const messagesEl = document.getElementById("messages");
const input = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");
const rescanBtn = document.getElementById("rescanBtn");

let currentProduct = null;
let history = [];

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg msg--${role}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function addTypingIndicator() {
  const div = document.createElement("div");
  div.className = "msg msg--assistant msg--typing";
  div.innerHTML = "<span class='dot'></span><span class='dot'></span><span class='dot'></span>";
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function renderProductCard(product) {
  if (!product || !product.scrape_ok) {
    productCard.className = "product-card";
    productCard.innerHTML = `
      <div class="product-card__title">Couldn't read this page</div>
      <div class="product-card__meta">
        <span class="chip chip--error">Not an Amazon product page, or scrape blocked</span>
      </div>
    `;
    return;
  }

  productCard.className = "product-card";
  const chips = [];
  if (product.price) chips.push(`<span class="chip chip--price">${escapeHtml(product.price)}</span>`);
  if (product.rating) chips.push(`<span class="chip chip--rating">${escapeHtml(product.rating)}</span>`);
  if (product.review_count) chips.push(`<span class="chip">${escapeHtml(product.review_count)}</span>`);

  productCard.innerHTML = `
    <div class="product-card__title">${escapeHtml(product.title || "Untitled product")}</div>
    <div class="product-card__meta">${chips.join("")}</div>
  `;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function setComposerEnabled(enabled) {
  input.disabled = !enabled;
  sendBtn.disabled = !enabled;
}

async function getActiveTabUrl() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      resolve(tabs[0]?.url || null);
    });
  });
}

async function scrapeCurrentPage() {
  productCard.className = "product-card product-card--loading";
  productCard.innerHTML = `<div class="product-card__title">Scanning this page&hellip;</div>`;
  messagesEl.innerHTML = "";
  history = [];
  setComposerEnabled(false);

  const url = await getActiveTabUrl();
  if (!url) {
    addMessage("system", "Couldn't read the active tab URL.");
    return;
  }

  if (!url.includes("amazon.")) {
    productCard.className = "product-card";
    productCard.innerHTML = `
      <div class="product-card__title">Not an Amazon product page</div>
      <div class="product-card__meta">
        <span class="chip">Open a product page on amazon.com to use KnowBeforeBuy</span>
      </div>
    `;
    return;
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api/scrape`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const product = await res.json();

    if (product.error) {
      throw new Error(product.error);
    }

    currentProduct = product;
    renderProductCard(product);

    if (product.scrape_ok) {
      addMessage("system", "Ask anything about this product \u2014 price, specs, whether it's worth it.");
      setComposerEnabled(true);
    } else {
      addMessage(
        "system",
        "This page loaded but key fields weren't found (Amazon may have changed layout or shown a CAPTCHA). Try a different product page."
      );
    }
  } catch (err) {
    productCard.className = "product-card";
    productCard.innerHTML = `
      <div class="product-card__title">Couldn't reach the backend</div>
      <div class="product-card__meta">
        <span class="chip chip--error">Is the local server running on port 5000?</span>
      </div>
    `;
    addMessage("system", `Error: ${err.message}`);
  }
}

async function sendQuestion() {
  const question = input.value.trim();
  if (!question || !currentProduct) return;

  addMessage("user", question);
  input.value = "";
  setComposerEnabled(false);

  const typingEl = addTypingIndicator();

  try {
    const res = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product: currentProduct, question, history }),
    });
    const data = await res.json();
    typingEl.remove();

    if (data.error) throw new Error(data.error);

    addMessage("assistant", data.answer);
    history.push({ role: "user", content: question });
    history.push({ role: "assistant", content: data.answer });
  } catch (err) {
    typingEl.remove();
    addMessage("system", `Error: ${err.message}`);
  } finally {
    setComposerEnabled(true);
    input.focus();
  }
}

sendBtn.addEventListener("click", sendQuestion);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendQuestion();
});
rescanBtn.addEventListener("click", scrapeCurrentPage);

document.addEventListener("DOMContentLoaded", scrapeCurrentPage);
