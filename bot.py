import os
import requests
import telebot
import sqlite3
import schedule
import time
import threading
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ------------------------------------------------------------
# 1. CONFIGURATION
# ------------------------------------------------------------
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "d2c5556ba64eb508457dcd097ecd6664")
ODDS_URL = "https://api.the-odds-api.com/v4/"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# ------------------------------------------------------------
# 2. CHAMPIONNATS (récupération dynamique depuis The Odds API)
# ------------------------------------------------------------
_SPORTS_CACHE = None
_SPORTS_CACHE_TIME = None

SPORTS_FALLBACK = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": "soccer_epl",
    "🇫🇷 Ligue 1": "soccer_france_ligue_one",
    "🇩🇪 Bundesliga": "soccer_germany_bundesliga",
    "🇪🇸 La Liga": "soccer_spain_la_liga",
    "🇮🇹 Serie A": "soccer_italy_serie_a",
    "🇺🇸 MLS": "soccer_usa_mls",
    "🏆 Champions League": "soccer_uefa_champs_league",
}

def get_all_sports(force_refresh=False):
    global _SPORTS_CACHE, _SPORTS_CACHE_TIME
    
    if not force_refresh and _SPORTS_CACHE and _SPORTS_CACHE_TIME:
        if datetime.now() - _SPORTS_CACHE_TIME < timedelta(hours=6):
            return _SPORTS_CACHE
    
    try:
        url = f"{ODDS_URL}sports/"
        params = {"apiKey": ODDS_API_KEY}
        r = requests.get(url, params=params, timeout=15)
        
        if r.status_code == 200:
            all_sports = r.json()
            soccer_leagues = {}
            
            for sport in all_sports:
                if sport.get("group") == "Soccer" and sport.get("active"):
                    key = sport["key"]
                    title = sport["title"]
                    display_name = f"⚽ {title}"
                    soccer_leagues[display_name] = key
            
            if soccer_leagues:
                print(f"✅ {len(soccer_leagues)} championnats récupérés depuis The Odds API")
                _SPORTS_CACHE = soccer_leagues
                _SPORTS_CACHE_TIME = datetime.now()
                return soccer_leagues
    except Exception as e:
        print(f"⚠️ Erreur récupération championnats: {e}")
    
    return SPORTS_FALLBACK

def get_sports():
    global _SPORTS_CACHE
    if _SPORTS_CACHE is None:
        _SPORTS_CACHE = get_all_sports()
    return _SPORTS_CACHE

# ------------------------------------------------------------
# 3. UTILITAIRES (dates et heures)
# ------------------------------------------------------------
def format_date(iso_date):
    """Convertit 2026-10-10T15:30:00Z en 10/10/2026."""
    if not iso_date:
        return "?"
    try:
        return datetime.strptime(iso_date[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        return iso_date[:10] if len(iso_date) >= 10 else "?"

def format_datetime(iso_date):
    """Convertit 2026-10-10T15:30:00Z en 10/10/2026 à 15h30."""
    if not iso_date:
        return "?"
    try:
        dt = datetime.strptime(iso_date[:19], "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%d/%m/%Y à %Hh%M")
    except:
        return format_date(iso_date)

def generate_progress_bar(value, total=100, length=10):
    filled = int((value / total) * length)
    return "█" * filled + "░" * (length - filled)

# ------------------------------------------------------------
# 4. TRADUCTIONS
# ------------------------------------------------------------
LANGUAGES = {
    "fr": {
        "welcome": "👋 *Bienvenue sur KING NI Predict Bot !*\n\nChoisis une option ci-dessous :",
        "menu_pred_today": "🔮 Pronostics du jour",
        "menu_by_league": "🏆 Par championnat",
        "menu_week": "📅 Pronostics de la semaine",
        "menu_search": "⚽ Rechercher une équipe",
        "menu_stats": "📊 Statistiques",
        "menu_standings": "🥇 Classements",
        "menu_follow": "🔔 Suivre une équipe",
        "menu_backtest": "📈 Backtesting",
        "menu_trends": "📊 Mes tendances",
        "menu_help": "❓ Aide",
        "menu_reset": "🔄 Réinitialiser",
        "no_matches": "⚠️ Aucun match trouvé.",
        "loading": "⏳ *Récupération...*",
        "back": "🔙 Retour",
        "choose_league": "🏆 *Choisis un championnat :*",
        "choose_match": "⚽ *Choisis un match :*",
    },
    "en": {
        "welcome": "👋 *Welcome to KING NI Predict Bot !*\n\nChoose an option below :",
        "menu_pred_today": "🔮 Today's predictions",
        "menu_by_league": "🏆 By league",
        "menu_week": "📅 Week's predictions",
        "menu_search": "⚽ Search team",
        "menu_stats": "📊 Statistics",
        "menu_standings": "🥇 Standings",
        "menu_follow": "🔔 Follow a team",
        "menu_backtest": "📈 Backtesting",
        "menu_trends": "📊 My trends",
        "menu_help": "❓ Help",
        "menu_reset": "🔄 Reset",
        "no_matches": "⚠️ No matches found.",
        "loading": "⏳ *Loading...*",
        "back": "🔙 Back",
        "choose_league": "🏆 *Choose a league :*",
        "choose_match": "⚽ *Choose a match :*",
    }
}

def detect_language(message):
    lang = "fr"
    if message.from_user.language_code and message.from_user.language_code.startswith("en"):
        lang = "en"
    return lang

# ------------------------------------------------------------
# 5. BASE DE DONNÉES
# ------------------------------------------------------------
def init_db():
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, home_team TEXT, away_team TEXT,
        market TEXT, prob_home REAL, prob_draw REAL, prob_away REAL,
        prediction TEXT, actual_result TEXT, user_id INTEGER, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, chat_id TEXT, username TEXT, lang TEXT, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS followed_teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, team_name TEXT, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sent_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, match_id TEXT, sent_at TEXT)''')
    conn.commit()
    conn.close()

# ------------------------------------------------------------
# 6. API THE ODDS
# ------------------------------------------------------------
def odds_request(endpoint, params=None, retries=3):
    if params is None:
        params = {}
    params["apiKey"] = ODDS_API_KEY
    url = f"{ODDS_URL}{endpoint}"
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"⚠️ {endpoint}: {e}")
        if attempt < retries - 1:
            time.sleep(2)
    return None

def get_matches_for_league(sport_key, markets="h2h"):
    data = odds_request(f"sports/{sport_key}/odds/",
                        {"regions": "eu,us", "markets": markets, "oddsFormat": "decimal"})
    if not data:
        return None, "⚠️ Impossible de contacter l'API."
    if len(data) == 0:
        return None, "ℹ️ Aucun match pour ce championnat."
    matches = []
    for ev in data:
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

def get_all_matches(days_ahead=None):
    all_matches = []
    today = datetime.now().date()
    sports = get_sports()
    
    for nom, cle in sports.items():
        matches, error = get_matches_for_league(cle, "h2h")
        if error or not matches:
            continue
        for m in matches:
            m["league_name"] = nom
            if days_ahead is None:
                all_matches.append(m)
            else:
                try:
                    md = datetime.strptime(m.get("commence_time","")[:10], "%Y-%m-%d").date()
                    if today <= md <= today + timedelta(days=days_ahead):
                        all_matches.append(m)
                except:
                    continue
    all_matches.sort(key=lambda x: x.get("commence_time", ""))
    return all_matches

# ------------------------------------------------------------
# 7. MARCHÉS ET PRONOSTICS
# ------------------------------------------------------------
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
                    t = ph + pd + pa
                    ph = (ph/t)*100; pd = (pd/t)*100; pa = (pa/t)*100
                    if ph > pa and ph > pd:
                        pred = f"🏠 {home}"
                    elif pa > ph and pa > pd:
                        pred = f"✈️ {away}"
                    else:
                        pred = "🤝 Nul"
                    return {"type": "1X2", "prob_home": ph, "prob_draw": pd, "prob_away": pa,
                            "prediction": pred,
                            "display": f"🏠 {home} : {ph:.1f}% {generate_progress_bar(ph)}\n🤝 Nul : {pd:.1f}% {generate_progress_bar(pd)}\n✈️ {away} : {pa:.1f}% {generate_progress_bar(pa)}",
                            "odds": {"home": oh, "draw": od, "away": oa}}
        return {"error": f"Marché '{market_type}' non disponible."}
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

def format_best_odds(match):
    best = get_best_odds(match)
    texte = "🏆 *Meilleures cotes*\n\n"
    texte += f"🏠 {match['home_team']} : *{best['home'][0]}* ({best['home'][1]})\n"
    texte += f"🤝 Nul : *{best['draw'][0]}* ({best['draw'][1]})\n"
    texte += f"✈️ {match['away_team']} : *{best['away'][0]}* ({best['away'][1]})\n"
    return texte

def analyze_value(match):
    pred = get_market_predictions(match, "h2h")
    if "error" in pred:
        return "❌ Analyse non disponible"
    best = get_best_odds(match)
    texte = "💎 *Analyse de valeur*\n\n"
    implied_prob = 100 / best['home'][0] if best['home'][0] > 0 else 0
    valeur = pred['prob_home'] - implied_prob
    emoji = "🟢" if valeur > 3 else ("🟡" if valeur > -3 else "🔴")
    texte += f"{emoji} 🏠 {match['home_team']}\n   Proba : {pred['prob_home']:.1f}% | Cote : {best['home'][0]} | Valeur : {valeur:+.1f}\n"
    implied_prob = 100 / best['draw'][0] if best['draw'][0] > 0 else 0
    valeur = pred['prob_draw'] - implied_prob
    emoji = "🟢" if valeur > 3 else ("🟡" if valeur > -3 else "🔴")
    texte += f"{emoji} 🤝 Nul\n   Proba : {pred['prob_draw']:.1f}% | Cote : {best['draw'][0]} | Valeur : {valeur:+.1f}\n"
    implied_prob = 100 / best['away'][0] if best['away'][0] > 0 else 0
    valeur = pred['prob_away'] - implied_prob
    emoji = "🟢" if valeur > 3 else ("🟡" if valeur > -3 else "🔴")
    texte += f"{emoji} ✈️ {match['away_team']}\n   Proba : {pred['prob_away']:.1f}% | Cote : {best['away'][0]} | Valeur : {valeur:+.1f}\n"
    texte += "\n🟢 Valeur positive  🟡 Neutre  🔴 À éviter"
    return texte

# ------------------------------------------------------------
# 8. LOGO (TheSportsDB)
# ------------------------------------------------------------
_logo_cache = {}
def get_team_logo(team_name):
    if team_name in _logo_cache:
        return _logo_cache[team_name]
    try:
        url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={team_name.replace(' ', '%20')}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            if data.get("teams"):
                logo = data["teams"][0].get("strTeamBadge") or data["teams"][0].get("strTeamLogo")
                _logo_cache[team_name] = logo
                return logo
    except:
        pass
    _logo_cache[team_name] = None
    return None

# ------------------------------------------------------------
# 9. BASE UTILISATEURS
# ------------------------------------------------------------
def register_user(user_id, chat_id, username, lang="fr"):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO users (user_id, chat_id, username, lang, created_at) VALUES (?, ?, ?, ?, ?)',
                (user_id, chat_id, username, lang, datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_user_lang(user_id):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('SELECT lang FROM users WHERE user_id = ?', (user_id,))
    row = cur.fetchone(); conn.close()
    return row[0] if row else "fr"

def add_followed_team(user_id, team_name):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO followed_teams (user_id, team_name, created_at) VALUES (?, ?, ?)',
                (user_id, team_name, datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_followed_teams(user_id):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('SELECT team_name FROM followed_teams WHERE user_id = ?', (user_id,))
    rows = cur.fetchall(); conn.close()
    return rows

def remove_followed_team(user_id, team_name):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM followed_teams WHERE user_id = ? AND team_name = ?', (user_id, team_name))
    conn.commit(); conn.close()

def save_prediction(home, away, market, ph, pd, pa, pred, user_id=None):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('''INSERT INTO predictions (date, home_team, away_team, market, prob_home, prob_draw, prob_away, prediction, user_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (datetime.now().strftime("%Y-%m-%d"), home, away, market, ph, pd, pa, pred, user_id, datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_stats(user_id=None):
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    if user_id:
        cur.execute('SELECT COUNT(*), SUM(CASE WHEN actual_result = prediction THEN 1 ELSE 0 END) FROM predictions WHERE user_id = ? AND actual_result IS NOT NULL', (user_id,))
    else:
        cur.execute('SELECT COUNT(*), SUM(CASE WHEN actual_result = prediction THEN 1 ELSE 0 END) FROM predictions WHERE actual_result IS NOT NULL')
    total, correct = cur.fetchone(); conn.close()
    if total and total > 0:
        return f"📊 *Statistiques*\n\nPronostics : {total}\nJustes : {correct or 0}\nTaux : {((correct or 0) / total * 100):.1f}%"
    return "📊 Aucune donnée disponible."

# ------------------------------------------------------------
# 10. NOTIFICATIONS
# ------------------------------------------------------------
def send_notifications():
    conn = sqlite3.connect('predictions.db')
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT user_id FROM followed_teams')
    users = cur.fetchall()
    conn.close()
    for (user_id,) in users:
        teams = get_followed_teams(user_id)
        matches = get_all_matches(days_ahead=7)
        for match in matches:
            mid = str(match.get('id', ''))
            home = match['home_team'].lower()
            away = match['away_team'].lower()
            for (team_name,) in teams:
                t = team_name.lower()
                if t in home or t in away:
                    conn = sqlite3.connect('predictions.db')
                    cur = conn.cursor()
                    cur.execute('SELECT COUNT(*) FROM sent_notifications WHERE user_id = ? AND match_id = ?', (user_id, mid))
                    already = cur.fetchone()[0]
                    conn.close()
                    if already:
                        continue
                    pred = get_market_predictions(match, "h2h")
                    if "error" in pred:
                        continue
                    dt = format_datetime(match.get('commence_time', ''))
                    league = match.get('league_name', '')
                    msg = (f"🔔 *Match de {team_name}*\n"
                           f"🏆 {league}\n"
                           f"📅 {dt}\n\n"
                           f"⚽ *{match['home_team']} vs {match['away_team']}*\n\n"
                           f"🏠 {match['home_team']} : {pred['prob_home']:.1f}%\n"
                           f"🤝 Nul : {pred['prob_draw']:.1f}%\n"
                           f"✈️ {match['away_team']} : {pred['prob_away']:.1f}%\n\n"
                           f"✅ *Pronostic : {pred['prediction']}*")
                    try:
                        bot.send_message(user_id, msg, parse_mode="Markdown")
                        conn = sqlite3.connect('predictions.db')
                        cur = conn.cursor()
                        cur.execute('INSERT INTO sent_notifications (user_id, match_id, sent_at) VALUES (?, ?, ?)',
                                    (user_id, mid, datetime.now().isoformat()))
                        conn.commit(); conn.close()
                    except Exception as e:
                        print(f"Erreur notif: {e}")

def run_scheduler():
    schedule.every().hour.do(send_notifications)
    while True:
        schedule.run_pending()
        time.sleep(60)

# ------------------------------------------------------------
# 11. MENUS
# ------------------------------------------------------------
def menu_options(lang="fr"):
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton(texts["menu_pred_today"]),
        KeyboardButton(texts["menu_week"]),
        KeyboardButton(texts["menu_by_league"]),
        KeyboardButton(texts["menu_search"]),
        KeyboardButton(texts["menu_stats"]),
        KeyboardButton(texts["menu_follow"]),
        KeyboardButton(texts["menu_backtest"]),
        KeyboardButton(texts["menu_trends"]),
        KeyboardButton(texts["menu_help"]),
        KeyboardButton(texts["menu_reset"])
    )
    return markup

def menu_ligues_inline(lang="fr", page=0):
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
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
        nav.append(InlineKeyboardButton("⬅️ Préc.", callback_data=f"lgpage_{page-1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton("Suiv. ➡️", callback_data=f"lgpage_{page+1}"))
    if nav:
        markup.add(*nav)
    markup.add(InlineKeyboardButton(f"📊 {len(sports)} ligues au total", callback_data="noop"))
    markup.add(InlineKeyboardButton(texts["back"], callback_data="menu_back"))
    return markup

def menu_matchs_list(matches, prefix="match_day", lang="fr", page=0):
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
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
        nav.append(InlineKeyboardButton("⬅️ Précédent", callback_data=f"page_{prefix}_{page-1}"))
    if end < len(matches):
        nav.append(InlineKeyboardButton("Suivant ➡️", callback_data=f"page_{prefix}_{page+1}"))
    if nav:
        markup.add(*nav)
    markup.add(InlineKeyboardButton(texts["back"], callback_data="menu_back"))
    return markup

def menu_match_actions(match_id, lang="fr"):
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔮 1X2", callback_data=f"market_{match_id}_h2h"))
    markup.add(InlineKeyboardButton("🏆 Meilleures cotes", callback_data=f"bestodds_{match_id}"))
    markup.add(InlineKeyboardButton("💎 Analyse de valeur", callback_data=f"value_{match_id}"))
    markup.add(InlineKeyboardButton("🖼️ Voir les logos", callback_data=f"logos_{match_id}"))
    markup.add(InlineKeyboardButton(texts["back"], callback_data="back_to_matches"))
    return markup

def menu_matchs_inline_list(sport_key, matches, lang="fr"):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, m in enumerate(matches[:10]):
        dt = format_datetime(m.get("commence_time", ""))
        markup.add(InlineKeyboardButton(f"📅 {dt}\n⚽ {m['home_team']} vs {m['away_team']}",
                                         callback_data=f"match_league_{sport_key}_{i}"))
    markup.add(InlineKeyboardButton("🔙 Retour", callback_data="choose_league"))
    return markup

# ------------------------------------------------------------
# 12. BOT TELEGRAM
# ------------------------------------------------------------
bot = telebot.TeleBot(TELEGRAM_TOKEN)
bot.match_cache = {}
bot.current_matches_list = []
bot.current_match_data = {}

def send_welcome(message):
    lang = detect_language(message)
    register_user(message.from_user.id, message.chat.id, message.from_user.username, lang)
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
    bot.reply_to(message, texts["welcome"], parse_mode="Markdown", reply_markup=menu_options(lang))

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.match_cache = {}
    bot.current_matches_list = []
    bot.current_match_data = {}
    send_welcome(message)

@bot.message_handler(commands=['refresh'])
def handle_refresh(message):
    global _SPORTS_CACHE, _SPORTS_CACHE_TIME
    _SPORTS_CACHE = None
    _SPORTS_CACHE_TIME = None
    new_sports = get_sports()
    bot.reply_to(message, f"✅ Liste des championnats mise à jour : {len(new_sports)} ligues disponibles.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        lang = get_user_lang(user_id)
        texts = LANGUAGES.get(lang, LANGUAGES["fr"])

        if call.data == "noop":
            return

        if call.data == "menu_back":
            bot.send_message(chat_id, texts["welcome"], parse_mode="Markdown", reply_markup=menu_options(lang))
            return

        if call.data == "choose_league":
            bot.send_message(chat_id, texts["choose_league"], parse_mode="Markdown", reply_markup=menu_ligues_inline(lang, 0))
            return

        if call.data.startswith("lgpage_"):
            page = int(call.data.replace("lgpage_", ""))
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=menu_ligues_inline(lang, page))
            return

        if call.data == "back_to_matches":
            if bot.current_matches_list:
                bot.send_message(chat_id, f"🔮 *{len(bot.current_matches_list)} matchs*",
                                 parse_mode="Markdown",
                                 reply_markup=menu_matchs_list(bot.current_matches_list, "match_day", lang))
            else:
                bot.send_message(chat_id, texts["back"], parse_mode="Markdown", reply_markup=menu_ligues_inline(lang))
            return

        if call.data.startswith("league_"):
            sport_key = call.data.replace("league_", "")
            loading = bot.send_message(chat_id, texts["loading"], parse_mode="Markdown")
            matches, error = get_matches_for_league(sport_key)
            if error or not matches:
                bot.edit_message_text(error or texts["no_matches"], chat_id, loading.message_id)
                return
            sports = get_sports()
            nom_ligue = next((k for k, v in sports.items() if v == sport_key), sport_key)
            for i, m in enumerate(matches[:10]):
                m["league_name"] = nom_ligue
                bot.match_cache[f"match_league_{sport_key}_{i}"] = m
            bot.delete_message(chat_id, loading.message_id)
            bot.send_message(chat_id, texts["choose_match"], parse_mode="Markdown",
                             reply_markup=menu_matchs_inline_list(sport_key, matches, lang))
            return

        if call.data.startswith("page_"):
            parts = call.data.replace("page_", "").rsplit("_", 1)
            prefix = parts[0]
            page = int(parts[1])
            if bot.current_matches_list:
                bot.send_message(chat_id, f"📄 Page {page+1}",
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
            league = match.get('league_name', 'Championnat inconnu')
            texte = (f"🏆 *{league}*\n"
                     f"📅 {dt}\n\n"
                     f"⚽ *{match['home_team']} vs {match['away_team']}*")
            bot.send_message(chat_id, texte, parse_mode="Markdown",
                             reply_markup=menu_match_actions(call.data, lang))
            return

        if call.data.startswith("logos_"):
            mid = call.data.replace("logos_", "")
            match = bot.current_match_data.get(mid) or bot.match_cache.get(mid)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            loading = bot.send_message(chat_id, "⏳ *Récupération des logos...*", parse_mode="Markdown")
            hl = get_team_logo(match['home_team'])
            al = get_team_logo(match['away_team'])
            bot.delete_message(chat_id, loading.message_id)
            if hl:
                try:
                    bot.send_photo(chat_id, hl, caption=f"🏠 *{match['home_team']}*", parse_mode="Markdown")
                except: pass
            if al:
                try:
                    bot.send_photo(chat_id, al, caption=f"✈️ *{match['away_team']}*", parse_mode="Markdown")
                except: pass
            if not hl and not al:
                bot.send_message(chat_id, "❌ Logos non disponibles.")
            return

        if call.data.startswith("bestodds_"):
            mid = call.data.replace("bestodds_", "")
            match = bot.current_match_data.get(mid) or bot.match_cache.get(mid)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            texte = format_best_odds(match)
            bot.send_message(chat_id, texte, parse_mode="Markdown",
                             reply_markup=menu_match_actions(mid, lang))
            return

        if call.data.startswith("value_"):
            mid = call.data.replace("value_", "")
            match = bot.current_match_data.get(mid) or bot.match_cache.get(mid)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            texte = analyze_value(match)
            bot.send_message(chat_id, texte, parse_mode="Markdown",
                             reply_markup=menu_match_actions(mid, lang))
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
                bot.send_message(chat_id, f"❌ {pred['error']}")
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
            bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_options(lang))
            return

        if call.data == "unfollow_all":
            conn = sqlite3.connect('predictions.db')
            cur = conn.cursor()
            cur.execute('DELETE FROM followed_teams WHERE user_id = ?', (user_id,))
            conn.commit(); conn.close()
            bot.send_message(chat_id, "✅ Équipes suivies supprimées.")
            return

    except Exception as e:
        print(f"❌ Erreur callback: {e}")
        try:
            bot.send_message(call.message.chat.id, f"❌ Erreur : {str(e)[:100]}")
        except: pass

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = get_user_lang(user_id)
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])

    if text.startswith('/'):
        return

    if text == texts["menu_reset"]:
        bot.match_cache = {}
        bot.current_matches_list = []
        send_welcome(message)
        return

    if text == texts["menu_pred_today"]:
        loading = bot.reply_to(message, texts["loading"], parse_mode="Markdown")
        all_matches = get_all_matches(days_ahead=1)
        if not all_matches:
            bot.edit_message_text("⚠️ Aucun match aujourd'hui ou demain.", chat_id, loading.message_id)
            return
        bot.current_matches_list = all_matches[:50]
        for i, m in enumerate(bot.current_matches_list):
            bot.match_cache[f"match_day_{i}"] = m
        bot.delete_message(chat_id, loading.message_id)
        bot.send_message(chat_id, f"🔮 *Pronostics du jour*\n\n{len(bot.current_matches_list)} matchs :",
                         parse_mode="Markdown",
                         reply_markup=menu_matchs_list(bot.current_matches_list, "match_day", lang, 0))
        return

    if text == texts["menu_week"]:
        loading = bot.reply_to(message, texts["loading"], parse_mode="Markdown")
        all_matches = get_all_matches(days_ahead=7)
        if not all_matches:
            bot.edit_message_text("⚠️ Aucun match dans les 7 prochains jours.", chat_id, loading.message_id)
            return
        bot.current_matches_list = all_matches[:50]
        for i, m in enumerate(bot.current_matches_list):
            bot.match_cache[f"match_day_{i}"] = m
        bot.delete_message(chat_id, loading.message_id)
        bot.send_message(chat_id, f"📅 *Pronostics de la semaine*\n\n{len(bot.current_matches_list)} matchs :",
                         parse_mode="Markdown",
                         reply_markup=menu_matchs_list(bot.current_matches_list, "match_day", lang, 0))
        return

    if text == texts["menu_by_league"]:
        sports = get_sports()
        bot.reply_to(message, f"🏆 *{len(sports)} championnats disponibles*\n\n{texts['choose_league']}",
                     parse_mode="Markdown", reply_markup=menu_ligues_inline(lang, 0))
        return

    if text == texts["menu_search"]:
        bot.reply_to(message, "⚽ *Recherche d'équipe*\n\nEnvoie le nom d'une équipe (ex: `Arsenal`).",
                     parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    if text == texts["menu_stats"]:
        bot.reply_to(message, get_stats(user_id), parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    if text == texts["menu_backtest"]:
        bot.reply_to(message, get_stats(user_id), parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    if text == texts["menu_trends"]:
        followed = get_followed_teams(user_id)
        if not followed:
            bot.reply_to(message, "🔔 Tu ne suis aucune équipe.", parse_mode="Markdown", reply_markup=menu_options(lang))
            return
        texte = "📋 *Équipes suivies*\n\n" + "\n".join([f"- {t[0]}" for t in followed])
        bot.reply_to(message, texte, parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    if text == texts["menu_follow"]:
        followed = get_followed_teams(user_id)
        if followed:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🗑️ Tout supprimer", callback_data="unfollow_all"))
            bot.reply_to(message, "Tu suis : " + ", ".join([t[0] for t in followed]), reply_markup=markup)
        else:
            bot.reply_to(message, "🔔 Envoie `suivre Arsenal` pour suivre une équipe.", parse_mode="Markdown")
        return

    if text == texts["menu_help"]:
        bot.reply_to(message, "❓ *Aide*\n\nUtilise les boutons du menu.", parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    if text.lower().startswith("suivre ") or text.lower().startswith("follow "):
        team = text.split(" ", 1)[1].strip()
        add_followed_team(user_id, team)
        bot.reply_to(message, f"✅ Tu suis *{team}*.\nTu recevras une notification à chaque match.",
                     parse_mode="Markdown", reply_markup=menu_options(lang))
        return

    # Recherche libre
    loading = bot.reply_to(message, f"⏳ *Recherche de {text}...*", parse_mode="Markdown")
    matches = get_all_matches(days_ahead=None)
    found = [m for m in matches if text.lower() in m['home_team'].lower() or text.lower() in m['away_team'].lower()]
    if not found:
        bot.edit_message_text(f"❌ Aucun match pour *{text}*.", chat_id, loading.message_id, parse_mode="Markdown")
        return
    texte = f"🔍 *{len(found)} match(s) trouvé(s)* :\n\n"
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
# 13. SERVEUR HTTP POUR RENDER
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
# 14. LANCEMENT
# ------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("✅ Base de données initialisée.")
    sports = get_sports()
    print(f"✅ {len(sports)} championnats chargés.")
    threading.Thread(target=run_scheduler, daemon=True).start()
    print("⏰ Notifications programmées (toutes les heures).")
    print("✅ Bot démarré.")
    bot.infinity_polling()