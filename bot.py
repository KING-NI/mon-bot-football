import os
import requests
import telebot
import sqlite3
import time
import threading
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ------------------------------------------------------------
# 1. CONFIGURATION
# ------------------------------------------------------------
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_BASE_URL = "https://v3.football.api-sports.io"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# ------------------------------------------------------------
# 2. CHAMPIONNATS POPULAIRES
# ------------------------------------------------------------
POPULAR_LEAGUES = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": 39,
    "🇫🇷 Ligue 1": 61,
    "🇩🇪 Bundesliga": 78,
    "🇪🇸 La Liga": 140,
    "🇮🇹 Serie A": 135,
    "🇳🇱 Eredivisie": 88,
    "🇵🇹 Primeira Liga": 94,
    "🇧🇪 Pro League": 144,
    "🇹🇷 Süper Lig": 203,
    "🇺🇸 MLS": 253,
    "🇧🇷 Brasileirão": 71,
    "🇲🇽 Liga MX": 262,
    "🇯🇵 J-League": 98,
    "🏆 Ligue des Champions": 2,
    "🏆 Ligue Europa": 3,
    "🇪🇺 Ligue des Nations": 5,
    "🌍 Coupe du Monde": 1,
}

# ------------------------------------------------------------
# 3. TRADUCTION DES TERMES API
# ------------------------------------------------------------
API_TERMS = {
    "fr": {
        "win_or_draw": "Victoire ou Nul", "under_over": "Plus/Moins de buts",
        "winner": "Vainqueur prévu", "advice": "Conseil",
        "form": "Forme", "att": "Attaque", "def": "Défense",
        "poisson": "Poisson", "h2h": "Confrontations",
        "goals": "Buts", "total": "Total",
        "yes": "✅ Oui", "no": "❌ Non",
        "not_available": "Non disponible", "no_advice": "Aucun conseil",
        "score_predicted": "Score exact prévu",
        "home": "Domicile", "away": "Extérieur", "draw": "Nul",
    },
    "en": {
        "win_or_draw": "Win or Draw", "under_over": "Under/Over",
        "winner": "Predicted winner", "advice": "Advice",
        "form": "Form", "att": "Attack", "def": "Defense",
        "poisson": "Poisson", "h2h": "Head to Head",
        "goals": "Goals", "total": "Total",
        "yes": "✅ Yes", "no": "❌ No",
        "not_available": "Not available", "no_advice": "No advice",
        "score_predicted": "Predicted score",
        "home": "Home", "away": "Away", "draw": "Draw",
    },
    "es": {
        "win_or_draw": "Victoria o Empate", "under_over": "Más/Menos goles",
        "winner": "Ganador previsto", "advice": "Consejo",
        "form": "Forma", "att": "Ataque", "def": "Defensa",
        "poisson": "Poisson", "h2h": "Cara a cara",
        "goals": "Goles", "total": "Total",
        "yes": "✅ Sí", "no": "❌ No",
        "not_available": "No disponible", "no_advice": "Sin consejo",
        "score_predicted": "Marcador previsto",
        "home": "Local", "away": "Visitante", "draw": "Empate",
    },
    "pt": {
        "win_or_draw": "Vitória ou Empate", "under_over": "Mais/Menos golos",
        "winner": "Vencedor previsto", "advice": "Conselho",
        "form": "Forma", "att": "Ataque", "def": "Defesa",
        "poisson": "Poisson", "h2h": "Confrontos",
        "goals": "Golos", "total": "Total",
        "yes": "✅ Sim", "no": "❌ Não",
        "not_available": "Não disponível", "no_advice": "Sem conselho",
        "score_predicted": "Resultado previsto",
        "home": "Casa", "away": "Fora", "draw": "Empate",
    },
    "ar": {
        "win_or_draw": "فوز أو تعادل", "under_over": "أكثر/أقل",
        "winner": "الفائز المتوقع", "advice": "نصيحة",
        "form": "الشكل", "att": "الهجوم", "def": "الدفاع",
        "poisson": "بواسون", "h2h": "المواجهات",
        "goals": "الأهداف", "total": "المجموع",
        "yes": "✅ نعم", "no": "❌ لا",
        "not_available": "غير متاح", "no_advice": "لا نصيحة",
        "score_predicted": "النتيجة المتوقعة",
        "home": "المنزل", "away": "الخارج", "draw": "تعادل",
    },
}

def at(lang, key):
    return API_TERMS.get(lang, API_TERMS["fr"]).get(key, key)

def translate_advice(advice, lang):
    """Traduit les conseils API-Football en langue cible."""
    if not advice:
        return advice
    # 1. D'abord les expressions complètes (avant les mots isolés)
    full_phrases = {
        "fr": {
            "Win or draw": "Victoire ou Nul",
            "Combo Double chance": "Combo Double chance",
            "Double chance": "Double chance",
            "Winner:": "Vainqueur :",
        },
        "es": {
            "Win or draw": "Victoria o Empate",
            "Combo Double chance": "Combo Doble oportunidad",
            "Double chance": "Doble oportunidad",
            "Winner:": "Ganador:",
        },
        "pt": {
            "Win or draw": "Vitória ou Empate",
            "Combo Double chance": "Combo Dupla chance",
            "Double chance": "Dupla chance",
            "Winner:": "Vencedor:",
        },
        "ar": {
            "Win or draw": "فوز أو تعادل",
            "Combo Double chance": "فرصة مزدوجة مركبة",
            "Double chance": "فرصة مزدوجة",
            "Winner:": "الفائز:",
        },
        "en": {},
    }
    # 2. Puis les mots isolés
    single_words = {
        "fr": {
            " and ": " et ", "goals": "buts", "goal": "but",
            "draw": "nul", " or ": " ou ",
        },
        "es": {
            " and ": " y ", "goals": "goles", "goal": "gol",
            "draw": "empate", " or ": " o ",
        },
        "pt": {
            " and ": " e ", "goals": "golos", "goal": "golo",
            "draw": "empate", " or ": " ou ",
        },
        "ar": {
            " and ": " و ", "goals": "أهداف", "goal": "هدف",
            "draw": "تعادل", " or ": " أو ",
        },
        "en": {},
    }
    result = advice
    for en_term, translated in full_phrases.get(lang, {}).items():
        result = result.replace(en_term, translated)
    for en_term, translated in single_words.get(lang, {}).items():
        result = result.replace(en_term, translated)
    return result

def is_valid_uo(value):
    """Vérifie si la valeur Under/Over est valide (positive)."""
    if not value or value == "N/A":
        return False
    try:
        v = float(str(value).replace("+", "").strip())
        return v > 0
    except:
        return False

# ------------------------------------------------------------
# 4. LANGUES
# ------------------------------------------------------------
LANG_FLAGS = {
    "fr": "🇫🇷 Français", "en": "🇬🇧 English", "es": "🇪🇸 Español",
    "pt": "🇵🇹 Português", "ar": "🇸🇦 العربية",
}

LANGUAGES = {
    "fr": {
        "welcome": "👋 *Bienvenue sur KING NI Predict Bot !*",
        "choose_lang": "🌐 *Choisis ta langue :*", "lang_set": "✅ Langue : *Français*.",
        "menu_pred_today": "🔮 Pronostics du jour", "menu_week": "📅 Pronostics de la semaine",
        "menu_by_league": "🏆 Par championnat", "menu_search": "⚽ Rechercher une équipe",
        "menu_stats": "📊 Statistiques", "menu_follow": "🔔 Suivre une équipe",
        "menu_backtest": "📈 Backtesting", "menu_trends": "📊 Mes tendances",
        "menu_lang": "🌐 Langue", "menu_help": "❓ Aide", "menu_reset": "🔄 Réinitialiser",
        "loading": "⏳ *Récupération...*", "back": "🔙 Retour",
        "choose_match": "⚽ *Choisis un match :*", "choose_market": "📊 *Choisis un marché :*",
        "no_match_today": "⚠️ Aucun match aujourd'hui.",
        "no_match_week": "⚠️ Aucun match dans les 7 prochains jours.",
        "m_all": "📚 Tous les marchés", "m_1x2": "🔮 1X2 + Probabilités",
        "m_ou": "📈 Plus/Moins de buts", "m_score": "⚽ Score exact prévu",
        "m_advice": "💡 Conseil API", "m_compare": "📊 Comparaison stats",
        "no_market": "❌ Aucun marché disponible.",
        "search_prompt": "⚽ *Recherche*\n\nEnvoie un nom (ex: `Arsenal`).",
        "follow_prompt": "🔔 Envoie `suivre Arsenal`.",
        "following": "✅ Tu suis *{team}*.", "following_list": "📋 *Équipes suivies*",
        "help_text": "❓ *Aide*\n\nUtilise les boutons.",
        "matches_found": "🔍 *{count} match(s)* :", "page": "📄 Page",
        "prev": "⬅️ Précédent", "next": "Suivant ➡️", "match_count": "🔮 *{count} matchs :*",
        "choose_league": "🏆 *Choisis un championnat :*",
    },
    "en": {
        "welcome": "👋 *Welcome to KING NI Predict Bot !*",
        "choose_lang": "🌐 *Choose your language :*", "lang_set": "✅ Language: *English*.",
        "menu_pred_today": "🔮 Today's predictions", "menu_week": "📅 Week's predictions",
        "menu_by_league": "🏆 By league", "menu_search": "⚽ Search team",
        "menu_stats": "📊 Statistics", "menu_follow": "🔔 Follow a team",
        "menu_backtest": "📈 Backtesting", "menu_trends": "📊 My trends",
        "menu_lang": "🌐 Language", "menu_help": "❓ Help", "menu_reset": "🔄 Reset",
        "loading": "⏳ *Loading...*", "back": "🔙 Back",
        "choose_match": "⚽ *Choose a match :*", "choose_market": "📊 *Choose a market :*",
        "no_match_today": "⚠️ No matches today.",
        "no_match_week": "⚠️ No matches in the next 7 days.",
        "m_all": "📚 All markets", "m_1x2": "🔮 1X2 + Odds",
        "m_ou": "📈 Over/Under", "m_score": "⚽ Predicted score",
        "m_advice": "💡 API Advice", "m_compare": "📊 Stats comparison",
        "no_market": "❌ No market available.",
        "search_prompt": "⚽ *Search*\n\nSend a name (e.g. `Arsenal`).",
        "follow_prompt": "🔔 Send `follow Arsenal`.",
        "following": "✅ You follow *{team}*.", "following_list": "📋 *Followed teams*",
        "help_text": "❓ *Help*\n\nUse the buttons.",
        "matches_found": "🔍 *{count} match(es)* :", "page": "📄 Page",
        "prev": "⬅️ Previous", "next": "Next ➡️", "match_count": "🔮 *{count} matches:*",
        "choose_league": "🏆 *Choose a league :*",
    },
    "es": {
        "welcome": "👋 *¡Bienvenido a KING NI Predict Bot !*",
        "choose_lang": "🌐 *Elige tu idioma :*", "lang_set": "✅ Idioma: *Español*.",
        "menu_pred_today": "🔮 Pronósticos de hoy", "menu_week": "📅 Pronósticos de la semana",
        "menu_by_league": "🏆 Por liga", "menu_search": "⚽ Buscar equipo",
        "menu_stats": "📊 Estadísticas", "menu_follow": "🔔 Seguir un equipo",
        "menu_backtest": "📈 Backtesting", "menu_trends": "📊 Mis tendencias",
        "menu_lang": "🌐 Idioma", "menu_help": "❓ Ayuda", "menu_reset": "🔄 Reiniciar",
        "loading": "⏳ *Cargando...*", "back": "🔙 Volver",
        "choose_match": "⚽ *Elige un partido :*", "choose_market": "📊 *Elige un mercado :*",
        "no_match_today": "⚠️ Sin partidos hoy.",
        "no_match_week": "⚠️ Sin partidos en 7 días.",
        "m_all": "📚 Todos los mercados", "m_1x2": "🔮 1X2 + Cuotas",
        "m_ou": "📈 Más/Menos", "m_score": "⚽ Marcador previsto",
        "m_advice": "💡 Consejo API", "m_compare": "📊 Comparación",
        "no_market": "❌ Sin mercado.",
        "search_prompt": "⚽ *Búsqueda*\n\nEnvía un nombre.",
        "follow_prompt": "🔔 Envía `seguir Arsenal`.",
        "following": "✅ Sigues a *{team}*.", "following_list": "📋 *Equipos seguidos*",
        "help_text": "❓ *Ayuda*\n\nUsa los botones.",
        "matches_found": "🔍 *{count} partido(s)* :", "page": "📄 Página",
        "prev": "⬅️ Anterior", "next": "Siguiente ➡️", "match_count": "🔮 *{count} partidos:*",
        "choose_league": "🏆 *Elige una liga :*",
    },
    "pt": {
        "welcome": "👋 *Bem-vindo ao KING NI Predict Bot !*",
        "choose_lang": "🌐 *Escolhe o teu idioma :*", "lang_set": "✅ Idioma: *Português*.",
        "menu_pred_today": "🔮 Prognósticos de hoje", "menu_week": "📅 Prognósticos da semana",
        "menu_by_league": "🏆 Por campeonato", "menu_search": "⚽ Buscar equipa",
        "menu_stats": "📊 Estatísticas", "menu_follow": "🔔 Seguir uma equipa",
        "menu_backtest": "📈 Backtesting", "menu_trends": "📊 Minhas tendências",
        "menu_lang": "🌐 Idioma", "menu_help": "❓ Ajuda", "menu_reset": "🔄 Reiniciar",
        "loading": "⏳ *A carregar...*", "back": "🔙 Voltar",
        "choose_match": "⚽ *Escolhe um jogo :*", "choose_market": "📊 *Escolhe um mercado :*",
        "no_match_today": "⚠️ Sem jogos hoje.",
        "no_match_week": "⚠️ Sem jogos em 7 dias.",
        "m_all": "📚 Todos os mercados", "m_1x2": "🔮 1X2 + Cotações",
        "m_ou": "📈 Mais/Menos", "m_score": "⚽ Resultado previsto",
        "m_advice": "💡 Conselho API", "m_compare": "📊 Comparação",
        "no_market": "❌ Sem mercado.",
        "search_prompt": "⚽ *Busca*\n\nEnvia um nome.",
        "follow_prompt": "🔔 Envia `seguir Arsenal`.",
        "following": "✅ Segues *{team}*.", "following_list": "📋 *Equipas seguidas*",
        "help_text": "❓ *Ajuda*\n\nUsa os botões.",
        "matches_found": "🔍 *{count} jogo(s)* :", "page": "📄 Página",
        "prev": "⬅️ Anterior", "next": "Seguinte ➡️", "match_count": "🔮 *{count} jogos:*",
        "choose_league": "🏆 *Escolhe um campeonato :*",
    },
    "ar": {
        "welcome": "👋 *مرحبا بك في KING NI Predict Bot !*",
        "choose_lang": "🌐 *اختر لغتك :*", "lang_set": "✅ اللغة: *العربية*.",
        "menu_pred_today": "🔮 توقعات اليوم", "menu_week": "📅 توقعات الأسبوع",
        "menu_by_league": "🏆 حسب البطولة", "menu_search": "⚽ البحث عن فريق",
        "menu_stats": "📊 الإحصائيات", "menu_follow": "🔔 متابعة فريق",
        "menu_backtest": "📈 الاختبار", "menu_trends": "📊 اتجاهاتي",
        "menu_lang": "🌐 اللغة", "menu_help": "❓ مساعدة", "menu_reset": "🔄 إعادة تعيين",
        "loading": "⏳ *جاري التحميل...*", "back": "🔙 رجوع",
        "choose_match": "⚽ *اختر مباراة :*", "choose_market": "📊 *اختر سوقاً :*",
        "no_match_today": "⚠️ لا مباريات اليوم.",
        "no_match_week": "⚠️ لا مباريات في 7 أيام.",
        "m_all": "📚 كل الأسواق", "m_1x2": "🔮 1X2",
        "m_ou": "📈 أكثر/أقل", "m_score": "⚽ النتيجة المتوقعة",
        "m_advice": "💡 نصيحة API", "m_compare": "📊 مقارنة",
        "no_market": "❌ لا سوق متاح.",
        "search_prompt": "⚽ *بحث*\n\nأرسل اسماً.",
        "follow_prompt": "🔔 أرسل `suivre Arsenal`.",
        "following": "✅ تتابع *{team}*.", "following_list": "📋 *الفرق المتابعة*",
        "help_text": "❓ *مساعدة*\n\nاستخدم الأزرار.",
        "matches_found": "🔍 *{count} مباراة* :", "page": "📄 صفحة",
        "prev": "⬅️ السابق", "next": "التالي ➡️", "match_count": "🔮 *{count} مباريات:*",
        "choose_league": "🏆 *اختر بطولة :*",
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
# 5. UTILITAIRES
# ------------------------------------------------------------
def format_datetime(iso_date):
    if not iso_date:
        return "?"
    try:
        dt = datetime.strptime(iso_date[:19], "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%d/%m/%Y %Hh%M")
    except:
        return iso_date[:10] if len(iso_date) >= 10 else "?"

def progress_bar(value, total=100, length=10):
    try:
        v = float(str(value).replace("%", ""))
    except:
        v = 0
    filled = int((v / total) * length)
    return "█" * max(0, filled) + "░" * (length - max(0, filled))

def is_match_upcoming(match, tolerance_minutes=20):
    try:
        date_str = match.get("fixture", {}).get("date", "")
        if not date_str:
            return True
        dt = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
        now_utc = datetime.utcnow()
        return now_utc <= dt + timedelta(minutes=tolerance_minutes)
    except:
        return True

def parse_score_value(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "?":
        return None
    if "-" in s and not s.startswith("-"):
        try:
            return int(s.split("-")[0])
        except:
            return None
    if s.startswith("-"):
        return None
    try:
        return int(float(s))
    except:
        return None

def calculate_score_from_probs(percent):
    try:
        ph = float(percent.get("home", "0%").replace("%", ""))
        pd = float(percent.get("draw", "0%").replace("%", ""))
        pa = float(percent.get("away", "0%").replace("%", ""))
    except:
        ph, pd, pa = 40, 30, 30
    if ph > 60: h, a = 2, 0
    elif ph > 45: h, a = 2, 1
    elif ph > 35: h, a = 1, 0
    elif pa > 60: h, a = 0, 2
    elif pa > 45: h, a = 1, 2
    elif pa > 35: h, a = 0, 1
    else: h, a = 1, 1
    if ph > pa + 20: h = max(h, a + 1)
    elif pa > ph + 20: a = max(a, h + 1)
    return h, a

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
    cur.execute('SELECT COUNT(*) FROM predictions WHERE user_id = ?', (user_id,))
    total_all = cur.fetchone()[0]
    conn.close()
    if total and total > 0:
        rate = ((correct or 0) / total * 100)
        return (f"📊 *Backtesting*\n\n"
                f"📝 Total enregistrés : {total_all}\n"
                f"✅ Vérifiés : {total}\n"
                f"🎯 Justes : {correct or 0}\n"
                f"📈 Taux : {rate:.1f}%")
    return (f"📊 Aucune donnée de backtesting pour le moment.\n\n"
            f"📝 Total de pronostics enregistrés : {total_all}\n"
            f"⏳ Les résultats seront vérifiés automatiquement.")

# ------------------------------------------------------------
# 7. API-FOOTBALL
# ------------------------------------------------------------
_cache = {}
_cache_time = {}

def api_request(endpoint, params=None, cache_ttl=600):
    cache_key = f"{endpoint}_{str(params)}"
    now = time.time()
    if cache_key in _cache and cache_key in _cache_time:
        if now - _cache_time[cache_key] < cache_ttl:
            return _cache[cache_key]
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    try:
        r = requests.get(f"{API_BASE_URL}/{endpoint}", headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("errors"):
                print(f"⚠️ API-Football: {data['errors']}")
                return None
            _cache[cache_key] = data
            _cache_time[cache_key] = now
            return data
    except Exception as e:
        print(f"⚠️ {endpoint}: {e}")
    return None

def get_fixtures_by_date(date_str):
    data = api_request("fixtures", params={"date": date_str}, cache_ttl=900)
    return data.get("response", []) if data else []

def get_matches_today():
    today = datetime.now().strftime("%Y-%m-%d")
    fixtures = get_fixtures_by_date(today)
    matches = []
    for f in fixtures:
        if not is_match_upcoming(f): continue
        status = f.get("fixture", {}).get("status", {}).get("short", "")
        if status in ("FT", "AET", "PEN"): continue
        matches.append(f)
    matches.sort(key=lambda x: x.get("fixture", {}).get("date", ""))
    return matches

def get_matches_week():
    all_matches = []
    for i in range(8):
        date_str = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        for f in get_fixtures_by_date(date_str):
            if not is_match_upcoming(f): continue
            status = f.get("fixture", {}).get("status", {}).get("short", "")
            if status in ("FT", "AET", "PEN"): continue
            all_matches.append(f)
    all_matches.sort(key=lambda x: x.get("fixture", {}).get("date", ""))
    return all_matches

def get_matches_by_league(league_id):
    all_matches = []
    current_season = datetime.now().year
    for i in range(8):
        date_str = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        data = api_request("fixtures", params={"league": league_id, "season": current_season, "date": date_str}, cache_ttl=1800)
        if data and data.get("response"):
            for f in data["response"]:
                if not is_match_upcoming(f): continue
                status = f.get("fixture", {}).get("status", {}).get("short", "")
                if status in ("FT", "AET", "PEN"): continue
                all_matches.append(f)
    all_matches.sort(key=lambda x: x.get("fixture", {}).get("date", ""))
    return all_matches

def get_predictions(fixture_id):
    data = api_request("predictions", params={"fixture": fixture_id}, cache_ttl=1800)
    if not data or not data.get("response"):
        return None
    return data["response"][0]

# ------------------------------------------------------------
# 8. MARCHÉS
# ------------------------------------------------------------
def get_all_markets_text(fixture, lang="fr"):
    try:
        fixture_id = fixture.get("fixture", {}).get("id")
        if not fixture_id: return t(lang, "no_market")
        preds = get_predictions(fixture_id)
        if not preds: return t(lang, "no_market")
        home = fixture.get("teams", {}).get("home", {}).get("name", "?")
        away = fixture.get("teams", {}).get("away", {}).get("name", "?")
        predictions = preds.get("predictions", {})
        percent = predictions.get("percent", {})
        comparison = preds.get("comparison", {})
        teams_stats = preds.get("teams", {})
        txt = f"⚽ *{home} vs {away}*\n\n"
        ph = percent.get("home", "0%"); pd = percent.get("draw", "0%"); pa = percent.get("away", "0%")
        txt += f"🔮 *1X2*\n"
        txt += f"🏠 {home} : {ph} {progress_bar(ph)}\n"
        txt += f"🤝 {at(lang, 'draw')} : {pd} {progress_bar(pd)}\n"
        txt += f"✈️ {away} : {pa} {progress_bar(pa)}\n\n"
        winner = predictions.get("winner", {})
        if winner.get("name"):
            txt += f"🏆 *{at(lang, 'winner')}* : {winner['name']}"
            if winner.get("comment"):
                comment = translate_advice(winner['comment'], lang)
                txt += f" _{comment}_"
            txt += "\n\n"
        wod = predictions.get("win_or_draw")
        if wod is not None:
            txt += f"🎯 *{at(lang, 'win_or_draw')}* : {at(lang, 'yes') if wod else at(lang, 'no')}\n\n"
        uo = predictions.get("under_over")
        if is_valid_uo(uo):
            txt += f"📈 *{at(lang, 'under_over')}* : {uo}\n\n"
        goals = predictions.get("goals", {})
        gh = parse_score_value(goals.get("home"))
        ga = parse_score_value(goals.get("away"))
        if gh is None or ga is None:
            gh, ga = calculate_score_from_probs(percent)
        txt += f"⚽ *{at(lang, 'score_predicted')}* : {home} {gh}-{ga} {away}\n\n"
        advice = predictions.get("advice")
        if advice and advice != "No predictions available":
            advice_translated = translate_advice(advice, lang)
            txt += f"💡 *{at(lang, 'advice')}* : {advice_translated}\n\n"
        if comparison:
            txt += f"📊 *{at(lang, 'total')}*\n"
            labels = [("form", at(lang, "form")), ("att", at(lang, "att")), ("def", at(lang, "def")),
                      ("poisson_distribution", at(lang, "poisson")), ("h2h", at(lang, "h2h")),
                      ("goals", at(lang, "goals")), ("total", at(lang, "total"))]
            for key, label in labels:
                data = comparison.get(key, {})
                h = data.get("home", "?"); a = data.get("away", "?")
                txt += f"`{label:<12} 🏠 {h:<6} ✈️ {a}`\n"
            txt += "\n"
        for team_key in ["home", "away"]:
            ts = teams_stats.get(team_key, {})
            form = ts.get("forme", "")
            if form:
                team_name = ts.get("name", "?")
                txt += f"📈 *{team_name}* : {form}\n"
        return txt
    except Exception as e:
        return f"❌ Erreur : {str(e)[:100]}"

def get_market_text(fixture, market_type, lang="fr"):
    try:
        fixture_id = fixture.get("fixture", {}).get("id")
        if not fixture_id: return t(lang, "no_market"), None
        preds = get_predictions(fixture_id)
        if not preds: return t(lang, "no_market"), None
        home = fixture.get("teams", {}).get("home", {}).get("name", "?")
        away = fixture.get("teams", {}).get("away", {}).get("name", "?")
        predictions = preds.get("predictions", {})
        comparison = preds.get("comparison", {})
        percent = predictions.get("percent", {})
        if market_type == "h2h":
            ph = percent.get("home", "0%").replace("%", "")
            pd = percent.get("draw", "0%").replace("%", "")
            pa = percent.get("away", "0%").replace("%", "")
            ph_f = float(ph) if ph else 0
            pd_f = float(pd) if pd else 0
            pa_f = float(pa) if pa else 0
            if ph_f > pa_f and ph_f > pd_f: pred = f"🏠 {home}"
            elif pa_f > ph_f and pa_f > pd_f: pred = f"✈️ {away}"
            else: pred = f"🤝 {at(lang, 'draw')}"
            txt = f"🔮 *1X2*\n\n"
            txt += f"🏠 {home} : {ph_f:.1f}% {progress_bar(ph_f)}\n"
            txt += f"🤝 {at(lang, 'draw')} : {pd_f:.1f}% {progress_bar(pd_f)}\n"
            txt += f"✈️ {away} : {pa_f:.1f}% {progress_bar(pa_f)}\n\n"
            txt += f"✅ *{pred}*"
            return txt, {"prob_home": ph_f, "prob_draw": pd_f, "prob_away": pa_f, "prediction": pred}
        elif market_type == "ou":
            uo = predictions.get("under_over", "N/A")
            goals = predictions.get("goals", {})
            txt = f"📈 *{at(lang, 'under_over')}*\n\n"
            if is_valid_uo(uo):
                txt += f"🎯 {at(lang, 'advice')} : *{uo}*\n\n"
            else:
                txt += f"⚠️ {at(lang, 'not_available')}\n\n"
            txt += f"⚽ {at(lang, 'goals')} :\n"
            txt += f"🏠 {home} : {goals.get('home','?')}\n"
            txt += f"✈️ {away} : {goals.get('away','?')}\n"
            return txt, {"prediction": uo if is_valid_uo(uo) else "N/A"}
        elif market_type == "score":
            goals = predictions.get("goals", {})
            gh = parse_score_value(goals.get("home"))
            ga = parse_score_value(goals.get("away"))
            if gh is None or ga is None:
                gh, ga = calculate_score_from_probs(percent)
            txt = f"⚽ *{at(lang, 'score_predicted')}*\n\n"
            txt += f"🎯 *{home} {gh}-{ga} {away}*\n\n"
            winner = predictions.get("winner", {}).get("name", "?")
            txt += f"🏆 {at(lang, 'winner')} : {winner}"
            return txt, {"prediction": f"{gh}-{ga}"}
        elif market_type == "advice":
            advice = predictions.get("advice", at(lang, "no_advice"))
            winner = predictions.get("winner", {})
            txt = f"💡 *{at(lang, 'advice')}*\n\n"
            if advice and advice != "No predictions available":
                advice_translated = translate_advice(advice, lang)
                txt += f"📌 {advice_translated}\n\n"
            else:
                txt += f"📌 {at(lang, 'no_advice')}\n\n"
            if winner.get("name"):
                txt += f"🏆 {at(lang, 'winner')} : *{winner['name']}*\n"
                if winner.get("comment"):
                    comment = translate_advice(winner['comment'], lang)
                    txt += f"_{comment}_"
            return txt, {"prediction": advice}
        elif market_type == "compare":
            txt = f"📊 *{at(lang, 'total')}*\n\n"
            labels = [("form", at(lang, "form")), ("att", at(lang, "att")), ("def", at(lang, "def")),
                      ("poisson_distribution", at(lang, "poisson")), ("h2h", at(lang, "h2h")),
                      ("goals", at(lang, "goals")), ("total", at(lang, "total"))]
            for key, label in labels:
                data = comparison.get(key, {})
                h = data.get("home", "?"); a = data.get("away", "?")
                txt += f"`{label:<12} 🏠 {h:<6} ✈️ {a}`\n"
            return txt, {"prediction": at(lang, "total")}
        return t(lang, "no_market"), None
    except Exception as e:
        return f"❌ Erreur : {str(e)[:100]}", None

# ------------------------------------------------------------
# 9. MENUS
# ------------------------------------------------------------
def menu_options(lang):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton(t(lang, "menu_pred_today")), KeyboardButton(t(lang, "menu_week")),
        KeyboardButton(t(lang, "menu_by_league")), KeyboardButton(t(lang, "menu_search")),
        KeyboardButton(t(lang, "menu_stats")), KeyboardButton(t(lang, "menu_follow")),
        KeyboardButton(t(lang, "menu_backtest")), KeyboardButton(t(lang, "menu_trends")),
        KeyboardButton(t(lang, "menu_lang")), KeyboardButton(t(lang, "menu_help")),
        KeyboardButton(t(lang, "menu_reset"))
    )
    return markup

def menu_lang_inline():
    markup = InlineKeyboardMarkup(row_width=1)
    for code, name in LANG_FLAGS.items():
        markup.add(InlineKeyboardButton(name, callback_data=f"setlang_{code}"))
    return markup

def menu_leagues_inline():
    markup = InlineKeyboardMarkup(row_width=2)
    for name, lid in POPULAR_LEAGUES.items():
        markup.add(InlineKeyboardButton(name, callback_data=f"league_{lid}"))
    return markup

def menu_matchs_list(matches, prefix="match_day", lang="fr", page=0):
    markup = InlineKeyboardMarkup(row_width=1)
    per_page = 8
    start = page * per_page
    end = start + per_page
    for i, f in enumerate(matches[start:end]):
        idx = start + i
        date_str = format_datetime(f.get("fixture", {}).get("date", ""))
        home = f.get("teams", {}).get("home", {}).get("name", "?")
        away = f.get("teams", {}).get("away", {}).get("name", "?")
        markup.add(InlineKeyboardButton(f"📅 {date_str}\n⚽ {home} vs {away}",
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

def menu_match_actions(match_id, lang="fr"):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(t(lang, "m_all"), callback_data=f"market_{match_id}_all"))
    markup.add(InlineKeyboardButton(t(lang, "m_1x2"), callback_data=f"market_{match_id}_h2h"))
    markup.add(InlineKeyboardButton(t(lang, "m_ou"), callback_data=f"market_{match_id}_ou"))
    markup.add(InlineKeyboardButton(t(lang, "m_score"), callback_data=f"market_{match_id}_score"))
    markup.add(InlineKeyboardButton(t(lang, "m_advice"), callback_data=f"market_{match_id}_advice"))
    markup.add(InlineKeyboardButton(t(lang, "m_compare"), callback_data=f"market_{match_id}_compare"))
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

        if call.data.startswith("league_"):
            league_id = int(call.data.replace("league_", ""))
            league_name = next((k for k, v in POPULAR_LEAGUES.items() if v == league_id), "?")
            loading = bot.send_message(chat_id, t(lang, "loading"), parse_mode="Markdown")
            matches = get_matches_by_league(league_id)
            if not matches:
                bot.edit_message_text(f"⚠️ Aucun match pour {league_name}.", chat_id, loading.message_id)
                return
            bot.current_matches_list = matches[:50]
            for i, m in enumerate(bot.current_matches_list):
                bot.match_cache[f"match_day_{i}"] = m
            bot.delete_message(chat_id, loading.message_id)
            bot.send_message(chat_id, t(lang, "match_count", count=len(bot.current_matches_list)),
                             parse_mode="Markdown",
                             reply_markup=menu_matchs_list(bot.current_matches_list, "match_day", lang, 0))
            return

        if call.data.startswith("match_day_"):
            fixture = bot.match_cache.get(call.data)
            if not fixture:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            bot.current_match_data[call.data] = fixture
            dt = format_datetime(fixture.get("fixture", {}).get("date", ""))
            league = fixture.get("league", {}).get("name", "?")
            home = fixture.get("teams", {}).get("home", {}).get("name", "?")
            away = fixture.get("teams", {}).get("away", {}).get("name", "?")
            texte = (f"🏆 *{league}*\n"
                     f"📅 {dt}\n\n"
                     f"⚽ *{home} vs {away}*\n\n"
                     f"{t(lang, 'choose_market')}")
            bot.send_message(chat_id, texte, parse_mode="Markdown",
                             reply_markup=menu_match_actions(call.data, lang))
            return

        if call.data.startswith("market_"):
            parts = call.data.replace("market_", "").rsplit("_", 1)
            market_type = parts[-1]
            mid = parts[0]
            fixture = bot.current_match_data.get(mid) or bot.match_cache.get(mid)
            if not fixture:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            
            home = fixture.get("teams", {}).get("home", {}).get("name", "?")
            away = fixture.get("teams", {}).get("away", {}).get("name", "?")
            dt = format_datetime(fixture.get("fixture", {}).get("date", ""))
            league = fixture.get("league", {}).get("name", "?")
            header = f"🏆 *{league}*\n📅 {dt}\n⚽ *{home} vs {away}*\n\n"
            
            if market_type == "all":
                txt = get_all_markets_text(fixture, lang)
                bot.send_message(chat_id, header + txt, parse_mode="Markdown")
                return
            
            txt, data = get_market_text(fixture, market_type, lang)
            if txt and data and market_type == "h2h":
                save_prediction(home, away, "1X2",
                                data.get('prob_home', 0), data.get('prob_draw', 0), data.get('prob_away', 0),
                                data.get('prediction', ''), user_id)
            
            bot.send_message(chat_id, header + txt, parse_mode="Markdown")
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
        bot.current_matches_list = all_matches[:80]
        for i, m in enumerate(bot.current_matches_list):
            bot.match_cache[f"match_day_{i}"] = m
        bot.delete_message(chat_id, loading.message_id)
        bot.send_message(chat_id, t(lang, "match_count", count=len(bot.current_matches_list)),
                         parse_mode="Markdown",
                         reply_markup=menu_matchs_list(bot.current_matches_list, "match_day", lang, 0))
        return

    if text == t(lang, "menu_by_league"):
        bot.reply_to(message, t(lang, "choose_league"),
                     parse_mode="Markdown", reply_markup=menu_leagues_inline())
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
            bot.reply_to(message, f"{t(lang, 'following_list')}\n\n" + ", ".join([f[0] for f in followed]))
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
        matches = get_matches_week()
    except:
        matches = []
    found = [m for m in matches 
             if text.lower() in m.get("teams", {}).get("home", {}).get("name", "").lower() 
             or text.lower() in m.get("teams", {}).get("away", {}).get("name", "").lower()]
    if not found:
        bot.edit_message_text(f"❌ Aucun match pour *{text}*.", chat_id, loading.message_id, parse_mode="Markdown")
        return
    bot.current_matches_list = found[:50]
    for i, m in enumerate(bot.current_matches_list):
        bot.match_cache[f"match_day_{i}"] = m
    bot.edit_message_text(t(lang, "matches_found", count=len(found)),
                          chat_id, loading.message_id, parse_mode="Markdown",
                          reply_markup=menu_matchs_list(bot.current_matches_list, "match_day", lang, 0))

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
    print("⚽ API-Football - Traduction complète + filtre U/O négatif")
    print("✅ Bot démarré.")
    bot.infinity_polling()