import os
import requests
import telebot
import sqlite3
import schedule
import time
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ------------------------------------------------------------
# 1. CONFIGURATION
# ------------------------------------------------------------
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "therundown-therundown-v1.p.rapidapi.com"
API_BASE_URL = f"https://{RAPIDAPI_HOST}"
FOOTBALL_SPORT_ID = 3

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# ------------------------------------------------------------
# 2. LANGUES
# ------------------------------------------------------------
LANG_FLAGS = {
    "fr": "🇫🇷 Français",
    "en": "🇬🇧 English",
    "es": "🇪🇸 Español",
    "pt": "🇵🇹 Português",
    "ar": "🇸🇦 العربية",
}

LANGUAGES = {
    "fr": {
        "welcome": "👋 *Bienvenue sur KING NI Predict Bot !*",
        "choose_lang": "🌐 *Choisis ta langue :*",
        "lang_set": "✅ Langue définie sur *Français*.",
        "menu_pred_today": "🔮 Pronostics du jour",
        "menu_week": "📅 Pronostics de la semaine",
        "menu_by_league": "🏆 Par championnat",
        "menu_search": "⚽ Rechercher une équipe",
        "menu_stats": "📊 Statistiques",
        "menu_follow": "🔔 Suivre une équipe",
        "menu_backtest": "📈 Backtesting",
        "menu_trends": "📊 Mes tendances",
        "menu_lang": "🌐 Langue",
        "menu_help": "❓ Aide",
        "menu_reset": "🔄 Réinitialiser",
        "no_matches": "⚠️ Aucun match trouvé.",
        "loading": "⏳ *Récupération...*",
        "back": "🔙 Retour",
        "choose_league": "🏆 *Choisis un championnat :*",
        "choose_match": "⚽ *Choisis un match :*",
        "choose_market": "📊 *Choisis un marché :*",
        "no_match_today": "⚠️ Aucun match aujourd'hui.",
        "no_match_week": "⚠️ Aucun match dans les 7 prochains jours.",
        "market_h2h": "🔮 1X2",
        "market_spreads": "📐 Handicap",
        "market_totals": "📈 Over/Under",
        "no_market": "❌ Aucun marché disponible.",
        "best_odds": "🏆 Meilleures cotes",
        "value_analysis": "💎 Analyse de valeur",
        "search_prompt": "⚽ *Recherche*\n\nEnvoie un nom (ex: `Arsenal`).",
        "follow_prompt": "🔔 Envoie `suivre Arsenal`.",
        "following": "✅ Tu suis *{team}*.",
        "following_list": "📋 *Équipes suivies*",
        "stats_title": "📊 *Statistiques*",
        "stats_saved": "Pronostics :",
        "stats_correct": "Justes :",
        "stats_rate": "Taux :",
        "no_data": "📊 Aucune donnée.",
        "help_text": "❓ *Aide*\n\nUtilise les boutons.",
        "matches_found": "🔍 *{count} match(s)* :",
        "page": "📄 Page",
        "prev": "⬅️ Précédent",
        "next": "Suivant ➡️",
        "prev_short": "⬅️ Préc.",
        "next_short": "Suiv. ➡️",
        "total_leagues": "📊 {count} ligues",
        "no_league_matches": "ℹ️ Aucun match pour ce championnat.",
        "match_count": "🔮 *{count} matchs :*",
    },
    "en": {
        "welcome": "👋 *Welcome to KING NI Predict Bot !*",
        "choose_lang": "🌐 *Choose your language :*",
        "lang_set": "✅ Language set to *English*.",
        "menu_pred_today": "🔮 Today's predictions",
        "menu_week": "📅 Week's predictions",
        "menu_by_league": "🏆 By league",
        "menu_search": "⚽ Search team",
        "menu_stats": "📊 Statistics",
        "menu_follow": "🔔 Follow a team",
        "menu_backtest": "📈 Backtesting",
        "menu_trends": "📊 My trends",
        "menu_lang": "🌐 Language",
        "menu_help": "❓ Help",
        "menu_reset": "🔄 Reset",
        "no_matches": "⚠️ No matches found.",
        "loading": "⏳ *Loading...*",
        "back": "🔙 Back",
        "choose_league": "🏆 *Choose a league :*",
        "choose_match": "⚽ *Choose a match :*",
        "choose_market": "📊 *Choose a market :*",
        "no_match_today": "⚠️ No matches today.",
        "no_match_week": "⚠️ No matches in the next 7 days.",
        "market_h2h": "🔮 1X2",
        "market_spreads": "📐 Handicap",
        "market_totals": "📈 Over/Under",
        "no_market": "❌ No market available.",
        "best_odds": "🏆 Best odds",
        "value_analysis": "💎 Value analysis",
        "search_prompt": "⚽ *Search*\n\nSend a name (e.g. `Arsenal`).",
        "follow_prompt": "🔔 Send `follow Arsenal`.",
        "following": "✅ You follow *{team}*.",
        "following_list": "📋 *Followed teams*",
        "stats_title": "📊 *Statistics*",
        "stats_saved": "Predictions:",
        "stats_correct": "Correct:",
        "stats_rate": "Rate:",
        "no_data": "📊 No data.",
        "help_text": "❓ *Help*\n\nUse the buttons.",
        "matches_found": "🔍 *{count} match(es)* :",
        "page": "📄 Page",
        "prev": "⬅️ Previous",
        "next": "Next ➡️",
        "prev_short": "⬅️ Prev",
        "next_short": "Next ➡️",
        "total_leagues": "📊 {count} leagues",
        "no_league_matches": "ℹ️ No matches for this league.",
        "match_count": "🔮 *{count} matches:*",
    },
    "es": {
        "welcome": "👋 *¡Bienvenido a KING NI Predict Bot !*",
        "choose_lang": "🌐 *Elige tu idioma :*",
        "lang_set": "✅ Idioma: *Español*.",
        "menu_pred_today": "🔮 Pronósticos de hoy",
        "menu_week": "📅 Pronósticos de la semana",
        "menu_by_league": "🏆 Por liga",
        "menu_search": "⚽ Buscar equipo",
        "menu_stats": "📊 Estadísticas",
        "menu_follow": "🔔 Seguir un equipo",
        "menu_backtest": "📈 Backtesting",
        "menu_trends": "📊 Mis tendencias",
        "menu_lang": "🌐 Idioma",
        "menu_help": "❓ Ayuda",
        "menu_reset": "🔄 Reiniciar",
        "no_matches": "⚠️ Sin partidos.",
        "loading": "⏳ *Cargando...*",
        "back": "🔙 Volver",
        "choose_league": "🏆 *Elige una liga :*",
        "choose_match": "⚽ *Elige un partido :*",
        "choose_market": "📊 *Elige un mercado :*",
        "no_match_today": "⚠️ Sin partidos hoy.",
        "no_match_week": "⚠️ Sin partidos en 7 días.",
        "market_h2h": "🔮 1X2",
        "market_spreads": "📐 Hándicap",
        "market_totals": "📈 Más/Menos",
        "no_market": "❌ Sin mercado.",
        "best_odds": "🏆 Mejores cuotas",
        "value_analysis": "💎 Análisis de valor",
        "search_prompt": "⚽ *Búsqueda*\n\nEnvía un nombre.",
        "follow_prompt": "🔔 Envía `seguir Arsenal`.",
        "following": "✅ Sigues a *{team}*.",
        "following_list": "📋 *Equipos seguidos*",
        "stats_title": "📊 *Estadísticas*",
        "stats_saved": "Pronósticos:",
        "stats_correct": "Correctos:",
        "stats_rate": "Tasa:",
        "no_data": "📊 Sin datos.",
        "help_text": "❓ *Ayuda*\n\nUsa los botones.",
        "matches_found": "🔍 *{count} partido(s)* :",
        "page": "📄 Página",
        "prev": "⬅️ Anterior",
        "next": "Siguiente ➡️",
        "prev_short": "⬅️ Ant.",
        "next_short": "Sig. ➡️",
        "total_leagues": "📊 {count} ligas",
        "no_league_matches": "ℹ️ Sin partidos.",
        "match_count": "🔮 *{count} partidos:*",
    },
    "pt": {
        "welcome": "👋 *Bem-vindo ao KING NI Predict Bot !*",
        "choose_lang": "🌐 *Escolhe o teu idioma :*",
        "lang_set": "✅ Idioma: *Português*.",
        "menu_pred_today": "🔮 Prognósticos de hoje",
        "menu_week": "📅 Prognósticos da semana",
        "menu_by_league": "🏆 Por campeonato",
        "menu_search": "⚽ Buscar equipa",
        "menu_stats": "📊 Estatísticas",
        "menu_follow": "🔔 Seguir uma equipa",
        "menu_backtest": "📈 Backtesting",
        "menu_trends": "📊 Minhas tendências",
        "menu_lang": "🌐 Idioma",
        "menu_help": "❓ Ajuda",
        "menu_reset": "🔄 Reiniciar",
        "no_matches": "⚠️ Nenhum jogo.",
        "loading": "⏳ *A carregar...*",
        "back": "🔙 Voltar",
        "choose_league": "🏆 *Escolhe um campeonato :*",
        "choose_match": "⚽ *Escolhe um jogo :*",
        "choose_market": "📊 *Escolhe um mercado :*",
        "no_match_today": "⚠️ Sem jogos hoje.",
        "no_match_week": "⚠️ Sem jogos em 7 dias.",
        "market_h2h": "🔮 1X2",
        "market_spreads": "📐 Handicap",
        "market_totals": "📈 Mais/Menos",
        "no_market": "❌ Sem mercado.",
        "best_odds": "🏆 Melhores cotações",
        "value_analysis": "💎 Análise de valor",
        "search_prompt": "⚽ *Busca*\n\nEnvia um nome.",
        "follow_prompt": "🔔 Envia `seguir Arsenal`.",
        "following": "✅ Segues *{team}*.",
        "following_list": "📋 *Equipas seguidas*",
        "stats_title": "📊 *Estatísticas*",
        "stats_saved": "Prognósticos:",
        "stats_correct": "Corretos:",
        "stats_rate": "Taxa:",
        "no_data": "📊 Sem dados.",
        "help_text": "❓ *Ajuda*\n\nUsa os botões.",
        "matches_found": "🔍 *{count} jogo(s)* :",
        "page": "📄 Página",
        "prev": "⬅️ Anterior",
        "next": "Seguinte ➡️",
        "prev_short": "⬅️ Ant.",
        "next_short": "Seg. ➡️",
        "total_leagues": "📊 {count} campeonatos",
        "no_league_matches": "ℹ️ Sem jogos.",
        "match_count": "🔮 *{count} jogos:*",
    },
    "ar": {
        "welcome": "👋 *مرحبا بك في KING NI Predict Bot !*",
        "choose_lang": "🌐 *اختر لغتك :*",
        "lang_set": "✅ اللغة: *العربية*.",
        "menu_pred_today": "🔮 توقعات اليوم",
        "menu_week": "📅 توقعات الأسبوع",
        "menu_by_league": "🏆 حسب البطولة",
        "menu_search": "⚽ البحث عن فريق",
        "menu_stats": "📊 الإحصائيات",
        "menu_follow": "🔔 متابعة فريق",
        "menu_backtest": "📈 الاختبار",
        "menu_trends": "📊 اتجاهاتي",
        "menu_lang": "🌐 اللغة",
        "menu_help": "❓ مساعدة",
        "menu_reset": "🔄 إعادة تعيين",
        "no_matches": "⚠️ لا مباريات.",
        "loading": "⏳ *جاري التحميل...*",
        "back": "🔙 رجوع",
        "choose_league": "🏆 *اختر بطولة :*",
        "choose_match": "⚽ *اختر مباراة :*",
        "choose_market": "📊 *اختر سوقاً :*",
        "no_match_today": "⚠️ لا مباريات اليوم.",
        "no_match_week": "⚠️ لا مباريات في 7 أيام.",
        "market_h2h": "🔮 1X2",
        "market_spreads": "📐 هانديكاب",
        "market_totals": "📈 أكثر/أقل",
        "no_market": "❌ لا سوق متاح.",
        "best_odds": "🏆 أفضل الأسعار",
        "value_analysis": "💎 تحليل القيمة",
        "search_prompt": "⚽ *بحث*\n\nأرسل اسماً.",
        "follow_prompt": "🔔 أرسل `suivre Arsenal`.",
        "following": "✅ تتابع *{team}*.",
        "following_list": "📋 *الفرق المتابعة*",
        "stats_title": "📊 *الإحصائيات*",
        "stats_saved": "التوقعات:",
        "stats_correct": "الصحيحة:",
        "stats_rate": "النسبة:",
        "no_data": "📊 لا بيانات.",
        "help_text": "❓ *مساعدة*\n\nاستخدم الأزرار.",
        "matches_found": "🔍 *{count} مباراة* :",
        "page": "📄 صفحة",
        "prev": "⬅️ السابق",
        "next": "التالي ➡️",
        "prev_short": "⬅️ السابق",
        "next_short": "التالي ➡️",
        "total_leagues": "📊 {count} بطولة",
        "no_league_matches": "ℹ️ لا مباريات.",
        "match_count": "🔮 *{count} مباريات:*",
    }
}

def t(lang, key, **kwargs):
    text = LANGUAGES.get(lang, LANGUAGES["fr"]).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except:
            pass
    return text

# ------------------------------------------------------------
# 3. UTILITAIRES
# ------------------------------------------------------------
def format_date(iso_date):
    if not iso_date:
        return "?"
    try:
        return datetime.strptime(iso_date[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        return iso_date[:10] if len(iso_date) >= 10 else "?"

def format_datetime(iso_date):
    if not iso_date:
        return "?"
    try:
        dt = datetime.strptime(iso_date[:19].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%d/%m/%Y %Hh%M")
    except:
        try:
            dt = datetime.strptime(iso_date[:16], "%Y-%m-%dT%H:%M")
            return dt.strftime("%d/%m/%Y %Hh%M")
        except:
            return format_date(iso_date)

def generate_progress_bar(value, total=100, length=10):
    filled = int((value / total) * length)
    return "█" * filled + "░" * (length - filled)

def is_match_upcoming(match, tolerance_minutes=20):
    try:
        commence = match.get("event_date", "")
        if not commence:
            return True
        dt = datetime.strptime(commence[:19].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        now_utc = datetime.utcnow()
        deadline = dt + timedelta(minutes=tolerance_minutes)
        return now_utc <= deadline
    except:
        return True

# ------------------------------------------------------------
# 4. BASE DE DONNÉES
# ------------------------------------------------------------
def init_db():
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, home_team TEXT, away_team TEXT,
        market TEXT, prob_home REAL, prob_draw REAL, prob_away REAL,
        prediction TEXT, actual_result TEXT, user_id INTEGER, created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, chat_id TEXT, username TEXT, lang TEXT, created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS followed_teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, team_name TEXT, created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sent_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, match_id TEXT, sent_at TEXT)''')
    conn.commit()
    conn.close()

def register_user(user_id, chat_id, username, lang=None):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO users (user_id, chat_id, username, lang, created_at) VALUES (?, ?, ?, ?, ?)',
                (user_id, chat_id, username, lang, datetime.now().isoformat()))
    if lang:
        cur.execute('UPDATE users SET lang = ? WHERE user_id = ?', (lang, user_id))
    conn.commit()
    conn.close()

def get_user_lang(user_id):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('SELECT lang FROM users WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def set_user_lang(user_id, lang):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('UPDATE users SET lang = ? WHERE user_id = ?', (lang, user_id))
    conn.commit()
    conn.close()

def add_followed_team(user_id, team_name):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO followed_teams (user_id, team_name, created_at) VALUES (?, ?, ?)',
                (user_id, team_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_followed_teams(user_id):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('SELECT team_name FROM followed_teams WHERE user_id = ?', (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def save_prediction(home, away, market, ph, pd, pa, pred, user_id=None):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('''INSERT INTO predictions (date, home_team, away_team, market, prob_home, prob_draw, prob_away, prediction, user_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (datetime.now().strftime("%Y-%m-%d"), home, away, market, ph, pd, pa, pred, user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_stats(user_id, lang):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*), SUM(CASE WHEN actual_result = prediction THEN 1 ELSE 0 END) FROM predictions WHERE user_id = ? AND actual_result IS NOT NULL', (user_id,))
    total, correct = cur.fetchone()
    conn.close()
    if total and total > 0:
        rate = ((correct or 0) / total * 100)
        return f"{t(lang, 'stats_title')}\n\n{t(lang, 'stats_saved')} {total}\n{t(lang, 'stats_correct')} {correct or 0}\n{t(lang, 'stats_rate')} {rate:.1f}%"
    return t(lang, "no_data")

# ------------------------------------------------------------
# 5. API THERUNDOWN
# ------------------------------------------------------------
_matches_cache = {}
_matches_cache_time = {}

def therundown_request(endpoint, params=None, retries=2):
    if params is None:
        params = {}
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }
    url = f"{API_BASE_URL}{endpoint}"
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
            print(f"⚠️ Erreur {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"⚠️ {endpoint}: {e}")
        if attempt < retries - 1:
            time.sleep(1)
    return None

def get_events_for_date(date_str, cache_ttl=600):
    """Récupère les matchs de football pour une date (YYYY-MM-DD)."""
    now = time.time()
    cache_key = f"events_{date_str}"
    if cache_key in _matches_cache and cache_key in _matches_cache_time:
        if now - _matches_cache_time[cache_key] < cache_ttl:
            return _matches_cache[cache_key]
    
    data = therundown_request(f"/sports/{FOOTBALL_SPORT_ID}/events/{date_str}")
    if not data:
        if cache_key in _matches_cache:
            return _matches_cache[cache_key]
        return []
    
    events = data.get("events", [])
    _matches_cache[cache_key] = events
    _matches_cache_time[cache_key] = now
    return events

def format_match_from_rundown(ev):
    """Convertit un événement TheRundown au format interne."""
    try:
        teams = ev.get("teams", [])
        home_team = "?"
        away_team = "?"
        for team in teams:
            if team.get("is_home"):
                home_team = team.get("name", "?")
            else:
                away_team = team.get("name", "?")
        
        # Récupérer les cotes (TheRundown fournit souvent des lignes)
        lines = ev.get("lines", {})
        bookmakers = []
        if lines:
            for market_key, market_data in lines.items():
                if isinstance(market_data, list):
                    for line in market_data:
                        if isinstance(line, dict):
                            bookmakers.append({
                                "key": market_key,
                                "outcomes": line.get("outcomes", [])
                            })
        
        return {
            "id": ev.get("event_id"),
            "home_team": home_team,
            "away_team": away_team,
            "league_name": ev.get("sport_name", "Football"),
            "commence_time": ev.get("event_date", ""),
            "bookmakers": bookmakers,
            "raw": ev  # On garde les données brutes
        }
    except Exception as e:
        print(f"⚠️ Erreur format: {e}")
        return None

def get_matches_today():
    today = datetime.now().strftime("%Y-%m-%d")
    events = get_events_for_date(today)
    matches = []
    for ev in events:
        if not is_match_upcoming(ev):
            continue
        m = format_match_from_rundown(ev)
        if m:
            matches.append(m)
    matches.sort(key=lambda x: x.get("commence_time", ""))
    return matches

def get_matches_week():
    all_matches = []
    for i in range(8):
        date_str = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        events = get_events_for_date(date_str)
        for ev in events:
            if not is_match_upcoming(ev):
                continue
            m = format_match_from_rundown(ev)
            if m:
                all_matches.append(m)
    all_matches.sort(key=lambda x: x.get("commence_time", ""))
    return all_matches

def get_all_matches(days_ahead=None):
    if days_ahead is None:
        return get_matches_week()
    all_matches = []
    for i in range(days_ahead + 1):
        date_str = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        events = get_events_for_date(date_str)
        for ev in events:
            if not is_match_upcoming(ev):
                continue
            m = format_match_from_rundown(ev)
            if m:
                all_matches.append(m)
    all_matches.sort(key=lambda x: x.get("commence_time", ""))
    return all_matches

# ------------------------------------------------------------
# 6. MARCHÉS (basé sur les données brutes TheRundown)
# ------------------------------------------------------------
def get_available_markets(match):
    """Détecte les marchés disponibles."""
    markets = set()
    raw = match.get("raw", {})
    lines = raw.get("lines", {})
    for key in lines.keys():
        if "moneyline" in key.lower() or "1x2" in key.lower():
            markets.add("h2h")
        elif "spread" in key.lower():
            markets.add("spreads")
        elif "total" in key.lower():
            markets.add("totals")
    if not markets:
        markets = {"h2h"}  # Par défaut, on suppose 1X2
    return list(markets)

def get_market_predictions(match, market_type="h2h"):
    """Extrait les probabilités depuis les cotes TheRundown."""
    try:
        raw = match.get("raw", {})
        lines = raw.get("lines", {})
        
        # Chercher les cotes 1X2
        target_keys = []
        if market_type == "h2h":
            target_keys = ["moneyline", "1x2", "h2h"]
        elif market_type == "spreads":
            target_keys = ["spread", "pointspread"]
        elif market_type == "totals":
            target_keys = ["total", "overunder"]
        
        for key, market_data in lines.items():
            if any(tk in key.lower() for tk in target_keys):
                if isinstance(market_data, list) and market_data:
                    for line in market_data:
                        if not isinstance(line, dict):
                            continue
                        outcomes = line.get("outcomes", [])
                        if not outcomes:
                            continue
                        
                        # Extraire les prix
                        prices = []
                        for o in outcomes:
                            price = o.get("price", 0)
                            if price and price > 0:
                                prices.append({"name": o.get("name", "?"), "price": price, "prob": (1/price)*100})
                        
                        if market_type == "h2h" and len(prices) >= 3:
                            home = match["home_team"]
                            away = match["away_team"]
                            ph = next((p["prob"] for p in prices if home.lower() in p["name"].lower()), 0)
                            pd = next((p["prob"] for p in prices if "draw" in p["name"].lower() or "nul" in p["name"].lower()), 0)
                            pa = next((p["prob"] for p in prices if away.lower() in p["name"].lower()), 0)
                            total = ph + pd + pa
                            if total > 0:
                                ph = (ph/total)*100; pd = (pd/total)*100; pa = (pa/total)*100
                                if ph > pa and ph > pd:
                                    pred = f"🏠 {home}"
                                elif pa > ph and pa > pd:
                                    pred = f"✈️ {away}"
                                else:
                                    pred = "🤝 Nul"
                                return {"type": "1X2", "prob_home": ph, "prob_draw": pd, "prob_away": pa,
                                        "prediction": pred,
                                        "display": f"🏠 {home} : {ph:.1f}% {generate_progress_bar(ph)}\n🤝 Nul : {pd:.1f}% {generate_progress_bar(pd)}\n✈️ {away} : {pa:.1f}% {generate_progress_bar(pa)}"}
                        elif market_type in ("spreads", "totals") and len(prices) >= 2:
                            best = max(prices, key=lambda x: x["prob"])
                            point = outcomes[0].get("point", "") if outcomes else ""
                            pred = f"{best['name']} {point}"
                            return {"type": "Handicap" if market_type == "spreads" else "Over/Under",
                                    "prediction": pred,
                                    "display": "\n".join([f"{p['name']} {point} : {p['prob']:.1f}% {generate_progress_bar(p['prob'])}" for p in prices])}
        
        return {"error": "not_available"}
    except Exception as e:
        return {"error": str(e)}

def get_best_odds(match):
    best = {"home": (0, ""), "draw": (0, ""), "away": (0, "")}
    raw = match.get("raw", {})
    lines = raw.get("lines", {})
    for key, market_data in lines.items():
        if "moneyline" in key.lower() or "1x2" in key.lower():
            if isinstance(market_data, list):
                for line in market_data:
                    if isinstance(line, dict):
                        for o in line.get("outcomes", []):
                            name = o.get("name", "")
                            price = o.get("price", 0)
                            if match["home_team"].lower() in name.lower() and price > best['home'][0]:
                                best['home'] = (price, key)
                            elif "draw" in name.lower() and price > best['draw'][0]:
                                best['draw'] = (price, key)
                            elif match["away_team"].lower() in name.lower() and price > best['away'][0]:
                                best['away'] = (price, key)
    return best

def format_best_odds(match, lang):
    best = get_best_odds(match)
    texte = f"{t(lang, 'best_odds')}\n\n"
    texte += f"🏠 {match['home_team']} : *{best['home'][0]}*\n"
    texte += f"🤝 Nul : *{best['draw'][0]}*\n"
    texte += f"✈️ {match['away_team']} : *{best['away'][0]}*\n"
    return texte

def analyze_value(match, lang):
    pred = get_market_predictions(match, "h2h")
    if "error" in pred:
        return t(lang, "no_market")
    best = get_best_odds(match)
    texte = f"{t(lang, 'value_analysis')}\n\n"
    for key, name in [("home", f"🏠 {match['home_team']}"), ("draw", "🤝 Nul"), ("away", f"✈️ {match['away_team']}")]:
        prob = pred.get(f"prob_{key}", 0)
        cote = best[key][0] if best[key][0] > 0 else 0
        if cote > 0:
            implied = 100 / cote
            valeur = prob - implied
            emoji = "🟢" if valeur > 3 else ("🟡" if valeur > -3 else "🔴")
            texte += f"{emoji} {name}\n   Proba : {prob:.1f}% | Cote : {cote} | Valeur : {valeur:+.1f}\n"
    return texte

# ------------------------------------------------------------
# 7. MENUS
# ------------------------------------------------------------
def menu_options(lang):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton(t(lang, "menu_pred_today")),
        KeyboardButton(t(lang, "menu_week")),
        KeyboardButton(t(lang, "menu_search")),
        KeyboardButton(t(lang, "menu_stats")),
        KeyboardButton(t(lang, "menu_follow")),
        KeyboardButton(t(lang, "menu_trends")),
        KeyboardButton(t(lang, "menu_lang")),
        KeyboardButton(t(lang, "menu_help")),
        KeyboardButton(t(lang, "menu_reset"))
    )
    return markup

def menu_lang_inline():
    markup = InlineKeyboardMarkup(row_width=1)
    for code, name in LANG_FLAGS.items():
        markup.add(InlineKeyboardButton(name, callback_data=f"setlang_{code}"))
    return markup

def menu_matchs_list(matches, prefix="match_day", lang="fr", page=0):
    markup = InlineKeyboardMarkup(row_width=1)
    per_page = 10
    start = page * per_page
    end = start + per_page
    for i, m in enumerate(matches[start:end]):
        dt = format_datetime(m.get("commence_time", ""))
        idx = start + i
        markup.add(InlineKeyboardButton(f"📅 {dt}\n⚽ {m['home_team']} vs {m['away_team']}",
                                         callback_data=f"{prefix}_{idx}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(t(lang, "prev"), callback_data=f"page_{prefix}_{page-1}"))
    if end < len(matches):
        nav.append(InlineKeyboardButton(t(lang, "next"), callback_data=f"page_{prefix}_{page+1}"))
    if nav:
        markup.add(*nav)
    markup.add(InlineKeyboardButton(t(lang, "back"), callback_data="menu_back"))
    return markup

def menu_match_actions(match_id, lang="fr", available_markets=None):
    markup = InlineKeyboardMarkup(row_width=1)
    if available_markets is None:
        available_markets = ["h2h"]
    if "h2h" in available_markets:
        markup.add(InlineKeyboardButton(t(lang, "market_h2h"), callback_data=f"market_{match_id}_h2h"))
    if "spreads" in available_markets:
        markup.add(InlineKeyboardButton(t(lang, "market_spreads"), callback_data=f"market_{match_id}_spreads"))
    if "totals" in available_markets:
        markup.add(InlineKeyboardButton(t(lang, "market_totals"), callback_data=f"market_{match_id}_totals"))
    markup.add(InlineKeyboardButton(t(lang, "best_odds"), callback_data=f"bestodds_{match_id}"))
    markup.add(InlineKeyboardButton(t(lang, "value_analysis"), callback_data=f"value_{match_id}"))
    markup.add(InlineKeyboardButton(t(lang, "back"), callback_data="back_to_matches"))
    return markup

# ------------------------------------------------------------
# 8. BOT TELEGRAM
# ------------------------------------------------------------
bot = telebot.TeleBot(TELEGRAM_TOKEN)
bot.match_cache = {}
bot.current_matches_list = []
bot.current_match_data = {}

def send_welcome(message, lang):
    bot.reply_to(message, f"{t(lang, 'welcome')}\n\n👇", parse_mode="Markdown", reply_markup=menu_options(lang))

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    exists = cur.fetchone()
    conn.close()
    
    if not exists:
        register_user(user_id, message.chat.id, message.from_user.username, None)
        bot.reply_to(message, t("fr", "welcome") + "\n\n" + t("fr", "choose_lang"),
                     parse_mode="Markdown", reply_markup=menu_lang_inline())
    else:
        lang = get_user_lang(user_id) or "fr"
        register_user(user_id, message.chat.id, message.from_user.username, lang)
        bot.match_cache = {}
        bot.current_matches_list = []
        bot.current_match_data = {}
        send_welcome(message, lang)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        lang = get_user_lang(user_id) or "fr"

        if call.data.startswith("setlang_"):
            new_lang = call.data.replace("setlang_", "")
            set_user_lang(user_id, new_lang)
            lang = new_lang
            register_user(user_id, chat_id, call.from_user.username, new_lang)
            bot.edit_message_text(t(lang, "lang_set"), chat_id, call.message.message_id, parse_mode="Markdown")
            bot.send_message(chat_id, f"{t(lang, 'welcome')}\n\n👇",
                             parse_mode="Markdown", reply_markup=menu_options(lang))
            return

        if call.data == "menu_back":
            bot.send_message(chat_id, f"{t(lang, 'welcome')}\n\n👇",
                             parse_mode="Markdown", reply_markup=menu_options(lang))
            return

        if call.data == "back_to_matches":
            if bot.current_matches_list:
                bot.send_message(chat_id, t(lang, "match_count", count=len(bot.current_matches_list)),
                                 parse_mode="Markdown",
                                 reply_markup=menu_matchs_list(bot.current_matches_list, "match_day", lang))
            else:
                bot.send_message(chat_id, t(lang, "back"), parse_mode="Markdown", reply_markup=menu_options(lang))
            return

        if call.data.startswith("page_"):
            parts = call.data.replace("page_", "").rsplit("_", 1)
            prefix = parts[0]
            page = int(parts[1])
            if bot.current_matches_list:
                bot.send_message(chat_id, f"{t(lang, 'page')} {page+1}",
                                 parse_mode="Markdown",
                                 reply_markup=menu_matchs_list(bot.current_matches_list, prefix, lang, page))
            return

        if call.data.startswith("match_day_"):
            match = bot.match_cache.get(call.data)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            bot.current_match_data[call.data] = match
            dt = format_datetime(match.get("commence_time", ""))
            league = match.get('league_name', '?')
            texte = (f"🏆 *{league}*\n"
                     f"📅 {dt}\n\n"
                     f"⚽ *{match['home_team']} vs {match['away_team']}*\n\n"
                     f"{t(lang, 'choose_market')}")
            available = get_available_markets(match)
            bot.send_message(chat_id, texte, parse_mode="Markdown",
                             reply_markup=menu_match_actions(call.data, lang, available))
            return

        if call.data.startswith("bestodds_"):
            mid = call.data.replace("bestodds_", "")
            match = bot.current_match_data.get(mid) or bot.match_cache.get(mid)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            available = get_available_markets(match)
            texte = format_best_odds(match, lang)
            bot.send_message(chat_id, texte, parse_mode="Markdown",
                             reply_markup=menu_match_actions(mid, lang, available))
            return

        if call.data.startswith("value_"):
            mid = call.data.replace("value_", "")
            match = bot.current_match_data.get(mid) or bot.match_cache.get(mid)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            available = get_available_markets(match)
            texte = analyze_value(match, lang)
            bot.send_message(chat_id, texte, parse_mode="Markdown",
                             reply_markup=menu_match_actions(mid, lang, available))
            return

        if call.data.startswith("market_"):
            parts = call.data.replace("market_", "").rsplit("_", 1)
            market_type = parts[-1]
            mid = parts[0]
            match = bot.current_match_data.get(mid) or bot.match_cache.get(mid)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            pred = get_market_predictions(match, market_type)
            if "error" in pred:
                bot.send_message(chat_id, t(lang, "no_market"))
                return
            save_prediction(match['home_team'], match['away_team'], pred.get('type', market_type),
                            pred.get('prob_home', 0), pred.get('prob_draw', 0), pred.get('prob_away', 0),
                            pred['prediction'], user_id)
            dt = format_datetime(match.get("commence_time", ""))
            texte = (f"🏆 *{match.get('league_name', '')}*\n"
                     f"📅 {dt}\n\n"
                     f"⚽ *{match['home_team']} vs {match['away_team']}*\n"
                     f"📊 *{pred.get('type', market_type)}*\n\n"
                     f"{pred['display']}\n\n"
                     f"✅ *{pred['prediction']}*")
            available = get_available_markets(match)
            bot.send_message(chat_id, texte, parse_mode="Markdown",
                             reply_markup=menu_match_actions(mid, lang, available))
            return

        if call.data == "unfollow_all":
            conn = sqlite3.connect('predictions.db')
            cur = conn.cursor()
            cur.execute('DELETE FROM followed_teams WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            bot.send_message(chat_id, "✅ OK")
            return

    except Exception as e:
        print(f"❌ Erreur callback: {e}")
        try:
            bot.send_message(call.message.chat.id, f"❌ Erreur : {str(e)[:100]}")
        except:
            pass

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = get_user_lang(user_id) or "fr"

    if text.startswith('/'):
        return

    if text == t(lang, "menu_reset"):
        bot.match_cache = {}
        bot.current_matches_list = []
        send_welcome(message, lang)
        return

    if text == t(lang, "menu_lang"):
        bot.reply_to(message, t(lang, "choose_lang"),
                     parse_mode="Markdown", reply_markup=menu_lang_inline())
        return

    if text == t(lang, "menu_pred_today"):
        loading = bot.reply_to(message, t(lang, "loading"), parse_mode="Markdown")
        try:
            all_matches = get_matches_today()
        except Exception as e:
            print(f"Erreur: {e}")
            all_matches = []
        if not all_matches:
            bot.edit_message_text(t(lang, "no_match_today"), chat_id, loading.message_id)
            return
        bot.current_matches_list = all_matches[:50]
        for i, m in enumerate(bot.current_matches_list):
            bot.match_cache[f"match_day_{i}"] = m
        bot.delete_message(chat_id, loading.message_id)
        bot.send_message(chat_id, t(lang, "match_count", count=len(bot.current_matches_list)),
                         parse_mode="Markdown",
                         reply_markup=menu_matchs_list(bot.current_matches_list, "match_day", lang, 0))
        return

    if text == t(lang, "menu_week"):
        loading = bot.reply_to(message, t(lang, "loading"), parse_mode="Markdown")
        try:
            all_matches = get_matches_week()
        except Exception as e:
            print(f"Erreur: {e}")
            all_matches = []
        if not all_matches:
            bot.edit_message_text(t(lang, "no_match_week"), chat_id, loading.message_id)
            return
        bot.current_matches_list = all_matches[:50]
        for i, m in enumerate(bot.current_matches_list):
            bot.match_cache[f"match_day_{i}"] = m
        bot.delete_message(chat_id, loading.message_id)
        bot.send_message(chat_id, t(lang, "match_count", count=len(bot.current_matches_list)),
                         parse_mode="Markdown",
                         reply_markup=menu_matchs_list(bot.current_matches_list, "match_day", lang, 0))
        return

    if text == t(lang, "menu_search"):
        bot.reply_to(message, t(lang, "search_prompt"),
                     parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    if text == t(lang, "menu_stats") or text == t(lang, "menu_backtest"):
        bot.reply_to(message, get_stats(user_id, lang), parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    if text == t(lang, "menu_trends"):
        followed = get_followed_teams(user_id)
        if not followed:
            bot.reply_to(message, t(lang, "follow_prompt"), parse_mode="Markdown", reply_markup=menu_options(lang))
            return
        texte = f"{t(lang, 'following_list')}\n\n" + "\n".join([f"- {f[0]}" for f in followed])
        bot.reply_to(message, texte, parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    if text == t(lang, "menu_follow"):
        followed = get_followed_teams(user_id)
        if followed:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🗑️", callback_data="unfollow_all"))
            bot.reply_to(message, f"{t(lang, 'following_list')}\n\n" + ", ".join([f[0] for f in followed]), reply_markup=markup)
        else:
            bot.reply_to(message, t(lang, "follow_prompt"), parse_mode="Markdown")
        return

    if text == t(lang, "menu_help"):
        bot.reply_to(message, t(lang, "help_text"), parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    if text.lower().startswith(("suivre ", "follow ", "seguir ")):
        parts = text.split(" ", 1)
        if len(parts) > 1:
            team = parts[1].strip()
            add_followed_team(user_id, team)
            bot.reply_to(message, t(lang, "following", team=team),
                         parse_mode="Markdown", reply_markup=menu_options(lang))
            return

    # Recherche libre
    loading = bot.reply_to(message, t(lang, "loading"), parse_mode="Markdown")
    try:
        matches = get_all_matches(days_ahead=7)
    except:
        matches = []
    found = [m for m in matches if text.lower() in m['home_team'].lower() or text.lower() in m['away_team'].lower()]
    if not found:
        bot.edit_message_text(f"❌ {text}", chat_id, loading.message_id)
        return
    texte = t(lang, "matches_found", count=len(found)) + "\n\n"
    for m in found[:10]:
        pred = get_market_predictions(m, "h2h")
        if "error" in pred:
            continue
        dt = format_datetime(m.get("commence_time", ""))
        texte += (f"🏆 {m['league_name']}\n"
                  f"📅 {dt}\n"
                  f"⚽ {m['home_team']} vs {m['away_team']}\n"
                  f"🏠 {pred['prob_home']:.1f}% | 🤝 {pred['prob_draw']:.1f}% | ✈️ {pred['prob_away']:.1f}%\n"
                  f"✅ *{pred['prediction']}*\n\n")
    bot.edit_message_text(texte, chat_id, loading.message_id, parse_mode="Markdown", reply_markup=menu_options(lang))

# ------------------------------------------------------------
# 9. SERVEUR HTTP POUR RENDER
# ------------------------------------------------------------
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b'Bot is running!')
    def do_HEAD(self):
        self.send_response(200); self.end_headers()

def run_http():
    HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()

threading.Thread(target=run_http, daemon=True).start()

# ------------------------------------------------------------
# 10. LANCEMENT
# ------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("✅ Base de données initialisée.")
    print(f"⚽ TheRundown API configurée (sport_id={FOOTBALL_SPORT_ID})")
    print("✅ Bot démarré.")
    bot.infinity_polling()