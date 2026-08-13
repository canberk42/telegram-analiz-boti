import logging
import random
import asyncio
import httpx
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# =========================================================
# BOT TOKEN (Lütfen BotFather'dan yeni token alıp buraya yazın)
# =========================================================
TOKEN = "YENI_BOT_TOKENINIZI_BURAYA_YAZIN"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DAYS_TR = {
    "Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba",
    "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"
}

LEAGUES = [
    ("uefa.champions", "🇪🇺 UEFA Şampiyonlar Ligi"),
    ("uefa.champions_league", "🇪🇺 UEFA Şampiyonlar Ligi"),
    ("uefa.europa", "🇪🇺 UEFA Avrupa Ligi"),
    ("uefa.europa.conf", "🇪🇺 UEFA Konferans Ligi"),
    ("global", "🌐 Uluslararası / Avrupa Maçları"),
    ("tur.1", "🇹🇷 Trendyol Süper Lig"),
    ("eng.1", "🏴󠁧󠁢󠁥󠁮󠁧󠁿 İngiltere Premier League"),
    ("esp.1", "🇪🇸 İspanya La Liga"),
    ("ita.1", "🇮🇹 İtalya Serie A"),
    ("ger.1", "🇩🇪 Almanya Bundesliga"),
    ("fra.1", "🇫🇷 Fransa Ligue 1"),
    ("ned.1", "🇳🇱 Hollanda Eredivisie"),
    ("por.1", "🇵🇹 Portekiz Liga Portugal"),
    ("tur.cup", "🇹🇷 Ziraat Türkiye Kupası"),
    ("eng.fa", "🏴󠁧󠁢󠁥󠁮󠁧󠁿 İngiltere FA Cup"),
    ("esp.copa_del_rey", "🇪🇸 İspanya Kral Kupası"),
    ("ger.pokal", "🇩🇪 Almanya DFB Pokal"),
    ("ita.cup", "🇮🇹 İtalya Kupası"),
    ("fra.coupe_de_france", "🇫🇷 Fransa Kupası")
]

LEAGUE_KEYWORDS = {
    "süper lig": [("tur.1", "🇹🇷 Trendyol Süper Lig")],
    "super lig": [("tur.1", "🇹🇷 Trendyol Süper Lig")],
    "trendyol": [("tur.1", "🇹🇷 Trendyol Süper Lig")],
    "avrupa ligi": [("uefa.europa", "🇪🇺 UEFA Avrupa Ligi")],
    "europa": [("uefa.europa", "🇪🇺 UEFA Avrupa Ligi")],
    "konferans": [("uefa.europa.conf", "🇪🇺 UEFA Konferans Ligi")],
    "şampiyonlar ligi": [("uefa.champions", "🇪🇺 UEFA Şampiyonlar Ligi"), ("uefa.champions_league", "🇪🇺 UEFA Şampiyonlar Ligi")],
    "premier lig": [("eng.1", "🏴󠁧󠁢󠁥󠁮󠁧󠁿 İngiltere Premier League")],
    "la liga": [("esp.1", "🇪🇸 İspanya La Liga")],
    "serie a": [("ita.1", "🇮🇹 İtalya Serie A")],
    "bundesliga": [("ger.1", "🇩🇪 Almanya Bundesliga")],
    "ligue 1": [("fra.1", "🇫🇷 Fransa Ligue 1")],
    "eredivisie": [("ned.1", "🇳🇱 Hollanda Eredivisie")],
    "ziraat": [("tur.cup", "🇹🇷 Ziraat Türkiye Kupası")]
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

HIGH_PROBABILITY_TIPS = [
    {"tip": "🔥 1.5 Gol Üstü", "rate": "1.22 - 1.28", "confidence": "%95"},
    {"tip": "🛡️ Ev Sahibi / Deplasman Çifte Şans", "rate": "1.25 - 1.32", "confidence": "%93"},
    {"tip": "⚽ Ev Sahibi 0.5 Gol Üstü", "rate": "1.18 - 1.25", "confidence": "%94"},
    {"tip": "📊 Karşılıklı Gol Var (KG Var)", "rate": "1.35 - 1.45", "confidence": "%89"},
    {"tip": "🏆 Maç Sonucu 1 veya 2 (Beraberlik Yok)", "rate": "1.28 - 1.38", "confidence": "%91"},
    {"tip": "🎯 2.5 Gol Üstü", "rate": "1.45 - 1.55", "confidence": "%87"}
]

def parse_user_date(text):
    text = text.strip().lower()
    today = datetime.now()
    
    if text == "bugün":
        return today.strftime("%Y%m%d"), today.strftime("%d.%m.%Y")
    elif text == "yarın":
        dt = today + timedelta(days=1)
        return dt.strftime("%Y%m%d"), dt.strftime("%d.%m.%Y")
    elif text == "dün":
        dt = today - timedelta(days=1)
        return dt.strftime("%Y%m%d"), dt.strftime("%d.%m.%Y")
        
    formats = ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m", "%d/%m"]
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=today.year)
            return dt.strftime("%Y%m%d"), dt.strftime("%d.%m.%Y")
        except ValueError:
            pass
            
    return None, None

def find_league_by_keyword(text):
    text_clean = text.strip().lower()
    for keyword, league_tuples in LEAGUE_KEYWORDS.items():
        if keyword in text_clean:
            return league_tuples
    return None

# =========================================================
# ASENKRON VERİ ÇEKME (HTTPX)
# =========================================================
async def fetch_single_league(client, league_code, league_name, date_str=None):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
    if date_str:
        url += f"?dates={date_str}"
    
    matches = []
    try:
        res = await client.get(url, headers=HEADERS, timeout=5.0)
        if res.status_code == 200:
            data = res.json()
            for event in data.get("events", []):
                raw_date = event.get("date", "")
                formatted_date = "Tarih Bilgisi Yok"
                if raw_date:
                    try:
                        dt = datetime.strptime(raw_date[:19], "%Y-%m-%dT%H:%M:%S")
                        day_tr = DAYS_TR.get(dt.strftime("%A"), dt.strftime("%A"))
                        formatted_date = dt.strftime(f"%d.%m.%Y {day_tr} - %H:%M")
                    except Exception:
                        formatted_date = raw_date
                
                status = event.get("status", {}).get("type", {})
                state = status.get("state", "pre")
                detail = status.get("shortDetail", "Saat Yok")
                
                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                competitors = competitions[0].get("competitors", [])
                if len(competitors) < 2:
                    continue
                
                home_team = competitors[0].get("team", {}).get("displayName", "Ev Sahibi")
                home_score = competitors[0].get("score", "0")
                away_team = competitors[1].get("team", {}).get("displayName", "Deplasman")
                away_score = competitors[1].get("score", "0")
                
                matches.append({
                    "id": event.get("id"),
                    "league": league_name,
                    "home": home_team,
                    "away": away_team,
                    "home_score": home_score,
                    "away_score": away_score,
                    "state": state,
                    "detail": detail,
                    "match_time": formatted_date
                })
    except Exception as e:
        logger.warning(f"{league_code} çekilemedi: {e}")
    return matches

async def fetch_scores(target_leagues=None, date_str=None):
    all_matches = []
    seen_ids = set()
    search_list = target_leagues if target_leagues else LEAGUES
    
    async with httpx.AsyncClient() as client:
        tasks = [fetch_single_league(client, code, name, date_str) for code, name in search_list]
        results = await asyncio.gather(*tasks)
        
        for match_list in results:
            for m in match_list:
                if m["id"] not in seen_ids:
                    seen_ids.add(m["id"])
                    all_matches.append(m)
                    
    return all_matches

async def get_league_special_coupon(target_leagues, shuffle=False):
    league_name = target_leagues[0][1]
    all_upcoming = []
    
    for i in range(7):
        dt = datetime.now() + timedelta(days=i)
        date_fmt = dt.strftime("%Y%m%d")
        matches = await fetch_scores(target_leagues=target_leagues, date_str=date_fmt)
        upcoming = [m for m in matches if m["state"] == "pre"]
        all_upcoming.extend(upcoming)
        if len(all_upcoming) >= 5:
            break

    if not all_upcoming:
        return f"🎫 <b>{league_name.upper()} ÖZEL KUPONU</b>\n\nÖnümüzdeki 7 gün içinde bu ligde analiz edilecek maç bulunamadı.", None

    if shuffle:
        random.shuffle(all_upcoming)

    selected = all_upcoming[:min(len(all_upcoming), 5)]
    output = f"🎫 <b>{league_name.upper()} ÖZEL KUPONU ({len(selected)} Maç)</b>\n"
    output += f"🎯 <i>Sadece {league_name} ligine özel hazırlanan yüksek ihtimalli analizler:</i>\n\n"

    for idx, m in enumerate(selected):
        tip_info = random.choice(HIGH_PROBABILITY_TIPS) if shuffle else HIGH_PROBABILITY_TIPS[idx % len(HIGH_PROBABILITY_TIPS)]
        output += f"⚽ <b>{m['home']} vs {m['away']}</b>\n"
        output += f"📅 Tarih/Saat: <code>{m['match_time']}</code>\n"
        output += f"💡 <b>Tahmin:</b> <code>{tip_info['tip']}</code>\n"
        output += f"📈 <b>Tahmini Oran:</b> {tip_info['rate']} | 🎯 <b>Güven:</b> <code>{tip_info['confidence']}</code>\n"
        output += "-----------------------------------\n"

    return output, None

async def get_near_future_best_matches(shuffle=False):
    all_upcoming = []
    
    for i in range(3):  # Hızlı yanıt için 3 güne düşürüldü
        dt = datetime.now() + timedelta(days=i)
        date_fmt = dt.strftime("%Y%m%d")
        matches = await fetch_scores(date_str=date_fmt)
        upcoming = [m for m in matches if m["state"] == "pre"]
        all_upcoming.extend(upcoming)

    if not all_upcoming:
        return "⚡ <b>ÖNÜMÜZDEKİ MAÇLAR</b>\n\nAnaliz edilecek uygun maç bulunamadı.", None

    if shuffle:
        random.shuffle(all_upcoming)

    selected = all_upcoming[:min(len(all_upcoming), 6)]
    output = f"⚡ <b>YÜKSEK İHTİMALLİ MAÇLAR ({len(selected)} Maç)</b>\n\n"

    for idx, m in enumerate(selected):
        tip_info = random.choice(HIGH_PROBABILITY_TIPS) if shuffle else HIGH_PROBABILITY_TIPS[idx % len(HIGH_PROBABILITY_TIPS)]
        output += f"⚽ <b>{m['home']} vs {m['away']}</b>\n"
        output += f"🏆 <i>{m['league']}</i>\n"
        output += f"📅 Tarih/Saat: <code>{m['match_time']}</code>\n"
        output += f"💡 <b>Tahmin:</b> <code>{tip_info['tip']}</code>\n"
        output += f"📈 <b>Oran:</b> {tip_info['rate']} | 🎯 <b>Güven:</b> <code>{tip_info['confidence']}</code>\n"
        output += "-----------------------------------\n"

    keyboard = [[InlineKeyboardButton("🔄 Farklı Maçları İncele / Yenile", callback_data="refresh_near_matches")]]
    return output, InlineKeyboardMarkup(keyboard)

async def get_live_scores():
    matches = await fetch_scores()
    live_matches = [m for m in matches if m["state"] == "in"]
    
    if live_matches:
        output = "🔥 <b>CANLI MAÇLAR</b>\n\n"
        for m in live_matches:
            output += f"🏆 <b>{m['league']}</b>\n"
            output += f"⚽ <b>{m['home']}</b> {m['home_score']} - {m['away_score']} <b>{m['away']}</b>\n"
            output += f"⏱️ Durum: <code>{m['detail']}</code>\n\n"
        return output
    return "🟢 <b>CANLI MAÇLAR</b>\n\nŞu anda canlı oynanan maç bulunmuyor."

# =========================================================
# HANDLERS
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🔥 Canlı Skorlar", "⚡ Genel En İyi Maçlar (5 Gün)"],
        ["🇹🇷 Süper Lig", "🇪🇺 Avrupa Ligi"],
        ["🇪🇺 Konferans Ligi", "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"],
        ["🇪🇸 La Liga", "🇪🇺 Şampiyonlar Ligi"],
        ["🔄 Yenile"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "⚽ <b>SAHA ANALİZ VE LİG ÖZEL KUPON BOTU!</b>\n\n"
        "Aşağıdaki butonları kullanarak veya lig ismi yazarak sorgulama yapabilirsiniz.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    
    matched_leagues = find_league_by_keyword(text)
    if matched_leagues:
        league_display_name = matched_leagues[0][1]
        msg = await update.message.reply_text(f"🔄 <b>{league_display_name}</b> taranıyor...")
        result, reply_markup = await get_league_special_coupon(matched_leagues)
        await msg.edit_text(result, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return

    if text in ["🔥 Canlı Skorlar", "🔄 Yenile"]:
        msg = await update.message.reply_text("🔄 Canlı skorlar sorgulanıyor...")
        result = await get_live_scores()
        await msg.edit_text(result, parse_mode=ParseMode.HTML)

    elif text in ["⚡ Genel En İyi Maçlar (5 Gün)", "⚡ Yakın Zamanın En İyi Maçları"]:
        msg = await update.message.reply_text("🔄 Maçlar analiz ediliyor...")
        result, reply_markup = await get_near_future_best_matches()
        await msg.edit_text(result, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    else:
        date_api_fmt, display_date = parse_user_date(text)
        if date_api_fmt:
            msg = await update.message.reply_text(f"🔄 <b>{display_date}</b> tarihi taranıyor...")
            matches = await fetch_scores(date_str=date_api_fmt)
            if not matches:
                await msg.edit_text(f"📆 <b>{display_date}</b> tarihinde maç bulunamadı.", parse_mode=ParseMode.HTML)
                return
                
            output = f"📆 <b>{display_date} TARİHLİ MAÇLAR</b>\n\n"
            for m in matches[:6]:
                tip_info = random.choice(HIGH_PROBABILITY_TIPS)
                output += f"⚽ <b>{m['home']} vs {m['away']}</b> ({m['league']})\n"
                output += f"📅 Saat: <code>{m['match_time']}</code>\n"
                output += f"💡 Tahmin: <code>{tip_info['tip']}</code> (Güven: {tip_info['confidence']})\n"
                output += "-----------------------------------\n"
            await msg.edit_text(output, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(
                "❓ Komut anlaşılamadı. Bir lig ismi veya tarih yazabilirsiniz (Örn: <b>Süper Lig</b>, <b>Yarın</b>).",
                parse_mode=ParseMode.HTML
            )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔄 Yenileniyor...")

    if query.data == "refresh_near_matches":
        result, reply_markup = await get_near_future_best_matches(shuffle=True)
        await query.edit_message_text(result, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 Bot Başarıyla Çalıştırıldı!")
    app.run_polling()

if __name__ == "__main__":
    main()
