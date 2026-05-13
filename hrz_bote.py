#!/usr/bin/env python3
"""
🌊 Hormuz (HRZ) Official Telegram Bot v8 — Ultimate Edition
2500+ lines | Gemini AI | Auto-posting | Giveaway | Anti-Raid | Price Alerts | Sentiment | Referral
"""

import logging
import random
import time
import os
import re
import json
import urllib.request
import urllib.parse
import requests
import hashlib
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

# ════════════════════════════════════════════════════════════════════
# ── CONFIGURATION
# ════════════════════════════════════════════════════════════════════

TOKEN      = os.getenv("TOKEN", "")
GEMINI_KEY = os.getenv("GEMINI_KEY", "")
XAI_KEY    = os.getenv("XAI_KEY", "")

HRZ_CONTRACT  = "0x4E788d423d90A15504455b4FF746B9C1D9951A82"
HRZ_NAME      = "Hormuz"
HRZ_SYMBOL    = "HRZ"
HRZ_SUPPLY    = 1_000_000_000
HRZ_BUY_TAX  = 0
HRZ_SELL_TAX = 3
HRZ_NETWORK  = "BNB Chain"
HRZ_LAUNCH   = "May 2026"

PANCAKE_BUY  = f"https://pancakeswap.finance/swap?outputCurrency={HRZ_CONTRACT}"
DEXSCREENER  = f"https://dexscreener.com/bsc/{HRZ_CONTRACT}"
BSCSCAN      = f"https://bscscan.com/token/{HRZ_CONTRACT}"
PINKLOCK     = "https://pinksale.finance/pinklock"
WEBSITE      = "https://hormuz-hrz.netlify.app"
COINSNIPER   = "https://coinsniper.net"
GEMFINDER    = "https://gemfinder.cc"
COINHUNT     = "https://coinhunt.cc"
DEXTOOLS     = f"https://www.dextools.io/app/en/bnb/pair-explorer/{HRZ_CONTRACT}"
TWITTER      = "https://x.com/armou224"
TELEGRAM_GRP = "https://t.me/HormuzHRZ"
BOT_USERNAME = "@Hurmoz_bot"

CHANNEL_ID   = -1003992608217

POST_INTERVAL        = 20 * 60
QUIZ_INTERVAL        = 24 * 60 * 60
BUY_BOT_INTERVAL     = 30
VOTE_INTERVAL        = 24 * 3600
REPORT_INTERVAL      = 24 * 3600
ATH_CHECK            = 5 * 60
SENTIMENT_INTERVAL   = 6 * 3600
LEADERBOARD_INTERVAL = 12 * 3600
PRICE_CACHE_TTL      = 60
WHALE_THRESHOLD_USD  = 100
WHALE_THRESHOLD_BNB  = 0.5
MIN_BUY_BNB          = 0.005
AI_REPLY_COOLDOWN    = 120
MAX_WARNS_BEFORE_BAN = 3
MUTE_DEFAULT_MINS    = 60
ANTI_RAID_THRESHOLD  = 8
ANTI_RAID_WINDOW     = 30

XP_MESSAGE   = 1
XP_COMMAND   = 2
XP_VOTE      = 5
XP_QUIZ_WIN  = 20
XP_REFERRAL  = 10
XP_DAILY     = 3

LEVELS = {
    0:    "🐚 Newcomer",
    50:   "🌊 Wave Rider",
    150:  "⚓ Sailor",
    300:  "🐋 Whale Hunter",
    600:  "🔱 Hormuz Guardian",
    1000: "👑 Strait Master",
    2000: "⚡ HRZ Legend",
    5000: "🌟 Hormuz God",
}

SPAM_PATTERNS = [
    r"t\.me/(?!HormuzHRZ|Hurmoz_bot)",
    r"(?:earn|make)\s+\$?\d+\s+(?:daily|per day)",
    r"(?:dm|message)\s+me\s+(?:for|to)",
    r"(?:free|giveaway)\s+(?:crypto|bnb|eth|usdt)(?!\s+giveaway\s+hrz)",
    r"(?:pump|moon)\s+guarantee",
    r"airdrop.*claim(?!.*hrz)",
]

BANNED_WORDS = [
    "scam", "rug", "rugpull", "fake", "honeypot",
    "send me", "dm me for profit", "guaranteed returns",
    "100x guaranteed", "ponzi", "pyramid",
]

CRYPTO_KEYWORDS = [
    "hrz", "hormuz", "buy", "sell", "price", "moon", "pump",
    "hodl", "hold", "bullish", "bearish", "dex", "bnb", "pancake",
    "liquidity", "contract", "wallet", "token", "crypto", "defi",
    "chart", "volume", "market cap", "ath", "dip", "gem",
]

POST_TYPES = [
    "price_update", "hype_call", "dex_stats", "strait_fact",
    "community_question", "buy_reminder", "liquidity_info",
    "comparison", "motivation", "chart_update", "whale_alert_teaser",
    "tokenomics", "roadmap_teaser", "why_hrz", "fun_fact",
    "market_insight", "holder_appreciation", "fomo_post",
    "educational", "meme_text",
]

QUIZ_QUESTIONS = [
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nWhat % of global oil passes through the Strait of Hormuz?\n\nA) 10%  B) 20%  C) 30%  D) 40%",
        "answers": ["20", "b", "20%"],
        "correct": "B) 20%",
        "fact": "The Strait of Hormuz controls 20% of global oil! 🛢️",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nWhat is HRZ total supply?\n\nA) 100M  B) 500M  C) 1B  D) 10B",
        "answers": ["1000000000", "c", "1 billion", "1b"],
        "correct": "C) 1 Billion",
        "fact": "HRZ total supply: exactly 1,000,000,000! 🌊",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nHRZ buy tax is?\n\nA) 1%  B) 3%  C) 5%  D) 0%",
        "answers": ["0", "d", "0%", "zero"],
        "correct": "D) 0%",
        "fact": "HRZ has ZERO buy tax! Buy freely! ✅",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nWhich blockchain is HRZ on?\n\nA) ETH  B) SOL  C) BNB Chain  D) Polygon",
        "answers": ["bnb", "c", "bnb chain", "bsc", "binance"],
        "correct": "C) BNB Chain",
        "fact": "HRZ lives on BNB Chain for speed and low fees! ⚡",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nHRZ liquidity is locked for?\n\nA) 3mo  B) 6mo  C) 1yr  D) 2yr",
        "answers": ["1", "c", "1 year", "one year", "12 months"],
        "correct": "C) 1 Year",
        "fact": "HRZ liquidity locked 1 full year on PinkLock! 🔒",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nWhere to buy HRZ?\n\nA) Uniswap  B) SushiSwap  C) PancakeSwap  D) Raydium",
        "answers": ["pancakeswap", "c", "pancake"],
        "correct": "C) PancakeSwap",
        "fact": "Buy HRZ on PancakeSwap V2 on BNB Chain! 🥞",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nThe Strait of Hormuz connects?\n\nA) Red Sea & Med  B) Persian Gulf & Gulf of Oman  C) Black Sea  D) Pacific",
        "answers": ["b", "persian", "gulf of oman", "persian gulf"],
        "correct": "B) Persian Gulf & Gulf of Oman",
        "fact": "Hormuz connects Persian Gulf to Gulf of Oman! 🌊",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nHRZ sell tax is?\n\nA) 1%  B) 3%  C) 5%  D) 10%",
        "answers": ["3", "b", "3%"],
        "correct": "B) 3%",
        "fact": "3% sell tax goes to dev wallet for development! 💰",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +25 XP!</b>\n\nWhat country controls the Strait of Hormuz?\n\nA) Saudi Arabia  B) UAE  C) Iran & Oman  D) Kuwait",
        "answers": ["c", "iran", "oman", "iran and oman"],
        "correct": "C) Iran & Oman",
        "fact": "Iran and Oman share control of the Strait of Hormuz! 🗺️",
        "xp": 25
    },
    {
        "q": "🧠 <b>Quiz Time! +25 XP!</b>\n\nHow wide is the Strait at its narrowest?\n\nA) 21km  B) 39km  C) 55km  D) 100km",
        "answers": ["b", "39", "39km"],
        "correct": "B) 39km",
        "fact": "The Strait is only 39km wide at its narrowest point! 🌊",
        "xp": 25
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nWhat does HRZ stand for?\n\nA) High Risk Zone  B) Hormuz  C) Horizon  D) Hard Reserve",
        "answers": ["b", "hormuz"],
        "correct": "B) Hormuz",
        "fact": "HRZ = Hormuz, the world's most strategic strait! ⚔️",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nHRZ contract is verified on?\n\nA) Etherscan  B) BscScan  C) Solscan  D) Polygonscan",
        "answers": ["b", "bscscan", "bsc"],
        "correct": "B) BscScan",
        "fact": "HRZ contract is fully verified on BscScan! ✅",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +30 XP!</b>\n\nHow many oil tankers pass through Hormuz daily?\n\nA) 5-10  B) 17-20  C) 30-40  D) 50+",
        "answers": ["b", "17", "20", "17-20"],
        "correct": "B) 17-20 tankers per day",
        "fact": "17-20 massive oil tankers pass through Hormuz every day! 🛢️",
        "xp": 30
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nHRZ liquidity is locked on?\n\nA) Unicrypt  B) Team Finance  C) PinkLock  D) DxSale",
        "answers": ["c", "pinklock", "pink", "pinksale"],
        "correct": "C) PinkLock",
        "fact": "HRZ liquidity is secured on PinkLock! 🔒",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +25 XP!</b>\n\nHRZ Twitter account is?\n\nA) @HormuzToken  B) @HRZ_BNB  C) @armou224  D) @HormuzHRZ",
        "answers": ["c", "armou224", "@armou224"],
        "correct": "C) @armou224",
        "fact": "Follow HRZ on Twitter: @armou224! 🐦",
        "xp": 25
    },
    {
        "q": "🧠 <b>Quiz Time! +25 XP!</b>\n\nHRZ was launched in?\n\nA) Jan 2026  B) March 2026  C) May 2026  D) July 2026",
        "answers": ["c", "may", "may 2026"],
        "correct": "C) May 2026",
        "fact": "HRZ launched in May 2026 — you're still very early! 🚀",
        "xp": 25
    },
    {
        "q": "🧠 <b>Quiz Time! +30 XP!</b>\n\nWhat % of world's LNG passes through Hormuz?\n\nA) 10%  B) 20%  C) 30%  D) 40%",
        "answers": ["c", "30", "30%"],
        "correct": "C) ~30%",
        "fact": "About 30% of world's LNG passes through Hormuz! 💨",
        "xp": 30
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nHRZ website is?\n\nA) hormuz.com  B) hrz.io  C) hormuz-hrz.netlify.app  D) hrz.xyz",
        "answers": ["c", "netlify", "hormuz-hrz", "hormuz-hrz.netlify.app"],
        "correct": "C) hormuz-hrz.netlify.app",
        "fact": "Visit hormuz-hrz.netlify.app for all HRZ info! 🌐",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nHRZ is listed on which DEX screener?\n\nA) PooCoin  B) DexScreener  C) DexGuru  D) GeckoTerminal",
        "answers": ["b", "dexscreener", "dex screener"],
        "correct": "B) DexScreener",
        "fact": "Track HRZ live on DexScreener! 📊",
        "xp": 20
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP!</b>\n\nHRZ Telegram group is?\n\nA) @HRZ_Official  B) @HormuzToken  C) @HormuzHRZ  D) @HRZ_BNB",
        "answers": ["c", "hormuzhrz", "@hormuzhrz"],
        "correct": "C) @HormuzHRZ",
        "fact": "Join HRZ Telegram: @HormuzHRZ! 💬",
        "xp": 20
    },
]

STRAIT_FACTS = [
    "The Strait of Hormuz is only 39km wide at its narrowest, yet controls 20% of global oil trade! 🌊",
    "Approximately 17-20 fully loaded supertankers pass through the Strait every single day! 🛢️",
    "The Strait of Hormuz connects the Persian Gulf to the Gulf of Oman and the Arabian Sea. 🗺️",
    "If the Strait of Hormuz were closed, global oil prices would skyrocket within days! 📈",
    "About 30% of the world's LNG also passes through the Strait! 💨",
    "Over $1 trillion worth of oil and gas passes through the Strait every single year! 💰",
    "The Strait has two 3.2km-wide shipping lanes — one inbound and one outbound! 🚢",
    "The Strait of Hormuz is considered the world's most important oil chokepoint! 🏆",
    "Qatar exports its entire natural gas production through the Strait of Hormuz! 💎",
    "Just like the Strait controls the world's oil, $HRZ aims to control crypto wealth flow! 🚀",
]

MOTIVATIONS = [
    "💎 The Strait controls the oil. $HRZ controls the gains. HODL tight! 🌊",
    "🚀 Every empire started small. HRZ is just beginning its conquest! ⚔️",
    "🌊 Like water through the strait — nothing can stop $HRZ's flow! 💪",
    "💰 Early birds catch the biggest gains. You're still very early on $HRZ! 🐦",
    "⚓ Sailors who stay the course reach the greatest treasures. HODL $HRZ! 🏆",
    "🔱 The guardian of the strait rewards those who believe! Keep HODLING! 👑",
    "💎 Diamond hands were forged in the fires of doubt. Stay strong $HRZ army! 🔥",
    "🌟 Legends aren't born, they're made. You're making history with $HRZ! ⭐",
    "🐋 Whales don't panic sell. Be a whale, think long term! 🌊",
    "⚡ The storm before the moon. Every dip is an opportunity! 🚀",
]

FOMO_MESSAGES = [
    "👀 While you're reading this, smart money is buying $HRZ!",
    "⏰ The clock is ticking. Early stage won't last forever!",
    "💸 Every minute you wait is a minute others are accumulating $HRZ!",
    "🚀 Rockets don't wait for late passengers. $HRZ is on the launchpad!",
    "🏆 Champions make moves when others hesitate. Are you a champion?",
    "💎 The best time to buy was at launch. The second best time is NOW!",
    "🎯 Don't be the person who says 'I should have bought earlier'!",
]

# ════════════════════════════════════════════════════════════════════
# ── LOGGING
# ════════════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
# ── STATE STORAGE
# ════════════════════════════════════════════════════════════════════

_price_cache:        dict | None = None
_price_cache_time:   float       = 0.0
_last_seen_tx:       str         = ""
_xp_store:           dict        = defaultdict(int)
_badge_store:        dict        = defaultdict(set)
_warn_store:         dict        = defaultdict(int)
_ath_store:          dict        = {"price": 0.0, "date": ""}
_ath_alerted:        float       = 0.0
_lockdown:           bool        = False
_quiz_active:        dict        = {}
_post_index:         int         = 0
_reply_cooldown:     dict        = {}
_daily_claim:        dict        = {}
_total_posts:        int         = 0
_bot_start_time:     float       = time.time()

# ── Giveaway System
_giveaway_active:    dict        = {}   # chat_id -> {prize_xp, entries: set, end_time, msg_id}

# ── Anti-Raid System
_join_timestamps:    dict        = defaultdict(list)  # chat_id -> [timestamps]
_raid_mode:          dict        = defaultdict(bool)  # chat_id -> bool
_raid_mode_until:    dict        = defaultdict(float) # chat_id -> timestamp

# ── Price Alerts System
_price_alerts:       dict        = defaultdict(list)  # user_id -> [{target, direction, chat_id}]
_alert_check_prices: dict        = {}  # last known price per chat

# ── Sentiment Voting
_sentiment_votes:    dict        = {}  # chat_id -> {bullish: set, bearish: set, date, msg_id}

# ── Referral System
_referral_codes:     dict        = {}  # code -> user_id
_referrals_made:     dict        = defaultdict(list)  # user_id -> [referred_user_ids]
# ── Suggestions
_suggestion_store:   list        = []
_referral_used:      dict        = {}  # user_id -> referrer_id

# ════════════════════════════════════════════════════════════════════
# ── HTTP HELPERS
# ════════════════════════════════════════════════════════════════════

def http_get(url: str, timeout: int = 8) -> dict | None:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 HRZBot/8.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.error(f"GET {url[:70]}: {e}")
        return None

def http_post(url: str, data: bytes, headers: dict = None, timeout: int = 15) -> dict | None:
    try:
        h = {"Content-Type": "application/json"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.error(f"POST {url[:70]}: {e}")
        return None

# ════════════════════════════════════════════════════════════════════
# ── PRICE & MARKET DATA
# ════════════════════════════════════════════════════════════════════

def fetch_hrz_price(force: bool = False) -> dict | None:
    global _price_cache, _price_cache_time, _ath_store
    if not force and _price_cache and (time.time() - _price_cache_time) < PRICE_CACHE_TTL:
        return _price_cache
    data = http_get(f"https://api.dexscreener.com/tokens/v1/bsc/{HRZ_CONTRACT}")
    if not data:
        return _price_cache
    pairs = data if isinstance(data, list) else data.get("pairs", [])
    if not pairs:
        return _price_cache
    p = pairs[0]
    result = {
        "price_usd":     p.get("priceUsd", "0"),
        "price_bnb":     p.get("priceNative", "0"),
        "change_5m":     p.get("priceChange", {}).get("m5", 0),
        "change_1h":     p.get("priceChange", {}).get("h1", 0),
        "change_6h":     p.get("priceChange", {}).get("h6", 0),
        "change_24h":    p.get("priceChange", {}).get("h24", 0),
        "volume_5m":     p.get("volume", {}).get("m5", 0),
        "volume_1h":     p.get("volume", {}).get("h1", 0),
        "volume_24h":    p.get("volume", {}).get("h24", 0),
        "liquidity":     p.get("liquidity", {}).get("usd", 0),
        "market_cap":    p.get("marketCap", 0),
        "fdv":           p.get("fdv", 0),
        "txns_5m_buys":  p.get("txns", {}).get("m5", {}).get("buys", 0),
        "txns_5m_sells": p.get("txns", {}).get("m5", {}).get("sells", 0),
        "txns_buys":     p.get("txns", {}).get("h24", {}).get("buys", 0),
        "txns_sells":    p.get("txns", {}).get("h24", {}).get("sells", 0),
        "pair_address":  p.get("pairAddress", ""),
    }
    current = float(result["price_usd"] or 0)
    if current > _ath_store["price"]:
        _ath_store = {
            "price": current,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        }
    _price_cache = result
    _price_cache_time = time.time()
    return result

def fetch_fear_greed() -> dict:
    data = http_get("https://api.alternative.me/fng/?limit=1")
    if data and data.get("data"):
        d = data["data"][0]
        return {
            "value": d.get("value", "?"),
            "label": d.get("value_classification", "Unknown"),
        }
    return {"value": "?", "label": "Unknown"}

def fetch_bnb_price() -> float:
    data = http_get("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT")
    if data and "price" in data:
        return float(data["price"])
    return 0.0

def fetch_latest_buys() -> list:
    data = http_get(
        f"https://api.bscscan.com/api?module=account&action=tokentx"
        f"&contractaddress={HRZ_CONTRACT}&sort=desc&offset=10&page=1"
    )
    if data and isinstance(data.get("result"), list):
        return data["result"]
    return []

def get_market_trend(d: dict) -> str:
    if not d:
        return "neutral"
    c24 = float(d.get("change_24h", 0) or 0)
    if c24 > 10:   return "🔥 bullish"
    elif c24 > 0:  return "📈 slightly bullish"
    elif c24 > -10:return "📉 slightly bearish"
    else:          return "🔴 bearish"

# ════════════════════════════════════════════════════════════════════

# ── GEMINI AI + GROQ FALLBACK

# ── GROK (xAI) API
async def educational_post(ctx):
    global _edu_index
    chat_id = ctx.job.chat_id
    topic, prompt = EDUCATIONAL_TOPICS[_edu_index % len(EDUCATIONAL_TOPICS)]
    _edu_index += 1
    
    d = fetch_hrz_price()
    price_ctx = f"Current $HRZ price: ${float(d['price_usd']):.10f}" if d else ""
    
    full_prompt = (
        f"{prompt}\n\n"
        f"{price_ctx}\n\n"
        f"Format for Telegram: Use HTML bold for key terms, emojis for sections, "
        f"max 10 lines, educational tone, end with a practical tip. "
        f"Include relevant $HRZ link when applicable."
    )
    
    content = ask_grok(full_prompt, max_tokens=400)
    if not content:
        return
    
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                f"📚 <b>Crypto Education</b>\n"
                f"{'━'*20}\n\n"
                f"{content}\n\n"
                f"<a href=\'{DEXSCREENER}\'>📊 $HRZ Chart</a> | "
                f"<a href=\'{PANCAKE_BUY}\'>💱 Buy $HRZ</a>"
            ),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Educational post error: {e}")


def ask_gemini(prompt: str, max_tokens: int = 400, temperature: float = 0.85) -> str:
    # Try Gemini first
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}}
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[Gemini failed] {e} → trying Groq...")

    # Fallback to Groq
    try:
        GROQ_KEY = os.getenv("GROQ_KEY", "")
        if not GROQ_KEY:
            return ""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Groq failed] {e}")
        return ""

def generate_post(post_type: str) -> str:
    d = fetch_hrz_price()
    fg = fetch_fear_greed()
    bnb = fetch_bnb_price()
    trend = get_market_trend(d)

    ctx = "No live data."
    if d:
        c24  = float(d["change_24h"] or 0)
        vol  = float(d["volume_24h"] or 0)
        liq  = float(d["liquidity"]  or 0)
        price= float(d["price_usd"]  or 0)
        ctx  = (
            f"Price: ${price:.10f} | 24h: {c24:+.2f}% | "
            f"Vol 24h: ${vol:,.2f} | Liq: ${liq:,.2f} | "
            f"Buys/Sells: {d['txns_buys']}/{d['txns_sells']} | "
            f"FDV: ${float(d['fdv'] or 0):,.2f} | "
            f"F&G: {fg['value']} ({fg['label']}) | "
            f"Trend: {trend} | BNB: ${bnb:.2f}"
        )

    fomo       = random.choice(FOMO_MESSAGES)
    motivation = random.choice(MOTIVATIONS)
    fact       = random.choice(STRAIT_FACTS)
    ath        = _ath_store

    prompts = {
        "price_update": (
            f"Write an exciting Telegram crypto post about HRZ live price. "
            f"Include price with emojis, 24h change, volume, trend. "
            f"Add buy link {PANCAKE_BUY} and chart {DEXSCREENER}. "
            f"End with #HRZ #Hormuz #BNBChain. Use HTML bold for numbers. Max 8 lines. Data: {ctx}"
        ),
        "hype_call": (
            f"Write a viral FOMO Telegram post about HRZ. Mention: early stage, 0% buy tax, "
            f"1yr locked liq, verified contract. Include buy link. FOMO line: '{fomo}'. Max 8 lines. Data: {ctx}"
        ),
        "dex_stats": (
            f"Write a professional DEX stats Telegram post for HRZ. "
            f"Include volume breakdown, liquidity health, buy/sell ratio. "
            f"Mention DexScreener {DEXSCREENER}. Sound like a market analyst. Max 8 lines. Data: {ctx}"
        ),
        "strait_fact": (
            f"Write educational Telegram post starting with: '{fact}' "
            f"Connect brilliantly to $HRZ mission. Educational AND exciting. Max 6 lines."
        ),
        "community_question": (
            f"Write an engaging community question for HRZ Telegram with A/B/C/D options. "
            f"Fun question about HRZ or Hormuz Strait. Mention +XP reward. Max 6 lines."
        ),
        "buy_reminder": (
            f"Write compelling 'why buy HRZ now' post. Highlight: 0% buy tax, verified, locked liq. "
            f"Step-by-step: 1) Get BNB 2) Open PancakeSwap 3) Paste contract. Include buy link. Max 8 lines. Data: {ctx}"
        ),
        "liquidity_info": (
            f"Write a trust-building post about HRZ locked liquidity. "
            f"Explain safety benefits. Include PinkLock proof {PINKLOCK}. Max 6 lines."
        ),
        "comparison": (
            f"Write a post comparing HRZ to typical meme coins. "
            f"HRZ advantages: real inspiration, 0% buy tax, 1yr locked liq, verified, active community. Max 7 lines."
        ),
        "motivation": (
            f"Write powerful motivational post for HRZ holders. Use: '{motivation}' "
            f"Reference Strait of Hormuz theme. Encourage HODLing. Max 6 lines."
        ),
        "chart_update": (
            f"Write exciting chart analysis style post for HRZ. "
            f"Mention price movement, volume trend, buy/sell pressure. "
            f"Use chart emojis 📈📉🕯️. Include DexScreener link. Sound professional. Max 8 lines. Data: {ctx}"
        ),
        "whale_alert_teaser": (
            f"Write mysterious 'whales are watching' post about HRZ. "
            f"Tease that big money might be accumulating. Reference ATH: ${ath['price']:.10f}. Create FOMO. Max 6 lines."
        ),
        "tokenomics": (
            f"Write clear Telegram post explaining HRZ tokenomics: 1B supply, 0% buy, 3% sell, locked liq. "
            f"Explain why investor-friendly. Include contract and buy link. Max 7 lines."
        ),
        "roadmap_teaser": (
            f"Write exciting roadmap teaser for HRZ. "
            f"Hype potential milestones: CoinGecko, CMC, CEX listing, partnerships. Aspirational but realistic. Max 6 lines."
        ),
        "why_hrz": (
            f"Write convincing 'Why HRZ?' post. "
            f"Answer: real inspiration (Strait of Hormuz), strong community, verified, locked, 0% buy tax. Max 7 lines."
        ),
        "fun_fact": (
            f"Write fun crypto trivia post connected to HRZ. "
            f"Start with amazing Strait of Hormuz fact. Connect cleverly to $HRZ potential. Shareable. Max 6 lines."
        ),
        "market_insight": (
            f"Write professional market insight post. Reference Fear & Greed: {fg['value']} ({fg['label']}). "
            f"Explain what current sentiment means for $HRZ. Sound like a strategist. Max 7 lines. Data: {ctx}"
        ),
        "holder_appreciation": (
            f"Write warm appreciation post for HRZ holders. "
            f"Thank early holders, call them 'HRZ Army', mention diamond hands, encourage community growth. Max 6 lines."
        ),
        "fomo_post": (
            f"Write extreme FOMO post about HRZ. Use: '{fomo}' "
            f"Mention ATH ${ath['price']:.10f}. Create urgency to buy NOW. Max 7 lines. Data: {ctx}"
        ),
        "educational": (
            f"Write educational post teaching newcomers about HRZ. "
            f"Cover: what it is, how to buy (PancakeSwap), why safe (verified, locked). "
            f"Include contract {HRZ_CONTRACT} and step-by-step guide. Friendly for beginners. Max 8 lines."
        ),
        "meme_text": (
            f"Write funny but bullish meme-style post about HRZ. "
            f"Use crypto humor, emojis, diamond hands references. Professional yet funny. Include buy link. Max 5 lines."
        ),
    }
    prompt = prompts.get(post_type, prompts["hype_call"])
    return ask_gemini(prompt, max_tokens=300)

# ════════════════════════════════════════════════════════════════════
# ── XP & LEVEL SYSTEM
# ════════════════════════════════════════════════════════════════════

def get_level(xp: int) -> str:
    level = LEVELS[0]
    for threshold, name in sorted(LEVELS.items()):
        if xp >= threshold:
            level = name
    return level

def get_next_level(xp: int):
    for threshold, name in sorted(LEVELS.items()):
        if threshold > xp:
            return threshold, name
    return None

def add_xp(user_id: int, amount: int) -> bool:
    old_level = get_level(_xp_store[user_id])
    _xp_store[user_id] += amount
    new_level = get_level(_xp_store[user_id])
    return old_level != new_level

def get_user_rank(user_id: int) -> int:
    sorted_users = sorted(_xp_store.items(), key=lambda x: x[1], reverse=True)
    for i, (uid, _) in enumerate(sorted_users, 1):
        if uid == user_id:
            return i
    return len(sorted_users) + 1

def can_claim_daily(user_id: int) -> bool:
    today = datetime.now(timezone.utc).date().isoformat()
    return _daily_claim.get(user_id) != today

def claim_daily(user_id: int):
    today = datetime.now(timezone.utc).date().isoformat()
    _daily_claim[user_id] = today

# ════════════════════════════════════════════════════════════════════
# ── SPAM & SAFETY
# ════════════════════════════════════════════════════════════════════

def is_spam(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in SPAM_PATTERNS)

def has_banned_words(text: str) -> bool:
    return any(w in text.lower() for w in BANNED_WORDS)

def is_crypto_related(text: str) -> bool:
    return any(kw in text.lower() for kw in CRYPTO_KEYWORDS)

def can_reply_to_user(user_id: int) -> bool:
    now = time.time()
    last = _reply_cooldown.get(user_id, 0)
    if now - last >= AI_REPLY_COOLDOWN:
        _reply_cooldown[user_id] = now
        return True
    return False

# ════════════════════════════════════════════════════════════════════
# ── REFERRAL SYSTEM HELPERS
# ════════════════════════════════════════════════════════════════════

def generate_referral_code(user_id: int) -> str:
    code = hashlib.md5(f"hrz_{user_id}".encode()).hexdigest()[:8].upper()
    _referral_codes[code] = user_id
    return code

def get_referral_code(user_id: int) -> str:
    for code, uid in _referral_codes.items():
        if uid == user_id:
            return code
    return generate_referral_code(user_id)

def process_referral(new_user_id: int, code: str) -> bool:
    if new_user_id in _referral_used:
        return False
    if code not in _referral_codes:
        return False
    referrer_id = _referral_codes[code]
    if referrer_id == new_user_id:
        return False
    _referral_used[new_user_id] = referrer_id
    _referrals_made[referrer_id].append(new_user_id)
    add_xp(referrer_id, XP_REFERRAL)
    add_xp(new_user_id, 5)
    return True

# ════════════════════════════════════════════════════════════════════
# ── TEXT FORMATTERS
# ════════════════════════════════════════════════════════════════════

def price_text(d: dict) -> str:
    c24 = float(d["change_24h"] or 0)
    c6  = float(d["change_6h"]  or 0)
    c1  = float(d["change_1h"]  or 0)
    c5m = float(d["change_5m"]  or 0)
    arrow = lambda v: "🟢" if v >= 0 else "🔴"
    vol  = float(d["volume_24h"] or 0)
    liq  = float(d["liquidity"]  or 0)
    mcap = float(d["market_cap"] or 0)
    ath  = _ath_store
    return (
        f"🌊 <b>Hormuz (HRZ) — Live Price</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 <code>${float(d['price_usd']):.10f}</code>\n"
        f"🔶 <code>{float(d['price_bnb']):.10f} BNB</code>\n\n"
        f"<b>📊 Price Changes:</b>\n"
        f"{arrow(c5m)} 5m:  <b>{c5m:+.2f}%</b>\n"
        f"{arrow(c1)} 1h:  <b>{c1:+.2f}%</b>\n"
        f"{arrow(c6)} 6h:  <b>{c6:+.2f}%</b>\n"
        f"{arrow(c24)} 24h: <b>{c24:+.2f}%</b>\n\n"
        f"<b>📈 Market Data:</b>\n"
        f"💧 Liquidity: <b>${liq:,.2f}</b>\n"
        f"📊 Vol 24h: <b>${vol:,.2f}</b>\n"
        f"📈 Market Cap: <b>${mcap:,.2f}</b>\n"
        f"🔄 Buys/Sells: <b>{d['txns_buys']}/{d['txns_sells']}</b>\n"
        f"🏆 ATH: <b>${ath['price']:.10f}</b>\n"
        f"📡 Trend: {get_market_trend(d)}\n\n"
        f"<a href='{PANCAKE_BUY}'>💱 Buy HRZ</a> | "
        f"<a href='{DEXSCREENER}'>📊 Chart</a> | "
        f"<a href='{TWITTER}'>🐦 Twitter</a>"
    )

def uptime_str() -> str:
    s = int(time.time() - _bot_start_time)
    return f"{s//86400}d {(s%86400)//3600}h {(s%3600)//60}m"

# ════════════════════════════════════════════════════════════════════
# ── KEYBOARDS
# ════════════════════════════════════════════════════════════════════

def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Price",        callback_data="price"),
            InlineKeyboardButton("📊 Stats",        callback_data="stats"),
            InlineKeyboardButton("😱 Fear & Greed", callback_data="feargreed"),
        ],
        [
            InlineKeyboardButton("💱 Buy HRZ",      url=PANCAKE_BUY),
            InlineKeyboardButton("📉 Chart",        url=DEXSCREENER),
            InlineKeyboardButton("🔍 BscScan",      url=BSCSCAN),
        ],
        [
            InlineKeyboardButton("🌐 Website",      url=WEBSITE),
            InlineKeyboardButton("🐦 Twitter",      url=TWITTER),
            InlineKeyboardButton("🗳️ Vote",         url=COINSNIPER),
        ],
        [
            InlineKeyboardButton("🏆 ATH",          callback_data="ath"),
            InlineKeyboardButton("🎖️ My XP",       callback_data="myxp"),
            InlineKeyboardButton("📋 Contract",     callback_data="contract"),
        ],
        [
            InlineKeyboardButton("🎁 Daily XP",    callback_data="daily"),
            InlineKeyboardButton("🏅 Leaderboard", callback_data="leaderboard"),
            InlineKeyboardButton("🔗 Referral",    callback_data="referral"),
        ],
        [
            InlineKeyboardButton("🎰 Giveaway",    callback_data="giveaway_info"),
            InlineKeyboardButton("📡 Sentiment",   callback_data="sentiment_info"),
            InlineKeyboardButton("ℹ️ About",        callback_data="about"),
        ],
    ])

def buy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Buy on PancakeSwap", url=PANCAKE_BUY)],
        [
            InlineKeyboardButton("📊 Chart",  url=DEXSCREENER),
            InlineKeyboardButton("🔍 Contract", url=BSCSCAN),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="back")],
    ])

# ════════════════════════════════════════════════════════════════════
# ── SCHEDULED JOBS
# ════════════════════════════════════════════════════════════════════

async def scheduled_post(ctx: ContextTypes.DEFAULT_TYPE):
    global _post_index, _total_posts
    chat_id = ctx.job.chat_id
    post_type = POST_TYPES[_post_index % len(POST_TYPES)]
    _post_index += 1
    _total_posts += 1
    post = generate_post(post_type)
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=post,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💱 Buy HRZ", url=PANCAKE_BUY),
                InlineKeyboardButton("📊 Chart",   url=DEXSCREENER),
                InlineKeyboardButton("🐦 Twitter", url=TWITTER),
            ]])
        )
    except Exception as e:
        logger.error(f"Auto post error: {e}")

async def post_to_channel(ctx: ContextTypes.DEFAULT_TYPE):
    global _post_index, _total_posts
    post_type = POST_TYPES[_post_index % len(POST_TYPES)]
    _post_index += 1
    _total_posts += 1
    post = generate_post(post_type)
    try:
        await ctx.bot.send_message(
            chat_id=CHANNEL_ID,
            text=post,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💱 Buy HRZ", url=PANCAKE_BUY),
                InlineKeyboardButton("📊 Chart",   url=DEXSCREENER),
                InlineKeyboardButton("🌐 Website", url=WEBSITE),
            ]])
        )
    except Exception as e:
        logger.error(f"Channel post error: {e}")

async def scheduled_quiz(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.job.chat_id
    q = random.choice(QUIZ_QUESTIONS)
    _quiz_active[chat_id] = {**q, "start_time": time.time()}
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                f"{q['q']}\n\n"
                f"⏰ <b>First correct answer wins +{q.get('xp', 20)} XP!</b> 🎯\n"
                f"<i>Reply with the letter (A/B/C/D) or the answer</i>"
            ),
            parse_mode=ParseMode.HTML
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
        new_buys.append(tx)
    if new_buys:
        _last_seen_tx = txs[0].get("hash", "")
    d = fetch_hrz_price()
    bnb_usd = fetch_bnb_price()
    for tx in reversed(new_buys):
        try:
            value_raw  = int(tx.get("value", 0))
            decimals   = int(tx.get("tokenDecimal", 18))
            amount     = value_raw / (10 ** decimals)
            tx_hash    = tx.get("hash", "")
            buyer_addr = tx.get("to", "")
            usd_val = bnb_val = 0.0
            if d:
                price   = float(d.get("price_usd", 0) or 0)
                usd_val = amount * price
                if bnb_usd > 0:
                    bnb_val = usd_val / bnb_usd
            if usd_val < 0.5:
                continue
            is_whale   = usd_val >= WHALE_THRESHOLD_USD
            buyer_short= buyer_addr[:6] + "..." + buyer_addr[-4:] if len(buyer_addr) > 10 else buyer_addr
            if is_whale:
                header = "🐋🚨 <b>WHALE BUY DETECTED!</b> 🚨🐋"
                footer = "🚀🚀 <b>Big money entering $HRZ!</b>\n#HRZ #Hormuz #WhaleAlert"
            else:
                header = f"🟢 <b>NEW HRZ BUY!</b>"
                footer = "🚀 Welcome to the HRZ family!\n#HRZ #Hormuz #BNBChain"
            msg_text = (
                f"{header}\n\n"
                f"🌊 <b>{amount:,.0f} HRZ</b>\n"
                f"💵 ≈ <b>${usd_val:,.4f}</b>"
                f"{f' ({bnb_val:.4f} BNB)' if bnb_val > 0 else ''}\n"
                f"👤 <code>{buyer_short}</code>\n"
                f"🔗 <a href='https://bscscan.com/tx/{tx_hash}'>View on BscScan</a>\n\n"
                f"{footer}"
            )
            await ctx.bot.send_message(
                chat_id=chat_id,
                text=msg_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💱 Buy Too!", url=PANCAKE_BUY),
                    InlineKeyboardButton("📊 Chart",    url=DEXSCREENER),
                ]])
            )
        except Exception as e:
            logger.error(f"Buy bot tx error: {e}")

async def ath_check_tick(ctx: ContextTypes.DEFAULT_TYPE):
    global _ath_alerted
    chat_id = ctx.job.chat_id
    d = fetch_hrz_price(force=True)
    if not d:
        return
    current = float(d["price_usd"] or 0)
    if current > 0 and current > _ath_alerted * 1.005:
        _ath_alerted = current
        c24 = float(d.get("change_24h", 0) or 0)
        try:
            await ctx.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🏆🚀 <b>NEW ALL-TIME HIGH!</b> 🚀🏆\n\n"
                    f"💵 <b>${current:.10f}</b>\n"
                    f"📈 24h: <b>{c24:+.2f}%</b>\n\n"
                    f"🌊 The Strait has never been this powerful!\n"
                    f"💎 HODL strong, HRZ Army!\n\n"
                    f"<a href='{DEXSCREENER}'>📊 View Chart</a> | "
                    f"<a href='{PANCAKE_BUY}'>💱 Buy Now</a>\n\n"
                    f"#HRZ #Hormuz #ATH #BNBChain 🔥"
                ),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"ATH alert error: {e}")

async def vote_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.job.chat_id
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🗳️ <b>Daily Vote Reminder!</b>\n\n"
                f"Your vote = +{XP_VOTE} XP + helps HRZ rank higher! 🚀\n\n"
                f"Vote now and boost our visibility:\n\n"
                f"• <a href='{COINSNIPER}'>🎯 CoinSniper</a>\n"
                f"• <a href='{GEMFINDER}'>💎 GemFinder</a>\n"
                f"• <a href='{COINHUNT}'>🔍 CoinHunt</a>\n\n"
                f"Type /voted after voting to claim your XP! 🎁"
            ),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Vote reminder error: {e}")

async def daily_report(ctx):
    chat_id = ctx.job.chat_id
    d = fetch_hrz_price()
    if not d:
        return

    price  = float(d.get('price_usd', 0))
    change = float(d.get('change_24h', 0))
    volume = float(d.get('volume_24h', 0))
    buys   = int(d.get('txns_buys', 0))
    sells  = int(d.get('txns_sells', 0))

    prompt = (
        f"Write a brief daily crypto market summary for $HRZ community.\n"
        f"HRZ Data: Price ${price:.10f} | 24h {change:+.2f}% | Vol ${volume:,.0f} | Buys {buys} Sells {sells}\n"
        f"Include: market sentiment, key observation, motivational closing. Max 5 lines. Use emojis."
    )
    summary = ask_grok(prompt, max_tokens=150)

    emoji = "🟢" if change >= 0 else "🔴"

    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=(
                f"📅 <b>Daily HRZ Report</b>\n"
                f"{'━'*22}\n\n"
                f"{emoji} <b>Price:</b> ${price:.10f}\n"
                f"📈 <b>24h:</b> {change:+.2f}%\n"
                f"💧 <b>Volume:</b> ${volume:,.0f}\n"
                f"🔄 <b>Txns:</b> {buys} buys / {sells} sells\n\n"
                f"{summary}\n\n"
                f"<a href='https://dexscreener.com/bsc/0x4E788d423d90A15504455b4FF746B9C1D9951A82'>📊 Chart</a> | "
                f"<a href='https://pancakeswap.finance/swap?outputCurrency=0x4E788d423d90A15504455b4FF746B9C1D9951A82'>💱 Buy</a>"
            ),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"[Daily report error] {e}")


async def cmd_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _ath_alerted
    user    = update.effective_user
    chat_id = update.effective_chat.id
    member  = await ctx.bot.get_chat_member(chat_id, user.id)
    if member.status not in ("creator", "administrator"):
        await update.message.reply_text("❌ Admin only.")
        return
    d = fetch_hrz_price()
    if d:
        _ath_alerted = float(d["price_usd"] or 0)
    name = str(chat_id)
    jobs = [
        (scheduled_post,      POST_INTERVAL,        10,   f"post_{name}"),
        (price_alert_advanced, 300,               10,   f"advalert_{name}"),
        (daily_report,         86400,             60,   f"daily_{name}"),
        (scheduled_quiz,      QUIZ_INTERVAL,         120,  f"quiz_{name}"),
        (buy_bot_tick,        BUY_BOT_INTERVAL,      5,    f"buybot_{name}"),
        (vote_reminder,       VOTE_INTERVAL,         3600, f"vote_{name}"),
        (daily_report,        REPORT_INTERVAL,       7200, f"report_{name}"),
        (ath_check_tick,      ATH_CHECK,             30,   f"ath_{name}"),
        (post_to_channel,     POST_INTERVAL,         15,   f"channel_{name}"),
        (sentiment_post,      SENTIMENT_INTERVAL,    1800, f"sentiment_{name}"),
        (post_leaderboard,    LEADERBOARD_INTERVAL,  900,  f"lb_{name}"),
        (price_alert_tick,    60,                    20,   f"alerts_{name}"),
        (educational_post_v2, 4 * 3600,              300,  f"edu_{name}"),
        (anti_raid_check,     30,                    10,   f"raid_{name}"),
    ]
    for func, interval, first, job_name in jobs:
        ctx.job_queue.run_repeating(
            func, interval=interval, first=first,
            chat_id=chat_id, name=job_name
        )
    await update.message.reply_html(
        f"✅ <b>HRZ Bot v8 — Fully Activated!</b>\n\n"
        f"📢 Auto-posts: every <b>20 min</b>\n"
        f"🧠 Quiz: every <b>1 hour</b>\n"
        f"🟢 Buy alerts: every <b>30 sec</b>\n"
        f"🏆 ATH detection: every <b>5 min</b>\n"
        f"🗳️ Vote reminder: every <b>24 hours</b>\n"
        f"📊 Daily report: every <b>24 hours</b>\n"
        f"📡 Sentiment vote: every <b>6 hours</b>\n"
        f"🏅 Leaderboard: every <b>12 hours</b>\n"
        f"🔔 Price alerts: every <b>1 min</b>\n"
        f"🛡️ Anti-raid: every <b>30 sec</b>\n"
        f"📺 Channel posts: every <b>20 min</b>\n\n"
        f"🌊 <b>The Strait is now ONLINE!</b>"
    )

async def cmd_stopschedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id
    member  = await ctx.bot.get_chat_member(chat_id, user.id)
    if member.status not in ("creator", "administrator"):
        await update.message.reply_text("❌ Admin only.")
        return
    name    = str(chat_id)
    count   = 0
    prefixes= ("post_","quiz_","buybot_","vote_","report_","ath_",
               "channel_","sentiment_","lb_","alerts_","raid_")
    for prefix in prefixes:
        for job in ctx.job_queue.get_jobs_by_name(f"{prefix}{name}"):
            job.schedule_removal()
            count += 1
    await update.message.reply_text(f"🛑 Stopped {count} auto-jobs.")

async def cmd_botstats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    chat_id= update.effective_chat.id
    member = await ctx.bot.get_chat_member(chat_id, user.id)
    if member.status not in ("creator", "administrator"):
        await update.message.reply_text("❌ Admin only.")
        return
    total_xp_users  = len(_xp_store)
    total_xp        = sum(_xp_store.values())
    total_alerts    = sum(len(v) for v in _price_alerts.values())
    total_referrals = sum(len(v) for v in _referrals_made.values())
    suggestions     = len(_suggestion_store)
    sentiment_data  = _sentiment_votes.get(chat_id, {})
    bull = len(sentiment_data.get("bullish", set()))
    bear = len(sentiment_data.get("bearish", set()))
    await update.message.reply_html(
        f"🤖 <b>Bot Statistics</b>\n"
        f"{'━'*20}\n\n"
        f"⏱️ Uptime: <b>{uptime_str()}</b>\n"
        f"📢 Total Posts: <b>{_total_posts}</b>\n"
        f"👥 XP Users: <b>{total_xp_users}</b>\n"
        f"💫 Total XP: <b>{total_xp}</b>\n"
        f"🔔 Active Alerts: <b>{total_alerts}</b>\n"
        f"🔗 Total Referrals: <b>{total_referrals}</b>\n"
        f"💡 Suggestions: <b>{suggestions}</b>\n"
        f"📡 Sentiment: 🟢{bull} / 🔴{bear}\n\n"
        f"🌊 Bot v8 — Running strong!"
    )

async def cmd_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id
    member  = await ctx.bot.get_chat_member(chat_id, user.id)
    if member.status not in ("creator", "administrator"):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a user to warn them.")
        return
    target    = update.message.reply_to_message.from_user
    reason    = " ".join(ctx.args) if ctx.args else "Violation of group rules"
    _warn_store[target.id] += 1
    warns     = _warn_store[target.id]
    if warns >= MAX_WARNS_BEFORE_BAN:
        try:
            await ctx.bot.ban_chat_member(chat_id, target.id)
        except Exception:
            pass
        await update.message.reply_html(
            f"🔨 <b>{target.first_name}</b> has been banned after {warns} warnings!\n"
            f"Reason: {reason}"
        )
    else:
        await update.message.reply_html(
            f"⚠️ <b>Warning {warns}/{MAX_WARNS_BEFORE_BAN}</b> — {target.mention_html()}\n"
            f"Reason: {reason}\n\n"
            f"{'One more warning = BAN!' if warns == MAX_WARNS_BEFORE_BAN - 1 else ''}"
        )

async def cmd_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id
    member  = await ctx.bot.get_chat_member(chat_id, user.id)
    if member.status not in ("creator", "administrator"):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("🔇 Reply to a user to mute them.")
        return
    target   = update.message.reply_to_message.from_user
    mins     = int(ctx.args[0]) if ctx.args else MUTE_DEFAULT_MINS
    until    = datetime.now(timezone.utc) + timedelta(minutes=mins)
    try:
        await ctx.bot.restrict_chat_member(
            chat_id, target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await update.message.reply_html(
            f"🔇 <b>{target.first_name}</b> muted for <b>{mins} minutes</b>."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Mute failed: {e}")

async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id
    member  = await ctx.bot.get_chat_member(chat_id, user.id)
    if member.status not in ("creator", "administrator"):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("🔨 Reply to a user to ban them.")
        return
    target = update.message.reply_to_message.from_user
    reason = " ".join(ctx.args) if ctx.args else "Violation of group rules"
    try:
        await ctx.bot.ban_chat_member(chat_id, target.id)
        await update.message.reply_html(
            f"🔨 <b>{target.first_name}</b> has been banned!\n"
            f"Reason: {reason}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ban failed: {e}")

async def cmd_announce(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    chat_id = update.effective_chat.id
    member  = await ctx.bot.get_chat_member(chat_id, user.id)
    if member.status not in ("creator", "administrator"):
        return
    if not ctx.args:
        await update.message.reply_text("📢 Usage: /announce [message]")
        return
    text = " ".join(ctx.args)
    await ctx.bot.send_message(
        chat_id=chat_id,
        text=(
            f"📢 <b>Official HRZ Announcement</b>\n"
            f"{'━'*25}\n\n"
            f"{text}\n\n"
            f"— <i>HRZ Team</i> 🌊"
        ),
        parse_mode=ParseMode.HTML
    )

# ════════════════════════════════════════════════════════════════════
# ── CALLBACK HANDLER
# ════════════════════════════════════════════════════════════════════

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q       = update.callback_query
    user    = q.from_user
    chat_id = q.message.chat_id
    data    = q.data
    await q.answer()

    # ── Price
    if data == "price":
        d = fetch_hrz_price(force=True)
        if d:
            await q.message.edit_text(
                price_text(d),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=buy_keyboard()
            )
        else:
            await q.answer("❌ Price unavailable", show_alert=True)

    # ── ATH
    elif data == "ath":
        ath = _ath_store
        d   = fetch_hrz_price()
        cur = float(d["price_usd"] or 0) if d else 0
        diff= ((cur - ath["price"]) / ath["price"] * 100) if ath["price"] > 0 else 0
        await q.message.reply_html(
            f"🏆 ATH: <b>${ath['price']:.10f}</b>\n"
            f"📅 {ath.get('date','Unknown')}\n"
            f"💵 Now: <b>${cur:.10f}</b>\n"
            f"📉 From ATH: <b>{diff:+.2f}%</b>"
        )

    # ── Stats
    elif data == "stats":
        d = fetch_hrz_price(force=True)
        if d:
            vol = float(d["volume_24h"] or 0)
            liq = float(d["liquidity"]  or 0)
            c24 = float(d["change_24h"] or 0)
            await q.message.reply_html(
                f"📊 <b>HRZ Quick Stats</b>\n\n"
                f"📊 Vol 24h: <b>${vol:,.2f}</b>\n"
                f"💧 Liquidity: <b>${liq:,.2f}</b>\n"
                f"📈 24h: <b>{c24:+.2f}%</b>\n"
                f"🔄 Buys/Sells: <b>{d['txns_buys']}/{d['txns_sells']}</b>\n"
                f"📡 Trend: {get_market_trend(d)}"
            )

    # ── Fear & Greed
    elif data == "feargreed":
        fg    = fetch_fear_greed()
        value = int(fg["value"]) if str(fg["value"]).isdigit() else 50
        bar   = "█" * (value // 10) + "░" * (10 - value // 10)
        await q.message.reply_html(
            f"😱 <b>Fear & Greed: {fg['value']} ({fg['label']})</b>\n\n"
            f"[{bar}] {value}/100\n\n"
            f"{'📉 Buy opportunity!' if value <= 30 else '📈 Be cautious!' if value >= 80 else '⚖️ Balanced market.'}"
        )

    # ── Contract
    elif data == "contract":
        await q.message.reply_html(
            f"📋 <b>HRZ Contract</b>\n\n"
            f"<code>{HRZ_CONTRACT}</code>\n\n"
            f"✅ Verified | 🔒 Locked | 🌐 BNB Chain\n"
            f"<a href='{BSCSCAN}'>View on BscScan</a>"
        )

    # ── My XP
    elif data == "myxp":
        xp    = _xp_store[user.id]
        level = get_level(xp)
        rank  = get_user_rank(user.id)
        nxt   = get_next_level(xp)
        nxt_t = f"Next: {nxt[1]} at {nxt[0]} XP" if nxt else "MAX LEVEL! 🌟"
        await q.message.reply_html(
            f"🎖️ <b>{user.first_name}'s Profile</b>\n\n"
            f"⭐ Level: <b>{level}</b>\n"
            f"💫 XP: <b>{xp}</b>\n"
            f"🏆 Rank: <b>#{rank}</b>\n"
            f"📈 {nxt_t}"
        )

    # ── Daily XP
    elif data == "daily":
        if not can_claim_daily(user.id):
            await q.answer("⏰ Already claimed today! Come back tomorrow.", show_alert=True)
            return
        claim_daily(user.id)
        bonus   = random.randint(3, 10)
        leveled = add_xp(user.id, bonus)
        await q.answer(
            f"🎁 +{bonus} XP claimed! {'LEVEL UP! 🎉' if leveled else ''}",
            show_alert=True
        )

    # ── Leaderboard
    elif data == "leaderboard":
        top    = sorted(_xp_store.items(), key=lambda x: x[1], reverse=True)[:5]
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
        lines  = ["🏆 <b>Top 5 XP Holders:</b>\n"]
        for i, (uid, xp) in enumerate(top):
            lines.append(f"{medals[i]} #{i+1} — {get_level(xp)} — <b>{xp} XP</b>")
        await q.message.reply_html("\n".join(lines))

    # ── About
    elif data == "about":
        await q.message.reply_html(
            f"🌊 <b>Hormuz (HRZ)</b>\n\n"
            f"Inspired by the world's most strategic waterway.\n"
            f"BNB Chain | 0% Buy Tax | 1yr Locked Liq\n\n"
            f"<a href='{WEBSITE}'>🌐 Website</a> | <a href='{PANCAKE_BUY}'>💱 Buy</a>",
            disable_web_page_preview=True
        )

    # ── Back
    elif data == "back":
        await q.message.edit_reply_markup(reply_markup=main_keyboard())

    # ── Referral Info
    elif data == "referral":
        code = get_referral_code(user.id)
        refs = len(_referrals_made.get(user.id, []))
        bot_info = await ctx.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start=ref_{code}"
        await q.message.reply_html(
            f"🔗 <b>Your Referral Link:</b>\n\n"
            f"<code>{link}</code>\n\n"
            f"📊 Referrals made: <b>{refs}</b>\n"
            f"💫 XP earned: <b>{refs * XP_REFERRAL}</b>\n\n"
            f"Share to earn +{XP_REFERRAL} XP per person!"
        )

    # ── Giveaway Info
    elif data == "giveaway_info":
        giveaway = _giveaway_active.get(chat_id)
        if giveaway:
            entries  = len(giveaway["entries"])
            prize    = giveaway["prize_xp"]
            secs_left= max(0, int(giveaway["end_time"] - time.time()))
            mins, s  = divmod(secs_left, 60)
            you_in   = "✅ You're IN!" if user.id in giveaway["entries"] else "❌ Not entered yet"
            await q.message.reply_html(
                f"🎰 <b>Active Giveaway!</b>\n\n"
                f"🏆 Prize: <b>{prize} XP</b>\n"
                f"👥 Entries: <b>{entries}</b>\n"
                f"⏰ Time left: <b>{mins}m {s}s</b>\n"
                f"Your status: {you_in}\n\n"
                f"Click /giveaway to enter!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎰 Enter!", callback_data="giveaway_enter")
                ]])
            )
        else:
            await q.answer("No active giveaway right now. Stay tuned! 🎰", show_alert=True)

    # ── Giveaway Enter
    elif data == "giveaway_enter":
        giveaway = _giveaway_active.get(chat_id)
        if not giveaway:
            await q.answer("No active giveaway!", show_alert=True)
            return
        if user.id in giveaway["entries"]:
            await q.answer("✅ You're already in! Good luck! 🍀", show_alert=True)
            return
        giveaway["entries"].add(user.id)
        entries = len(giveaway["entries"])
        await q.answer(f"🎰 Entered! You're #{entries} in the giveaway! Good luck! 🍀", show_alert=True)
        try:
            await q.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🎰 Enter! ({entries} entries)", callback_data="giveaway_enter")
                ]])
            )
        except Exception:
            pass

    # ── Sentiment Voting
    elif data in ("sentiment_bull", "sentiment_bear"):
        today = datetime.now(timezone.utc).date().isoformat()
        if chat_id not in _sentiment_votes or _sentiment_votes[chat_id].get("date") != today:
            _sentiment_votes[chat_id] = {
                "bullish": set(), "bearish": set(),
                "date": today, "msg_id": None
            }
        sv = _sentiment_votes[chat_id]
        already_voted = user.id in sv["bullish"] or user.id in sv["bearish"]
        if already_voted:
            await q.answer("✅ Already voted today! Come back tomorrow.", show_alert=True)
            return
        if data == "sentiment_bull":
            sv["bullish"].add(user.id)
            choice = "🟢 Bullish"
        else:
            sv["bearish"].add(user.id)
            choice = "🔴 Bearish"
        add_xp(user.id, XP_VOTE)
        bull = len(sv["bullish"])
        bear = len(sv["bearish"])
        total= bull + bear
        bull_pct = int(bull / total * 100) if total > 0 else 50
        bear_pct = 100 - bull_pct
        await q.answer(f"✅ Voted {choice}! +{XP_VOTE} XP earned! 🎯", show_alert=True)
        try:
            await q.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🟢 Bullish ({bull_pct}%)", callback_data="sentiment_bull"),
                    InlineKeyboardButton(f"🔴 Bearish ({bear_pct}%)", callback_data="sentiment_bear"),
                ]])
            )
        except Exception:
            pass

    # ── Sentiment Info
    elif data == "sentiment_info":
        today = datetime.now(timezone.utc).date().isoformat()
        data_s= _sentiment_votes.get(chat_id, {})
        bull  = len(data_s.get("bullish", set()))
        bear  = len(data_s.get("bearish", set()))
        total = bull + bear
        bp    = int(bull / total * 100) if total > 0 else 50
        await q.message.reply_html(
            f"📡 <b>Today's Sentiment</b>\n\n"
            f"🟢 Bullish: <b>{bull}</b> ({bp}%)\n"
            f"🔴 Bearish: <b>{bear}</b> ({100-bp}%)\n\n"
            f"Vote with /sentiment to earn XP! 🎯"
        )

    # ── Safety
    elif data == "safety":
        await q.message.reply_html(
            f"🛡️ <b>HRZ Safety Checklist</b>\n\n"
            f"✅ Contract verified on BscScan\n"
            f"✅ Liquidity locked 1 year on PinkLock\n"
            f"✅ 0% buy tax — no hidden fees\n"
            f"✅ Open source tokenomics\n"
            f"✅ Active dev & community\n"
            f"✅ Anti-bot measures in place\n\n"
            f"<a href='{BSCSCAN}'>🔍 Verify Contract</a> | "
            f"<a href='{PINKLOCK}'>🔒 Check Lock</a>",
            disable_web_page_preview=True
        )

    # ── Shill
    elif data == "shill":
        shill_text = (
            f"🌊 <b>$HRZ — Hormuz Token</b>\n\n"
            f"Inspired by the world's most strategic strait "
            f"controlling 20% of global oil! 🛢️\n\n"
            f"✅ 0% Buy Tax\n"
            f"🔒 1yr Locked Liquidity\n"
            f"📋 Verified Contract\n"
            f"🌐 BNB Chain\n\n"
            f"💱 Buy: {PANCAKE_BUY}\n"
            f"📊 Chart: {DEXSCREENER}\n"
            f"🐦 Twitter: {TWITTER}\n\n"
            f"#HRZ #Hormuz #BNBChain #GEM 🔥"
        )
        await q.message.reply_html(shill_text, disable_web_page_preview=True)

# ════════════════════════════════════════════════════════════════════
# ── MESSAGE HANDLER
# ════════════════════════════════════════════════════════════════════

async def welcome_member(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        # Anti-raid check
        now = time.time()
        _join_timestamps[chat_id].append(now)
        # Clean old timestamps
        _join_timestamps[chat_id] = [t for t in _join_timestamps[chat_id] if now - t < ANTI_RAID_WINDOW]
        if len(_join_timestamps[chat_id]) >= ANTI_RAID_THRESHOLD and not _raid_mode.get(chat_id):
            _raid_mode[chat_id]       = True
            _raid_mode_until[chat_id] = now + 300  # 5 minutes
            try:
                await ctx.bot.set_chat_permissions(
                    chat_id=chat_id,
                    permissions=ChatPermissions(can_send_messages=False)
                )
                await ctx.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🚨 <b>ANTI-RAID MODE ACTIVATED!</b> 🚨\n\n"
                        f"⚠️ Unusual join activity detected!\n"
                        f"🔒 Group locked for <b>5 minutes</b>.\n"
                        f"Restrictions will be lifted automatically."
                    ),
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Anti-raid activation error: {e}")
            continue
        if _raid_mode.get(chat_id):
            continue
        # Normal welcome
        try:
            await ctx.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🌊 <b>Welcome to HRZ, {member.first_name}!</b>\n\n"
                    f"🚀 You've joined the official Hormuz (HRZ) community!\n\n"
                    f"<b>Quick Start:</b>\n"
                    f"💰 /price — Live price\n"
                    f"💱 /buy — How to buy\n"
                    f"🎖️ /myxp — Your XP level\n"
                    f"🔗 /refer — Earn with referrals\n"
                    f"🔔 /alert — Set price alert\n\n"
                    f"💡 Chat to earn XP and climb the leaderboard!\n"
                    f"🌊 <i>The Strait awaits!</i>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=main_keyboard()
            )
        except Exception as e:
            logger.error(f"Welcome error: {e}")

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user    = update.effective_user
    chat_id = update.effective_chat.id
    text    = update.message.text

    # Lockdown check
    if _lockdown:
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    # Raid mode check
    if _raid_mode.get(chat_id):
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    # Spam check
    if is_spam(text) or has_banned_words(text):
        _warn_store[user.id] += 1
        try:
            await update.message.delete()
        except Exception:
            pass
        try:
            await ctx.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"⚠️ {user.mention_html()} — Message removed (rule violation).\n"
                    f"Warning {_warn_store[user.id]}/{MAX_WARNS_BEFORE_BAN}"
                ),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        if _warn_store[user.id] >= MAX_WARNS_BEFORE_BAN:
            try:
                await ctx.bot.ban_chat_member(chat_id, user.id)
            except Exception:
                pass
        return

    # XP for message
    add_xp(user.id, XP_MESSAGE)

    # Quiz check
    if chat_id in _quiz_active:
        q       = _quiz_active[chat_id]
        answer  = text.strip().lower()
        correct_answers = [a.lower() for a in q.get("answers", [])]
        if answer in correct_answers:
            prize   = q.get("xp", 20)
            leveled = add_xp(user.id, prize)
            del _quiz_active[chat_id]
            try:
                await update.message.reply_html(
                    f"🎉 <b>CORRECT!</b> Well done {user.first_name}!\n\n"
                    f"✅ Answer: <b>{q['correct']}</b>\n"
                    f"💡 Fact: <i>{q.get('fact', '')}</i>\n\n"
                    f"🎁 You earned <b>+{prize} XP!</b>\n"
                    f"{'🆙 <b>LEVEL UP!</b> 🎉' if leveled else ''}"
                )
            except Exception:
                pass
            return

    # AI auto-reply for crypto questions
    if is_crypto_related(text) and len(text) > 15 and "?" in text:
        if can_reply_to_user(user.id):
            try:
                answer = ask_smart(uid, text, fetch_hrz_price())
                await update.message.reply_html(
                    f"🤖 {answer}",
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"AI reply error: {e}")

# ════════════════════════════════════════════════════════════════════
# ── MAIN
# ════════════════════════════════════════════════════════════════════


# ── AIRDROP CONFIG
import datetime as _dt
AIRDROP_CHANNEL   = "HormuzHRZ"
AIRDROP_MAX       = 50
AIRDROP_DAYS      = 5
_airdrop_db       = {}
_airdrop_active   = False
_airdrop_end      = None

async def cmd_startairdrop(update, ctx):
    global _airdrop_active, _airdrop_end, _airdrop_db
    member = await ctx.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ("creator", "administrator"):
        return
    _airdrop_active = True
    _airdrop_end    = _dt.datetime.now() + _dt.timedelta(days=AIRDROP_DAYS)
    _airdrop_db     = {}
    await update.message.reply_html(
        f"🎁 <b>HRZ Airdrop Started!</b>\n\n"
        f"⏰ Ends: {_airdrop_end.strftime('%Y-%m-%d %H:%M')}\n"
        f"👥 Max: {AIRDROP_MAX} participants\n\n"
        f"Users can now join with /airdrop"
    )

async def cmd_airdrop(update, ctx):
    global _airdrop_active, _airdrop_db
    user    = update.effective_user
    user_id = user.id

    if not _airdrop_active:
        await update.message.reply_text("❌ No active airdrop right now. Stay tuned! 🌊")
        return

    if _dt.datetime.now() > _airdrop_end:
        _airdrop_active = False
        await update.message.reply_text("❌ Airdrop has ended!")
        return

    if len(_airdrop_db) >= AIRDROP_MAX:
        await update.message.reply_text("❌ Airdrop is full! 50/50 spots taken.")
        return

    if user_id in _airdrop_db:
        await update.message.reply_text("✅ You are already registered!")
        return

    try:
        member = await ctx.bot.get_chat_member(f"@{AIRDROP_CHANNEL}", user_id)
        if member.status == "left":
            await update.message.reply_html(
                f"❌ You must join our channel first!\n\n"
                f"👉 <a href='https://t.me/{AIRDROP_CHANNEL}'>Join HRZ Channel</a>\n\n"
                f"Then send /airdrop again."
            )
            return
    except Exception:
        await update.message.reply_html(
            f"❌ Please join our channel first!\n\n"
            f"👉 <a href='https://t.me/{AIRDROP_CHANNEL}'>Join HRZ Channel</a>"
        )
        return

    if not ctx.args:
        await update.message.reply_html(
            f"🎁 <b>HRZ Airdrop</b>\n\n"
            f"👥 Spots: {len(_airdrop_db)}/{AIRDROP_MAX}\n"
            f"⏰ Ends: {_airdrop_end.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"Send your BNB wallet address:\n"
            f"<code>/airdrop 0xYourWalletAddress</code>"
        )
        return

    wallet = ctx.args[0].strip()
    if not wallet.startswith("0x") or len(wallet) != 42:
        await update.message.reply_text("❌ Invalid BNB wallet address. Must start with 0x and be 42 characters.")
        return

    if any(v["wallet"] == wallet for v in _airdrop_db.values()):
        await update.message.reply_text("❌ This wallet is already registered!")
        return

    _airdrop_db[user_id] = {
        "username": user.username or user.first_name,
        "wallet":   wallet,
        "time":     _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    await update.message.reply_html(
        f"✅ <b>Successfully Registered!</b>\n\n"
        f"👤 User: @{user.username or user.first_name}\n"
        f"💼 Wallet: <code>{wallet}</code>\n"
        f"🎫 Spot: #{len(_airdrop_db)}/{AIRDROP_MAX}\n\n"
        f"🌊 Good luck! Winners announced after {_airdrop_end.strftime('%Y-%m-%d')}"
    )

async def cmd_airdropstatus(update, ctx):
    if not _airdrop_active:
        await update.message.reply_text("No active airdrop.")
        return
    remaining = (_airdrop_end - _dt.datetime.now()).days
    await update.message.reply_html(
        f"📊 <b>Airdrop Status</b>\n\n"
        f"👥 Registered: {len(_airdrop_db)}/{AIRDROP_MAX}\n"
        f"⏰ Ends in: {remaining} days\n"
        f"🟢 Status: Active"
    )

async def cmd_exportwinners(update, ctx):
    member = await ctx.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ("creator", "administrator"):
        return
    if not _airdrop_db:
        await update.message.reply_text("No participants yet.")
        return
    lines = ["💼 Airdrop Participants — Copy for Multisender:\n"]
    for uid, data in _airdrop_db.items():
        lines.append(f"{data['wallet']}, 1000")
    lines.append(f"\nTotal: {len(_airdrop_db)} wallets")
    await update.message.reply_text("\n".join(lines))

async def cmd_stopairdrop(update, ctx):
    global _airdrop_active
    member = await ctx.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ("creator", "administrator"):
        return
    _airdrop_active = False
    await update.message.reply_text(f"🛑 Airdrop stopped. {len(_airdrop_db)} participants registered.")

def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # ── Commands
    commands = [
        ("start",          cmd_start),
        ("help",           cmd_help),
        ("price",          cmd_price),
        ("stats",          cmd_stats),
        ("buy",            cmd_buy),
        ("ath",            cmd_ath),
        ("feargreed",      cmd_feargreed),
        ("contract",       cmd_contract),
        ("tokenomics",     cmd_tokenomics),
        ("liquidity",      cmd_liquidity),
        ("about",          cmd_about),
        ("links",          cmd_links),
        ("roadmap",        cmd_roadmap),
        ("quiz",           cmd_quiz),
        ("myxp",           cmd_myxp),
        ("daily",          cmd_daily),
        ("voted",          cmd_voted),
        ("leaderboard",    cmd_leaderboard),
        ("ask",            cmd_ask),
        ("suggest",        cmd_suggest),
        ("alert",          cmd_alert),
        ("myalerts",       cmd_myalerts),
        ("cancelalert",    cmd_cancelalert),
        ("refer",          cmd_refer),
        ("sentiment",      cmd_sentiment),
        ("startgiveaway",  cmd_startgiveaway),
        ("endgiveaway",    cmd_endgiveaway),
        ("schedule",       cmd_schedule),
        ("stopschedule",   cmd_stopschedule),
        ("botstats",       cmd_botstats),
        ("warn",           cmd_warn),
        ("mute",           cmd_mute),
        ("ban",            cmd_ban),
        ("announce",       cmd_announce),
        ("clearmemory",    cmd_clearmemory),
        ("mylevel",        cmd_mylevel),
        ("news",           cmd_news),
        ("marketing",      cmd_marketing),
        ("airdrop",        cmd_airdrop),
        ("startairdrop",   cmd_startairdrop),
        ("stopairdrop",    cmd_stopairdrop),
        ("airdropstatus",  cmd_airdropstatus),
        ("exportwinners",  cmd_exportwinners),
        ("analysis",       cmd_analysis),
        ("dashboard",      cmd_dashboard),
        ("referral",       cmd_referral),
        ("topreferrals",   cmd_topreferrals),
    ]

    for name, handler in commands:
        app.add_handler(CommandHandler(name, handler))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, message_handler
    ))

    logger.info("🌊 HRZ Bot v8 — Ultimate Edition Starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
