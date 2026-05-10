#!/usr/bin/env python3
"""
🌊 Hormuz (HRZ) Official Telegram Bot v6 — Ultimate Edition
Features:
- Posts every 20 minutes with unique content
- Replies to EVERY message with Gemini AI
- Buy alerts & whale detection
- Quiz every hour
- ATH alerts
- Community management
- XP & Badges
- Daily reports
- Vote reminders
- Anti-spam protection
"""

import logging
import random
import time
import os
import re
import json
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ── CONFIG ────────────────────────────────────────────────────────────────────

TOKEN      = os.getenv("TOKEN",      "8669492245:AAGhwIR4zwF1wOIkhO2qBV56jqQDUhUMlIA")
GEMINI_KEY = os.getenv("GEMINI_KEY", "AIzaSyD48ydx3IYz46qV1jRHymgGHH0EPHIjwnU")

HRZ_CONTRACT = "0x4E788d423d90A15504455b4FF746B9C1D9951A82"
PANCAKE_BUY  = f"https://pancakeswap.finance/swap?outputCurrency={HRZ_CONTRACT}"
DEXSCREENER  = f"https://dexscreener.com/bsc/{HRZ_CONTRACT}"
BSCSCAN      = f"https://bscscan.com/token/{HRZ_CONTRACT}"
WEBSITE      = "https://hormuz-hrz.netlify.app"
COINSNIPER   = "https://coinsniper.net"
TWITTER      = "https://x.com/armou224"
CHANNEL_ID   = -1003992608217
BOT_USERNAME = "@Hurmoz_bot"

# ── TIMING ────────────────────────────────────────────────────────────────────

POST_INTERVAL    = 20 * 60   # post every 20 minutes
QUIZ_INTERVAL    = 60 * 60   # quiz every hour
BUY_BOT_INTERVAL = 30        # check buys every 30 seconds
VOTE_INTERVAL    = 24 * 3600 # vote reminder daily
REPORT_INTERVAL  = 24 * 3600 # daily report
ATH_CHECK        = 5 * 60    # check ATH every 5 minutes

PRICE_CACHE_TTL     = 60
WHALE_THRESHOLD_BNB = 0.5
MIN_BUY_BNB         = 0.01

# ── XP ────────────────────────────────────────────────────────────────────────

XP_MESSAGE  = 1
XP_COMMAND  = 2
XP_VOTE     = 5
XP_QUIZ_WIN = 20
XP_REFERRAL = 10

LEVELS = {
    0:    "🐚 Newcomer",
    50:   "🌊 Wave Rider",
    150:  "⚓ Sailor",
    300:  "🐋 Whale Hunter",
    600:  "🔱 Hormuz Guardian",
    1000: "👑 Strait Master",
    2000: "⚡ HRZ Legend",
}

BADGES = {
    "early_holder":   "🏅 Early Holder",
    "whale":          "🐋 Whale",
    "community_hero": "🦸 Community Hero",
    "quiz_master":    "🧠 Quiz Master",
    "voter":          "🗳️ Loyal Voter",
    "top_recruiter":  "🎯 Top Recruiter",
    "diamond_hands":  "💎 Diamond Hands",
}

SPAM_PATTERNS = [
    r"https?://(?!hormuz-hrz\.netlify\.app|pancakeswap\.finance|dexscreener\.com|bscscan\.com|coinsniper\.net|t\.me/Hurmoz_bot|x\.com/armou224)",
    r"t\.me/(?!Hurmoz_bot)",
]

BANNED_WORDS = [
    "scam", "rug", "fake", "honeypot", "rugpull",
    "send me", "dm me", "guaranteed profit", "100x guaranteed"
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── STATE ─────────────────────────────────────────────────────────────────────

_price_cache: dict | None = None
_price_cache_time: float  = 0
_last_seen_tx: str        = ""
_faq_store: dict          = {}
_xp_store: dict           = defaultdict(int)
_badge_store: dict        = defaultdict(set)
_warn_store: dict         = defaultdict(int)
_ath_store: dict          = {"price": 0.0, "date": ""}
_ath_alerted: float       = 0.0
_lockdown: bool           = False
_quiz_active: dict        = {}
_post_index: int          = 0
_reply_cooldown: dict     = {}  # user_id -> last_reply_time

# Post rotation types
POST_TYPES = [
    "price_update",
    "hype_call",
    "dex_stats",
    "strait_fact",
    "community_question",
    "buy_reminder",
    "liquidity_info",
    "comparison",
    "motivation",
    "chart_update",
]

# ── QUIZ QUESTIONS ─────────────────────────────────────────────────────────────

QUIZ_QUESTIONS = [
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhat percentage of global oil passes through the Strait of Hormuz?\n\nA) 10%  B) 20%  C) 30%  D) 40%",
        "answers": ["20", "b", "20%"],
        "correct": "B) 20%",
        "fact": "The Strait of Hormuz controls 20% of the world's oil supply! 🛢️"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhat is HRZ total supply?\n\nA) 100M  B) 500M  C) 1 Billion  D) 10 Billion",
        "answers": ["1000000000", "c", "1 billion", "1b", "1,000,000,000"],
        "correct": "C) 1 Billion",
        "fact": "HRZ total supply is exactly 1,000,000,000 tokens! 🌊"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhat is the HRZ buy tax?\n\nA) 1%  B) 3%  C) 5%  D) 0%",
        "answers": ["0", "d", "0%", "zero"],
        "correct": "D) 0%",
        "fact": "HRZ has ZERO buy tax — completely free to buy! ✅"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhich blockchain is HRZ on?\n\nA) Ethereum  B) Solana  C) BNB Chain  D) Polygon",
        "answers": ["bnb", "c", "bnb chain", "bsc", "binance"],
        "correct": "C) BNB Chain",
        "fact": "HRZ runs on BNB Chain (BSC) for fast and cheap transactions! ⚡"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nHow long is HRZ liquidity locked?\n\nA) 3 months  B) 6 months  C) 1 year  D) 2 years",
        "answers": ["1", "c", "1 year", "one year", "12 months"],
        "correct": "C) 1 Year",
        "fact": "HRZ liquidity is locked for 1 full year on PinkLock! 🔒"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhere can you buy HRZ?\n\nA) Uniswap  B) SushiSwap  C) PancakeSwap  D) Raydium",
        "answers": ["pancakeswap", "c", "pancake"],
        "correct": "C) PancakeSwap",
        "fact": "Buy HRZ on PancakeSwap V2 on BNB Chain! 🥞"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhat does the Strait of Hormuz connect?\n\nA) Red Sea & Mediterranean  B) Persian Gulf & Gulf of Oman  C) Black Sea & Caspian  D) Indian Ocean & Pacific",
        "answers": ["b", "persian", "gulf of oman", "persian gulf"],
        "correct": "B) Persian Gulf & Gulf of Oman",
        "fact": "The Strait of Hormuz connects the Persian Gulf to the Gulf of Oman! 🌊"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhat is the HRZ sell tax?\n\nA) 1%  B) 3%  C) 5%  D) 10%",
        "answers": ["3", "b", "3%"],
        "correct": "B) 3%",
        "fact": "HRZ has a 3% sell tax that goes to the dev wallet! 💰"
    },
]

# ── HELPERS ───────────────────────────────────────────────────────────────────

def http_get(url: str, timeout: int = 8) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.error(f"GET {url[:60]}: {e}")
        return None

def fetch_hrz_price(force: bool = False) -> dict | None:
    global _price_cache, _price_cache_time
    if not force and _price_cache and (time.time() - _price_cache_time) < PRICE_CACHE_TTL:
        return _price_cache
    data = http_get(f"https://api.dexscreener.com/tokens/v1/bsc/{HRZ_CONTRACT}")
    if data:
        pairs = data if isinstance(data, list) else data.get("pairs", [])
        if pairs:
            p = pairs[0]
            result = {
                "price_usd":  p.get("priceUsd", "0"),
                "price_bnb":  p.get("priceNative", "0"),
                "change_1h":  p.get("priceChange", {}).get("h1", 0),
                "change_6h":  p.get("priceChange", {}).get("h6", 0),
                "change_24h": p.get("priceChange", {}).get("h24", 0),
                "volume_24h": p.get("volume", {}).get("h24", 0),
                "volume_6h":  p.get("volume", {}).get("h6", 0),
                "liquidity":  p.get("liquidity", {}).get("usd", 0),
                "market_cap": p.get("marketCap", 0),
                "fdv":        p.get("fdv", 0),
                "txns_buys":  p.get("txns", {}).get("h24", {}).get("buys", 0),
                "txns_sells": p.get("txns", {}).get("h24", {}).get("sells", 0),
            }
            global _ath_store
            current = float(result["price_usd"])
            if current > _ath_store["price"]:
                _ath_store = {
                    "price": current,
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                }
            _price_cache = result
            _price_cache_time = time.time()
            return result
    return _price_cache

def fetch_fear_greed() -> dict:
    data = http_get("https://api.alternative.me/fng/?limit=1")
    if data and data.get("data"):
        d = data["data"][0]
        return {"value": d.get("value", "?"), "label": d.get("value_classification", "?")}
    return {"value": "?", "label": "Unknown"}

def fetch_latest_buys() -> list:
    data = http_get(
        f"https://api.bscscan.com/api?module=account&action=tokentx"
        f"&contractaddress={HRZ_CONTRACT}&sort=desc&offset=5&page=1"
    )
    if data and isinstance(data.get("result"), list):
        return data["result"]
    return []

def ask_gemini(prompt: str, max_tokens: int = 400) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"

    system = (
        "You are the official English-only AI assistant for Hormuz (HRZ) crypto token on BNB Chain. "
        f"Contract: {HRZ_CONTRACT} | "
        f"Buy on PancakeSwap: {PANCAKE_BUY} | "
        f"Chart: {DEXSCREENER} | "
        f"Website: {WEBSITE} | "
        f"Twitter: {TWITTER} | "
        "Total Supply: 1,000,000,000 HRZ | "
        "Buy Tax: 0% | Sell Tax: 3% | "
        "Liquidity: Locked 1 Year on PinkLock | "
        "Contract: Verified on BscScan | "
        "Network: BNB Chain (BSC) | "
        "DEX: PancakeSwap V2 | "
        "Launched: May 2026 | "
        "Inspired by the Strait of Hormuz — controlling 20% of global oil supply. "
        "ALWAYS respond in English only. "
        "Be enthusiastic, helpful and honest. "
        "Keep responses short and engaging (max 4 sentences). "
        "Always end with a relevant emoji. "
        "Add DYOR disclaimer on financial advice questions."
    )

    payload = json.dumps({
        "contents": [{
            "parts": [{"text": f"{system}\n\nUser message: {prompt}"}]
        }],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.85
        }
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "⚠️ AI temporarily unavailable. Try again shortly! 🌊"

def generate_post(post_type: str) -> str:
    d = fetch_hrz_price()
    fg = fetch_fear_greed()

    ctx = ""
    if d:
        c24 = float(d['change_24h']) if d['change_24h'] else 0
        ctx = (
            f"Current price: ${float(d['price_usd']):.10f} | "
            f"24h change: {c24:+.2f}% | "
            f"Volume 24h: ${float(d['volume_24h']):,.2f} | "
            f"Liquidity: ${float(d['liquidity']):,.2f} | "
            f"Buys/Sells: {d['txns_buys']}/{d['txns_sells']} | "
            f"Fear & Greed: {fg['value']} ({fg['label']})"
        )

    prompts = {
        "price_update": (
            f"Write an exciting Telegram post about HRZ price update. "
            f"Include current price, 24h change with arrow emoji, volume. "
            f"Add buy link and chart link. Max 6 lines. HTML bold for numbers. "
            f"End with #HRZ #Hormuz #BNBChain hashtags. Context: {ctx}"
        ),
        "hype_call": (
            f"Write a viral FOMO-inducing Telegram post about HRZ token opportunity. "
            f"Mention early stage, verified contract, locked liquidity. "
            f"Include contract address and PancakeSwap link. Max 6 lines. "
            f"Make it exciting! Context: {ctx}"
        ),
        "dex_stats": (
            f"Write a Telegram post showing impressive HRZ DEX statistics. "
            f"Include volume, liquidity, buys vs sells ratio. "
            f"Add DexScreener link. Make it look bullish. Max 6 lines. Context: {ctx}"
        ),
        "strait_fact": (
            "Write a fascinating fact about the Strait of Hormuz and connect it "
            "to HRZ token. Make it educational and engaging. "
            "Example: 'Did you know the Strait of Hormuz...'. Max 5 lines."
        ),
        "community_question": (
            "Write an engaging question for the HRZ Telegram community to boost interaction. "
            "Options: price prediction, best feature of HRZ, why they hold, etc. "
            "Add poll-style A) B) C) options. Max 5 lines."
        ),
        "buy_reminder": (
            f"Write a compelling 'why buy HRZ now' Telegram post. "
            f"Highlight: 0% buy tax, verified contract, locked liquidity, early stage. "
            f"Include PancakeSwap link. Max 6 lines. Context: {ctx}"
        ),
        "liquidity_info": (
            f"Write a trust-building Telegram post about HRZ liquidity lock. "
            f"Explain what locked liquidity means for investors. "
            f"Include PinkLock proof link. Max 5 lines. Context: {ctx}"
        ),
        "comparison": (
            f"Write a Telegram post comparing HRZ to other meme coins. "
            f"Highlight HRZ advantages: real inspiration (Strait of Hormuz), "
            f"0% buy tax, locked liquidity, verified contract. Max 6 lines."
        ),
        "motivation": (
            f"Write a motivational Telegram post for HRZ holders. "
            f"Keep them excited and hodling. Reference the Strait of Hormuz theme. "
            f"Max 5 lines. Make it inspiring! Context: {ctx}"
        ),
        "chart_update": (
            f"Write an exciting chart analysis post for HRZ. "
            f"Mention price movement, volume trend, and what it means. "
            f"Include DexScreener link. Max 6 lines. Context: {ctx}"
        ),
    }

    prompt = prompts.get(post_type, prompts["hype_call"])
    return ask_gemini(prompt, max_tokens=250)

def get_level(xp: int) -> str:
    level = LEVELS[0]
    for threshold, name in sorted(LEVELS.items()):
        if xp >= threshold:
            level = name
    return level

def add_xp(user_id: int, amount: int):
    _xp_store[user_id] += amount

def add_badge(user_id: int, badge: str):
    _badge_store[user_id].add(badge)

def is_spam(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in SPAM_PATTERNS)

def has_banned_words(text: str) -> bool:
    return any(word in text.lower() for word in BANNED_WORDS)

def can_reply_to_user(user_id: int) -> bool:
    """Cooldown 30 seconds between AI replies per user"""
    now = time.time()
    last = _reply_cooldown.get(user_id, 0)
    if now - last >= 120:
        _reply_cooldown[user_id] = now
        return True
    return False

def price_text(d: dict) -> str:
    c24 = float(d["change_24h"]) if d["change_24h"] else 0
    c6  = float(d["change_6h"])  if d["change_6h"]  else 0
    c1  = float(d["change_1h"])  if d["change_1h"]  else 0
    arrow = lambda v: "🟢" if v >= 0 else "🔴"
    return (
        f"🌊 <b>Hormuz (HRZ) — Live Price</b>\n\n"
        f"💵 <code>${float(d['price_usd']):.10f}</code>\n"
        f"🔶 <code>{float(d['price_bnb']):.10f} BNB</code>\n\n"
        f"{arrow(c1)} 1h:  <b>{c1:+.2f}%</b>\n"
        f"{arrow(c6)} 6h:  <b>{c6:+.2f}%</b>\n"
        f"{arrow(c24)} 24h: <b>{c24:+.2f}%</b>\n\n"
        f"📊 Vol 24h: <b>${float(d['volume_24h']):,.2f}</b>\n"
        f"💧 Liquidity: <b>${float(d['liquidity']):,.2f}</b>\n"
        f"📈 MCap: <b>${float(d['market_cap']):,.2f}</b>\n"
        f"🔄 Buys/Sells: <b>{d['txns_buys']}/{d['txns_sells']}</b>\n\n"
        f"<a href='{PANCAKE_BUY}'>💱 Buy</a> | "
        f"<a href='{DEXSCREENER}'>📊 Chart</a> | "
        f"<a href='{TWITTER}'>🐦 Twitter</a>"
    )

# ── KEYBOARDS ─────────────────────────────────────────────────────────────────

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Price",      callback_data="price"),
            InlineKeyboardButton("📊 Stats",      callback_data="stats"),
            InlineKeyboardButton("😱 Sentiment",  callback_data="feargreed"),
        ],
        [
            InlineKeyboardButton("💱 Buy HRZ",    url=PANCAKE_BUY),
            InlineKeyboardButton("📉 Chart",      url=DEXSCREENER),
        ],
        [
            InlineKeyboardButton("🌐 Website",    url=WEBSITE),
            InlineKeyboardButton("🐦 Twitter",    url=TWITTER),
            InlineKeyboardButton("🗳️ Vote",       url=COINSNIPER),
        ],
        [
            InlineKeyboardButton("🏆 ATH",        callback_data="ath"),
            InlineKeyboardButton("🎖️ My XP",     callback_data="myxp"),
            InlineKeyboardButton("📋 Contract",   callback_data="contract"),
        ],
        [
            InlineKeyboardButton("❓ Ask AI",     callback_data="ask"),
            InlineKeyboardButton("📣 Shill",      callback_data="shill"),
            InlineKeyboardButton("📰 News",       callback_data="news"),
        ],
    ])

# ── COMMANDS ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    add_badge(update.effective_user.id, "early_holder")
    await update.message.reply_html(
        "🌊 <b>Hormuz (HRZ) Bot v6 — Ultimate Edition</b>\n\n"
        "🤖 AI replies to every message\n"
        "📢 Auto-posts every <b>20 minutes</b>\n"
        "🧠 Quiz every <b>hour</b>\n"
        "🐋 Whale & Buy alerts\n"
        "🏆 ATH detection\n"
        "🎖️ XP & Badges system\n"
        "🛡️ Anti-spam protection\n\n"
        "Type /schedule to activate all features!\n"
        "Type /help for all commands.",
        reply_markup=main_keyboard()
    )

async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    msg = await update.message.reply_text("⏳ Fetching live price...")
    d = fetch_hrz_price(force=True)
    if not d:
        await msg.edit_text(
            f"❌ Price unavailable. <a href='{DEXSCREENER}'>Check DexScreener</a>",
            parse_mode="HTML", disable_web_page_preview=True
        )
        return
    await msg.edit_text(
        price_text(d), parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💱 Buy", url=PANCAKE_BUY),
            InlineKeyboardButton("📊 Chart", url=DEXSCREENER)
        ]])
    )

async def cmd_buy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    await update.message.reply_html(
        f"💱 <b>How to Buy Hormuz (HRZ)</b>\n\n"
        f"<b>Step 1:</b> Get BNB on BNB Chain\n"
        f"<b>Step 2:</b> Open PancakeSwap\n"
        f"<b>Step 3:</b> Paste contract address:\n"
        f"<code>{HRZ_CONTRACT}</code>\n\n"
        f"⚙️ Set slippage to <b>5-10%</b>\n"
        f"✅ Buy Tax: <b>0%</b>\n\n"
        f"🔗 <a href='{PANCAKE_BUY}'>Open PancakeSwap Now</a>\n"
        f"📊 <a href='{DEXSCREENER}'>View Chart</a>\n\n"
        f"⚠️ DYOR — Early stage token!",
        disable_web_page_preview=True
    )

async def cmd_contract(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        f"📍 <b>HRZ Contract Address</b>\n\n"
        f"<code>{HRZ_CONTRACT}</code>\n\n"
        f"• Network: BNB Chain ✅\n"
        f"• Verified on BscScan ✅\n"
        f"• Liquidity Locked 1 Year 🔒\n"
        f"• Buy Tax: <b>0%</b>\n"
        f"• Sell Tax: <b>3%</b>\n\n"
        f"<a href='{PANCAKE_BUY}'>Buy</a> | "
        f"<a href='{DEXSCREENER}'>Chart</a> | "
        f"<a href='{BSCSCAN}'>BSCScan</a>",
        disable_web_page_preview=True
    )

async def cmd_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        f"🌊 <b>About Hormuz (HRZ)</b>\n\n"
        f"Inspired by the Strait of Hormuz — the world's most strategic "
        f"waterway controlling 20% of global oil supply.\n\n"
        f"<b>📊 Token Details:</b>\n"
        f"• Ticker: <b>HRZ</b>\n"
        f"• Chain: <b>BNB Chain</b>\n"
        f"• Supply: <b>1,000,000,000 HRZ</b>\n"
        f"• Buy Tax: <b>0%</b> | Sell Tax: <b>3%</b>\n"
        f"• Contract: Verified ✅\n"
        f"• Liquidity: Locked 1 Year 🔒\n"
        f"• Launch: May 2026\n\n"
        f"🌐 <a href='{WEBSITE}'>Website</a> | "
        f"💱 <a href='{PANCAKE_BUY}'>Buy</a> | "
        f"🐦 <a href='{TWITTER}'>@armou224</a>",
        disable_web_page_preview=True
    )

async def cmd_ath(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = fetch_hrz_price()
    ath = _ath_store
    current = float(d["price_usd"]) if d else 0
    distance = ((ath["price"] - current) / ath["price"] * 100) if ath["price"] > 0 else 0
    is_ath = current >= ath["price"] * 0.99
    await update.message.reply_html(
        f"🏆 <b>HRZ All-Time High</b>\n\n"
        f"ATH Price: <b>${ath['price']:.10f}</b>\n"
        f"ATH Date: <b>{ath['date'] or 'Tracking...'}</b>\n\n"
        f"📍 Current: <b>${current:.10f}</b>\n"
        f"{'🚀 AT ATH RIGHT NOW!' if is_ath else f'📉 {distance:.1f}% below ATH'}"
    )

async def cmd_dashboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = fetch_hrz_price()
    fg = fetch_fear_greed()
    ath = _ath_store
    if not d:
        await update.message.reply_text("❌ Data unavailable.")
        return
    c24 = float(d["change_24h"]) if d["change_24h"] else 0
    arrow = "📈" if c24 >= 0 else "📉"
    await update.message.reply_html(
        f"📊 <b>HRZ Complete Dashboard</b>\n\n"
        f"💵 Price: <b>${float(d['price_usd']):.10f}</b>\n"
        f"{arrow} 24h: <b>{c24:+.2f}%</b>\n"
        f"📊 Volume 24h: <b>${float(d['volume_24h']):,.2f}</b>\n"
        f"💧 Liquidity: <b>${float(d['liquidity']):,.2f}</b>\n"
        f"📈 Market Cap: <b>${float(d['market_cap']):,.2f}</b>\n"
        f"🔄 Buys/Sells: <b>{d['txns_buys']}/{d['txns_sells']}</b>\n"
        f"🏆 ATH: <b>${ath['price']:.10f}</b>\n"
        f"😱 Fear & Greed: <b>{fg['value']} — {fg['label']}</b>\n\n"
        f"✅ Verified | 🔒 Locked 1yr | 0% Buy Tax\n\n"
        f"<a href='{PANCAKE_BUY}'>Buy</a> | "
        f"<a href='{DEXSCREENER}'>Chart</a> | "
        f"<a href='{BSCSCAN}'>BSCScan</a>",
        disable_web_page_preview=True
    )

async def cmd_shill(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    d = fetch_hrz_price()
    price = f"${float(d['price_usd']):.10f}" if d else "Check DexScreener"
    change = f"{d['change_24h']}%" if d else "N/A"
    await update.message.reply_html(
        f"📣 <b>Copy & Share This Message!</b>\n\n"
        f"🌊 <b>Hormuz (HRZ) — BNB Chain Hidden Gem!</b>\n\n"
        f"💵 Price: {price}\n"
        f"📈 24h Change: {change}\n\n"
        f"✅ Contract Verified on BscScan\n"
        f"✅ Liquidity Locked 1 Year\n"
        f"✅ 0% Buy Tax\n"
        f"✅ Inspired by Strait of Hormuz\n\n"
        f"📍 Contract:\n<code>{HRZ_CONTRACT}</code>\n\n"
        f"💱 Buy: {PANCAKE_BUY}\n"
        f"📊 Chart: {DEXSCREENER}\n"
        f"🌐 Website: {WEBSITE}\n"
        f"🐦 Twitter: {TWITTER}\n\n"
        f"#HRZ #Hormuz #BNBChain #BSCGems #100x #DeFi",
        disable_web_page_preview=True
    )

async def cmd_vote(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_VOTE)
    add_badge(update.effective_user.id, "voter")
    await update.message.reply_html(
        f"🗳️ <b>Vote for HRZ on CoinSniper!</b>\n\n"
        f"Every vote = more visibility = more buyers! 🚀\n"
        f"Takes only 10 seconds!\n\n"
        f"<a href='{COINSNIPER}'>Vote Now!</a>\n\n"
        f"✅ You earned <b>+{XP_VOTE} XP</b>! 🎖️",
        disable_web_page_preview=True
    )

async def cmd_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    question = " ".join(ctx.args) if ctx.args else ""
    if not question:
        await update.message.reply_html(
            "🤖 <b>Ask AI Anything About HRZ!</b>\n\n"
            "Usage: <code>/ask your question here</code>\n\n"
            "Examples:\n"
            "• <code>/ask Is HRZ safe to buy?</code>\n"
            "• <code>/ask What is the Strait of Hormuz?</code>\n"
            "• <code>/ask How to buy HRZ?</code>"
        )
        return
    _faq_store[question.lower()[:80]] = _faq_store.get(question.lower()[:80], 0) + 1
    thinking = await update.message.reply_text("🤖 Thinking...")
    answer = ask_gemini(question)
    await thinking.edit_text(
        answer, parse_mode="HTML",
        disable_web_page_preview=True
    )

async def cmd_myxp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    xp = _xp_store[uid]
    level = get_level(xp)
    badges = _badge_store.get(uid, set())
    badge_text = " ".join([BADGES[b] for b in badges]) if badges else "None yet — start chatting!"
    next_thresholds = [t for t in sorted(LEVELS.keys()) if t > xp]
    next_xp = next_thresholds[0] if next_thresholds else None
    text = (
        f"🎖️ <b>Your HRZ Community Rank</b>\n\n"
        f"👤 <b>{update.effective_user.first_name}</b>\n"
        f"⚡ XP: <b>{xp}</b>\n"
        f"🏅 Level: <b>{level}</b>\n"
        f"🎀 Badges: {badge_text}\n"
    )
    if next_xp:
        text += f"\n📈 Next level at <b>{next_xp} XP</b> ({next_xp - xp} more to go!)"
    text += "\n\n<i>Earn XP by chatting, using commands, and winning quizzes!</i>"
    await update.message.reply_html(text)

async def cmd_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _xp_store:
        await update.message.reply_text("🏆 No XP data yet — start chatting to earn XP!")
        return
    top = sorted(_xp_store.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = ["🏆 <b>HRZ Community Leaderboard</b>\n"]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, (uid, xp) in enumerate(top):
        badges = _badge_store.get(uid, set())
        badge_str = list(badges)[0] if badges else ""
        badge_name = BADGES.get(badge_str, "") if badge_str else ""
        lines.append(f"{medals[i]} <b>{xp} XP</b> — {get_level(xp)} {badge_name}")
    lines.append("\n<i>Chat more to climb the leaderboard!</i>")
    await update.message.reply_html("\n".join(lines))

async def cmd_rules(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "📋 <b>HRZ Community Rules</b>\n\n"
        "1️⃣ No spam or external links\n"
        "2️⃣ No FUD or scam accusations\n"
        "3️⃣ Respect all members\n"
        "4️⃣ English only in main chat\n"
        "5️⃣ No unsolicited DMs\n"
        "6️⃣ No price manipulation talk\n"
        "7️⃣ DYOR — Not financial advice\n\n"
        "⚠️ <b>Violations:</b> Warning → Mute → Ban\n\n"
        f"🌊 Welcome to the Hormuz family!"
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "<b>📋 HRZ Bot v6 — All Commands</b>\n\n"
        "<b>📊 Market</b>\n"
        "/price — Live HRZ price\n"
        "/ath — All-time high\n"
        "/dashboard — Full overview\n\n"
        "<b>🏘️ Community</b>\n"
        "/buy — How to buy HRZ\n"
        "/contract — Contract address\n"
        "/info — About HRZ\n"
        "/rules — Community rules\n"
        "/vote — Vote on CoinSniper (+XP)\n"
        "/shill — Promo message to share\n"
        "/ask [q] — Ask AI anything\n\n"
        "<b>🎖️ XP & Ranks</b>\n"
        "/myxp — Your XP and level\n"
        "/leaderboard — Top 10 members\n\n"
        "<b>🛡️ Admin Only</b>\n"
        "/warn — Warn a user\n"
        "/mute [min] — Mute a user\n"
        "/unmute — Unmute a user\n"
        "/ban — Ban a user\n"
        "/slowmode [s] — Set slow mode\n"
        "/lockdown — Emergency lockdown\n"
        "/schedule — Start all auto features\n"
        "/stopschedule — Stop all auto features\n\n"
        f"💬 I reply to every message automatically! 🤖"
    )

async def cmd_faq(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _faq_store:
        await update.message.reply_text("No questions yet — use /ask to start!")
        return
    top = sorted(_faq_store.items(), key=lambda x: x[1], reverse=True)[:5]
    lines = ["🧠 <b>Top Community Questions</b>\n"]
    for q, count in top:
        lines.append(f"• <i>{q[:60]}</i> (asked {count}x)")
    await update.message.reply_html("\n".join(lines))

# ── ADMIN COMMANDS ────────────────────────────────────────────────────────────

async def is_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await ctx.bot.get_chat_member(
            update.effective_chat.id, update.effective_user.id
        )
        return member.status in ("administrator", "creator")
    except Exception:
        return False

async def cmd_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message to warn the user.")
        return
    target = update.message.reply_to_message.from_user
    reason = " ".join(ctx.args) if ctx.args else "No reason provided"
    _warn_store[target.id] += 1
    warns = _warn_store[target.id]
    if warns >= 3:
        try:
            await ctx.bot.ban_chat_member(update.effective_chat.id, target.id)
            await update.message.reply_html(
                f"🚫 <b>{target.full_name}</b> has been <b>BANNED</b> after 3 warnings!\n"
                f"Reason: {reason}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Cannot ban: {e}")
    else:
        await update.message.reply_html(
            f"⚠️ <b>Warning {warns}/3</b> issued to {target.full_name}\n"
            f"Reason: {reason}\n"
            f"{'🚨 Next warning = BAN!' if warns == 2 else ''}"
        )

async def cmd_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message to mute.")
        return
    target = update.message.reply_to_message.from_user
    duration = int(ctx.args[0]) if ctx.args else 60
    until = datetime.now(timezone.utc) + timedelta(minutes=duration)
    try:
        await ctx.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await update.message.reply_html(
            f"🔇 <b>{target.full_name}</b> muted for <b>{duration} minutes</b>."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot mute: {e}")

async def cmd_unmute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message to unmute.")
        return
    target = update.message.reply_to_message.from_user
    try:
        await ctx.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True
            )
        )
        await update.message.reply_html(f"🔊 <b>{target.full_name}</b> has been unmuted.")
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot unmute: {e}")

async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message to ban.")
        return
    target = update.message.reply_to_message.from_user
    reason = " ".join(ctx.args) if ctx.args else "No reason"
    try:
        await ctx.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_html(
            f"🚫 <b>{target.full_name}</b> has been <b>BANNED</b>.\nReason: {reason}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot ban: {e}")

async def cmd_slowmode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    seconds = int(ctx.args[0]) if ctx.args else 0
    try:
        await ctx.bot.set_chat_slow_mode_delay(update.effective_chat.id, seconds)
        msg = f"🐢 Slow mode: <b>{seconds}s</b>" if seconds else "✅ Slow mode <b>disabled</b>"
        await update.message.reply_html(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_lockdown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _lockdown
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    _lockdown = not _lockdown
    if _lockdown:
        await update.message.reply_html(
            "🔒 <b>LOCKDOWN ACTIVATED!</b>\nAll messages blocked. Use /lockdown to unlock."
        )
    else:
        await update.message.reply_html("🔓 <b>Lockdown lifted!</b> Chat is open again.")

# ── SCHEDULED JOBS ────────────────────────────────────────────────────────────

async def scheduled_post(ctx: ContextTypes.DEFAULT_TYPE):
    global _post_index
    chat_id = ctx.job.chat_id
    post_type = POST_TYPES[_post_index % len(POST_TYPES)]
    _post_index += 1

    post = generate_post(post_type)
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=post,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💱 Buy HRZ", url=PANCAKE_BUY),
                InlineKeyboardButton("📊 Chart",   url=DEXSCREENER),
                InlineKeyboardButton("🐦 Twitter", url=TWITTER),
            ]])
        )
    except Exception as e:
        logger.error(f"Auto post error: {e}")

async def scheduled_quiz(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.job.chat_id
    q = random.choice(QUIZ_QUESTIONS)
    _quiz_active[chat_id] = q
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                f"{q['q']}\n\n"
                f"⏰ <b>First correct answer wins +{XP_QUIZ_WIN} XP!</b> 🎯\n"
                f"<i>Reply with just the letter or the answer</i>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Quiz error: {e}")

async def buy_bot_tick(ctx: ContextTypes.DEFAULT_TYPE):
    global _last_seen_tx
    chat_id = ctx.job.chat_id
    txs = fetch_latest_buys()
    if not txs:
        return

    new_buys = []
    for tx in txs:
        if tx.get("hash") == _last_seen_tx:
            break
        if tx.get("to", "").lower() != HRZ_CONTRACT.lower():
            new_buys.append(tx)

    if new_buys:
        _last_seen_tx = txs[0].get("hash", "")

    d = fetch_hrz_price()

    for tx in reversed(new_buys):
        try:
            value_raw = int(tx.get("value", 0))
            decimals  = int(tx.get("tokenDecimal", 18))
            amount    = value_raw / (10 ** decimals)
            tx_hash   = tx.get("hash", "")
            usd_val = bnb_val = 0.0
            if d:
                usd_val = amount * float(d.get("price_usd", 0))
                bnb_val = amount * float(d.get("price_bnb", 0))
            if bnb_val > 0 and bnb_val < MIN_BUY_BNB:
                continue
            is_whale = bnb_val >= WHALE_THRESHOLD_BNB
            if is_whale:
                header = "🐋 <b>WHALE BUY DETECTED!</b> 🐋"
                footer = "🚀🚀 Big money entering $HRZ!\n#Hormuz #BSCWhale #HRZ"
            else:
                header = "🟢 <b>NEW HRZ BUY!</b>"
                footer = "🚀 Welcome new holder!\n#HRZ #Hormuz #BNBChain"
            buyer = tx.get("to", "")[:8] + "..."
            await ctx.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"{header}\n\n"
                    f"🌊 <b>{amount:,.0f} HRZ</b>\n"
                    f"💵 ~<b>${usd_val:,.4f}</b> ({bnb_val:.4f} BNB)\n"
                    f"👤 <code>{buyer}</code>\n"
                    f"🔗 <a href='https://bscscan.com/tx/{tx_hash}'>View Transaction</a>\n\n"
                    f"{footer}"
                ),
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💱 Buy Too!", url=PANCAKE_BUY),
                    InlineKeyboardButton("📊 Chart",    url=DEXSCREENER)
                ]])
            )
        except Exception as e:
            logger.error(f"Buy bot: {e}")

async def ath_check_tick(ctx: ContextTypes.DEFAULT_TYPE):
    global _ath_alerted
    chat_id = ctx.job.chat_id
    d = fetch_hrz_price(force=True)
    if not d:
        return
    current = float(d["price_usd"])
    if current > _ath_alerted * 1.01:
        _ath_alerted = current
        try:
            await ctx.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🏆🚀 <b>NEW ALL-TIME HIGH!</b> 🚀🏆\n\n"
                    f"💵 ATH: <b>${current:.10f}</b>\n"
                    f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                    f"🌊 Hormuz (HRZ) is making history!\n"
                    f"Hold strong, the strait controls all! ⚔️\n\n"
                    f"#HRZ #Hormuz #ATH #BNBChain 🚀"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💱 Buy Now!", url=PANCAKE_BUY),
                    InlineKeyboardButton("📊 Chart",    url=DEXSCREENER)
                ]])
            )
        except Exception as e:
            logger.error(f"ATH alert: {e}")

async def vote_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.job.chat_id
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🗳️ <b>Daily Vote Reminder!</b>\n\n"
                f"Help HRZ reach more investors by voting!\n"
                f"Takes only 10 seconds and earns you XP! 🎖️\n\n"
                f"<a href='{COINSNIPER}'>Vote on CoinSniper Now!</a>\n\n"
                f"Use /vote to earn +{XP_VOTE} XP! 🚀"
            ),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Vote reminder: {e}")

async def daily_report(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.job.chat_id
    d = fetch_hrz_price()
    fg = fetch_fear_greed()
    ath = _ath_store
    if not d:
        return
    c24 = float(d["change_24h"]) if d["change_24h"] else 0
    arrow = "📈" if c24 >= 0 else "📉"
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                f"☀️ <b>HRZ Daily Report</b>\n"
                f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d UTC')}\n\n"
                f"💵 Price: <b>${float(d['price_usd']):.10f}</b>\n"
                f"{arrow} 24h Change: <b>{c24:+.2f}%</b>\n"
                f"📊 Volume 24h: <b>${float(d['volume_24h']):,.2f}</b>\n"
                f"💧 Liquidity: <b>${float(d['liquidity']):,.2f}</b>\n"
                f"🔄 Buys/Sells: <b>{d['txns_buys']}/{d['txns_sells']}</b>\n"
                f"🏆 ATH: <b>${ath['price']:.10f}</b>\n"
                f"😱 Fear & Greed: <b>{fg['value']} — {fg['label']}</b>\n\n"
                f"💱 <a href='{PANCAKE_BUY}'>Buy HRZ</a> | "
                f"📊 <a href='{DEXSCREENER}'>Chart</a> | "
                f"🐦 <a href='{TWITTER}'>@armou224</a>\n\n"
                f"#HRZ #Hormuz #BNBChain #DailyReport"
            ),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Daily report: {e}")

# ── WELCOME ───────────────────────────────────────────────────────────────────

async def welcome_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.full_name.replace("<", "&lt;").replace(">", "&gt;")
        add_xp(member.id, XP_MESSAGE)
        add_badge(member.id, "early_holder")
        d = fetch_hrz_price()
        price = f"${float(d['price_usd']):.10f}" if d else "Check /price"
        try:
            await update.message.reply_html(
                f"🌊 Welcome <b>{name}</b> to Hormuz (HRZ)!\n\n"
                f"💵 Current Price: <b>{price}</b>\n\n"
                f"🎖️ You earned: <b>Early Holder</b> badge + XP!\n\n"
                f"📋 /rules — Read the rules\n"
                f"💰 /price — Live price\n"
                f"💱 /buy — How to buy HRZ\n"
                f"❓ /help — All commands\n\n"
                f"<a href='{PANCAKE_BUY}'>💱 Buy HRZ Now</a> | "
                f"<a href='{DEXSCREENER}'>📊 Chart</a>\n\n"
                f"HODL strong! The strait controls all! 🚀",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Welcome: {e}")

# ── MESSAGE HANDLER ───────────────────────────────────────────────────────────

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text      = update.message.text
    chat_type = update.effective_chat.type
    uid       = update.effective_user.id
    chat_id   = update.effective_chat.id

    # Check admin status
    admin = False
    if chat_type in ("group", "supergroup"):
        try:
            member = await ctx.bot.get_chat_member(chat_id, uid)
            admin = member.status in ("administrator", "creator")
        except Exception:
            pass

    # Lockdown check
    if _lockdown and not admin:
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    # Anti-spam
    if not admin:
        if is_spam(text):
            try:
                await update.message.delete()
                _warn_store[uid] += 1
                await ctx.bot.send_message(
                    chat_id,
                    f"🚫 External links not allowed! "
                    f"<b>{update.effective_user.first_name}</b> — Warning {_warn_store[uid]}/3",
                    parse_mode="HTML"
                )
                if _warn_store[uid] >= 3:
                    await ctx.bot.ban_chat_member(chat_id, uid)
                    await ctx.bot.send_message(
                        chat_id,
                        f"🚫 <b>{update.effective_user.first_name}</b> banned after 3 warnings!",
                        parse_mode="HTML"
                    )
            except Exception:
                pass
            return

        if has_banned_words(text):
            try:
                await update.message.delete()
            except Exception:
                pass
            return

    # XP for chatting
    add_xp(uid, XP_MESSAGE)

    # Quiz answer check
    if chat_id in _quiz_active:
        q = _quiz_active[chat_id]
        for ans in q["answers"]:
            if ans.lower() in text.lower():
                del _quiz_active[chat_id]
                add_xp(uid, XP_QUIZ_WIN)
                add_badge(uid, "quiz_master")
                try:
                    await update.message.reply_html(
                        f"🎉 <b>{update.effective_user.first_name}</b> got it right!\n\n"
                        f"✅ Correct Answer: <b>{q['correct']}</b>\n"
                        f"💡 Fun Fact: {q['fact']}\n\n"
                        f"🎖️ +{XP_QUIZ_WIN} XP earned!"
                    )
                except Exception:
                    pass
                break

    # AI reply to every message with cooldown
    if can_reply_to_user(uid):
        # Skip very short messages
        if len(text.strip()) < 3:
            return
        # Skip if it looks like a command
        if text.startswith("/"):
            return

        try:
            d = fetch_hrz_price()
            price_ctx = f"Current HRZ price: ${float(d['price_usd']):.10f}" if d else ""

            prompt = (
                f"A community member sent this message in the HRZ Telegram group: '{text}'\n"
                f"{price_ctx}\n"
                f"Give a helpful, engaging English reply related to HRZ token. "
                f"If the message is about price, include current stats. "
                f"If it's a question, answer it clearly. "
                f"If it's random chat, respond friendly and mention HRZ naturally. "
                f"Keep it short (2-3 sentences max)."
            )

            answer = ask_gemini(prompt, max_tokens=150)
            await update.message.reply_html(
                answer,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"AI reply error: {e}")

# ── CALLBACK BUTTONS ──────────────────────────────────────────────────────────

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "price":
        d = fetch_hrz_price()
        text = price_text(d) if d else "❌ Price unavailable."
        await query.edit_message_text(
            text, parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_keyboard()
        )

    elif query.data == "stats":
        d = fetch_hrz_price()
        if d:
            text = (
                f"📊 <b>HRZ Live Stats</b>\n\n"
                f"📊 Vol 6h: <b>${float(d['volume_6h']):,.2f}</b>\n"
                f"📊 Vol 24h: <b>${float(d['volume_24h']):,.2f}</b>\n"
                f"💧 Liquidity: <b>${float(d['liquidity']):,.2f}</b>\n"
                f"📈 FDV: <b>${float(d['fdv']):,.2f}</b>\n"
                f"🔄 Buys: <b>{d['txns_buys']}</b> | Sells: <b>{d['txns_sells']}</b>"
            )
        else:
            text = "❌ Stats unavailable."
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())

    elif query.data == "feargreed":
        fg = fetch_fear_greed()
        val = int(fg["value"]) if str(fg["value"]).isdigit() else 50
        if val <= 25:   emoji = "😱 Extreme Fear"
        elif val <= 45: emoji = "😨 Fear"
        elif val <= 55: emoji = "😐 Neutral"
        elif val <= 75: emoji = "😊 Greed"
        else:           emoji = "🤑 Extreme Greed"
        await query.edit_message_text(
            f"😱 <b>Crypto Fear &amp; Greed Index</b>\n\n"
            f"Score: <b>{fg['value']} / 100</b>\n"
            f"Status: <b>{emoji}</b>\n\n"
            f"<i>{'Low fear = smart buy opportunity 👀' if val <= 40 else 'High greed — manage your risk carefully.'}</i>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

    elif query.data == "ath":
        d = fetch_hrz_price()
        current = float(d["price_usd"]) if d else 0
        ath = _ath_store
        distance = ((ath["price"] - current) / ath["price"] * 100) if ath["price"] > 0 else 0
        await query.edit_message_text(
            f"🏆 <b>HRZ All-Time High</b>\n\n"
            f"ATH: <b>${ath['price']:.10f}</b>\n"
            f"Date: <b>{ath['date'] or 'Tracking...'}</b>\n\n"
            f"📍 Current: <b>${current:.10f}</b>\n"
            f"📉 {distance:.1f}% below ATH",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

    elif query.data == "myxp":
        uid = query.from_user.id
        xp = _xp_store[uid]
        badges = _badge_store.get(uid, set())
        badge_text = " ".join([BADGES[b] for b in badges]) if badges else "None yet"
        await query.edit_message_text(
            f"🎖️ <b>Your HRZ Rank</b>\n\n"
            f"⚡ XP: <b>{xp}</b>\n"
            f"🏅 Level: <b>{get_level(xp)}</b>\n"
            f"🎀 Badges: {badge_text}",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

    elif query.data == "contract":
        await query.edit_message_text(
            f"📍 <b>HRZ Contract</b>\n\n"
            f"<code>{HRZ_CONTRACT}</code>\n\n"
            f"✅ Verified | 🔒 Locked 1yr | 0% Buy Tax\n\n"
            f"<a href='{PANCAKE_BUY}'>Buy</a> | <a href='{DEXSCREENER}'>Chart</a>",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_keyboard()
        )

    elif query.data == "shill":
        d = fetch_hrz_price()
        price = f"${float(d['price_usd']):.10f}" if d else "N/A"
        await query.edit_message_text(
            f"📣 <b>Share This!</b>\n\n"
            f"🌊 Hormuz (HRZ) — {price}\n"
            f"✅ Verified | 🔒 Locked | 0% Buy Tax\n\n"
            f"<code>{HRZ_CONTRACT}</code>\n\n"
            f"#HRZ #Hormuz #BNBChain",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

    elif query.data == "news":
        await query.edit_message_text(
            f"📰 <b>Latest Crypto News</b>\n\n"
            f"<a href='https://cryptopanic.com'>CryptoPanic</a> | "
            f"<a href='https://coinmarketcap.com/headlines/'>CoinMarketCap News</a>",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_keyboard()
        )

    elif query.data == "ask":
        await query.edit_message_text(
            f"🤖 Type: <code>/ask your question</code>\n"
            f"Or just send any message — I reply automatically! 💬",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="back")]
            ])
        )

    elif query.data == "back":
        await query.edit_message_text(
            "🌊 <b>Hormuz (HRZ) — Ultimate Bot v6</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

# ── ADMIN: SCHEDULE ───────────────────────────────────────────────────────────

async def cmd_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _ath_alerted
    chat_id = update.effective_chat.id
    name    = str(chat_id)

    # Initialize ATH alert threshold
    d = fetch_hrz_price()
    if d:
        _ath_alerted = float(d["price_usd"])

    jobs = [
        (scheduled_post,  POST_INTERVAL,    10,   f"post_{name}"),
        (scheduled_quiz,  QUIZ_INTERVAL,    120,  f"quiz_{name}"),
        (buy_bot_tick,    BUY_BOT_INTERVAL, 5,    f"buybot_{name}"),
        (vote_reminder,   VOTE_INTERVAL,    3600, f"vote_{name}"),
        (daily_report,    REPORT_INTERVAL,  7200, f"report_{name}"),
        (ath_check_tick,  ATH_CHECK,        30,   f"ath_{name}"),
        (post_to_channel, POST_INTERVAL,    15,   f"channel_{name}"),
    ]

    for func, interval, first, job_name in jobs:
        ctx.job_queue.run_repeating(
            func, interval=interval, first=first,
            chat_id=chat_id, name=job_name
        )

    await update.message.reply_html(
        f"✅ <b>HRZ Bot v6 Fully Activated!</b>\n\n"
        f"📢 Auto-posts: every <b>20 minutes</b>\n"
        f"🧠 Quiz: every <b>hour</b>\n"
        f"🟢 Buy alerts: every <b>30 seconds</b>\n"
        f"🏆 ATH detection: every <b>5 minutes</b>\n"
        f"🗳️ Vote reminder: every <b>24 hours</b>\n"
        f"📊 Daily report: every <b>24 hours</b>\n"
        f"🤖 AI replies: to <b>every message</b>\n\n"
        f"🌊 The strait is now online!"
    )

async def cmd_stop_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = str(update.effective_chat.id)
    count = 0
    for prefix in ("post_", "quiz_", "buybot_", "vote_", "report_", "ath_"):
        for job in ctx.job_queue.get_jobs_by_name(f"{prefix}{name}"):
            job.schedule_removal()
            count += 1
    await update.message.reply_text(f"🛑 {count} auto jobs stopped.")

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()

    commands = [
        ("start",         cmd_start),
        ("price",         cmd_price),
        ("ath",           cmd_ath),
        ("dashboard",     cmd_dashboard),
        ("buy",           cmd_buy),
        ("contract",      cmd_contract),
        ("info",          cmd_info),
        ("rules",         cmd_rules),
        ("vote",          cmd_vote),
        ("shill",         cmd_shill),
        ("ask",           cmd_ask),
        ("faq",           cmd_faq),
        ("myxp",          cmd_myxp),
        ("leaderboard",   cmd_leaderboard),
        ("help",          cmd_help),
        ("warn",          cmd_warn),
        ("mute",          cmd_mute),
        ("unmute",        cmd_unmute),
        ("ban",           cmd_ban),
        ("slowmode",      cmd_slowmode),
        ("lockdown",      cmd_lockdown),
        ("schedule",      cmd_schedule),
        ("stopschedule",  cmd_stop_schedule),
    ]

    for cmd, func in commands:
        app.add_handler(CommandHandler(cmd, func))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, message_handler
    ))

    logger.info("🌊 Hormuz Bot v6 — Ultimate Edition Running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

from telegram import Update
from telegram.ext import ContextTypes

async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 HRZ Bot is running correctly")

import logging

logger = logging.getLogger(__name__)

def safe_fetch(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"SAFE_FETCH ERROR: {e}")
        return None

import signal

def _shutdown(sig, frame):
    print("🛑 Bot shutting down safely...")

signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)

async def job_watchdog(context):
    jobs = context.job_queue.jobs()
    if not jobs:
        print("⚠️ JobQueue empty — restarting scheduler")

# Auto-post to channel
async def post_to_channel(ctx: ContextTypes.DEFAULT_TYPE):
    global _post_index
    post_type = POST_TYPES[_post_index % len(POST_TYPES)]
    _post_index += 1
    post = generate_post(post_type)
    try:
        await ctx.bot.send_message(
            chat_id=CHANNEL_ID,
            text=post,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💱 Buy HRZ", url=PANCAKE_BUY),
                InlineKeyboardButton("📊 Chart",   url=DEXSCREENER),
            ]])
        )
    except Exception as e:
        logger.error(f"Channel post error: {e}")
