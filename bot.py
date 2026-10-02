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
        "lang_set": "✅ Langue : *Français*.",
        "menu_pred_today": "🔮 Pronostics du jour",
        "menu_week": "📅 Pronostics de la semaine",
        "menu_search": "⚽ Rechercher une équipe",
        "menu_stats": "📊 Statistiques",
        "menu_follow": "🔔 Suivre une équipe",
        "menu_trends": "📊 Mes tendances",
        "menu_lang": "🌐 Langue",
        "menu_help": "❓ Aide",
        "menu_reset": "🔄 Réinitialiser",
        "loading": "⏳ *Récupération...*",
        "back": "🔙 Retour",
        "choose_match": "⚽ *Choisis un match :*",
        "choose_market": "📊 *Choisis un marché :*",
        "no_match_today": "⚠️ Aucun match aujourd'hui.",
        "no_match_week": "⚠️ Aucun match dans les 7 prochains jours.",
        "m_1x2": "🔮 1X2 + Probabilités",
        "m_ou": "📈 Over/Under",
        "m_score": "⚽ Score exact prévu",
        "m_advice": "💡 Conseil API",
        "m_compare": "📊 Comparaison stats",
        "m_all": "📚 Tous les marchés",
        "no_market": "❌ Aucun marché disponible.",
        "search_prompt": "⚽ *Recherche*\n\nEnvoie un nom (ex: `Arsenal`).",
        "follow_prompt": "🔔 Envoie `suivre Arsenal`.",
        "following": "✅ Tu suis *{team}*.",
        "following_list": "📋 *Équipes suivies*",
        "stats_title": "📊 *Statistiques*",
        "no_data": "📊 Aucune donnée.",
        "help_text": "❓ *Aide*\n\nUtilise les boutons.",
        "matches_found": "🔍 *{count} match(s)* :",
        "page": "📄 Page",
        "prev": "⬅️ Précédent",
        "next": "Suivant ➡️",
        "match_count": "🔮 *{count} matchs :*",
    },
    "en": {
        "welcome": "👋 *Welcome to KING NI Predict Bot !*",
        "choose_lang": "🌐 *Choose your language :*",
        "lang_set": "✅ Language: *English*.",
        "menu_pred_today": "🔮 Today's predictions",
        "menu_week": "📅 Week's predictions",
        "menu_search": "⚽ Search team",
        "menu_stats": "📊 Statistics",
        "menu_follow": "🔔 Follow a team",
        "menu_trends": "📊 My trends",
        "menu_lang": "🌐 Language",
        "menu_help": "❓ Help",
        "menu_reset": "🔄 Reset",
        "loading": "⏳ *Loading...*",
        "back": "🔙 Back",
        "choose_match": "⚽ *Choose a match :*",
        "choose_market": "📊 *Choose a market :*",
        "no_match_today": "⚠️ No matches today.",
        "no_match_week": "⚠️ No matches in the next 7 days.",
        "m_1x2": "🔮 1X2 + Odds",
        "m_ou": "📈 Over/Under",
        "m_score": "⚽ Predicted score",
        "m_advice": "💡 API Advice",
        "m_compare": "📊 Stats comparison",
        "m_all": "📚 All markets",
        "no_market": "❌ No market available.",
        "search_prompt": "⚽ *Search*\n\nSend a name (e.g. `Arsenal`).",
        "follow_prompt": "🔔 Send `follow Arsenal`.",
        "following": "✅ You follow *{team}*.",
        "following_list": "📋 *Followed teams*",
        "stats_title": "📊 *Statistics*",
        "no_data": "📊 No data.",
        "help_text": "❓ *Help*\n\nUse the buttons.",
        "matches_found": "🔍 *{count} match(es)* :",
        "page": "📄 Page",
        "prev": "⬅️ Previous",
        "next": "Next ➡️",
        "match_count": "🔮 *{count} matches:*",
    },
    "es": {
        "welcome": "👋 *¡Bienvenido a KING NI Predict Bot !*",
        "choose_lang": "🌐 *Elige tu idioma :*",
        "lang_set": "✅ Idioma: *Español*.",
        "menu_pred_today": "🔮 Pronósticos de hoy",
        "menu_week": "📅 Pronósticos de la semana",
        "menu_search": "⚽ Buscar equipo",
        "menu_stats": "📊 Estadísticas",
        "menu_follow": "🔔 Seguir un equipo",
        "menu_trends": "📊 Mis tendencias",
        "menu_lang": "🌐 Idioma",
        "menu_help": "❓ Ayuda",
        "menu_reset": "🔄 Reiniciar",
        "loading": "⏳ *Cargando...*",
        "back": "🔙 Volver",
        "choose_match": "⚽ *Elige un partido :*",
        "choose_market": "📊 *Elige un mercado :*",
        "no_match_today": "⚠️ Sin partidos hoy.",
        "no_match_week": "⚠️ Sin partidos en 7 días.",
        "m_1x2": "🔮 1X2 + Cuotas",
        "m_ou": "📈 Más/Menos",
        "m_score": "⚽ Marcador previsto",
        "m_advice": "💡 Consejo API",
        "m_compare": "📊 Comparación",
        "m_all": "📚 Todos los mercados",
        "no_market": "❌ Sin mercado.",
        "search_prompt": "⚽ *Búsqueda*\n\nEnvía un nombre.",
        "follow_prompt": "🔔 Envía `seguir Arsenal`.",
        "following": "✅ Sigues a *{team}*.",
        "following_list": "📋 *Equipos seguidos*",
        "stats_title": "📊 *Estadísticas*",
        "no_data": "📊 Sin datos.",
        "help_text": "❓ *Ayuda*\n\nUsa los botones.",
        "matches_found": "🔍 *{count} partido(s)* :",
        "page": "📄 Página",
        "prev": "⬅️ Anterior",
        "next": "Siguiente ➡️",
        "match_count": "🔮 *{count} partidos:*",
    },
    "pt": {
        "welcome": "👋 *Bem-vindo ao KING NI Predict Bot !*",
        "choose_lang": "🌐 *Escolhe o teu idioma :*",
        "lang_set": "✅ Idioma: *Português*.",
        "menu_pred_today": "🔮 Prognósticos de hoje",
        "menu_week": "📅 Prognósticos da semana",
        "menu_search": "⚽ Buscar equipa",
        "menu_stats": "📊 Estatísticas",
        "menu_follow": "🔔 Seguir uma equipa",
        "menu_trends": "📊 Minhas tendências",
        "menu_lang": "🌐 Idioma",
        "menu_help": "❓ Ajuda",
        "menu_reset": "🔄 Reiniciar",
        "loading": "⏳ *A carregar...*",
        "back": "🔙 Voltar",
        "choose_match": "⚽ *Escolhe um jogo :*",
        "choose_market": "📊 *Escolhe um mercado :*",
        "no_match_today": "⚠️ Sem jogos hoje.",
        "no_match_week": "⚠️ Sem jogos em 7 dias.",
        "m_1x2": "🔮 1X2 + Cotações",
        "m_ou": "📈 Mais/Menos",
        "m_score": "⚽ Resultado previsto",
        "m_advice": "💡 Conselho API",
        "m_compare": "📊 Comparação",
        "m_all": "📚 Todos os mercados",
        "no_market": "❌ Sem mercado.",
        "search_prompt": "⚽ *Busca*\n\nEnvia um nome.",
        "follow_prompt": "🔔 Envia `seguir Arsenal`.",
        "following": "✅ Segues *{team}*.",
        "following_list": "📋 *Equipas seguidas*",
        "stats_title": "📊 *Estatísticas*",
        "no_data": "📊 Sem dados.",
        "help_text": "❓ *Ajuda*\n\nUsa os botões.",
        "matches_found": "🔍 *{count} jogo(s)* :",
        "page": "📄 Página",
        "prev": "⬅️ Anterior",
        "next": "Seguinte ➡️",
        "match_count": "🔮 *{count} jogos:*",
    },
    "ar": {
        "welcome": "👋 *مرحبا بك في KING NI Predict Bot !*",
        "choose_lang": "🌐 *اختر لغتك :*",
        "lang_set": "✅ اللغة: *العربية*.",
        "menu_pred_today": "🔮 توقعات اليوم",
        "menu_week": "📅 توقعات الأسبوع",
        "menu_search": "⚽ البحث عن فريق",
        "menu_stats": "📊 الإحصائيات",
        "menu_follow": "🔔 متابعة فريق",
        "menu_trends": "📊 اتجاهاتي",
        "menu_lang": "🌐 اللغة",
        "menu_help": "❓ مساعدة",
        "menu_reset": "🔄 إعادة تعيين",
        "loading": "⏳ *جاري التحميل...*",
        "back": "🔙 رجوع",
        "choose_match": "⚽ *اختر مباراة :*",
        "choose_market": "📊 *اختر سوقاً :*",
        "no_match_today": "⚠️ لا مباريات اليوم.",
        "no_match_week": "⚠️ لا مباريات في 7 أيام.",
        "m_1x2": "🔮 1X2",
        "m_ou": "📈 أكثر/أقل",
        "m_score": "⚽ النتيجة المتوقعة",
        "m_advice": "💡 نصيحة API",
        "m_compare": "📊 مقارنة",
        "m_all": "📚 كل الأسواق",
        "no_market": "❌ لا سوق متاح.",
        "search_prompt": "⚽ *بحث*\n\nأرسل اسماً.",
        "follow_prompt": "🔔 أرسل `suivre Arsenal`.",
        "following": "✅ تتابع *{team}*.",
        "following_list": "📋 *الفرق المتابعة*",
        "stats_title": "📊 *الإحصائيات*",
        "no_data": "📊 لا بيانات.",
        "help_text": "❓ *مساعدة*\n\nاستخدم الأزرار.",
        "matches_found": "🔍 *{count} مباراة* :",
        "page": "📄 صفحة",
        "prev": "⬅️ السابق",
        "next": "التالي ➡️",
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
        v = float(value)
    except:
        v = 0
    filled = int((v / total) * length)
    return "█" * filled + "░" * (length - filled)

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
        return f"{t(lang, 'stats_title')}\n\nPronostics : {total}\nJustes : {correct or 0}\nTaux : {rate:.1f}%"
    return t(lang, "no_data")

# ------------------------------------------------------------
# 5. API-FOOTBALL
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
        if not is_match_upcoming(f):
            continue
        status = f.get("fixture", {}).get("status", {}).get("short", "")
        if status in ("FT", "AET", "PEN"):
            continue
        matches.append(f)
    matches.sort(key=lambda x: x.get("fixture", {}).get("date", ""))
    return matches

def get_matches_week():
    all_matches = []
    for i in range(8):
        date_str = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        for f in get_fixtures_by_date(date_str):
            if not is_match_upcoming(f):
                continue
            status = f.get("fixture", {}).get("status", {}).get("short", "")
            if status in ("FT", "AET", "PEN"):
                continue
            all_matches.append(f)
    all_matches.sort(key=lambda x: x.get("fixture", {}).get("date", ""))
    return all_matches

def get_predictions(fixture_id):
    data = api_request("predictions", params={"fixture": fixture_id}, cache_ttl=1800)
    if not data or not data.get("response"):
        return None
    return data["response"][0]

# ---------- TOUS LES MARCHÉS ----------
def get_all_markets_text(fixture, lang="fr"):
    """Affiche TOUS les marchés disponibles pour un match."""
    try:
        fixture_id = fixture.get("fixture", {}).get("id")
        if not fixture_id:
            return t(lang, "no_market")
        
        preds = get_predictions(fixture_id)
        if not preds:
            return t(lang, "no_market")
        
        home = fixture.get("teams", {}).get("home", {}).get("name", "?")
        away = fixture.get("teams", {}).get("away", {}).get("name", "?")
        predictions = preds.get("predictions", {})
        percent = predictions.get("percent", {})
        comparison = preds.get("comparison", {})
        teams_stats = preds.get("teams", {})
        
        txt = f"⚽ *{home} vs {away}*\n\n"
        
        # ---- 1X2 ----
        ph = percent.get("home", "0%")
        pd = percent.get("draw", "0%")
        pa = percent.get("away", "0%")
        txt += f"🔮 *1X2*\n"
        txt += f"🏠 {home} : {ph} {progress_bar(ph.replace('%',''))}\n"
        txt += f"🤝 Nul : {pd} {progress_bar(pd.replace('%',''))}\n"
        txt += f"✈️ {away} : {pa} {progress_bar(pa.replace('%',''))}\n\n"
        
        # ---- WINNER ----
        winner = predictions.get("winner", {})
        if winner.get("name"):
            txt += f"🏆 *Vainqueur prévu* : {winner['name']}"
            if winner.get("comment"):
                txt += f" _{winner['comment']}_"
            txt += "\n\n"
        
        # ---- WIN OR DRAW ----
        wod = predictions.get("win_or_draw")
        if wod is not None:
            txt += f"🎯 *Win or Draw* : {'✅ Oui' if wod else '❌ Non'}\n\n"
        
        # ---- UNDER / OVER ----
        uo = predictions.get("under_over")
        if uo and uo != "N/A":
            txt += f"📈 *Under/Over* : {uo}\n\n"
        
        # ---- GOALS ----
        goals = predictions.get("goals", {})
        if goals:
            txt += f"⚽ *Score prévu* : {home} {goals.get('home','?')} - {goals.get('away','?')} {away}\n\n"
        
        # ---- ADVICE ----
        advice = predictions.get("advice")
        if advice and advice != "No predictions available":
            txt += f"💡 *Conseil* : {advice}\n\n"
        
        # ---- COMPARAISON ----
        if comparison:
            txt += f"📊 *Comparaison*\n"
            for key, label in [("form", "Forme"), ("att", "Attaque"), ("def", "Défense"),
                               ("poisson_distribution", "Poisson"), ("h2h", "H2H"),
                               ("goals", "Buts"), ("total", "Total")]:
                data = comparison.get(key, {})
                h = data.get("home", "?")
                a = data.get("away", "?")
                txt += f"`{label:<10} 🏠 {h:<6} ✈️ {a}`\n"
            txt += "\n"
        
        # ---- FORME DES ÉQUIPES ----
        for team_key in ["home", "away"]:
            ts = teams_stats.get(team_key, {})
            form = ts.get("forme", "")
            if form:
                emoji = ts.get("name", "?")
                txt += f"📈 *{emoji}* : {form}\n"
        
        return txt
    except Exception as e:
        return f"❌ Erreur : {str(e)[:100]}"

def get_market_text(fixture, market_type, lang="fr"):
    """Affiche un marché spécifique."""
    try:
        fixture_id = fixture.get("fixture", {}).get("id")
        if not fixture_id:
            return t(lang, "no_market")
        preds = get_predictions(fixture_id)
        if not preds:
            return t(lang, "no_market")
        
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
            if ph_f > pa_f and ph_f > pd_f:
                pred = f"🏠 {home}"
            elif pa_f > ph_f and pa_f > pd_f:
                pred = f"✈️ {away}"
            else:
                pred = "🤝 Nul"
            txt = f"🔮 *1X2*\n\n"
            txt += f"🏠 {home} : {ph_f:.1f}% {progress_bar(ph_f)}\n"
            txt += f"🤝 Nul : {pd_f:.1f}% {progress_bar(pd_f)}\n"
            txt += f"✈️ {away} : {pa_f:.1f}% {progress_bar(pa_f)}\n\n"
            txt += f"✅ *{pred}*"
            return txt, {"prob_home": ph_f, "prob_draw": pd_f, "prob_away": pa_f, "prediction": pred}
        
        elif market_type == "ou":
            uo = predictions.get("under_over", "N/A")
            goals = predictions.get("goals", {})
            txt = f"📈 *Over/Under*\n\n"
            txt += f"🎯 Prédiction : *{uo}*\n\n"
            txt += f"⚽ Buts prévus :\n"
            txt += f"🏠 {home} : {goals.get('home','?')}\n"
            txt += f"✈️ {away} : {goals.get('away','?')}\n"
            return txt, {"prediction": uo}
        
        elif market_type == "score":
            goals = predictions.get("goals", {})
            gh = goals.get("home", "?")
            ga = goals.get("away", "?")
            txt = f"⚽ *Score exact prévu*\n\n"
            txt += f"🎯 *{home} {gh} - {ga} {away}*\n\n"
            winner = predictions.get("winner", {}).get("name", "?")
            txt += f"🏆 Vainqueur : {winner}"
            return txt, {"prediction": f"{gh}-{ga}"}
        
        elif market_type == "advice":
            advice = predictions.get("advice", "N/A")
            winner = predictions.get("winner", {})
            txt = f"💡 *Conseil API-Football*\n\n"
            txt += f"📌 {advice}\n\n"
            if winner.get("name"):
                txt += f"🏆 Favori : *{winner['name']}*\n"
                if winner.get("comment"):
                    txt += f"_{winner['comment']}_"
            return txt, {"prediction": advice}
        
        elif market_type == "compare":
            txt = f"📊 *Comparaison des stats*\n\n"
            for key, label in [("form", "Forme"), ("att", "Attaque"), ("def", "Défense"),
                               ("poisson_distribution", "Poisson"), ("h2h", "H2H"),
                               ("goals", "Buts"), ("total", "Total")]:
                data = comparison.get(key, {})
                h = data.get("home", "?")
                a = data.get("away", "?")
                txt += f"`{label:<12} 🏠 {h:<6} ✈️ {a}`\n"
            return txt, {"prediction": "Comparaison"}
        
        return t(lang, "no_market"), None
    except Exception as e:
        return f"❌ Erreur : {str(e)[:100]}", None

# ------------------------------------------------------------
# 6. MENUS
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
# 7. BOT TELEGRAM
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
            
            # === TOUS LES MARCHÉS ===
            if market_type == "all":
                txt = get_all_markets_text(fixture, lang)
                bot.send_message(chat_id, header + txt, parse_mode="Markdown",
                                 reply_markup=menu_match_actions(mid, lang))
                return
            
            # === MARCHÉS SPÉCIFIQUES ===
            txt, data = get_market_text(fixture, market_type, lang)
            if txt and data and market_type == "h2h":
                save_prediction(home, away, "1X2",
                                data.get('prob_home', 0), data.get('prob_draw', 0), data.get('prob_away', 0),
                                data.get('prediction', ''), user_id)
            
            bot.send_message(chat_id, header + txt, parse_mode="Markdown",
                             reply_markup=menu_match_actions(mid, lang))
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

    if text == t(lang, "menu_search"):
        bot.reply_to(message, t(lang, "search_prompt"),
                     parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    if text == t(lang, "menu_stats"):
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
# 8. SERVEUR HTTP POUR RENDER
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
# 9. LANCEMENT
# ------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("✅ Base de données initialisée.")
    print("⚽ API-Football - Tous marchés activés")
    print("✅ Bot démarré.")
    bot.infinity_polling()