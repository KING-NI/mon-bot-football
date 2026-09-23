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
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")  # Ta clé RapidAPI
RAPIDAPI_HOST = "api-football-v1.p.rapidapi.com"
API_BASE_URL = f"https://{RAPIDAPI_HOST}/v3"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# ------------------------------------------------------------
# 2. LIGUES (API-Football)
# ------------------------------------------------------------
# Format : { "Nom affiché": league_id }
LEAGUES = {
    "Premier League": 39,
    "Ligue 1": 61,
    "Bundesliga": 78,
    "La Liga": 140,
    "Serie A": 135,
    "Champions League": 2,
    "Europa League": 3,
    "MLS": 253,
    "Brasil Serie A": 71,
}

# ------------------------------------------------------------
# 3. MULTILINGUE
# ------------------------------------------------------------
LANGUAGES = {
    "fr": {
        "welcome": "👋 *Bienvenue sur KING NI Predict Bot !*\n\nChoisis une option ci-dessous :",
        "menu_pred_today": "🔮 Pronostics du jour",
        "menu_by_league": "🏆 Par championnat",
        "menu_coming": "📅 Matchs à venir",
        "menu_search": "⚽ Rechercher une équipe",
        "menu_stats": "📊 Statistiques",
        "menu_live": "📡 En direct",
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
        "menu_coming": "📅 Upcoming matches",
        "menu_search": "⚽ Search team",
        "menu_stats": "📊 Statistics",
        "menu_live": "📡 Live",
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
    },
    "es": {
        "welcome": "👋 *¡Bienvenido a KING NI Predict Bot !*\n\nElige una opción a continuación :",
        "menu_pred_today": "🔮 Pronósticos de hoy",
        "menu_by_league": "🏆 Por liga",
        "menu_coming": "📅 Próximos partidos",
        "menu_search": "⚽ Buscar equipo",
        "menu_stats": "📊 Estadísticas",
        "menu_live": "📡 En directo",
        "menu_follow": "🔔 Seguir un equipo",
        "menu_backtest": "📈 Backtesting",
        "menu_trends": "📊 Mis tendencias",
        "menu_help": "❓ Ayuda",
        "menu_reset": "🔄 Reiniciar",
        "no_matches": "⚠️ No se encontraron partidos.",
        "loading": "⏳ *Cargando...*",
        "back": "🔙 Volver",
        "choose_league": "🏆 *Elige una liga :*",
        "choose_match": "⚽ *Elige un partido :*",
    }
}

def detect_language(message):
    lang = "fr"
    if message.from_user.language_code:
        if message.from_user.language_code.startswith("en"):
            lang = "en"
        elif message.from_user.language_code.startswith("es"):
            lang = "es"
    return lang

# ------------------------------------------------------------
# 4. BASE DE DONNÉES
# ------------------------------------------------------------
def init_db():
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, home_team TEXT, away_team TEXT, market TEXT,
            prob_home REAL, prob_draw REAL, prob_away REAL,
            prediction TEXT, actual_result TEXT, user_id INTEGER, created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, chat_id TEXT, username TEXT, lang TEXT, created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS followed_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, team_name TEXT, created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ------------------------------------------------------------
# 5. FONCTIONS API-FOOTBALL
# ------------------------------------------------------------
# Système de cache pour économiser les requêtes (quota : 100/jour)
_cache = {}
_cache_ttl = {}

def api_request(endpoint, params=None, cache_ttl=300):
    """Requête avec cache pour économiser le quota (100 req/jour)."""
    cache_key = f"{endpoint}_{str(params)}"
    now = time.time()
    
    # Vérifier le cache
    if cache_key in _cache and cache_key in _cache_ttl:
        if now - _cache_ttl[cache_key] < cache_ttl:
            return _cache[cache_key]
    
    # Faire la requête
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }
    url = f"{API_BASE_URL}/{endpoint}"
    
    for attempt in range(2):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                _cache[cache_key] = data
                _cache_ttl[cache_key] = now
                return data
            print(f"⚠️ Tentative {attempt+1}: erreur {response.status_code}")
        except Exception as e:
            print(f"⚠️ Tentative {attempt+1}: {e}")
        if attempt == 0:
            time.sleep(2)
    return None

def get_matches_for_league(league_id, date_from=None, date_to=None):
    """Récupère les matchs d'une ligue."""
    if date_from is None:
        date_from = datetime.now().strftime("%Y-%m-%d")
    if date_to is None:
        date_to = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    params = {
        "league": league_id,
        "from": date_from,
        "to": date_to,
        "season": datetime.now().year,
    }
    data = api_request("fixtures", params=params, cache_ttl=600)
    
    if not data or "response" not in data:
        return None, "⚠️ Impossible de contacter l'API."
    
    matches = []
    for fixture in data["response"]:
        matches.append({
            "id": fixture["fixture"]["id"],
            "home_team": fixture["teams"]["home"]["name"],
            "away_team": fixture["teams"]["away"]["name"],
            "league_name": fixture["league"]["name"],
            "commence_time": fixture["fixture"]["date"],
        })
    
    if not matches:
        return None, "ℹ️ Aucun match pour ce championnat."
    return matches, None

def get_fixture_predictions(fixture_id):
    """Récupère les prédictions de l'API pour un match."""
    data = api_request("predictions", params={"fixture": fixture_id}, cache_ttl=1800)
    if not data or "response" not in data or not data["response"]:
        return None
    return data["response"][0]

def get_market_predictions(fixture_id, market_type="h2h"):
    """Calcule les probabilités pour un marché donné."""
    try:
        pred_data = get_fixture_predictions(fixture_id)
        if not pred_data:
            return {"error": "Prédiction non disponible."}
        
        predictions = pred_data.get("predictions", {})
        percent = predictions.get("percent", {})
        
        if market_type == "h2h":
            home_pct = percent.get("home", "0%").replace("%", "")
            draw_pct = percent.get("draw", "0%").replace("%", "")
            away_pct = percent.get("away", "0%").replace("%", "")
            
            prob_home = float(home_pct) if home_pct else 0
            prob_draw = float(draw_pct) if draw_pct else 0
            prob_away = float(away_pct) if away_pct else 0
            
            if prob_home > prob_away and prob_home > prob_draw:
                pred = f"🏠 Victoire domicile"
            elif prob_away > prob_home and prob_away > prob_draw:
                pred = f"✈️ Victoire extérieur"
            else:
                pred = "🤝 Nul"
            
            return {
                "type": "1X2",
                "prob_home": prob_home,
                "prob_draw": prob_draw,
                "prob_away": prob_away,
                "prediction": pred,
                "display": f"🏠 Domicile : {prob_home:.1f}%\n🤝 Nul : {prob_draw:.1f}%\n✈️ Extérieur : {prob_away:.1f}%"
            }
        else:
            return {"error": f"Marché '{market_type}' non disponible."}
    except Exception as e:
        return {"error": str(e)}

def generate_progress_bar(value, total=100, length=10):
    filled = int((value / total) * length)
    return "█" * filled + "░" * (length - filled)

def save_prediction(home, away, market, prob_h, prob_d, prob_a, pred, user_id=None):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO predictions (date, home_team, away_team, market, prob_home, prob_draw, prob_away, prediction, user_id, created_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (datetime.now().strftime("%Y-%m-%d"), home, away, market, prob_h, prob_d, prob_a, pred, user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_stats(user_id=None):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    if user_id:
        cursor.execute('SELECT COUNT(*), SUM(CASE WHEN actual_result = prediction THEN 1 ELSE 0 END) FROM predictions WHERE user_id = ? AND actual_result IS NOT NULL', (user_id,))
    else:
        cursor.execute('SELECT COUNT(*), SUM(CASE WHEN actual_result = prediction THEN 1 ELSE 0 END) FROM predictions WHERE actual_result IS NOT NULL')
    total, correct = cursor.fetchone()
    conn.close()
    if total and total > 0:
        return f"📊 *Statistiques*\n\nPronostics : {total}\nJustes : {correct or 0}\nTaux : {((correct or 0) / total * 100):.1f}%"
    return "📊 Aucune donnée disponible."

def calculate_backtest(user_id=None, days=30):
    return get_stats(user_id)

# ------------------------------------------------------------
# 6. UTILISATEURS ET SUIVI
# ------------------------------------------------------------
def register_user(user_id, chat_id, username, lang="fr"):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, chat_id, username, lang, created_at) VALUES (?, ?, ?, ?, ?)',
                   (user_id, chat_id, username, lang, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_lang(user_id):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('SELECT lang FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "fr"

def add_followed_team(user_id, team_name):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO followed_teams (user_id, team_name, created_at) VALUES (?, ?, ?)',
                   (user_id, team_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_followed_teams(user_id):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('SELECT team_name FROM followed_teams WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def remove_followed_team(user_id, team_name):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM followed_teams WHERE user_id = ? AND team_name = ?', (user_id, team_name))
    conn.commit()
    conn.close()

# ------------------------------------------------------------
# 7. RECHERCHE D'ÉQUIPE
# ------------------------------------------------------------
def search_team(team_name):
    resultats = []
    team_clean = team_name.strip().lower()
    if not team_clean:
        return "❌ Entre un nom d'équipe valide."
    
    for nom, league_id in LEAGUES.items():
        matches, error = get_matches_for_league(league_id)
        if error or not matches:
            continue
        for match in matches:
            if team_clean in match["home_team"].lower() or team_clean in match["away_team"].lower():
                pred = get_market_predictions(match["id"], "h2h")
                if "error" in pred:
                    continue
                date_str = match.get("commence_time", "")[:10] if match.get("commence_time") else "Date inconnue"
                resultats.append(f"📅 {date_str} | {match['league_name']}\n⚽ {match['home_team']} vs {match['away_team']}\n   🏠 {pred['prob_home']:.1f}% {generate_progress_bar(pred['prob_home'])}\n   🤝 Nul : {pred['prob_draw']:.1f}% {generate_progress_bar(pred['prob_draw'])}\n   ✈️ {pred['prob_away']:.1f}% {generate_progress_bar(pred['prob_away'])}\n   ✅ *{pred['prediction']}*\n")
    if not resultats:
        return f"❌ Aucun match pour *{team_name}*."
    return "\n\n".join(resultats)

# ------------------------------------------------------------
# 8. NOTIFICATIONS
# ------------------------------------------------------------
def send_notifications():
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT user_id FROM followed_teams')
    users = cursor.fetchall()
    conn.close()
    
    for (user_id,) in users:
        teams = get_followed_teams(user_id)
        for (team_name,) in teams:
            for nom, league_id in LEAGUES.items():
                matches, error = get_matches_for_league(league_id)
                if error or not matches:
                    continue
                for match in matches:
                    if team_name.lower() in match['home_team'].lower() or team_name.lower() in match['away_team'].lower():
                        pred = get_market_predictions(match["id"], "h2h")
                        if "error" not in pred:
                            msg = f"🔔 *Match de {team_name}*\n\n⚽ {match['home_team']} vs {match['away_team']}\n🏠 {pred['prob_home']:.1f}%\n🤝 {pred['prob_draw']:.1f}%\n✈️ {pred['prob_away']:.1f}%\n✅ *{pred['prediction']}*"
                            try:
                                bot.send_message(user_id, msg, parse_mode="Markdown")
                            except:
                                pass

def run_scheduler():
    schedule.every().day.at("08:00").do(send_notifications)
    while True:
        schedule.run_pending()
        time.sleep(60)

# ------------------------------------------------------------
# 9. MENUS
# ------------------------------------------------------------
def menu_options(lang="fr"):
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton(texts["menu_pred_today"]),
        KeyboardButton(texts["menu_by_league"]),
        KeyboardButton(texts["menu_coming"]),
        KeyboardButton(texts["menu_search"]),
        KeyboardButton(texts["menu_stats"]),
        KeyboardButton(texts["menu_live"]),
        KeyboardButton(texts["menu_follow"]),
        KeyboardButton(texts["menu_backtest"]),
        KeyboardButton(texts["menu_trends"]),
        KeyboardButton(texts["menu_help"]),
        KeyboardButton(texts["menu_reset"])
    )
    return markup

def menu_ligues_inline(lang="fr"):
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
    markup = InlineKeyboardMarkup(row_width=2)
    for nom, league_id in LEAGUES.items():
        markup.add(InlineKeyboardButton(nom, callback_data=f"league_{league_id}"))
    markup.add(InlineKeyboardButton(texts["back"], callback_data="menu_back"))
    return markup

def menu_matchs_inline(league_id, matches, lang="fr"):
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
    markup = InlineKeyboardMarkup(row_width=1)
    for i, m in enumerate(matches[:10]):
        markup.add(InlineKeyboardButton(f"⚽ {m['home_team']} vs {m['away_team']}", callback_data=f"match_{league_id}_{i}"))
    markup.add(InlineKeyboardButton(texts["back"], callback_data="choose_league"))
    return markup

def menu_matchs_list(matches, prefix="match_day", lang="fr"):
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
    markup = InlineKeyboardMarkup(row_width=1)
    for i, m in enumerate(matches[:20]):
        date = m.get("commence_time", "")[:10] if m.get("commence_time") else "?"
        markup.add(InlineKeyboardButton(f"📅 {date} | {m['home_team']} vs {m['away_team']}", callback_data=f"{prefix}_{i}"))
    markup.add(InlineKeyboardButton(texts["back"], callback_data="menu_back"))
    return markup

def menu_match_actions(fixture_id, lang="fr"):
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔮 1X2", callback_data=f"market_{fixture_id}_h2h"))
    markup.add(InlineKeyboardButton(texts["back"], callback_data="back_to_matches"))
    return markup

# ------------------------------------------------------------
# 10. BOT TELEGRAM
# ------------------------------------------------------------
bot = telebot.TeleBot(TELEGRAM_TOKEN)
bot.match_cache = {}
bot.day_matches = []
bot.current_match_data = {}

def send_welcome(message):
    lang = detect_language(message)
    register_user(message.from_user.id, message.chat.id, message.from_user.username, lang)
    texts = LANGUAGES.get(lang, LANGUAGES["fr"])
    bot.reply_to(message, texts["welcome"], parse_mode="Markdown", reply_markup=menu_options(lang))

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.match_cache = {}
    bot.day_matches = []
    bot.current_match_data = {}
    send_welcome(message)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        lang = get_user_lang(user_id)
        texts = LANGUAGES.get(lang, LANGUAGES["fr"])

        if call.data == "menu_back":
            bot.send_message(chat_id, texts["welcome"], parse_mode="Markdown", reply_markup=menu_options(lang))
        elif call.data == "choose_league":
            bot.send_message(chat_id, texts["choose_league"], parse_mode="Markdown", reply_markup=menu_ligues_inline(lang))
        elif call.data == "back_to_matches":
            if bot.day_matches:
                bot.send_message(chat_id, f"🔮 {len(bot.day_matches)} matchs :", parse_mode="Markdown", reply_markup=menu_matchs_list(bot.day_matches, "match_day", lang))
            else:
                bot.send_message(chat_id, texts["back"], parse_mode="Markdown", reply_markup=menu_ligues_inline(lang))
        elif call.data.startswith("league_"):
            league_id = call.data.replace("league_", "")
            loading = bot.send_message(chat_id, texts["loading"], parse_mode="Markdown")
            matches, error = get_matches_for_league(league_id)
            if error or not matches:
                bot.edit_message_text(error or texts["no_matches"], chat_id, loading.message_id)
                return
            for i, m in enumerate(matches[:10]):
                bot.match_cache[f"match_{league_id}_{i}"] = m
            bot.delete_message(chat_id, loading.message_id)
            bot.send_message(chat_id, texts["choose_match"], parse_mode="Markdown", reply_markup=menu_matchs_inline(league_id, matches, lang))
        elif call.data.startswith("match_"):
            match = bot.match_cache.get(call.data)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            bot.current_match_data[call.data] = match
            bot.send_message(chat_id, f"⚽ *{match['home_team']} vs {match['away_team']}*", parse_mode="Markdown", reply_markup=menu_match_actions(match['id'], lang))
        elif call.data.startswith("market_"):
            parts = call.data.replace("market_", "").split("_")
            market_type = parts[-1]
            fixture_id = "_".join(parts[:-1])
            match = bot.current_match_data.get(fixture_id) or bot.match_cache.get(fixture_id)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.")
                return
            pred = get_market_predictions(fixture_id, market_type)
            if "error" in pred:
                bot.send_message(chat_id, f"❌ {pred['error']}")
                return
            save_prediction(match['home_team'], match['away_team'], pred.get('type', market_type),
                            pred.get('prob_home', 0), pred.get('prob_draw', 0), pred.get('prob_away', 0),
                            pred['prediction'], user_id)
            texte = f"⚽ *{match['home_team']} vs {match['away_team']}*\n📊 *{pred.get('type', market_type)}*\n\n{pred['display']}\n\n✅ *{pred['prediction']}*"
            bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_options(lang))
        elif call.data == "unfollow_all":
            conn = sqlite3.connect('predictions.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM followed_teams WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            bot.send_message(chat_id, "✅ Toutes les équipes ont été retirées.")
    except Exception as e:
        print(f"❌ Erreur callback: {e}")

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
        bot.day_matches = []
        send_welcome(message)
    elif text == texts["menu_pred_today"]:
        loading = bot.reply_to(message, texts["loading"], parse_mode="Markdown")
        # Récupérer les matchs du jour pour toutes les ligues
        all_matches = []
        for nom, league_id in LEAGUES.items():
            matches, error = get_matches_for_league(league_id)
            if not error and matches:
                for m in matches:
                    m["league_name"] = nom
                    all_matches.append(m)
        if not all_matches:
            bot.edit_message_text(texts["no_matches"], chat_id, loading.message_id)
            return
        bot.day_matches = all_matches[:20]
        for i, m in enumerate(bot.day_matches):
            bot.match_cache[f"match_day_{i}"] = m
        bot.delete_message(chat_id, loading.message_id)
        bot.send_message(chat_id, f"🔮 *Pronostics du jour*\n\n{len(bot.day_matches)} matchs :", parse_mode="Markdown", reply_markup=menu_matchs_list(bot.day_matches, "match_day", lang))
    elif text == texts["menu_coming"]:
        loading = bot.reply_to(message, texts["loading"], parse_mode="Markdown")
        all_matches = []
        for nom, league_id in LEAGUES.items():
            matches, error = get_matches_for_league(league_id)
            if not error and matches:
                for m in matches:
                    m["league_name"] = nom
                    all_matches.append(m)
        if not all_matches:
            bot.edit_message_text(texts["no_matches"], chat_id, loading.message_id)
            return
        bot.day_matches = all_matches[:30]
        for i, m in enumerate(bot.day_matches):
            bot.match_cache[f"match_day_{i}"] = m
        bot.delete_message(chat_id, loading.message_id)
        bot.send_message(chat_id, f"📅 *Matchs à venir*\n\n{len(bot.day_matches)} matchs :", parse_mode="Markdown", reply_markup=menu_matchs_list(bot.day_matches, "match_day", lang))
    elif text == texts["menu_by_league"]:
        bot.reply_to(message, texts["choose_league"], parse_mode="Markdown", reply_markup=menu_ligues_inline(lang))
    elif text == texts["menu_search"]:
        bot.reply_to(message, "⚽ *Recherche d'équipe*\n\nEnvoie le nom d'une équipe (ex: `Arsenal`).", parse_mode="Markdown", reply_markup=menu_options(lang))
    elif text == texts["menu_stats"]:
        bot.reply_to(message, get_stats(user_id), parse_mode="Markdown", reply_markup=menu_options(lang))
    elif text == texts["menu_backtest"]:
        bot.reply_to(message, calculate_backtest(user_id, 30), parse_mode="Markdown", reply_markup=menu_options(lang))
    elif text == texts["menu_live"]:
        bot.reply_to(message, "📡 Fonctionnalité en direct non disponible pour le moment.", parse_mode="Markdown", reply_markup=menu_options(lang))
    elif text == texts["menu_trends"]:
        followed = get_followed_teams(user_id)
        if not followed:
            bot.reply_to(message, "🔔 Tu ne suis aucune équipe.", parse_mode="Markdown", reply_markup=menu_options(lang))
            return
        texte = "📋 *Équipes suivies*\n\n" + "\n".join([f"- {t[0]}" for t in followed])
        bot.reply_to(message, texte, parse_mode="Markdown", reply_markup=menu_options(lang))
    elif text == texts["menu_follow"]:
        followed = get_followed_teams(user_id)
        if followed:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🗑️ Ne plus rien suivre", callback_data="unfollow_all"))
            bot.reply_to(message, "Tu suis : " + ", ".join([t[0] for t in followed]), reply_markup=markup)
        else:
            bot.reply_to(message, "🔔 Envoie `suivre Arsenal` pour suivre une équipe.", parse_mode="Markdown")
    elif text == texts["menu_help"]:
        bot.reply_to(message, "❓ *Aide*\n\nUtilise les boutons du menu pour naviguer.", parse_mode="Markdown", reply_markup=menu_options(lang))
    elif text.lower().startswith("suivre ") or text.lower().startswith("follow "):
        team = text.split(" ", 1)[1].strip()
        add_followed_team(user_id, team)
        bot.reply_to(message, f"✅ Tu suis *{team}*.", parse_mode="Markdown", reply_markup=menu_options(lang))
    else:
        loading = bot.reply_to(message, f"⏳ *Recherche de {text}...*", parse_mode="Markdown")
        result = search_team(text)
        if len(result) > 4000:
            result = result[:4000] + "..."
        bot.edit_message_text(result, chat_id, loading.message_id, parse_mode="Markdown", reply_markup=menu_options(lang))

# ------------------------------------------------------------
# 11. SERVEUR HTTP POUR RENDER
# ------------------------------------------------------------
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_http():
    HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()

threading.Thread(target=run_http, daemon=True).start()

# ------------------------------------------------------------
# 12. LANCEMENT
# ------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("✅ Base de données initialisée.")
    threading.Thread(target=run_scheduler, daemon=True).start()
    print("⏰ Notifications programmées à 8h.")
    print("✅ Bot démarré.")
    bot.infinity_polling()