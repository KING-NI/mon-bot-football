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
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "d2c5556ba64eb508457dcd097ecd6664")
ODDS_URL = "https://api.the-odds-api.com/v4/"
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
# 3. TRADUCTION DES LIGUES
# ------------------------------------------------------------
LEAGUES_FR = {
    "EPL": "Premier League - Angleterre",
    "Premier League": "Premier League - Angleterre",
    "Championship": "Championnat - Angleterre (D2)",
    "EFL Cup": "Coupe de la Ligue anglaise",
    "League 1": "League One - Angleterre (D3)",
    "League 2": "League Two - Angleterre (D4)",
    "Ligue 1 - France": "Ligue 1 - France",
    "Ligue 2 - France": "Ligue 2 - France",
    "Bundesliga - Germany": "Bundesliga - Allemagne",
    "Bundesliga 2 - Germany": "Bundesliga 2 - Allemagne",
    "3. Liga - Germany": "3. Liga - Allemagne",
    "DFB-Pokal": "Coupe d'Allemagne",
    "Frauen-Bundesliga": "Bundesliga féminine - Allemagne",
    "La Liga - Spain": "Liga - Espagne",
    "La Liga 2 - Spain": "Liga 2 - Espagne",
    "Serie A - Italy": "Serie A - Italie",
    "Serie B - Italy": "Serie B - Italie",
    "Primeira Liga - Portugal": "Liga Portugal",
    "Dutch Eredivisie": "Eredivisie - Pays-Bas",
    "Belgium First Div": "Pro League - Belgique",
    "Premiership - Scotland": "Premiership - Écosse",
    "Swiss Superleague": "Super League - Suisse",
    "Austrian Football Bundesliga": "Bundesliga - Autriche",
    "Turkey Super League": "Süper Lig - Turquie",
    "Super League - Greece": "Super League - Grèce",
    "Premier League - Russia": "Premier League - Russie",
    "Eliteserien - Norway": "Eliteserien - Norvège",
    "Allsvenskan - Sweden": "Allsvenskan - Suède",
    "Superettan - Sweden": "Superettan - Suède",
    "Veikkausliiga - Finland": "Veikkausliiga - Finlande",
    "Denmark Superliga": "Superliga - Danemark",
    "Ekstraklasa - Poland": "Ekstraklasa - Pologne",
    "League of Ireland": "Championnat d'Irlande",
    "MLS": "MLS - États-Unis",
    "Liga MX": "Liga MX - Mexique",
    "Brazil Série A": "Brasileirão Série A",
    "Brazil Série B": "Brasileirão Série B",
    "Primera División - Argentina": "Primera División - Argentine",
    "Primera División - Chile": "Primera División - Chili",
    "Copa Libertadores": "Copa Libertadores",
    "Copa Sudamericana": "Copa Sudamericana",
    "J League": "J-League - Japon",
    "K League 1": "K-League 1 - Corée",
    "A-League": "A-League - Australie",
    "UEFA Champions League": "🏆 Ligue des Champions UEFA",
    "UEFA Europa League": "🏆 Ligue Europa UEFA",
    "UEFA Europa Conference Leag…": "🏆 Ligue Europa Conference UEFA",
    "UEFA Europa Conference League": "🏆 Ligue Europa Conference UEFA",
    "UEFA Nations League": "🇪🇺 Ligue des Nations UEFA",
}

def translate_league(name):
    return LEAGUES_FR.get(name, name)

# ------------------------------------------------------------
# 4. CHAMPIONNATS
# ------------------------------------------------------------
_SPORTS_CACHE = None
_SPORTS_CACHE_TIME = None

SPORTS_FALLBACK = {
    "⚽ Premier League - Angleterre": "soccer_epl",
    "⚽ Ligue 1 - France": "soccer_france_ligue_one",
    "⚽ Bundesliga - Allemagne": "soccer_germany_bundesliga",
    "⚽ Liga - Espagne": "soccer_spain_la_liga",
    "⚽ Serie A - Italie": "soccer_italy_serie_a",
    "⚽ MLS - États-Unis": "soccer_usa_mls",
    "🏆 Ligue des Champions UEFA": "soccer_uefa_champs_league",
    "🇪🇺 Ligue des Nations UEFA": "soccer_uefa_nations_league",
}

def get_all_sports(force_refresh=False):
    global _SPORTS_CACHE, _SPORTS_CACHE_TIME
    if not force_refresh and _SPORTS_CACHE and _SPORTS_CACHE_TIME:
        if datetime.now() - _SPORTS_CACHE_TIME < timedelta(hours=6):
            return _SPORTS_CACHE
    try:
        r = requests.get(f"{ODDS_URL}sports/", params={"apiKey": ODDS_API_KEY}, timeout=15)
        if r.status_code == 200:
            soccer_leagues = {}
            for sport in r.json():
                if sport.get("group") == "Soccer" and sport.get("active"):
                    title_fr = translate_league(sport["title"])
                    soccer_leagues[f"⚽ {title_fr}"] = sport["key"]
            if soccer_leagues:
                print(f"✅ {len(soccer_leagues)} championnats récupérés")
                _SPORTS_CACHE = soccer_leagues
                _SPORTS_CACHE_TIME = datetime.now()
                return soccer_leagues
    except Exception as e:
        print(f"⚠️ Erreur sports: {e}")
    return SPORTS_FALLBACK

def get_sports():
    global _SPORTS_CACHE
    if _SPORTS_CACHE is None:
        _SPORTS_CACHE = get_all_sports()
    return _SPORTS_CACHE

# ------------------------------------------------------------
# 5. UTILITAIRES
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
        dt = datetime.strptime(iso_date[:19], "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%d/%m/%Y %Hh%M")
    except:
        return format_date(iso_date)

def generate_progress_bar(value, total=100, length=10):
    filled = int((value / total) * length)
    return "█" * filled + "░" * (length - filled)

def is_match_upcoming(match, tolerance_minutes=20):
    """Garde les matchs qui n'ont pas commencé il y a plus de 20 min."""
    try:
        commence = match.get("commence_time", "")
        if not commence:
            return True
        match_dt = datetime.strptime(commence[:19], "%Y-%m-%dT%H:%M:%S")
        now_utc = datetime.utcnow()
        deadline = match_dt + timedelta(minutes=tolerance_minutes)
        return now_utc <= deadline
    except:
        return True

# ------------------------------------------------------------
# 6. BASE DE DONNÉES
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
# 7. API THE ODDS
# ------------------------------------------------------------
def odds_request(endpoint, params=None, retries=2):
    if params is None:
        params = {}
    params["apiKey"] = ODDS_API_KEY
    url = f"{ODDS_URL}{endpoint}"
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"⚠️ {endpoint}: {e}")
        if attempt < retries - 1:
            time.sleep(1)
    return None

def get_matches_for_league(sport_key, markets="h2h,spreads,totals"):
    data = odds_request(f"sports/{sport_key}/odds/",
                        {"regions": "eu,us", "markets": markets, "oddsFormat": "decimal"})
    if not data:
        return None, "error"
    if len(data) == 0:
        return None, "empty"
    matches = []
    for ev in data:
        if not is_match_upcoming(ev):
            continue
        matches.append({
            "id": ev.get("id"),
            "home_team": ev.get("home_team", "?"),
            "away_team": ev.get("away_team", "?"),
            "league_name": sport_key,
            "commence_time": ev.get("commence_time", ""),
            "bookmakers": ev.get("bookmakers", [])
        })
    matches.sort(key=lambda x: x.get("commence_time", ""))
    return matches, None

# ---------- NOUVEAU : requêtes parallèles ----------
def get_matches_for_multiple_leagues(sports_dict, max_workers=10):
    """Interroge plusieurs championnats EN PARALLÈLE pour aller plus vite."""
    all_matches = []
    
    def fetch(item):
        nom, cle = item
        try:
            matches, error = get_matches_for_league(cle)
            if error or not matches:
                return []
            for m in matches:
                m["league_name"] = nom
            return matches
        except:
            return []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch, item) for item in sports_dict.items()]
        for future in as_completed(futures):
            try:
                result = future.result(timeout=20)
                all_matches.extend(result)
            except:
                continue
    
    all_matches.sort(key=lambda x: x.get("commence_time", ""))
    return all_matches

def get_matches_today():
    today = datetime.now().date()
    all_matches = get_matches_for_multiple_leagues(get_sports())
    filtered = []
    for m in all_matches:
        try:
            md = datetime.strptime(m.get("commence_time","")[:10], "%Y-%m-%d").date()
            if md == today:
                filtered.append(m)
        except:
            continue
    return filtered

def get_matches_week():
    today = datetime.now().date()
    limit = today + timedelta(days=7)
    all_matches = get_matches_for_multiple_leagues(get_sports())
    filtered = []
    for m in all_matches:
        try:
            md = datetime.strptime(m.get("commence_time","")[:10], "%Y-%m-%d").date()
            if today <= md <= limit:
                filtered.append(m)
        except:
            continue
    return filtered

def get_all_matches(days_ahead=None):
    all_matches = get_matches_for_multiple_leagues(get_sports())
    if days_ahead is None:
        return all_matches
    today = datetime.now().date()
    filtered = []
    for m in all_matches:
        try:
            md = datetime.strptime(m.get("commence_time","")[:10], "%Y-%m-%d").date()
            if today <= md <= today + timedelta(days=days_ahead):
                filtered.append(m)
        except:
            continue
    return filtered

# ------------------------------------------------------------
# 8. MARCHÉS
# ------------------------------------------------------------
def get_available_markets(match):
    markets = set()
    for bm in match.get('bookmakers', []):
        for market in bm.get('markets', []):
            key = market.get('key')
            if key:
                markets.add(key)
    return list(markets)

def get_market_predictions(match, market_type="h2h"):
    try:
        home = match["home_team"]
        away = match["away_team"]
        for bm in match.get('bookmakers', []):
            for market in bm.get('markets', []):
                if market.get('key') != market_type:
                    continue
                outcomes = market.get('outcomes', [])
                
                if market_type == "h2h":
                    oh = next((o["price"] for o in outcomes if o["name"] == home), None)
                    od = next((o["price"] for o in outcomes if o["name"] == "Draw"), None)
                    oa = next((o["price"] for o in outcomes if o["name"] == away), None)
                    if None in (oh, od, oa):
                        continue
                    ph = (1/oh)*100; pd = (1/od)*100; pa = (1/oa)*100
                    total = ph + pd + pa
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
                
                elif market_type == "spreads":
                    lines = []
                    for o in outcomes:
                        if o.get('price', 0) > 0:
                            lines.append({"name": o["name"], "point": o.get("point", ""), "price": o["price"],
                                          "prob": (1/o["price"])*100})
                    if not lines:
                        continue
                    best = max(lines, key=lambda x: x["prob"])
                    pred = f"{best['name']} ({best['point']})"
                    return {"type": "Handicap", "prediction": pred,
                            "display": "\n".join([f"{l['name']} {l['point']} : {l['prob']:.1f}% {generate_progress_bar(l['prob'])}" for l in lines])}
                
                elif market_type == "totals":
                    lines = []
                    for o in outcomes:
                        if o.get('price', 0) > 0 and o.get('point'):
                            lines.append({"name": o["name"], "point": o["point"], "price": o["price"],
                                          "prob": (1/o["price"])*100})
                    if not lines:
                        continue
                    best = max(lines, key=lambda x: x["prob"])
                    pred = f"{best['name']} {best['point']}"
                    return {"type": "Over/Under", "prediction": pred,
                            "display": "\n".join([f"{l['name']} {l['point']} : {l['prob']:.1f}% {generate_progress_bar(l['prob'])}" for l in lines])}
        return {"error": "not_available"}
    except Exception as e:
        return {"error": str(e)}

def get_best_odds(match):
    best = {"home": (0, ""), "draw": (0, ""), "away": (0, "")}
    for bm in match.get('bookmakers', []):
        name = bm.get('title', bm.get('key', '?'))
        for market in bm.get('markets', []):
            if market.get('key') != 'h2h':
                continue
            for o in market.get('outcomes', []):
                if o['name'] == match['home_team'] and o['price'] > best['home'][0]:
                    best['home'] = (o['price'], name)
                elif o['name'] == 'Draw' and o['price'] > best['draw'][0]:
                    best['draw'] = (o['price'], name)
                elif o['name'] == match['away_team'] and o['price'] > best['away'][0]:
                    best['away'] = (o['price'], name)
    return best

def format_best_odds(match, lang):
    best = get_best_odds(match)
    texte = f"{t(lang, 'best_odds')}\n\n"
    texte += f"🏠 {match['home_team']} : *{best['home'][0]}* ({best['home'][1]})\n"
    texte += f"🤝 Nul : *{best['draw'][0]}* ({best['draw'][1]})\n"
    texte += f"✈️ {match['away_team']} : *{best['away'][0]}* ({best['away'][1]})\n"
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
# 9. MENUS
# ------------------------------------------------------------
def menu_options(lang):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton(t(lang, "menu_pred_today")),
        KeyboardButton(t(lang, "menu_week")),
        KeyboardButton(t(lang, "menu_by_league")),
        KeyboardButton(t(lang, "menu_search")),
        KeyboardButton(t(lang, "menu_stats")),
        KeyboardButton(t(lang, "menu_follow")),
        KeyboardButton(t(lang, "menu_backtest")),
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

def menu_ligues_inline(lang, page=0):
    markup = InlineKeyboardMarkup(row_width=2)
    sports = get_sports()
    items = list(sports.items())
    per_page = 20
    start = page * per_page
    end = start + per_page
    for nom, cle in items[start:end]:
        display = nom if len(nom) <= 30 else nom[:29] + "…"
        markup.add(InlineKeyboardButton(display, callback_data=f"league_{cle}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(t(lang, "prev_short"), callback_data=f"lgpage_{page-1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton(t(lang, "next_short"), callback_data=f"lgpage_{page+1}"))
    if nav:
        markup.add(*nav)
    markup.add(InlineKeyboardButton(t(lang, "total_leagues", count=len(sports)), callback_data="noop"))
    markup.add(InlineKeyboardButton(t(lang, "back"), callback_data="menu_back"))
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

def menu_matchs_inline_list(sport_key, matches, lang="fr"):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, m in enumerate(matches[:10]):
        dt = format_datetime(m.get("commence_time", ""))
        markup.add(InlineKeyboardButton(f"📅 {dt}\n⚽ {m['home_team']} vs {m['away_team']}",
                                         callback_data=f"match_league_{sport_key}_{i}"))
    markup.add(InlineKeyboardButton(t(lang, "back"), callback_data="choose_league"))
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
# 10. BOT TELEGRAM
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

@bot.message_handler(commands=['refresh'])
def handle_refresh(message):
    global _SPORTS_CACHE, _SPORTS_CACHE_TIME
    _SPORTS_CACHE = None
    _SPORTS_CACHE_TIME = None
    lang = get_user_lang(message.from_user.id) or "fr"
    new_sports = get_sports()
    bot.reply_to(message, f"✅ {len(new_sports)} championnats rechargés.")

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

        if call.data == "noop":
            return

        if call.data == "menu_back":
            bot.send_message(chat_id, f"{t(lang, 'welcome')}\n\n👇",
                             parse_mode="Markdown", reply_markup=menu_options(lang))
            return

        if call.data == "choose_league":
            bot.send_message(chat_id, t(lang, "choose_league"),
                             parse_mode="Markdown", reply_markup=menu_ligues_inline(lang, 0))
            return

        if call.data.startswith("lgpage_"):
            page = int(call.data.replace("lgpage_", ""))
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=menu_ligues_inline(lang, page))
            return

        if call.data == "back_to_matches":
            if bot.current_matches_list:
                bot.send_message(chat_id, t(lang, "match_count", count=len(bot.current_matches_list)),
                                 parse_mode="Markdown",
                                 reply_markup=menu_matchs_list(bot.current_matches_list, "match_day", lang))
            else:
                bot.send_message(chat_id, t(lang, "back"), parse_mode="Markdown", reply_markup=menu_ligues_inline(lang))
            return

        if call.data.startswith("league_"):
            sport_key = call.data.replace("league_", "")
            loading = bot.send_message(chat_id, t(lang, "loading"), parse_mode="Markdown")
            matches, error = get_matches_for_league(sport_key)
            if error == "empty":
                bot.edit_message_text(t(lang, "no_league_matches"), chat_id, loading.message_id)
                return
            if error or not matches:
                bot.edit_message_text(t(lang, "no_matches"), chat_id, loading.message_id)
                return
            sports = get_sports()
            nom_ligue = next((k for k, v in sports.items() if v == sport_key), sport_key)
            for i, m in enumerate(matches[:10]):
                m["league_name"] = nom_ligue
                bot.match_cache[f"match_league_{sport_key}_{i}"] = m
            bot.delete_message(chat_id, loading.message_id)
            bot.send_message(chat_id, t(lang, "choose_match"), parse_mode="Markdown",
                             reply_markup=menu_matchs_inline_list(sport_key, matches, lang))
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

        if call.data.startswith("match_day_") or call.data.startswith("match_league_"):
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

    if text == t(lang, "menu_by_league"):
        sports = get_sports()
        bot.reply_to(message, f"🏆 *{len(sports)}*\n\n{t(lang, 'choose_league')}",
                     parse_mode="Markdown", reply_markup=menu_ligues_inline(lang, 0))
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
        matches = get_all_matches(days_ahead=None)
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
# 11. SERVEUR HTTP POUR RENDER
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
# 12. LANCEMENT
# ------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("✅ Base de données initialisée.")
    sports = get_sports()
    print(f"✅ {len(sports)} championnats chargés.")
    print("⏱️ Filtre : masque les matchs commencés il y a plus de 20 minutes.")
    print("⚡ Parallélisation : 10 requêtes simultanées")
    print("✅ Bot démarré.")
    bot.infinity_polling()