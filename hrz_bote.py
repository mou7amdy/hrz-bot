#!/usr/bin/env python3
"""
🌊 Hormuz (HRZ) Official Telegram Bot v6 — Fixed Edition
"""

import logging
import random
import time
import os
import re
import json
import urllib.request
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

POST_INTERVAL    = 30 * 60
QUIZ_INTERVAL    = 60 * 60
BUY_BOT_INTERVAL = 30
VOTE_INTERVAL    = 24 * 3600
REPORT_INTERVAL  = 24 * 3600
ATH_CHECK        = 5 * 60

PRICE_CACHE_TTL     = 60
WHALE_THRESHOLD_BNB = 0.5
MIN_BUY_BNB         = 0.01

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
    2000: "⚡ HRZ Legend",
}

BADGES = {
    "early_holder":   "🏅 Early Holder",
    "whale":          "🐋 Whale",
    "community_hero": "🦸 Community Hero",
    "quiz_master":    "🧠 Quiz Master",
    "voter":          "🗳️ Loyal Voter",
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

_price_cache      = None
_price_cache_time = 0.0
_last_seen_tx     = ""
_faq_store        = {}
_xp_store         = defaultdict(int)
_badge_store      = defaultdict(set)
_warn_store       = defaultdict(int)
_ath_store        = {"price": 0.0, "date": ""}
_ath_alerted      = 0.0
_lockdown         = False
_quiz_active      = {}
_post_index       = 0
_reply_cooldown   = {}

POST_TYPES = [
    "price_update", "hype_call", "dex_stats", "strait_fact",
    "community_question", "buy_reminder", "liquidity_info",
    "comparison", "motivation", "chart_update",
]

QUIZ_QUESTIONS = [
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhat percentage of global oil passes through the Strait of Hormuz?\n\nA) 10%  B) 20%  C) 30%  D) 40%",
        "answers": ["20", "b", "20%"],
        "correct": "B) 20%",
        "fact": "The Strait of Hormuz controls 20% of the world's oil supply! 🛢️"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhat is HRZ total supply?\n\nA) 100M  B) 500M  C) 1 Billion  D) 10 Billion",
        "answers": ["1000000000", "c", "1 billion", "1b"],
        "correct": "C) 1 Billion",
        "fact": "HRZ total supply is exactly 1,000,000,000 tokens! 🌊"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhat is the HRZ buy tax?\n\nA) 1%  B) 3%  C) 5%  D) 0%",
        "answers": ["0", "d", "0%", "zero"],
        "correct": "D) 0%",
        "fact": "HRZ has ZERO buy tax! ✅"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nWhich blockchain is HRZ on?\n\nA) Ethereum  B) Solana  C) BNB Chain  D) Polygon",
        "answers": ["bnb", "c", "bnb chain", "bsc"],
        "correct": "C) BNB Chain",
        "fact": "HRZ runs on BNB Chain! ⚡"
    },
    {
        "q": "🧠 <b>Quiz Time! +20 XP for first correct answer!</b>\n\nHow long is HRZ liquidity locked?\n\nA) 3 months  B) 6 months  C) 1 year  D) 2 years",
        "answers": ["1", "c", "1 year", "one year"],
        "correct": "C) 1 Year",
        "fact": "HRZ liquidity is locked for 1 full year! 🔒"
    },
]

# ── HELPERS ───────────────────────────────────────────────────────────────────

def http_get(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.error(f"GET {url[:60]}: {e}")
        return None

def fetch_hrz_price(force=False):
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

def fetch_fear_greed():
    data = http_get("https://api.alternative.me/fng/?limit=1")
    if data and data.get("data"):
        d = data["data"][0]
        return {"value": d.get("value", "?"), "label": d.get("value_classification", "?")}
    return {"value": "?", "label": "Unknown"}

def ask_gemini(prompt, max_tokens=400):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    system = (
        f"You are the official English-only AI assistant for Hormuz (HRZ) crypto token on BNB Chain. "
        f"Contract: {HRZ_CONTRACT} | Buy: {PANCAKE_BUY} | Chart: {DEXSCREENER} | Website: {WEBSITE} | "
        f"Total Supply: 1,000,000,000 HRZ | Buy Tax: 0% | Sell Tax: 3% | "
        f"Liquidity: Locked 1 Year | Contract: Verified on BscScan | Network: BNB Chain | "
        f"Launched: May 2026 | Inspired by the Strait of Hormuz — controlling 20% of global oil. "
        f"ALWAYS respond in English only. Be enthusiastic and helpful. "
        f"Keep responses short (max 4 sentences). End with a relevant emoji."
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": f"{system}\n\nUser: {prompt}"}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.85}
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "⚠️ AI temporarily unavailable. Try again shortly! 🌊"

def generate_post(post_type):
    d = fetch_hrz_price()
    fg = fetch_fear_greed()
    ctx = ""
    if d:
        c24 = float(d['change_24h']) if d['change_24h'] else 0
        ctx = (
            f"Price: ${float(d['price_usd']):.10f} | 24h: {c24:+.2f}% | "
            f"Vol: ${float(d['volume_24h']):,.2f} | Liq: ${float(d['liquidity']):,.2f} | "
            f"Buys/Sells: {d['txns_buys']}/{d['txns_sells']} | Fear&Greed: {fg['value']}"
        )
    prompts = {
        "price_update": f"Write an exciting Telegram post about HRZ price. Include price, 24h change, volume. Add buy and chart links. Max 6 lines. End with #HRZ #Hormuz #BNBChain. Context: {ctx}",
        "hype_call": f"Write a viral FOMO Telegram post about HRZ. Mention early stage, verified contract, locked liquidity. Include contract and PancakeSwap link. Max 6 lines. Context: {ctx}",
        "dex_stats": f"Write a Telegram post showing HRZ DEX stats. Include volume, liquidity, buys vs sells. Add DexScreener link. Max 6 lines. Context: {ctx}",
        "strait_fact": "Write a fascinating fact about the Strait of Hormuz and connect it to HRZ token. Educational and engaging. Max 5 lines.",
        "community_question": "Write an engaging question for the HRZ Telegram community to boost interaction. Add A) B) C) options. Max 5 lines.",
        "buy_reminder": f"Write a 'why buy HRZ now' post. Highlight: 0% buy tax, verified, locked liquidity, early stage. Include PancakeSwap link. Max 6 lines. Context: {ctx}",
        "liquidity_info": f"Write a trust-building post about HRZ locked liquidity. Explain what it means for investors. Max 5 lines. Context: {ctx}",
        "comparison": "Write a post comparing HRZ to other meme coins. Highlight: real Strait of Hormuz inspiration, 0% buy tax, locked liquidity. Max 6 lines.",
        "motivation": f"Write a motivational post for HRZ holders. Keep them excited. Reference Strait of Hormuz. Max 5 lines. Context: {ctx}",
        "chart_update": f"Write an exciting chart analysis for HRZ. Mention price movement, volume, what it means. Include DexScreener link. Max 6 lines. Context: {ctx}",
    }
    prompt = prompts.get(post_type, prompts["hype_call"])
    return ask_gemini(prompt, max_tokens=250)

def get_level(xp):
    level = LEVELS[0]
    for threshold, name in sorted(LEVELS.items()):
        if xp >= threshold:
            level = name
    return level

def add_xp(user_id, amount):
    _xp_store[user_id] += amount

def add_badge(user_id, badge):
    _badge_store[user_id].add(badge)

def is_spam(text):
    return any(re.search(p, text, re.IGNORECASE) for p in SPAM_PATTERNS)

def has_banned_words(text):
    return any(word in text.lower() for word in BANNED_WORDS)

def can_reply_to_user(user_id):
    now = time.time()
    last = _reply_cooldown.get(user_id, 0)
    if now - last >= 300:
        _reply_cooldown[user_id] = now
        return True
    return False

def price_text(d):
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

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Price",     callback_data="price"),
            InlineKeyboardButton("📊 Stats",     callback_data="stats"),
            InlineKeyboardButton("😱 Sentiment", callback_data="feargreed"),
        ],
        [
            InlineKeyboardButton("💱 Buy HRZ",   url=PANCAKE_BUY),
            InlineKeyboardButton("📉 Chart",     url=DEXSCREENER),
        ],
        [
            InlineKeyboardButton("🌐 Website",   url=WEBSITE),
            InlineKeyboardButton("🐦 Twitter",   url=TWITTER),
            InlineKeyboardButton("🗳️ Vote",      url=COINSNIPER),
        ],
        [
            InlineKeyboardButton("🏆 ATH",       callback_data="ath"),
            InlineKeyboardButton("🎖️ My XP",    callback_data="myxp"),
            InlineKeyboardButton("📋 Contract",  callback_data="contract"),
        ],
    ])

# ── SCHEDULED JOBS (defined BEFORE cmd_schedule) ──────────────────────────────

async def scheduled_post(ctx: ContextTypes.DEFAULT_TYPE):
    global _post_index
    chat_id = ctx.job.chat_id
    post_type = POST_TYPES[_post_index % len(POST_TYPES)]
    _post_index += 1
    post = generate_post(post_type)
    try:
        await ctx.bot.send_message(
            chat_id=chat_id, text=post, parse_mode="HTML",
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
    global _post_index
    post_type = POST_TYPES[_post_index % len(POST_TYPES)]
    _post_index += 1
    post = generate_post(post_type)
    try:
        await ctx.bot.send_message(
            chat_id=CHANNEL_ID, text=post, parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💱 Buy HRZ", url=PANCAKE_BUY),
                InlineKeyboardButton("📊 Chart",   url=DEXSCREENER),
            ]])
        )
    except Exception as e:
        logger.error(f"Channel post error: {e}")

async def scheduled_quiz(ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = ctx.job.chat_id
    q = random.choice(QUIZ_QUESTIONS)
    _quiz_active[chat_id] = q
    try:
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=f"{q['q']}\n\n⏰ <b>First correct answer wins +{XP_QUIZ_WIN} XP!</b> 🎯",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Quiz error: {e}")

async def buy_bot_tick(ctx: ContextTypes.DEFAULT_TYPE):
    global _last_seen_tx
    chat_id = ctx.job.chat_id
    data = http_get(
        f"https://api.bscscan.com/api?module=account&action=tokentx"
        f"&contractaddress={HRZ_CONTRACT}&sort=desc&offset=5&page=1"
    )
    if not data or not isinstance(data.get("result"), list):
        return
    txs = data["result"]
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
            header = "🐋 <b>WHALE BUY DETECTED!</b> 🐋" if is_whale else "🟢 <b>NEW HRZ BUY!</b>"
            footer = "🚀🚀 Big money entering $HRZ!" if is_whale else "🚀 Welcome new holder!"
            buyer = tx.get("to", "")[:8] + "..."
            await ctx.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"{header}\n\n"
                    f"🌊 <b>{amount:,.0f} HRZ</b>\n"
                    f"💵 ~<b>${usd_val:,.4f}</b> ({bnb_val:.4f} BNB)\n"
                    f"👤 <code>{buyer}</code>\n"
                    f"🔗 <a href='https://bscscan.com/tx/{tx_hash}'>View Tx</a>\n\n{footer}"
                ),
                parse_mode="HTML", disable_web_page_preview=True,
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
                    f"🌊 Hormuz (HRZ) is making history! #HRZ #ATH"
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
                f"Help HRZ reach more investors!\n"
                f"Takes only 10 seconds! 🎖️\n\n"
                f"<a href='{COINSNIPER}'>Vote on CoinSniper!</a>\n\n"
                f"Use /vote to earn +{XP_VOTE} XP! 🚀"
            ),
            parse_mode="HTML", disable_web_page_preview=True
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
                f"☀️ <b>HRZ Daily Report</b>\n"
                f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d UTC')}\n\n"
                f"💵 Price: <b>${float(d['price_usd']):.10f}</b>\n"
                f"{arrow} 24h: <b>{c24:+.2f}%</b>\n"
                f"📊 Vol 24h: <b>${float(d['volume_24h']):,.2f}</b>\n"
                f"💧 Liquidity: <b>${float(d['liquidity']):,.2f}</b>\n"
                f"😱 Fear & Greed: <b>{fg['value']} — {fg['label']}</b>\n\n"
                f"#HRZ #Hormuz #BNBChain #DailyReport"
            ),
            parse_mode="HTML", disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Daily report: {e}")

# ── COMMANDS ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    add_badge(update.effective_user.id, "early_holder")
    await update.message.reply_html(
        "🌊 <b>Hormuz (HRZ) Bot v6</b>\n\n"
        "📢 Auto-posts every <b>20 minutes</b>\n"
        "🧠 Quiz every <b>hour</b>\n"
        "🐋 Whale & Buy alerts\n"
        "🏆 ATH detection\n\n"
        "Type /schedule to activate!\nType /help for commands.",
        reply_markup=main_keyboard()
    )

async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    msg = await update.message.reply_text("⏳ Fetching live price...")
    d = fetch_hrz_price(force=True)
    if not d:
        await msg.edit_text("❌ Price unavailable. Check DexScreener.", parse_mode="HTML")
        return
    await msg.edit_text(
        price_text(d), parse_mode="HTML", disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💱 Buy", url=PANCAKE_BUY),
            InlineKeyboardButton("📊 Chart", url=DEXSCREENER)
        ]])
    )

async def cmd_buy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    await update.message.reply_html(
        f"💱 <b>How to Buy HRZ</b>\n\n"
        f"1️⃣ Get BNB on BNB Chain\n"
        f"2️⃣ Open PancakeSwap\n"
        f"3️⃣ Paste contract:\n<code>{HRZ_CONTRACT}</code>\n\n"
        f"⚙️ Slippage: <b>5-10%</b>\n✅ Buy Tax: <b>0%</b>\n\n"
        f"<a href='{PANCAKE_BUY}'>Open PancakeSwap Now</a>",
        disable_web_page_preview=True
    )

async def cmd_contract(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        f"📍 <b>HRZ Contract</b>\n\n<code>{HRZ_CONTRACT}</code>\n\n"
        f"✅ Verified | 🔒 Locked 1yr | 0% Buy Tax | 3% Sell Tax\n\n"
        f"<a href='{PANCAKE_BUY}'>Buy</a> | <a href='{DEXSCREENER}'>Chart</a> | <a href='{BSCSCAN}'>BSCScan</a>",
        disable_web_page_preview=True
    )

async def cmd_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        f"🌊 <b>About Hormuz (HRZ)</b>\n\n"
        f"Inspired by the Strait of Hormuz — controlling 20% of global oil.\n\n"
        f"• Ticker: <b>HRZ</b> | Chain: <b>BNB Chain</b>\n"
        f"• Supply: <b>1,000,000,000</b>\n"
        f"• Buy Tax: <b>0%</b> | Sell Tax: <b>3%</b>\n"
        f"• Contract: Verified ✅ | Liquidity: Locked 🔒\n\n"
        f"<a href='{WEBSITE}'>Website</a> | <a href='{PANCAKE_BUY}'>Buy</a> | <a href='{TWITTER}'>Twitter</a>",
        disable_web_page_preview=True
    )

async def cmd_ath(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = fetch_hrz_price()
    ath = _ath_store
    current = float(d["price_usd"]) if d else 0
    distance = ((ath["price"] - current) / ath["price"] * 100) if ath["price"] > 0 else 0
    await update.message.reply_html(
        f"🏆 <b>HRZ All-Time High</b>\n\n"
        f"ATH: <b>${ath['price']:.10f}</b>\n"
        f"Date: <b>{ath['date'] or 'Tracking...'}</b>\n\n"
        f"📍 Current: <b>${current:.10f}</b>\n"
        f"{'🚀 AT ATH!' if current >= ath['price'] * 0.99 else f'📉 {distance:.1f}% below ATH'}"
    )

async def cmd_vote(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_VOTE)
    add_badge(update.effective_user.id, "voter")
    await update.message.reply_html(
        f"🗳️ <b>Vote for HRZ!</b>\n\nTakes 10 seconds!\n\n"
        f"<a href='{COINSNIPER}'>Vote Now!</a>\n\n✅ +{XP_VOTE} XP earned!",
        disable_web_page_preview=True
    )

async def cmd_shill(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    d = fetch_hrz_price()
    price = f"${float(d['price_usd']):.10f}" if d else "Check DexScreener"
    await update.message.reply_html(
        f"📣 <b>Copy & Share!</b>\n\n"
        f"🌊 <b>Hormuz (HRZ) — BNB Chain Gem!</b>\n\n"
        f"💵 Price: {price}\n"
        f"✅ Verified | ✅ Liquidity Locked 1yr | ✅ 0% Buy Tax\n\n"
        f"<code>{HRZ_CONTRACT}</code>\n\n"
        f"💱 {PANCAKE_BUY}\n📊 {DEXSCREENER}\n\n"
        f"#HRZ #Hormuz #BNBChain #BSCGems",
        disable_web_page_preview=True
    )

async def cmd_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_xp(update.effective_user.id, XP_COMMAND)
    question = " ".join(ctx.args) if ctx.args else ""
    if not question:
        await update.message.reply_html(
            "🤖 Usage: <code>/ask your question</code>\n\nExample: <code>/ask Is HRZ safe?</code>"
        )
        return
    thinking = await update.message.reply_text("🤖 Thinking...")
    answer = ask_gemini(question)
    await thinking.edit_text(answer, parse_mode="HTML", disable_web_page_preview=True)

async def cmd_myxp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    xp = _xp_store[uid]
    level = get_level(xp)
    badges = _badge_store.get(uid, set())
    badge_text = " ".join([BADGES.get(b, b) for b in badges]) if badges else "None yet"
    await update.message.reply_html(
        f"🎖️ <b>Your HRZ Rank</b>\n\n"
        f"⚡ XP: <b>{xp}</b>\n"
        f"🏅 Level: <b>{level}</b>\n"
        f"🎀 Badges: {badge_text}"
    )

async def cmd_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _xp_store:
        await update.message.reply_text("🏆 No XP yet — start chatting!")
        return
    top = sorted(_xp_store.items(), key=lambda x: x[1], reverse=True)[:10]
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    lines = ["🏆 <b>HRZ Leaderboard</b>\n"]
    for i, (uid, xp) in enumerate(top):
        lines.append(f"{medals[i]} <b>{xp} XP</b> — {get_level(xp)}")
    await update.message.reply_html("\n".join(lines))

async def cmd_rules(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "📋 <b>HRZ Community Rules</b>\n\n"
        "1️⃣ No spam or external links\n"
        "2️⃣ No FUD or scam accusations\n"
        "3️⃣ Respect all members\n"
        "4️⃣ English only\n"
        "5️⃣ No unsolicited DMs\n"
        "6️⃣ DYOR — Not financial advice\n\n"
        "⚠️ Violations: Warning → Mute → Ban"
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "<b>📋 HRZ Bot — All Commands</b>\n\n"
        "/price — Live price\n/ath — All-time high\n"
        "/buy — How to buy\n/contract — Contract\n"
        "/info — About HRZ\n/rules — Rules\n"
        "/vote — Vote (+XP)\n/shill — Promo message\n"
        "/ask [q] — Ask AI\n/myxp — Your XP\n"
        "/leaderboard — Top 10\n\n"
        "<b>Admin:</b>\n"
        "/warn /mute /unmute /ban\n"
        "/slowmode /lockdown\n"
        "/schedule /stopschedule"
    )

# ── ADMIN COMMANDS ────────────────────────────────────────────────────────────

async def is_admin(update, ctx):
    try:
        member = await ctx.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

async def cmd_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message to warn.")
        return
    target = update.message.reply_to_message.from_user
    reason = " ".join(ctx.args) if ctx.args else "No reason"
    _warn_store[target.id] += 1
    warns = _warn_store[target.id]
    if warns >= 3:
        try:
            await ctx.bot.ban_chat_member(update.effective_chat.id, target.id)
            await update.message.reply_html(f"🚫 <b>{target.full_name}</b> BANNED after 3 warnings!")
        except Exception as e:
            await update.message.reply_text(f"❌ Cannot ban: {e}")
    else:
        await update.message.reply_html(f"⚠️ Warning {warns}/3 — {target.full_name}\nReason: {reason}")

async def cmd_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to mute.")
        return
    target = update.message.reply_to_message.from_user
    duration = int(ctx.args[0]) if ctx.args else 60
    until = datetime.now(timezone.utc) + timedelta(minutes=duration)
    try:
        await ctx.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=False), until_date=until
        )
        await update.message.reply_html(f"🔇 <b>{target.full_name}</b> muted for {duration} minutes.")
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot mute: {e}")

async def cmd_unmute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to unmute.")
        return
    target = update.message.reply_to_message.from_user
    try:
        await ctx.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True)
        )
        await update.message.reply_html(f"🔊 <b>{target.full_name}</b> unmuted.")
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot unmute: {e}")

async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to ban.")
        return
    target = update.message.reply_to_message.from_user
    reason = " ".join(ctx.args) if ctx.args else "No reason"
    try:
        await ctx.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_html(f"🚫 <b>{target.full_name}</b> BANNED. Reason: {reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot ban: {e}")

async def cmd_slowmode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    seconds = int(ctx.args[0]) if ctx.args else 0
    try:
        await ctx.bot.set_chat_slow_mode_delay(update.effective_chat.id, seconds)
        await update.message.reply_html(f"🐢 Slow mode: <b>{seconds}s</b>" if seconds else "✅ Slow mode disabled")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_lockdown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _lockdown
    if not await is_admin(update, ctx):
        await update.message.reply_text("❌ Admins only.")
        return
    _lockdown = not _lockdown
    msg = "🔒 <b>LOCKDOWN ACTIVATED!</b>" if _lockdown else "🔓 <b>Lockdown lifted!</b>"
    await update.message.reply_html(msg)

# ── WELCOME & MESSAGE HANDLER ─────────────────────────────────────────────────

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
                f"💵 Price: <b>{price}</b>\n"
                f"🎖️ Early Holder badge earned!\n\n"
                f"/buy — How to buy | /help — Commands\n\n"
                f"<a href='{PANCAKE_BUY}'>💱 Buy HRZ</a> | <a href='{DEXSCREENER}'>📊 Chart</a>",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Welcome: {e}")

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    if update.channel_post or update.edited_channel_post:
        return
    chat_type = update.effective_chat.type
    if not update.effective_user or update.effective_user.is_bot:
        return
    uid = update.effective_user.id
    chat_id = update.effective_chat.id

    admin = False
    if chat_type in ("group", "supergroup"):
        try:
            member = await ctx.bot.get_chat_member(chat_id, uid)
            admin = member.status in ("administrator", "creator")
        except Exception:
            pass

    if _lockdown and not admin:
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    if not admin:
        if is_spam(text):
            try:
                await update.message.delete()
                _warn_store[uid] += 1
                await ctx.bot.send_message(
                    chat_id,
                    f"🚫 No external links! Warning {_warn_store[uid]}/3",
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

    if chat_id in _quiz_active:
        q = _quiz_active[chat_id]
        for ans in q["answers"]:
            if ans.lower() in text.lower():
                del _quiz_active[chat_id]
                add_xp(uid, XP_QUIZ_WIN)
                add_badge(uid, "quiz_master")
                try:
                    await update.message.reply_html(
                        f"🎉 <b>{update.effective_user.first_name}</b> got it!\n\n"
                        f"✅ Correct: <b>{q['correct']}</b>\n"
                        f"💡 {q['fact']}\n\n🎖️ +{XP_QUIZ_WIN} XP!"
                    )
                except Exception:
                    pass
                break

    if can_reply_to_user(uid) and len(text.strip()) >= 3 and not text.startswith("/"):
        try:
            d = fetch_hrz_price()
            price_ctx = f"Current HRZ price: ${float(d['price_usd']):.10f}" if d else ""
            prompt = (
                f"Community message: '{text}'\n{price_ctx}\n"
                f"Give a helpful English reply about HRZ. Short (2-3 sentences max)."
            )
            answer = ask_gemini(prompt, max_tokens=150)
            await update.message.reply_html(answer, disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"AI reply: {e}")

# ── CALLBACK BUTTONS ──────────────────────────────────────────────────────────

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "price":
        d = fetch_hrz_price()
        text = price_text(d) if d else "❌ Price unavailable."
        await query.edit_message_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=main_keyboard())
    elif query.data == "stats":
        d = fetch_hrz_price()
        if d:
            text = (
                f"📊 <b>HRZ Stats</b>\n\n"
                f"Vol 6h: <b>${float(d['volume_6h']):,.2f}</b>\n"
                f"Vol 24h: <b>${float(d['volume_24h']):,.2f}</b>\n"
                f"Liquidity: <b>${float(d['liquidity']):,.2f}</b>\n"
                f"Buys: <b>{d['txns_buys']}</b> | Sells: <b>{d['txns_sells']}</b>"
            )
        else:
            text = "❌ Stats unavailable."
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
    elif query.data == "feargreed":
        fg = fetch_fear_greed()
        val = int(fg["value"]) if str(fg["value"]).isdigit() else 50
        emoji = "😱 Extreme Fear" if val<=25 else "😨 Fear" if val<=45 else "😐 Neutral" if val<=55 else "😊 Greed" if val<=75 else "🤑 Extreme Greed"
        await query.edit_message_text(
            f"😱 <b>Fear & Greed Index</b>\n\nScore: <b>{fg['value']}/100</b>\nStatus: <b>{emoji}</b>",
            parse_mode="HTML", reply_markup=main_keyboard()
        )
    elif query.data == "ath":
        d = fetch_hrz_price()
        current = float(d["price_usd"]) if d else 0
        ath = _ath_store
        distance = ((ath["price"] - current) / ath["price"] * 100) if ath["price"] > 0 else 0
        await query.edit_message_text(
            f"🏆 <b>HRZ ATH</b>\n\nATH: <b>${ath['price']:.10f}</b>\nDate: <b>{ath['date'] or 'Tracking...'}</b>\n\nCurrent: <b>${current:.10f}</b>\n📉 {distance:.1f}% below ATH",
            parse_mode="HTML", reply_markup=main_keyboard()
        )
    elif query.data == "myxp":
        uid = query.from_user.id
        xp = _xp_store[uid]
        badges = _badge_store.get(uid, set())
        badge_text = " ".join([BADGES.get(b, b) for b in badges]) if badges else "None yet"
        await query.edit_message_text(
            f"🎖️ <b>Your Rank</b>\n\n⚡ XP: <b>{xp}</b>\n🏅 Level: <b>{get_level(xp)}</b>\n🎀 Badges: {badge_text}",
            parse_mode="HTML", reply_markup=main_keyboard()
        )
    elif query.data == "contract":
        await query.edit_message_text(
            f"📍 <b>HRZ Contract</b>\n\n<code>{HRZ_CONTRACT}</code>\n\n✅ Verified | 🔒 Locked 1yr | 0% Buy Tax",
            parse_mode="HTML", reply_markup=main_keyboard()
        )

# ── SCHEDULE COMMANDS ─────────────────────────────────────────────────────────

async def cmd_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _ath_alerted
    chat_id = update.effective_chat.id
    name = str(chat_id)

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
        f"✅ <b>HRZ Bot Fully Activated!</b>\n\n"
        f"📢 Auto-posts: every <b>20 min</b>\n"
        f"🧠 Quiz: every <b>hour</b>\n"
        f"🟢 Buy alerts: every <b>30s</b>\n"
        f"🏆 ATH detection: every <b>5 min</b>\n"
        f"📊 Daily report: every <b>24h</b>\n"
        f"📣 Channel posts: every <b>20 min</b>\n\n"
        f"🌊 The strait is now online!"
    )

async def cmd_stop_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = str(update.effective_chat.id)
    count = 0
    for prefix in ("post_", "quiz_", "buybot_", "vote_", "report_", "ath_", "channel_"):
        for job in ctx.job_queue.get_jobs_by_name(f"{prefix}{name}"):
            job.schedule_removal()
            count += 1
    await update.message.reply_text(f"🛑 {count} auto jobs stopped.")

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()

    commands = [
        ("start",        cmd_start),
        ("price",        cmd_price),
        ("ath",          cmd_ath),
        ("buy",          cmd_buy),
        ("contract",     cmd_contract),
        ("info",         cmd_info),
        ("rules",        cmd_rules),
        ("vote",         cmd_vote),
        ("shill",        cmd_shill),
        ("ask",          cmd_ask),
        ("myxp",         cmd_myxp),
        ("leaderboard",  cmd_leaderboard),
        ("help",         cmd_help),
        ("warn",         cmd_warn),
        ("mute",         cmd_mute),
        ("unmute",       cmd_unmute),
        ("ban",          cmd_ban),
        ("slowmode",     cmd_slowmode),
        ("lockdown",     cmd_lockdown),
        ("schedule",     cmd_schedule),
        ("stopschedule", cmd_stop_schedule),
    ]

    for cmd, func in commands:
        app.add_handler(CommandHandler(cmd, func))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("🌊 Hormuz Bot v6 — Running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
