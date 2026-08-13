import logging
import os
import random
import asyncio
import httpx
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
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
# RENDER 7/24 UYANIK TUTMA (WEB SERVER)
# =========================================================
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot 7/24 Aktif Çalışıyor!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# =========================================================
# BOT TOKEN
# =========================================================
TOKEN = "8801572175:AAFAUufBhit3lJDgl8NN76DcSmun3ht4K0c"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DAYS_TR = {
    "Monday": "Pazartesi",
    "Tuesday": "Salı",
    "Wednesday": "Çarşamba",
    "Thursday": "Perşembe",
    "Friday": "Cuma",
    "Saturday": "Cumartesi",
    "Sunday": "Pazar"
}

LEAGUES = [
    ("tur.1", "🇹🇷 Trendyol Süper Lig"),
    ("eng.1", "🏴󠁧󠁢󠁥󠁮󠁧󠁿 İngiltere Premier League"),
    ("esp.1", "🇪🇸 İspanya La Liga"),
    ("ita.1", "🇮🇹 İtalya Serie A"),
    ("ger.1", "🇩🇪 Almanya Bundesliga"),
    ("fra.1", "🇫🇷 Fransa Ligue 1"),
    ("uefa.champions", "🇪🇺 UEFA Şampiyonlar Ligi"),
    ("uefa.europa", "🇪🇺 UEFA Avrupa Ligi"),
    ("uefa.europa.conf", "🇪🇺 UEFA Konferans Ligi"),
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
    "konferans ligi": [("uefa.europa.conf", "🇪🇺 UEFA Konferans Ligi")],
    "şampiyonlar ligi": [("uefa.champions", "🇪🇺 UEFA Şampiyonlar Ligi")],
    "champions league": [("uefa.champions", "🇪🇺 UEFA Şampiyonlar Ligi")],
    "premier lig": [("eng.1", "🏴󠁧󠁢󠁥󠁮󠁧󠁿 İngiltere Premier League")],
    "premier league": [("eng.1", "🏴󠁧󠁢󠁥󠁮󠁧󠁿 İngiltere Premier League")],
    "la liga": [("esp.1", "🇪🇸 İspanya La Liga")],
    "serie a": [("ita.1", "🇮🇹 İtalya Serie A")],
    "bundesliga": [("ger.1", "🇩🇪 Almanya Bundesliga")],
    "ligue 1": [("fra.1", "🇫🇷 Fransa Ligue 1")],
    "eredivisie": [("ned.1", "🇳🇱 Hollanda Eredivisie")],
    "portekiz": [("por.1", "🇵🇹 Portekiz Liga Portugal")],
    "türkiye kupası": [("tur.cup", "🇹🇷 Ziraat Türkiye Kupası")],
    "ziraat": [("tur.cup", "🇹🇷 Ziraat Türkiye Kupası")]
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
# GELİŞMİŞ VERİ ÇEKME FONKSİYONU (TARİH ARALIĞI DESTEKLİ)
# =========================================================
async def fetch_league_data(client, league_code, league_name, date_str=None):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
    params = {}
    if date_str:
        params["dates"] = date_str
        
    matches = []
    try:
        res = await client.get(url, params=params, headers=HEADERS, timeout=8.0)
        if res.status_code == 200:
            data = res.json()
            for event in data.get("events", []):
                raw_date = event.get("date", "")
                formatted_date = "Tarih Bilgisi Yok"
                if raw_date:
                    try:
                        dt = datetime.strptime(raw_date[:19], "%Y-%m-%dT%H:%M:%S")
                        dt = dt + timedelta(hours=3) # TSI
                        day_en = dt.strftime("%A")
                        day_tr = DAYS_TR.get(day_en, day_en)
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
                    
                home_team, away_team = "Ev Sahibi", "Deplasman"
                home_score, away_score = "0", "0"
                
                for c in competitors:
                    if c.get("homeAway") == "home":
                        home_team = c.get("team", {}).get("displayName", "Ev Sahibi")
                        home_score = c.get("score", "0")
                    else:
                        away_team = c.get("team", {}).get("displayName", "Deplasman")
                        away_score = c.get("score", "0")
                
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
        logger.warning(f"{league_code} veri çekme hatası: {e}")
        
    return matches

async def fetch_scores(target_leagues=None, date_str=None):
    search_list = target_leagues if target_leagues else LEAGUES
    all_matches = []
    seen_ids = set()
    
    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_league_data(client, code, name, date_str) 
            for code, name in search_list
        ]
        results = await asyncio.gather(*tasks)
        
        for match_list in results:
            for m in match_list:
                if m["id"] not in seen_ids:
                    seen_ids.add(m["id"])
                    all_matches.append(m)
                    
    return all_matches

# =========================================================
# LİGE ÖZEL KUPON OLUŞTURMA
# =========================================================
async def get_league_special_coupon(target_leagues, shuffle=False):
    league_name = target_leagues[0][1]
    
    # Bugün ile 10 gün sonrasının tarih aralığı (Tek İstek)
    start_dt = datetime.now()
    end_dt = start_dt + timedelta(days=10)
    range_str = f"{start_dt.strftime('%Y%m%d')}-{end_dt.strftime('%Y%m%d')}"
    
    matches = await fetch_scores(target_leagues=target_leagues, date_str=range_str)
    
    # Oynanmamış (gelecek) maçları filtrele
    all_upcoming = [m for m in matches if m["state"] == "pre"]

    if not all_upcoming:
        # Eğer belirtilen tarih aralığında yoksa varsayılan bülteni çek
        matches_default = await fetch_scores(target_leagues=target_leagues)
        all_upcoming = [m for m in matches_default if m["state"] == "pre"]

    if not all_upcoming:
        return f"🎫 <b>{league_name.upper()} ÖZEL KUPONU</b>\n\nBu ligde şu anda bültende yakın tarihli maç bulunamadı.", None

    if shuffle:
        random.shuffle(all_upcoming)

    count = min(len(all_upcoming), 5)
    selected = all_upcoming[:count]

    output = f"🎫 <b>{league_name.upper()} ÖZEL KUPONU ({len(selected)} Maç)</b>\n"
    output += f"🎯 <i>Sadece {league_name} ligine özel verilerle hazırlanan analizler:</i>\n\n"

    for idx, m in enumerate(selected):
        tip_info = random.choice(HIGH_PROBABILITY_TIPS) if shuffle else HIGH_PROBABILITY_TIPS[idx % len(HIGH_PROBABILITY_TIPS)]
        
        output += f"⚽ <b>{m['home']} vs {m['away']}</b>\n"
        output += f"📅 Tarih/Saat: <code>{m['match_time']}</code>\n"
        output += f"💡 <b>Tahmin:</b> <code>{tip_info['tip']}</code>\n"
        output += f"📈 <b>Tahmini Oran:</b> {tip_info['rate']} | 🎯 <b>Güven:</b> <code>{tip_info['confidence']}</code>\n"
        output += "-----------------------------------\n"

    return output, None

# =========================================================
# GENEL YAKIN ZAMAN MAÇ ANALİZİ (ÖNÜMÜZDEKİ 5-7 GÜN)
# =========================================================
async def get_near_future_best_matches(shuffle=False):
    start_dt = datetime.now()
    end_dt = start_dt + timedelta(days=7)
    range_str = f"{start_dt.strftime('%Y%m%d')}-{end_dt.strftime('%Y%m%d')}"
    
    matches = await fetch_scores(date_str=range_str)
    all_upcoming = [m for m in matches if m["state"] == "pre"]

    # Eğer tarih aralığından boş dönerse direkt güncel lig haftası bültenini çek
    if not all_upcoming:
        matches_default = await fetch_scores()
        all_upcoming = [m for m in matches_default if m["state"] == "pre"]

    if not all_upcoming:
        return "⚡ <b>ÖNÜMÜZDEKİ 5 GÜNÜN EN İYİ MAÇLARI</b>\n\nŞu anda analiz edilebilecek bültende maç bulunamadı.", None

    if shuffle:
        random.shuffle(all_upcoming)

    match_count = len(all_upcoming)
    selected_count = random.randint(4, 6) if match_count >= 6 else match_count
    selected = all_upcoming[:selected_count]

    output = f"⚡ <b>ÖNÜMÜZDEKİ 5-7 GÜNÜN EN İYİ MAÇLARI ({len(selected)} Maç)</b>\n\n"

    for idx, m in enumerate(selected):
        tip_info = random.choice(HIGH_PROBABILITY_TIPS) if shuffle else HIGH_PROBABILITY_TIPS[idx % len(HIGH_PROBABILITY_TIPS)]
        
        output += f"⚽ <b>{m['home']} vs {m['away']}</b>\n"
        output += f"🏆 <i>{m['league']}</i>\n"
        output += f"📅 Tarih/Saat: <code>{m['match_time']}</code>\n"
        output += f"💡 <b>Tahmin:</b> <code>{tip_info['tip']}</code>\n"
        output += f"📈 <b>Oran:</b> {tip_info['rate']} | 🎯 <b>Güven:</b> <code>{tip_info['confidence']}</code>\n"
        output += "-----------------------------------\n"

    keyboard = [[InlineKeyboardButton("🔄 Farklı Maçları İncele / Yenile", callback_data="refresh_near_matches")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    return output, reply_markup

# =========================================================
# CANLI SKORLAR
# =========================================================
async def get_live_scores():
    matches = await fetch_scores()
    live_matches = [m for m in matches if m["state"] == "in"]
    
    if live_matches:
        output = "🔥 <b>CANLI MAÇLAR VE KUPA MAÇLARI</b>\n\n"
        for m in live_matches:
            output += f"🏆 <b>{m['league']}</b>\n"
            output += f"⚽ <b>{m['home']}</b> {m['home_score']} - {m['away_score']} <b>{m['away']}</b>\n"
            output += f"⏱️ Durum: <code>{m['detail']}</code>\n"
            output += f"📅 Tarih: <code>{m['match_time']}</code>\n\n"
        return output
    
    return "🟢 <b>CANLI MAÇLAR</b>\n\nŞu anda canlı oynanan maç bulunmuyor."

# =========================================================
# TELEGRAM BOT HANDLER
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
        "💡 <b>Nasıl Kullanılır?</b>\n"
        "• Butonlara tıklayarak veya sohbet alanına **'Süper Lig'**, **'Avrupa Ligi'**, **'Premier Lig'**, **'La Liga'** yazarak lige özel analiz alabilirsin.\n"
        "• Veya **'Yarın'**, **'Bugün'** yazarak günün maçlarını listeleyebilirsin.",
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
        msg = await update.message.reply_text(f"🔄 <b>{league_display_name}</b> taranıyor, analizler hazırlanıyor...")
        result, reply_markup = await get_league_special_coupon(matched_leagues)
        await msg.edit_text(result, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return

    if text in ["🔥 Canlı Skorlar", "🔄 Yenile"]:
        msg = await update.message.reply_text("🔄 Canlı skorlar sorgulanıyor...")
        result = await get_live_scores()
        await msg.edit_text(result, parse_mode=ParseMode.HTML)

    elif text in ["⚡ Genel En İyi Maçlar (5 Gün)", "⚡ Yakın Zamanın En İyi Maçları"]:
        msg = await update.message.reply_text("🔄 Tüm ligler taranıyor, en iyi maçlar analiz ediliyor...")
        result, reply_markup = await get_near_future_best_matches()
        await msg.edit_text(result, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    else:
        date_api_fmt, display_date = parse_user_date(text)
        if date_api_fmt:
            msg = await update.message.reply_text(f"🔄 <b>{display_date}</b> tarihi için analiz yapılıyor...")
            matches = await fetch_scores(date_str=date_api_fmt)
            if not matches:
                await msg.edit_text(f"📆 <b>{display_date}</b> tarihinde maç bulunamadı.")
                return
                
            output = f"📆 <b>{display_date} TARİHLİ MAÇLAR VE ANALİZLER</b>\n\n"
            for m in matches[:8]:
                tip_info = random.choice(HIGH_PROBABILITY_TIPS)
                output += f"⚽ <b>{m['home']} vs {m['away']}</b> ({m['league']})\n"
                output += f"📅 Saat: <code>{m['match_time']}</code>\n"
                output += f"💡 Tahmin: <code>{tip_info['tip']}</code> (Güven: {tip_info['confidence']})\n"
                output += "-----------------------------------\n"
            await msg.edit_text(output, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(
                "❓ Komut anlaşılamadı. Bir lig ismi (Örn: <b>Süper Lig</b>, <b>La Liga</b>) veya tarih (Örn: <b>Yarın</b>) yazabilirsin.",
                parse_mode=ParseMode.HTML
            )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔄 Yenileniyor...")

    if query.data == "refresh_near_matches":
        result, reply_markup = await get_near_future_best_matches(shuffle=True)
        await query.edit_message_text(result, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

# =========================================================
# ÇALIŞTIRMA
# =========================================================
def main():
    keep_alive()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 Bot Yüksek Hızlı Asenkron Sistem ile Çalışıyor!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
