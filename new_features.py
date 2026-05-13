# ══════════════════════════════════════════════════════
# ── 1. SMART PRICE ALERTS
# ══════════════════════════════════════════════════════

_last_price     = 0.0
_last_volume    = 0.0
_last_alert     = 0.0

async def price_alert_advanced(ctx):
    global _last_price, _last_volume, _last_alert
    import time
    d = fetch_hrz_price()
    if not d:
        return
    try:
        price  = float(d.get('price_usd', 0))
        volume = float(d.get('volume_24h', 0))
        change = float(d.get('change_24h', 0))
        chat_id = ctx.job.chat_id

        # تنبيه تغيير السعر 10%+
        if _last_price > 0:
            price_change = abs((price - _last_price) / _last_price * 100)
            if price_change >= 10 and time.time() - _last_alert > 3600:
                direction = "🚀 PUMPING" if price > _last_price else "📉 DROPPING"
                await ctx.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"⚡ <b>PRICE ALERT!</b>\n\n"
                        f"{direction} <b>{price_change:.1f}%</b>\n\n"
                        f"💰 Price: <b>${price:.10f}</b>\n"
                        f"📊 24h: <b>{change:+.2f}%</b>\n"
                        f"💧 Volume: <b>${volume:,.0f}</b>\n\n"
                        f"<a href='https://dexscreener.com/bsc/0x4E788d423d90A15504455b4FF746B9C1D9951A82'>📊 Chart</a>"
                    ),
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                _last_alert = time.time()

        # تنبيه ارتفاع الحجم 300%+
        if _last_volume > 0:
            vol_change = (volume - _last_volume) / _last_volume * 100
            if vol_change >= 300 and time.time() - _last_alert > 3600:
                await ctx.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🐋 <b>VOLUME SPIKE DETECTED!</b>\n\n"
                        f"📈 Volume increased <b>{vol_change:.0f}%</b>\n"
                        f"💧 Current: <b>${volume:,.0f}</b>\n"
                        f"💰 Price: <b>${price:.10f}</b>\n\n"
                        f"<i>Smart money moving? 👀</i>\n\n"
                        f"<a href='https://dexscreener.com/bsc/0x4E788d423d90A15504455b4FF746B9C1D9951A82'>📊 Chart</a>"
                    ),
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                _last_alert = time.time()

        _last_price  = price
        _last_volume = volume
    except Exception as e:
        print(f"[Alert error] {e}")


# ══════════════════════════════════════════════════════
# ── 2. TECHNICAL ANALYSIS
# ══════════════════════════════════════════════════════

async def cmd_analysis(update, ctx):
    d = fetch_hrz_price()
    if not d:
        await update.message.reply_text("❌ Data unavailable.")
        return

    price  = float(d.get('price_usd', 0))
    change = float(d.get('change_24h', 0))
    volume = float(d.get('volume_24h', 0))
    liq    = float(d.get('liquidity', 0))
    buys   = int(d.get('txns_buys', 0))
    sells  = int(d.get('txns_sells', 0))
    total  = buys + sells if buys + sells > 0 else 1
    buy_pressure = buys / total * 100

    # تحديد الاتجاه
    if change > 5:
        trend = "🟢 Strong Bullish"
    elif change > 0:
        trend = "🟡 Slightly Bullish"
    elif change > -5:
        trend = "🟡 Slightly Bearish"
    else:
        trend = "🔴 Strong Bearish"

    # تحليل الضغط
    if buy_pressure > 65:
        pressure = "🟢 Strong Buy Pressure"
    elif buy_pressure > 50:
        pressure = "🟡 Moderate Buy Pressure"
    else:
        pressure = "🔴 Sell Pressure Dominant"

    # تحليل السيولة
    if liq > 50000:
        liq_status = "🟢 Healthy"
    elif liq > 10000:
        liq_status = "🟡 Moderate"
    else:
        liq_status = "🔴 Low"

    prompt = (
        f"Analyze $HRZ token technically:\n"
        f"Price: ${price:.10f} | 24h: {change:+.2f}%\n"
        f"Volume: ${volume:,.0f} | Liquidity: ${liq:,.0f}\n"
        f"Buys: {buys} | Sells: {sells}\n\n"
        f"Give: trend analysis, key levels, recommendation. Max 6 lines. HTML bold."
    )

    ai_analysis = ask_grok(prompt, max_tokens=200)

    await update.message.reply_html(
        f"📊 <b>$HRZ Technical Analysis</b>\n"
        f"{'━'*22}\n\n"
        f"💰 <b>Price:</b> ${price:.10f}\n"
        f"📈 <b>24h:</b> {change:+.2f}%\n"
        f"💧 <b>Volume:</b> ${volume:,.0f}\n"
        f"🏊 <b>Liquidity:</b> ${liq:,.0f} {liq_status}\n\n"
        f"📉 <b>Trend:</b> {trend}\n"
        f"⚖️ <b>Pressure:</b> {pressure}\n"
        f"🔄 <b>Buys/Sells:</b> {buys}/{sells} ({buy_pressure:.0f}% buys)\n\n"
        f"🤖 <b>AI Analysis:</b>\n{ai_analysis}\n\n"
        f"<a href='https://dexscreener.com/bsc/0x4E788d423d90A15504455b4FF746B9C1D9951A82'>📊 Full Chart</a>",
        disable_web_page_preview=True
    )


# ══════════════════════════════════════════════════════
# ── 3. ADMIN DASHBOARD
# ══════════════════════════════════════════════════════

_user_activity: dict = {}

async def cmd_dashboard(update, ctx):
    from telegram.constants import ParseMode
    member = await ctx.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ("creator", "administrator"):
        await update.message.reply_text("❌ Admin only.")
        return

    d = fetch_hrz_price()
    price  = float(d.get('price_usd', 0)) if d else 0
    change = float(d.get('change_24h', 0)) if d else 0
    volume = float(d.get('volume_24h', 0)) if d else 0

    total_users   = len(_user_activity)
    active_today  = sum(1 for v in _user_activity.values() if v.get('messages', 0) > 0)
    top_users     = sorted(_user_activity.items(), key=lambda x: x[1].get('messages', 0), reverse=True)[:3]

    top_text = ""
    for uid, data in top_users:
        top_text += f"  • @{data.get('username','unknown')}: {data.get('messages',0)} msgs\n"

    await update.message.reply_html(
        f"🎛️ <b>Admin Dashboard</b>\n"
        f"{'━'*22}\n\n"
        f"💰 <b>HRZ Price:</b> ${price:.10f}\n"
        f"📈 <b>24h Change:</b> {change:+.2f}%\n"
        f"💧 <b>Volume:</b> ${volume:,.0f}\n\n"
        f"👥 <b>Total Users:</b> {total_users}\n"
        f"⚡ <b>Active Today:</b> {active_today}\n"
        f"🎁 <b>Airdrop:</b> {len(_airdrop_db)}/{AIRDROP_MAX}\n\n"
        f"🏆 <b>Top Users:</b>\n{top_text}\n"
        f"{'━'*22}\n"
        f"<i>Updated: just now</i>"
    )


# ══════════════════════════════════════════════════════
# ── 4. REFERRAL SYSTEM
# ══════════════════════════════════════════════════════

_referral_data: dict = {}  # user_id -> {"referrer": uid, "count": 0}

async def cmd_referral(update, ctx):
    user    = update.effective_user
    user_id = user.id
    bot_username = (await ctx.bot.get_me()).username

    if user_id not in _referral_data:
        _referral_data[user_id] = {"count": 0, "username": user.username or user.first_name}

    count = _referral_data[user_id].get("count", 0)
    link  = f"https://t.me/{bot_username}?start=ref_{user_id}"

    await update.message.reply_html(
        f"🔗 <b>Your Referral Link</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"👥 <b>You've referred:</b> {count} users\n\n"
        f"📋 <b>How it works:</b>\n"
        f"→ Share your link\n"
        f"→ Each person who joins = +1 referral\n"
        f"→ Top referrers win HRZ rewards! 🏆\n\n"
        f"<i>Keep sharing! 🌊</i>"
    )

async def cmd_topreferrals(update, ctx):
    if not _referral_data:
        await update.message.reply_text("No referrals yet.")
        return
    top = sorted(_referral_data.items(), key=lambda x: x[1].get('count', 0), reverse=True)[:10]
    lines = ["🏆 <b>Top Referrals</b>\n"]
    for i, (uid, data) in enumerate(top, 1):
        medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"{i}."
        lines.append(f"{medal} @{data.get('username','unknown')}: {data.get('count',0)} referrals")
    await update.message.reply_html("\n".join(lines))


# ══════════════════════════════════════════════════════
# ── 5. DAILY REPORT
# ══════════════════════════════════════════════════════

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

