#!/usr/bin/env python3
"""
🌊 Hormuz (HRZ) Official Telegram Bot v5 — Gemini Powered
- Posts every 20 minutes
- Quiz questions every hour
- Full English content
- Community management
- Buy alerts & whale detection
- XP & Badges system
"""

import logging
import random
import time
import os
import re
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ── CONFIG ────────────────────────────────────────────────────────────────────

TOKEN      = "8669492245:AAGhwIR4zwF1wOIkhO2qBV56jqQDUhUMlIA"       # ← ضع توكن البوت الجديد هنا
GEMINI_KEY = "AIzaSyD48ydx3IYz46qV1jRHymgGHH0EPHIjwnU"  # ← ضع مفتاح Gemini الجديد هنا

HRZ_CONTRACT = "0x4E788d423d90A15504455b4FF746B9C1D9951A82"
PANCAKE_BUY  = f"https://pancakeswap.finance/swap?outputCurrency={HRZ_CONTRACT}"
DEXSCREENER  = f"https://dexscreener.com/bsc/{HRZ_CONTRACT}"
BSCSCAN      = f"https://bscscan.com/token/{HRZ_CONTRACT}"
WEBSITE      = "https://hormuz-hrz.netlify.app"
COINSNIPER   = "https://coinsniper.net"
TWITTER      = "https://x.com/armou224"
BOT_USERNAME = "@Hurmoz_bot"

# ── TIMING CONFIG ─────────────────────────────────────────────────────────────

POST_INTERVAL    = 20 * 60    # نشر كل 20 دقيقة
QUIZ_INTERVAL    = 60 * 60    # أسئلة كل ساعة
BUY_BOT_INTERVAL = 30         # فحص مشتريات كل 30 ثانية
VOTE_INTERVAL    = 24 * 3600  # تذكير تصويت كل 24 ساعة
REPORT_INTERVAL  = 24 * 3600  # تقرير يومي

PRICE_CACHE_TTL     = 60
WHALE_THRESHOLD_BNB = 0.5
MIN_BUY_BNB         = 0.01

# ── XP SYSTEM ─────────────────────────────────────────────────────────────────

XP_MESSAGE  = 1
XP_COMMAND  = 2
XP_VOTE     = 5
XP_QUIZ_WIN = 20

LEVELS = {
    0:    "🐚 Newcomer",
    50:   "🌊 Wave Rider",
    150:  "⚓ Sailor",
    300:  "🐋 Whale Hunter",
    600:  "🔱 Hormuz Guardian",
    1000: "👑 Strait Master",
}

BADGES = {
    "early_holder":   "🏅 Early Holder",
    "whale":          "🐋 Whale",
    "community_hero": "🦸 Community Hero",
    "quiz_master":    "🧠 Quiz Master",
    "voter":          "🗳️ Loyal Voter",
}

SPAM_PATTERNS = [
    r"https?://(?!hormuz-hrz\.netlify\.app|pancakeswap\.finance|dexscreener\.com|bscscan\.com|coinsniper\.net|t\.me/Hurmoz_bot|x\.com/armou224)",
    r"t\.me/(?!Hurmoz_bot)",
]

BANNED_WORDS = [
    "scam", "rug", "fake", "honeypot", "rugpull",
    "send me", "dm me", "guaranteed profit"
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── RUNTIME STATE ─────────────────────────────────────────────────────────────

_price_cache: dict | None = None
_price_cache_time: float  = 0
_last_seen_tx: str        = ""
_faq_store: dict          = {}
_xp_store: dict           = defaultdict(int)
_badge_store: dict        = defaultdict(set)
_warn_store: dict         = defaultdict(int)
_ath_store: dict          = {"price": 0.0, "date": ""}
_lockdown: bool           = False
_quiz_active: dict        = {}
_post_types: list         = ["price", "hype", "fact", "question", "whale", "chart"]
_post_index: int          = 0

# ── QUIZ QUESTIONS ────────────────────────────────────────────────────────────

QUIZ_QUESTIONS = [
    {
        "q": "🧠 <b>Quiz Time!</b>\n\nWhat percentage of global oil supply passes through the Strait of Hormuz?\n\nA) 10%\nB) 20%\nC) 30%\nD) 40%",
        "a": ["20", "b", "20%"],
        "correct": "B) 20%",
        "hint": "The Strait of Hormuz controls 20% of the world's oil! 🛢️"
    },
    {
        "q": "🧠 <b>Quiz Time!</b>\n\nWhat is the total supply of HRZ tokens?\n\nA) 100 Million\nB) 500 Million\nC) 1 Billion\nD) 10 Billion",
        "a": ["1000000000", "c", "1 billion", "1b"],
        "correct": "C) 1 Billion",
        "hint": "HRZ total supply is 1,000,000,000 tokens! 🌊"
    },
    {
        "q": "🧠 <b>Quiz Time!</b>\n\nWhat is the buy tax for HRZ?\n\nA) 1%\nB) 3%\nC) 5%\nD) 0%",
        "a": ["0", "d", "0%"],
        "correct": "D) 0%",
        "hint": "HRZ has ZERO buy tax — completely free to buy! ✅"
    },
    {
        "q": "🧠 <b>Quiz Time!</b>\n\nOn which blockchain is HRZ deployed?\n\nA) Ethereum\nB) Solana\nC) BNB Chain\nD) Polygon",
        "a": ["bnb", "c", "bnb chain", "bsc"],
        "correct": "C) BNB Chain",
        "hint": "HRZ is on BNB Chain (BSC)! ⚡"
    },
    {
        "q": "🧠 <b>Quiz Time!</b>\n\nHow long is the HRZ liquidity locked?\n\nA) 3 months\nB) 6 months\nC) 1 year\nD) 2 years",
        "a": ["1", "c", "1 year", "one year"],
        "correct": "C) 1 Year",
        "hint": "HRZ liquidity is locked for 1 full year on PinkLock! 🔒"
    },
    {
        "q": "🧠 <b>Quiz Time!</b>\n\nWhat is the sell tax for HRZ?\n\nA) 1%\nB) 3%\nC) 5%\nD) 10%",
        "a": ["3", "b", "3%"],
        "correct": "B) 3%",
        "hint": "HRZ has a 3% sell tax! 💰"
    },
    {
        "q": "🧠 <b>Quiz Time!</b>\n\nWhich DEX can you buy HRZ on?\n\nA) Uniswap\nB) SushiSwap\nC) PancakeSwap\nD) Raydium",
        "a": ["pancakeswap", "c", "pancake"],
        "correct": "C) PancakeSwap",
        "hint": "Buy HRZ on PancakeSwap! 🥞"
    },
    {
        "q": "🧠 <b>Quiz Time!</b>\n\nWhat does HRZ stand for?\n\nA) Horizon\nB) Hormuz\nC) Harbor\nD) Hydra",
        "a": ["hormuz", "b"],
        "correct": "B) Hormuz",
        "hint": "HRZ = Hormuz — inspired by the Strait of Hormuz! 🌊"
    },
]

# ── HELPERS ───────────────────────────────────────────────────────────────────

def http_get(url: str, timeout: int = 8) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.error(f"GET {url[:60]}: {e}")
        return None

def fetch_hrz_price(force: bool = False) -> dict | None:
    global _price_cache, _price_cache_time
    if not force and _price_cache and (time.time() - _price_cache_time) < PRICE_CACHE_TTL:
        return _price_cache
    data = http_get(f"https://api.dexscreener.com/latest/dex/tokens/{HRZ_CONTRACT}")
    if data:
        pairs = data.get("pairs") or []
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
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
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

def ask_gemini(prompt: str, max_tokens: int = 300) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    
    system_context = (
        "You are the official English-only AI assistant for Hormuz (HRZ) token on BNB Chain. "
        f"Contract: {HRZ_CONTRACT} | "
        f"Buy: {PANCAKE_BUY} | "
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
        "Be enthusiastic but honest. "
        "Add DYOR warning on financial questions. "
        "Max 4 sentences. End with relevant emoji."
    )
    
    payload = json.dumps({
        "contents": [{
            "parts": [{
                "text": f"{system_context}\n\nUser: {prompt}"
            }]
        }],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.8
        }
    }).encode()
    
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json"
    })
    
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini: {e}")
        return "⚠️ AI unavailable. Try again shortly."
    def generate_shill_post(style="hype"):
    prompts = {
        "hype": "Write a viral Telegram shill post about HRZ token. Make it exciting and add emojis.",
        "fomo": "Write a strong FOMO crypto post about whales buying HRZ.",
        "meme": "Write a funny crypto meme post about HRZ holders.",
        "twitter": "Write a tweet-style crypto post under 280 characters.",
        "raid": "Write a community raid message to promote HRZ on X/Twitter."
    }
    return ask_gemini(prompts.get(style, prompts["hype"]), 200)

def generate_auto_post(post_type: str = "hype") -> str:
    d = fetch_hrz_price()
    fg = fetch_fear_greed()
    
    context = ""
    if d:
        context = (
            f"HRZ price: ${float(d['price_usd']):.10f} | "
            f"24h change: {d['change_24h']}% | "
            f"volume: ${float(d['volume_24h']):,.2f} | "
            f"Fear & Greed: {fg['value']} ({fg['label']})"
        )
    
    prompts = {
        "price": (
            f"Write a short exciting Telegram post about HRZ current price. "
            f"Include price, 24h change, buy link. Max 5 lines. HTML format. "
            f"Add hashtags #HRZ #Hormuz #BNBChain. Context: {context}"
        ),
        "hype": (
            f"Write a viral hype Telegram post promoting HRZ token. "
            f"Make it exciting and FOMO-inducing. Include contract address "
            f"and PancakeSwap link. Max 5 lines. Context: {context}"
        ),
        "fact": (
            "Write a Telegram post with an interesting fact about the "
            "Strait of Hormuz and connect it to HRZ token. "
            "Make it educational and engaging. Max 5 lines."
        ),
        "question": (
            "Write a Telegram post that asks the community a fun question "
            "related to HRZ or crypto to boost engagement. "
            "End with poll-style options like A) B) C). Max 5 lines."
        ),
        "chart": (
            f"Write a Telegram post encouraging people to check the HRZ chart. "
            f"Include DexScreener link. Make it exciting. Context: {context}"
        ),
        "whale": (
            f"Write a Telegram post about smart money and whales buying HRZ. "
            f"Make it exciting and FOMO-inducing. Context: {context}"
        ),
    }
    
    prompt = prompts.get(post_type, prompts["hype"])
    return ask_gemini(prompt, max_tokens=200)

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

def price_text(d: dict) -> str:
    c24 = float(d["change_24h"]) if d["change_24h"] else 0
    c6  = float(d["change_6h"])  if d["change_6h"]  else 0
    c1  = float(d["change_1h"])  if d["change_1h"]  else 0
    def arrow(v): return "🟢" if v >= 0 else "🔴"
    return (
        f"🌊 <b>Hormuz (HRZ) — Live Price</b>\n\n"
        f"💵 <code>${float(d['price_usd']):.10f}</code>\n"
        f"🔶 <code>{float(d['price_bnb']):.10f} BNB</code>\n\n"
        f"{arrow(c1)}  1h:  <b>{c1:+.2f}%</b>\n"
        f"{arrow(c6)}  6h:  <b>{c6:+.2f}%</b>\n"
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
            InlineKeyboardButton("📊 Volume",     callback_data="volume"),
            InlineKeyboardButton("😱 Fear/Greed", callback_data="feargreed")
        ],
        [
            InlineKeyboardButton("💱 Buy HRZ",    url=PANCAKE_BUY),
            InlineKeyboardButton("📉 Chart",      url=DEXSCREENER)
        ],
        [
            InlineKeyboardButton("🌐 Website",    url=WEBSITE),
            InlineKeyboardButton("🐦 Twitter",    url=TWITTER),
            InlineKeyboardButton("🗳️ Vote",       url=COINSNIPER)
        ],
        [
            InlineKeyboardButton("🏆 ATH",        callback_data="ath"),
            InlineKeyboardButton("🎖️ My XP",     callback_data="myxp"),
            InlineKeyboardButton("📋 Contract",   callback_data="contract")
        ],
        [
            InlineKeyboardButton("❓ Ask AI",     callback_data="ask"),
            InlineKeyboardButton("📰 News",       callback_data="news"),
            InlineKeyboardButton("📣 Shill",      callback_data="shill")
        ],
    ])

# ── COMMANDS ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    await update.message.reply_html(
        "🌊 <b>Hormuz (HRZ) Bot v5</b>\n\n"
        "• Posts every <b>20 minutes</b> automatically\n"
        "• Quiz questions every <b>hour</b>\n"
        "• Live price & buy alerts\n"
        "• Whale detection 🐋\n"
        "• XP & Badges system 🎖️\n"
        "• Community management 🛡️\n\n"
        "<i>Use /schedule to activate all features!</i>",
        reply_markup=main_keyboard()
    )

async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    msg = await update.message.reply_text("⏳ Fetching...")
    d = fetch_hrz_price(force=True)
    if not d:
        await msg.edit_text(
            f"❌ Price unavailable. <a href='{DEXSCREENER}'>Check DexScreener</a>",
            parse_mode="HTML", disable_web_page_preview=True
        )
        return
    await msg.edit_text(price_text(d), parse_mode="HTML", disable_web_page_preview=True)

async def cmd_buy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    await update.message.reply_html(
        f"💱 <b>How to Buy Hormuz (HRZ)</b>\n\n"
        f"<b>1.</b> Get BNB on BNB Chain\n"
        f"<b>2.</b> Open PancakeSwap\n"
        f"<b>3.</b> Paste contract:\n"
        f"<code>{HRZ_CONTRACT}</code>\n\n"
        f"⚙️ Set slippage: <b>5-10%</b>\n\n"
        f"🔗 <a href='{PANCAKE_BUY}'>Open PancakeSwap</a>\n"
        f"📊 <a href='{DEXSCREENER}'>Chart</a>\n\n"
        f"⚠️ DYOR — Early stage token!",
        disable_web_page_preview=True
    )

async def cmd_contract(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        f"📍 <b>HRZ Contract Address</b>\n\n"
        f"<code>{HRZ_CONTRACT}</code>\n\n"
        f"• Network: BNB Chain ✅\n"
        f"• Verified: ✅\n"
        f"• Liquidity: 🔒 Locked 1 Year\n"
        f"• Buy Tax: 0% | Sell Tax: 3%\n\n"
        f"<a href='{PANCAKE_BUY}'>Buy</a> | "
        f"<a href='{DEXSCREENER}'>Chart</a> | "
        f"<a href='{BSCSCAN}'>BSCScan</a>",
        disable_web_page_preview=True
    )

async def cmd_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        f"🌊 <b>About Hormuz (HRZ)</b>\n\n"
        f"Inspired by the Strait of Hormuz — controlling 20% of global oil supply.\n\n"
        f"• Ticker: HRZ | Chain: BNB Chain\n"
        f"• Supply: 1,000,000,000 HRZ\n"
        f"• Buy Tax: 0% | Sell Tax: 3%\n"
        f"• Contract: Verified ✅\n"
        f"• Liquidity: Locked 1 Year 🔒\n"
        f"• Launch: May 2026\n\n"
        f"🌐 <a href='{WEBSITE}'>Website</a> | "
        f"💱 <a href='{PANCAKE_BUY}'>Buy</a> | "
        f"🐦 <a href='{TWITTER}'>Twitter</a>",
        disable_web_page_preview=True
    )

async def cmd_rules(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "📋 <b>HRZ Community Rules</b>\n\n"
        "1️⃣ No spam or external links\n"
        "2️⃣ No FUD or scam accusations\n"
        "3️⃣ Be respectful to all members\n"
        "4️⃣ English only in main chat\n"
        "5️⃣ No unsolicited DMs\n"
        "6️⃣ DYOR — Not financial advice\n\n"
        "⚠️ Violations: Warning → Mute → Ban\n\n"
        f"🌊 Welcome to the Hormuz family!"
    )

async def cmd_shill(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    d = fetch_hrz_price()
    price = f"${float(d['price_usd']):.10f}" if d else "Check DexScreener"
    change = f"{d['change_24h']}%" if d else "N/A"
    await update.message.reply_html(
        f"📣 <b>Copy & Share This!</b>\n\n"
        f"🌊 <b>Hormuz (HRZ) — BNB Chain Gem!</b>\n\n"
        f"💵 Price: {price} | 📈 24h: {change}\n\n"
        f"✅ Contract Verified\n"
        f"✅ Liquidity Locked 1 Year\n"
        f"✅ 0% Buy Tax\n\n"
        f"📍 <code>{HRZ_CONTRACT}</code>\n\n"
        f"💱 {PANCAKE_BUY}\n"
        f"🌐 {WEBSITE}\n"
        f"🐦 {TWITTER}\n\n"
        f"#HRZ #Hormuz #BNBChain #BSCGems #100x",
        disable_web_page_preview=True
    )

async def cmd_vote(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_VOTE)
    add_badge(update.effective_user.id, "voter")
    await update.message.reply_html(
        f"🗳️ <b>Vote for HRZ!</b>\n\n"
        f"Every vote = more visibility = more buyers! 🚀\n\n"
        f"<a href='{COINSNIPER}'>Vote on CoinSniper</a>\n\n"
        f"✅ +{XP_VOTE} XP earned! 🎖️",
        disable_web_page_preview=True
    )

async def cmd_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    question = " ".join(ctx.args) if ctx.args else ""
    if not question:
        await update.message.reply_html(
            "🤖 <b>Ask AI about HRZ</b>\n\n"
            "Usage: <code>/ask your question</code>\n"
            "Example: <code>/ask Is HRZ safe?</code>"
        )
        return
    _faq_store[question.lower()[:80]] = _faq_store.get(question.lower()[:80], 0) + 1
    thinking = await update.message.reply_text("🤖 Thinking...")
    answer = ask_gemini(question)
    await thinking.edit_text(answer, parse_mode="HTML", disable_web_page_preview=True)

async def cmd_myxp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    xp = _xp_store[uid]
    level = get_level(xp)
    badges = _badge_store.get(uid, set())
    badge_text = " ".join([BADGES[b] for b in badges]) if badges else "None yet"
    next_thresholds = [t for t in sorted(LEVELS.keys()) if t > xp]
    next_xp = next_thresholds[0] if next_thresholds else None
    text = (
        f"🎖️ <b>Your HRZ Rank</b>\n\n"
        f"👤 {update.effective_user.first_name}\n"
        f"⚡ XP: <b>{xp}</b>\n"
        f"🏅 Level: <b>{level}</b>\n"
        f"🎀 Badges: {badge_text}\n"
    )
    if next_xp:
        text += f"📈 Next level: <b>{next_xp} XP</b> ({next_xp - xp} to go)"
    await update.message.reply_html(text)

async def cmd_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _xp_store:
        await update.message.reply_text("No XP data yet!")
        return
    top = sorted(_xp_store.items(), key=lambda x: x[1], reverse=True)[:5]
    lines = ["🏆 <b>HRZ Leaderboard</b>\n"]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, (uid, xp) in enumerate(top):
        lines.append(f"{medals[i]} UID:{uid} — {xp} XP — {get_level(xp)}")
    await update.message.reply_html("\n".join(lines))

async def cmd_ath(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = fetch_hrz_price()
    ath = _ath_store
    current = float(d["price_usd"]) if d else 0
    distance = ((ath["price"] - current) / ath["price"] * 100) if ath["price"] > 0 else 0
    await update.message.reply_html(
        f"🏆 <b>HRZ All-Time High</b>\n\n"
        f"ATH: <b>${ath['price']:.10f}</b>\n"
        f"Date: <b>{ath['date'] or 'Tracking...'}</b>\n\n"
        f"📍 Now: <b>${current:.10f}</b>\n"
        f"📉 From ATH: <b>{distance:.1f}%</b>"
    )

async def cmd_dashboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = fetch_hrz_price()
    fg = fetch_fear_greed()
    if not d:
        await update.message.reply_text("❌ Data unavailable.")
        return
    c24 = float(d["change_24h"]) if d["change_24h"] else 0
    await update.message.reply_html(
        f"📊 <b>HRZ Dashboard</b>\n\n"
        f"💵 Price: <b>${float(d['price_usd']):.10f}</b>\n"
        f"📈 24h: <b>{c24:+.2f}%</b>\n"
        f"📊 Volume: <b>${float(d['volume_24h']):,.2f}</b>\n"
        f"💧 Liquidity: <b>${float(d['liquidity']):,.2f}</b>\n"
        f"🔄 Buys/Sells: <b>{d['txns_buys']}/{d['txns_sells']}</b>\n"
        f"😱 Fear & Greed: <b>{fg['value']} — {fg['label']}</b>\n\n"
        f"✅ Verified | 🔒 Locked 1yr | 0% Buy Tax\n\n"
        f"<a href='{PANCAKE_BUY}'>Buy</a> | "
        f"<a href='{DEXSCREENER}'>Chart</a> | "
        f"<a href='{BSCSCAN}'>BSCScan</a>",
        disable_web_page_preview=True
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "<b>📋 Hormuz Bot v5 Commands</b>\n\n"
        "<b>📊 Market</b>\n"
        "/price — Live price\n"
        "/ath — All-time high\n"
        "/dashboard — Full overview\n\n"
        "<b>🏘️ Community</b>\n"
        "/buy — How to buy\n"
        "/contract — Contract address\n"
        "/info — About HRZ\n"
        "/rules — Community rules\n"
        "/vote — Vote (+XP)\n"
        "/shill — Promo message\n"
        "/ask [q] — Ask AI\n\n"
        "<b>🎖️ XP</b>\n"
        "/myxp — Your rank\n"
        "/leaderboard — Top members\n\n"
        "<b>🛡️ Admin</b>\n"
        "/warn — Warn user\n"
        "/mute [min] — Mute user\n"
        "/ban — Ban user\n"
        "/slowmode [s] — Slow mode\n"
        "/lockdown — Emergency lock\n"
        "/schedule — Start auto features\n"
        "/stopschedule — Stop auto features\n\n"
        f"💬 Mention {BOT_USERNAME} for AI reply."
    )
    async def cmd_shillai(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🤖 Generating AI shill...")
    text = generate_shill_post("hype")
    await msg.edit_text(text, parse_mode="HTML")
    async def cmd_fomo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🚀 Generating FOMO...")
    text = generate_shill_post("fomo")
    await msg.edit_text(text, parse_mode="HTML")
    async def cmd_meme(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("😂 Creating meme...")
    text = generate_shill_post("meme")
    await msg.edit_text(text, parse_mode="HTML")

# ── ADMIN COMMANDS ────────────────────────────────────────────────────────────

async def cmd_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message to warn.")
        return
    try:
        member = await ctx.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("❌ Admins only.")
            return
    except Exception:
        return
    target = update.message.reply_to_message.from_user
    _warn_store[target.id] += 1
    warns = _warn_store[target.id]
    reason = " ".join(ctx.args) if ctx.args else "No reason"
    if warns >= 3:
        try:
            await ctx.bot.ban_chat_member(update.effective_chat.id, target.id)
            await update.message.reply_html(f"🚫 <b>{target.full_name}</b> banned after 3 warnings!")
        except Exception as e:
            await update.message.reply_text(f"❌ Cannot ban: {e}")
    else:
        await update.message.reply_html(
            f"⚠️ Warning <b>{warns}/3</b> for {target.full_name}\n"
            f"Reason: {reason}"
        )

async def cmd_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to mute.")
        return
    try:
        member = await ctx.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("❌ Admins only.")
            return
    except Exception:
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
        await update.message.reply_html(f"🔇 <b>{target.full_name}</b> muted for {duration} minutes.")
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot mute: {e}")

async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to ban.")
        return
    try:
        member = await ctx.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("❌ Admins only.")
            return
    except Exception:
        return
    target = update.message.reply_to_message.from_user
    reason = " ".join(ctx.args) if ctx.args else "No reason"
    try:
        await ctx.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_html(f"🚫 <b>{target.full_name}</b> banned. Reason: {reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot ban: {e}")

async def cmd_slowmode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        member = await ctx.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("❌ Admins only.")
            return
    except Exception:
        return
    seconds = int(ctx.args[0]) if ctx.args else 0
    try:
        await ctx.bot.set_chat_slow_mode_delay(update.effective_chat.id, seconds)
        msg = f"🐢 Slow mode: <b>{seconds}s</b>" if seconds else "✅ Slow mode <b>off</b>"
        await update.message.reply_html(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_lockdown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _lockdown
    try:
        member = await ctx.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("❌ Admins only.")
            return
    except Exception:
        return
    _lockdown = not _lockdown
    if _lockdown:
        await update.message.reply_html("🔒 <b>LOCKDOWN ON!</b> Use /lockdown to unlock.")
    else:
        await update.message.reply_html("🔓 <b>Lockdown OFF!</b> Chat is open.")

# ── SCHEDULED JOBS ────────────────────────────────────────────────────────────

async def scheduled_post(ctx: ContextTypes.DEFAULT_TYPE):
    global _post_index
    chat_id = ctx.job.chat_id
    post_type = _post_types[_post_index % len(_post_types)]
    _post_index += 1
    post = generate_auto_post(post_type)
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=post,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("💱 Buy HRZ", url=PANCAKE_BUY),
                    InlineKeyboardButton("📊 Chart",   url=DEXSCREENER)
                ]
            ])
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
                f"⏰ First correct answer wins <b>+{XP_QUIZ_WIN} XP</b>! 🎯"
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
            header = "🐋 <b>WHALE BUY!</b> 🐋" if is_whale else "🟢 <b>NEW BUY!</b>"
            footer = "#Hormuz #BSCWhale 🚀🚀" if is_whale else "#HRZ #Hormuz 🚀"
            await ctx.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"{header}\n\n"
                    f"🌊 <b>{amount:,.0f} HRZ</b>\n"
                    f"💵 ~<b>${usd_val:,.2f}</b> ({bnb_val:.3f} BNB)\n"
                    f"👤 <code>{tx.get('to','')[:8]}...</code>\n"
                    f"🔗 <a href='https://bscscan.com/tx/{tx_hash}'>View Tx</a>\n\n"
                    f"{footer}"
                ),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Buy bot: {e}")

async def vote_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.job.chat_id
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🗳️ <b>Daily Vote Reminder!</b>\n\n"
                f"Vote for HRZ on CoinSniper to get more visibility! 🚀\n"
                f"Takes only 10 seconds!\n\n"
                f"<a href='{COINSNIPER}'>Vote Now!</a>\n\n"
                f"Use /vote to earn XP! 🎖️"
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
    if not d:
        return
    c24 = float(d["change_24h"]) if d["change_24h"] else 0
    arrow = "📈" if c24 >= 0 else "📉"
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                f"☀️ <b>HRZ Daily Report</b>\n\n"
                f"💵 Price: <b>${float(d['price_usd']):.10f}</b>\n"
                f"{arrow} 24h: <b>{c24:+.2f}%</b>\n"
                f"📊 Volume: <b>${float(d['volume_24h']):,.2f}</b>\n"
                f"💧 Liquidity: <b>${float(d['liquidity']):,.2f}</b>\n"
                f"🔄 Buys/Sells: <b>{d['txns_buys']}/{d['txns_sells']}</b>\n"
                f"😱 Fear & Greed: <b>{fg['value']} — {fg['label']}</b>\n\n"
                f"💱 <a href='{PANCAKE_BUY}'>Buy HRZ</a> | "
                f"📊 <a href='{DEXSCREENER}'>Chart</a>\n\n"
                f"#HRZ #Hormuz #BNBChain"
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
        try:
            await update.message.reply_html(
                f"🌊 Welcome <b>{name}</b> to Hormuz (HRZ)!\n\n"
                f"🎖️ You earned: <b>Early Holder</b> badge!\n\n"
                f"💱 <a href='{PANCAKE_BUY}'>Buy HRZ</a> | "
                f"📊 <a href='{DEXSCREENER}'>Chart</a>\n\n"
                f"/rules /price /help\n\n"
                f"HODL strong! 🚀",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Welcome: {e}")

# ── MESSAGE HANDLER ───────────────────────────────────────────────────────────

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    chat_type = update.effective_chat.type
    uid = update.effective_user.id
    chat_id = update.effective_chat.id

    is_admin = False
    if chat_type in ("group", "supergroup"):
        try:
            member = await ctx.bot.get_chat_member(chat_id, uid)
            is_admin = member.status in ("administrator", "creator")
        except Exception:
            pass

    if not is_admin:
        if is_spam(text):
            try:
                await update.message.delete()
                _warn_store[uid] += 1
                await ctx.bot.send_message(
                    chat_id,
                    f"🚫 External links not allowed! Warning {_warn_store[uid]}/3",
                    parse_mode="HTML"
                )
                if _warn_store[uid] >= 3:
                    await ctx.bot.ban_chat_member(chat_id, uid)
            except Exception:
                pass
            return
        if has_banned_words(text):
            try:
                await update.message.delete()
            except Exception:
                pass
            return

    add_xp(uid, XP_MESSAGE)

    # Quiz answer check
    if chat_id in _quiz_active:
        q = _quiz_active[chat_id]
        for answer in q["a"]:
            if answer.lower() in text.lower():
                del _quiz_active[chat_id]
                add_xp(uid, XP_QUIZ_WIN)
                add_badge(uid, "quiz_master")
                await update.message.reply_html(
                    f"🎉 <b>{update.effective_user.first_name}</b> got it right!\n"
                    f"✅ {q['correct']}\n"
                    f"💡 {q['hint']}\n\n"
                    f"+{XP_QUIZ_WIN} XP earned! 🎖️"
                )
                break

    # AI reply
    if chat_type == "private" or BOT_USERNAME.lower() in text.lower():
        question = text.replace(BOT_USERNAME, "").strip()
        if len(question) < 2:
            return
        thinking = await update.message.reply_text("🤖 Thinking...")
        answer = ask_gemini(question)
        await thinking.edit_text(answer, parse_mode="HTML", disable_web_page_preview=True)

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
    elif query.data == "volume":
        d = fetch_hrz_price()
        if d:
            text = (
                f"📊 <b>HRZ Volume</b>\n\n"
                f"6h: <b>${float(d['volume_6h']):,.2f}</b>\n"
                f"24h: <b>${float(d['volume_24h']):,.2f}</b>\n"
                f"Buys/Sells: <b>{d['txns_buys']}/{d['txns_sells']}</b>"
            )
        else:
            text = "❌ Unavailable."
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())

    elif query.data == "feargreed":
        fg = fetch_fear_greed()
        await query.edit_message_text(
            f"😱 <b>Fear &amp; Greed: {fg['value']} — {fg['label']}</b>\n\n"
            f"<i>Low = fear = opportunity 👀</i>",
            parse_mode="HTML", reply_markup=main_keyboard()
        )
    elif query.data == "ath":
        d = fetch_hrz_price()
        current = float(d["price_usd"]) if d else 0
        ath = _ath_store
        distance = ((ath["price"] - current) / ath["price"] * 100) if ath["price"] > 0 else 0
        await query.edit_message_text(
            f"🏆 <b>ATH: ${ath['price']:.10f}</b>\n"
            f"📍 Now: ${current:.10f}\n"
            f"📉 {distance:.1f}% from ATH",
            parse_mode="HTML", reply_markup=main_keyboard()
        )
    elif query.data == "myxp":
        uid = query.from_user.id
        xp = _xp_store[uid]
        badges = _badge_store.get(uid, set())
        badge_text = " ".join([BADGES[b] for b in badges]) if badges else "None yet"
        await query.edit_message_text(
            f"🎖️ XP: <b>{xp}</b>\n🏅 {get_level(xp)}\n🎀 {badge_text}",
            parse_mode="HTML", reply_markup=main_keyboard()
        )
    elif query.data == "contract":
        await query.edit_message_text(
            f"📍 <b>Contract</b>\n\n<code>{HRZ_CONTRACT}</code>\n\n"
            f"<a href='{PANCAKE_BUY}'>Buy</a> | <a href='{DEXSCREENER}'>Chart</a>",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_keyboard()
        )
    elif query.data == "news":
        await query.edit_message_text(
            f"📰 Latest crypto news:\n<a href='https://cryptopanic.com'>CryptoPanic</a>",
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
    elif query.data == "ask":
        await query.edit_message_text(
            f"🤖 Type: <code>/ask your question</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="back")]
            ])
        )
    elif query.data == "back":
        await query.edit_message_text(
            "🌊 <b>Hormuz (HRZ)</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

# ── ADMIN: SCHEDULE ───────────────────────────────────────────────────────────

async def cmd_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = str(chat_id)

    ctx.job_queue.run_repeating(
        scheduled_post, interval=POST_INTERVAL,
        first=10, chat_id=chat_id, name=f"post_{name}"
    )
    ctx.job_queue.run_repeating(
        scheduled_quiz, interval=QUIZ_INTERVAL,
        first=60, chat_id=chat_id, name=f"quiz_{name}"
    )
    ctx.job_queue.run_repeating(
        buy_bot_tick, interval=BUY_BOT_INTERVAL,
        first=5, chat_id=chat_id, name=f"buybot_{name}"
    )
    ctx.job_queue.run_repeating(
        vote_reminder, interval=VOTE_INTERVAL,
        first=3600, chat_id=chat_id, name=f"vote_{name}"
    )
    ctx.job_queue.run_repeating(
        daily_report, interval=REPORT_INTERVAL,
        first=7200, chat_id=chat_id, name=f"report_{name}"
    )

    await update.message.reply_html(
        f"✅ <b>Bot Activated!</b>\n\n"
        f"📢 Auto-posts: every <b>20 minutes</b>\n"
        f"🧠 Quiz: every <b>1 hour</b>\n"
        f"🟢 Buy alerts: every <b>30 seconds</b>\n"
        f"🗳️ Vote reminder: every <b>24 hours</b>\n"
        f"📊 Daily report: every <b>24 hours</b>"
    )

async def cmd_stop_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = str(update.effective_chat.id)
    for prefix in ("post_", "quiz_", "buybot_", "vote_", "report_"):
        for job in ctx.job_queue.get_jobs_by_name(f"{prefix}{name}"):
            job.schedule_removal()
    await update.message.reply_text("🛑 All auto jobs stopped.")

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()

    for cmd, func in [
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
        ("myxp",          cmd_myxp),
        ("leaderboard",   cmd_leaderboard),
        ("help",          cmd_help),
        ("warn",          cmd_warn),
        ("mute",          cmd_mute),
        ("ban",           cmd_ban),
        ("slowmode",      cmd_slowmode),
        ("lockdown",      cmd_lockdown),
        ("schedule",      cmd_schedule),
        ("stopschedule",  cmd_stop_schedule),
        ("shillai",       cmd_shillai),
        ("fomo",          cmd_fomo),
        ("meme",          cmd_meme),
    ]:
        app.add_handler(CommandHandler(cmd, func))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, message_handler
    ))

    logger.info("🌊 Hormuz Bot v5 — Running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()