import os
import requests # type: ignore
import telebot # type: ignore
import sqlite3
import schedule # type: ignore
import time
import threading
import matplotlib.pyplot as plt # type: ignore
import io
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton # type: ignore

# ------------------------------------------------------------
# 1. CONFIGURATION
# ------------------------------------------------------------
BZZOIRO_API_KEY = os.getenv("BZZOIRO_API_KEY", "633d50eb603d3d9845fb270244372396cb95")
BZZOIRO_URL = "https://sports.bzzoiro.com/api/v2/"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8602372536:AAEtG5qLBhOg97PfoneuWV9XWR0FSmQIYwU")
CHAT_ID = os.getenv("CHAT_ID", "6842436232")

# ------------------------------------------------------------
# 2. BASE DE DONNÉES SQLITE
# ------------------------------------------------------------
def init_db():
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    # Table des pronostics
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            market TEXT,
            prob_home REAL,
            prob_draw REAL,
            prob_away REAL,
            prediction TEXT,
            actual_result TEXT,
            user_id INTEGER,
            created_at TEXT
        )
    ''')
    # Table des utilisateurs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            chat_id TEXT,
            username TEXT,
            created_at TEXT
        )
    ''')
    # Table des équipes suivies
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS followed_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            team_name TEXT,
            league_name TEXT,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    # Ajout des colonnes manquantes
    try:
        cursor.execute('ALTER TABLE predictions ADD COLUMN user_id INTEGER')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE predictions ADD COLUMN market TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE predictions ADD COLUMN prob_draw REAL')
    except:
        pass
    conn.commit()
    conn.close()

# ------------------------------------------------------------
# 3. FONCTIONS BZZOIRO
# ------------------------------------------------------------
def bzzoiro_request(endpoint, params=None, method='GET'):
    headers = {"Authorization": f"Token {BZZOIRO_API_KEY}"}
    url = f"{BZZOIRO_URL}{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url, params=params, headers=headers, timeout=10)
        else:
            response = requests.post(url, json=params, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Erreur Bzzoiro {endpoint}: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        print(f"❌ Exception Bzzoiro: {e}")
        return None

# ------------------------------------------------------------
# 4. FONCTIONS MÉTIERS (A à F)
# ------------------------------------------------------------

# ----- A. Classements et forme -----
def get_league_table(league_name):
    data = bzzoiro_request('standings/', params={"league": league_name})
    if not data or 'standings' not in data:
        return None
    return data['standings']

def get_team_form(team_name):
    data = bzzoiro_request('team-form/', params={"team": team_name})
    if not data or 'form' not in data:
        return None
    return data['form']

def format_league_table(table, team_filter=None):
    if not table:
        return "📊 Classement non disponible"
    texte = "🏆 *Classement*\n\n"
    for item in table[:10]:
        pos = item.get('position', '?')
        team = item.get('team', 'Inconnu')
        points = item.get('points', 0)
        played = item.get('played', 0)
        if team_filter and team_filter.lower() in team.lower():
            texte += f"👉 {pos}. *{team}* - {points} pts ({played} matchs)\n"
        else:
            texte += f"{pos}. {team} - {points} pts ({played} matchs)\n"
    return texte

def format_team_form(form):
    if not form:
        return "📈 Forme non disponible"
    emojis = {'W': '✅', 'D': '➖', 'L': '❌'}
    return "📈 *Forme récente* : " + " ".join([emojis.get(f, '❓') for f in form[:5]])

# ----- B. Comparateur de cotes -----
def get_odds_comparison(match):
    bookmakers = match.get('bookmakers', [])
    if not bookmakers:
        return "Aucune cote disponible"
    texte = "📊 *Comparateur de cotes*\n\n"
    for bm in bookmakers[:3]:
        name = bm.get('name', 'Inconnu')
        odds = bm.get('odds', [])
        for odd in odds:
            if odd.get('market') == '1x2':
                outcomes = odd.get('outcomes', [])
                home_odd = next((o['price'] for o in outcomes if o['name'] == match['home_team']), 'N/A')
                draw_odd = next((o['price'] for o in outcomes if o['name'] == 'Draw'), 'N/A')
                away_odd = next((o['price'] for o in outcomes if o['name'] == match['away_team']), 'N/A')
                texte += f"*{name}* : {home_odd} | {draw_odd} | {away_odd}\n"
                break
    return texte

# ----- C. Graphiques -----
def generate_probability_chart(probs, labels):
    fig, ax = plt.subplots(figsize=(5, 3))
    bars = ax.bar(labels, probs, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    ax.set_ylabel('Probabilité (%)')
    ax.set_title('Pronostic')
    ax.set_ylim(0, 100)
    for bar, v in zip(bars, probs):
        ax.text(bar.get_x() + bar.get_width()/2, v + 2, f"{v:.1f}%", ha='center', fontsize=9)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf

# ----- D. Prédictions ML (CatBoost) -----
def get_ml_prediction(match_id):
    data = bzzoiro_request(f'predictions/{match_id}/')
    if not data or 'prediction' not in data:
        return None
    return data['prediction']

def format_ml_prediction(pred, home_team, away_team):
    if not pred:
        return "🤖 Prédiction ML non disponible"
    texte = "🤖 *Prédiction ML (CatBoost)*\n\n"
    mapping = {
        'home_win': f"🏠 Victoire {home_team}",
        'draw': "🤝 Nul",
        'away_win': f"✈️ Victoire {away_team}"
    }
    for key, value in pred.items():
        label = mapping.get(key, key)
        texte += f"{label} : {value:.1f}%\n"
    return texte

# ----- E. Notifications personnalisées -----
def register_user(user_id, chat_id, username):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, chat_id, username, created_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, chat_id, username, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def add_followed_team(user_id, team_name, league_name):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO followed_teams (user_id, team_name, league_name, created_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, team_name, league_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def remove_followed_team(user_id, team_name):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM followed_teams WHERE user_id = ? AND team_name = ?
    ''', (user_id, team_name))
    conn.commit()
    conn.close()

def get_followed_teams(user_id):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('SELECT team_name, league_name FROM followed_teams WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ----- F. Événements en direct -----
def get_live_events():
    data = bzzoiro_request('livescore/', params={"sport": "soccer"})
    if not data or 'events' not in data:
        return None
    return data['events']

def format_live_events(events):
    if not events:
        return "📡 Aucun événement en direct"
    texte = "📡 *Événements en direct*\n\n"
    for ev in events[:10]:
        home = ev.get('home_team', '?')
        away = ev.get('away_team', '?')
        score = ev.get('score', '0-0')
        time_elapsed = ev.get('time', '0')
        texte += f"⚽ {home} {score} {away} ({time_elapsed}')\n"
    return texte

# ------------------------------------------------------------
# 5. NOUVELLES FONCTIONNALITÉS AVANCÉES (Backtesting, Tendances, Meilleures cotes)
# ------------------------------------------------------------

# ----- 1. Backtesting -----
def calculate_backtest(user_id=None, days=30):
    """Calcule le taux de réussite des pronostics sur les X derniers jours."""
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    if user_id:
        cursor.execute('''
            SELECT prediction, actual_result FROM predictions
            WHERE user_id = ? AND date >= date('now', ?)
        ''', (user_id, f'-{days} days'))
    else:
        cursor.execute('''
            SELECT prediction, actual_result FROM predictions
            WHERE date >= date('now', ?)
        ''', (f'-{days} days',))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "📊 Aucun pronostic enregistré sur cette période."
    total = len(rows)
    correct = sum(1 for pred, actual in rows if actual and pred == actual)
    taux = (correct / total) * 100 if total > 0 else 0
    return f"📊 *Backtesting ({days} jours)*\n\nPronostics : {total}\nCorrects : {correct}\nTaux de réussite : {taux:.1f}%"

def save_actual_result(match_id, result):
    """Enregistre le résultat réel d'un match (pour le backtesting)."""
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE predictions SET actual_result = ? WHERE id = ?
    ''', (result, match_id))
    conn.commit()
    conn.close()

# ----- 2. Analyse des tendances -----
def analyze_team_trends(team_name):
    """Analyse les tendances d'une équipe."""
    form = get_team_form(team_name)
    if not form:
        return "📈 Tendances non disponibles"
    
    recent = form[:5]
    wins = recent.count('W')
    draws = recent.count('D')
    losses = recent.count('L')
    
    texte = f"📈 *Tendances de {team_name}*\n\n"
    texte += f"📊 Forme récente : {' '.join(['✅' if f=='W' else '➖' if f=='D' else '❌' for f in recent])}\n"
    texte += f"   Victoires : {wins} | Nuls : {draws} | Défaites : {losses}\n"
    
    if wins >= 4:
        texte += "🔥 *Équipe en feu !* (4+ victoires sur 5)\n"
    elif wins >= 3:
        texte += "🔥 *Bonne dynamique* (3 victoires sur 5)\n"
    elif losses >= 4:
        texte += "❄️ *Équipe en crise* (4+ défaites sur 5)\n"
    elif losses >= 3:
        texte += "❄️ *Mauvaise dynamique* (3 défaites sur 5)\n"
    else:
        texte += "⚖️ *Dynamique stable*\n"
    
    return texte

# ----- 3. Meilleures cotes en temps réel -----
def get_best_odds(match):
    """Trouve les meilleures cotes pour un match parmi tous les bookmakers."""
    bookmakers = match.get('bookmakers', [])
    if not bookmakers:
        return "Aucune cote disponible"
    
    best = {
        'home': {'price': 0, 'bookmaker': ''},
        'draw': {'price': 0, 'bookmaker': ''},
        'away': {'price': 0, 'bookmaker': ''}
    }
    
    for bm in bookmakers:
        name = bm.get('name', 'Inconnu')
        for odd in bm.get('odds', []):
            if odd.get('market') == '1x2':
                outcomes = odd.get('outcomes', [])
                for o in outcomes:
                    if o['name'] == match['home_team'] and o['price'] > best['home']['price']:
                        best['home'] = {'price': o['price'], 'bookmaker': name}
                    elif o['name'] == 'Draw' and o['price'] > best['draw']['price']:
                        best['draw'] = {'price': o['price'], 'bookmaker': name}
                    elif o['name'] == match['away_team'] and o['price'] > best['away']['price']:
                        best['away'] = {'price': o['price'], 'bookmaker': name}
    
    texte = "🏆 *Meilleures cotes*\n\n"
    texte += f"🏠 {match['home_team']} : {best['home']['price']} ({best['home']['bookmaker']})\n"
    texte += f"🤝 Nul : {best['draw']['price']} ({best['draw']['bookmaker']})\n"
    texte += f"✈️ {match['away_team']} : {best['away']['price']} ({best['away']['bookmaker']})\n"
    return texte

# ------------------------------------------------------------
# 6. FONCTIONS PRINCIPALES (récupération des matchs)
# ------------------------------------------------------------
def fetch_bzzoiro_events(date_from=None, date_to=None, market="1x2"):
    if date_from is None:
        date_from = datetime.now().strftime("%Y-%m-%d")
    if date_to is None:
        date_to = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    params = {"date_from": date_from, "date_to": date_to, "market": market}
    data = bzzoiro_request('events/', params=params)
    if not data or 'results' not in data:
        return None
    return data['results']

def format_match(event):
    return {
        "id": event.get("id"),
        "home_team": event.get("home_team", "Inconnu"),
        "away_team": event.get("away_team", "Inconnu"),
        "league_name": event.get("league_name", "Inconnu"),
        "commence_time": event.get("start_time", datetime.now().isoformat()),
        "bookmakers": event.get("bookmakers", [])
    }

def get_all_matches():
    events = fetch_bzzoiro_events(market="1x2")
    if not events:
        return []
    return [format_match(e) for e in events]

def get_matches_next_days(days=7):
    date_from = datetime.now().strftime("%Y-%m-%d")
    date_to = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    events = fetch_bzzoiro_events(date_from, date_to, market="1x2")
    if not events:
        return []
    return [format_match(e) for e in events]

def get_matches_for_league(league_filter):
    events = fetch_bzzoiro_events(market="1x2")
    if not events:
        return None, "⚠️ Impossible de contacter l'API."
    filtered = []
    league_lower = league_filter.lower()
    for e in events:
        if league_lower in e.get("league_name", "").lower():
            filtered.append(format_match(e))
    if not filtered:
        return None, f"ℹ️ Aucun match pour cette ligue."
    return filtered, None

# ------------------------------------------------------------
# 7. MARCHÉS ET PRONOSTICS
# ------------------------------------------------------------
def get_available_markets(match):
    markets = []
    for bm in match.get('bookmakers', []):
        for odd in bm.get('odds', []):
            market_key = odd.get('market')
            if market_key and market_key not in markets:
                markets.append(market_key)
    return markets

def get_market_predictions(match, market_type="1x2"):
    try:
        home = match["home_team"]
        away = match["away_team"]
        for bm in match.get('bookmakers', []):
            for odd in bm.get('odds', []):
                if odd.get('market') != market_type:
                    continue
                outcomes = odd.get('outcomes', [])
                if market_type == "1x2":
                    odds_home = next((o["price"] for o in outcomes if o["name"] == home), None)
                    odds_draw = next((o["price"] for o in outcomes if o["name"] == "Draw"), None)
                    odds_away = next((o["price"] for o in outcomes if o["name"] == away), None)
                    if odds_home is None or odds_draw is None or odds_away is None:
                        return {"error": "Cotes 1X2 incomplètes"}
                    prob_home = (1/odds_home)*100
                    prob_draw = (1/odds_draw)*100
                    prob_away = (1/odds_away)*100
                    total = prob_home + prob_draw + prob_away
                    prob_home = (prob_home/total)*100
                    prob_draw = (prob_draw/total)*100
                    prob_away = (prob_away/total)*100
                    if prob_home > prob_away and prob_home > prob_draw:
                        pred = f"🏠 {home}"
                    elif prob_away > prob_home and prob_away > prob_draw:
                        pred = f"✈️ {away}"
                    else:
                        pred = "🤝 Nul"
                    return {
                        "type": "1X2",
                        "prob_home": prob_home,
                        "prob_draw": prob_draw,
                        "prob_away": prob_away,
                        "prediction": pred,
                        "display": f"🏠 {home} : {prob_home:.1f}%\n🤝 Nul : {prob_draw:.1f}%\n✈️ {away} : {prob_away:.1f}%"
                    }
                elif market_type == "btts":
                    odds_yes = next((o["price"] for o in outcomes if o["name"] == "Yes"), None)
                    odds_no = next((o["price"] for o in outcomes if o["name"] == "No"), None)
                    if odds_yes is None or odds_no is None:
                        return {"error": "Cotes BTTS incomplètes"}
                    prob_yes = (1/odds_yes)*100
                    prob_no = (1/odds_no)*100
                    total = prob_yes + prob_no
                    prob_yes = (prob_yes/total)*100
                    prob_no = (prob_no/total)*100
                    pred = "✅ Oui" if prob_yes > prob_no else "❌ Non"
                    return {
                        "type": "BTTS",
                        "prob_yes": prob_yes,
                        "prob_no": prob_no,
                        "prediction": pred,
                        "display": f"✅ Oui : {prob_yes:.1f}%\n❌ Non : {prob_no:.1f}%"
                    }
                elif market_type.startswith("over_under"):
                    lines = []
                    for o in outcomes:
                        if o.get('price', 0) > 0:
                            lines.append({
                                "name": o["name"],
                                "point": o.get("point", ""),
                                "price": o["price"],
                                "prob": (1/o["price"])*100
                            })
                    if not lines:
                        return {"error": "Aucune ligne Over/Under"}
                    best = max(lines, key=lambda x: x["prob"])
                    return {
                        "type": "Over/Under",
                        "display": "\n".join([f"{l['name']} {l['point']} : {l['prob']:.1f}%" for l in lines]),
                        "prediction": f"{best['name']} {best['point']}"
                    }
                elif market_type == "double_chance":
                    odds_1x = next((o["price"] for o in outcomes if o["name"] == "1X"), None)
                    odds_12 = next((o["price"] for o in outcomes if o["name"] == "12"), None)
                    odds_x2 = next((o["price"] for o in outcomes if o["name"] == "X2"), None)
                    if odds_1x is None or odds_12 is None or odds_x2 is None:
                        return {"error": "Cotes Double Chance incomplètes"}
                    prob_1x = (1/odds_1x)*100
                    prob_12 = (1/odds_12)*100
                    prob_x2 = (1/odds_x2)*100
                    total = prob_1x + prob_12 + prob_x2
                    prob_1x = (prob_1x/total)*100
                    prob_12 = (prob_12/total)*100
                    prob_x2 = (prob_x2/total)*100
                    max_prob = max(prob_1x, prob_12, prob_x2)
                    if max_prob == prob_1x:
                        pred = "1X"
                    elif max_prob == prob_12:
                        pred = "12"
                    else:
                        pred = "X2"
                    return {
                        "type": "Double Chance",
                        "prob_1x": prob_1x,
                        "prob_12": prob_12,
                        "prob_x2": prob_x2,
                        "prediction": pred,
                        "display": f"1X : {prob_1x:.1f}%\n12 : {prob_12:.1f}%\nX2 : {prob_x2:.1f}%"
                    }
                elif market_type == "total_corners":
                    lines = []
                    for o in outcomes:
                        if o.get('price', 0) > 0 and o.get('point'):
                            lines.append({
                                "name": o["name"],
                                "point": o["point"],
                                "price": o["price"],
                                "prob": (1/o["price"])*100
                            })
                    if not lines:
                        return {"error": "Aucune ligne Corners"}
                    best = max(lines, key=lambda x: x["prob"])
                    return {
                        "type": "Corners",
                        "display": "\n".join([f"{l['name']} {l['point']} : {l['prob']:.1f}%" for l in lines]),
                        "prediction": f"{best['name']} {best['point']}"
                    }
        return {"error": f"Marché '{market_type}' non disponible"}
    except Exception as e:
        return {"error": str(e)}

# ------------------------------------------------------------
# 8. RECHERCHE D'ÉQUIPE
# ------------------------------------------------------------
def search_team(team_name):
    resultats = []
    team_clean = team_name.strip().lower()
    if not team_clean:
        return "❌ Veuillez entrer un nom d'équipe valide."
    matches = get_all_matches()
    if not matches:
        return "⚠️ Aucun match trouvé."
    for match in matches:
        if team_clean in match["home_team"].lower() or team_clean in match["away_team"].lower():
            pred = get_market_predictions(match, "1x2")
            if "error" in pred:
                continue
            date_str = match.get("commence_time", "")[:10] if match.get("commence_time") else "Date inconnue"
            resultats.append(
                f"📅 {date_str} | {match['league_name']}\n"
                f"⚽ {match['home_team']} vs {match['away_team']}\n"
                f"   🏠 {match['home_team']} : {pred['prob_home']:.1f}%\n"
                f"   🤝 Nul   : {pred['prob_draw']:.1f}%\n"
                f"   ✈️ {match['away_team']} : {pred['prob_away']:.1f}%\n"
                f"   ✅ *{pred['prediction']}*\n"
            )
    if not resultats:
        return f"❌ Aucun match trouvé pour *{team_name}*."
    return "\n\n".join(resultats)

# ------------------------------------------------------------
# 9. STATISTIQUES ET COMPOSITIONS
# ------------------------------------------------------------
def get_match_statistics(match_id):
    data = bzzoiro_request(f'events/{match_id}/statistics/')
    return data

def format_statistics(stats):
    if not stats:
        return "📊 *Statistiques non disponibles*"
    texte = "📊 *Statistiques du match*\n\n"
    keys = [("possession","Possession","%"),("shots_on_target","Tirs cadrés",""),
            ("shots_off_target","Tirs non cadrés",""),("corners","Corners",""),
            ("fouls","Fautes",""),("yellow_cards","Cartons jaunes",""),
            ("red_cards","Cartons rouges","")]
    for key, label, suffix in keys:
        if key in stats:
            home_val = stats[key].get("home", "N/A")
            away_val = stats[key].get("away", "N/A")
            texte += f"{label} : 🏠 {home_val}{suffix} | ✈️ {away_val}{suffix}\n"
    return texte

def get_match_lineups(match_id):
    data = bzzoiro_request(f'events/{match_id}/lineups/')
    return data

def format_lineups(lineups):
    if not lineups:
        return "📋 *Compositions non disponibles*"
    texte = "📋 *Compositions officielles*\n\n"
    for team in lineups.get("teams", []):
        texte += f"*{team.get('name', 'Inconnu')}*\n"
        for player in team.get("starting_xi", []):
            numero = player.get("number", "?")
            nom = player.get("name", "Inconnu")
            position = player.get("position", "")
            texte += f"   {numero}. {nom} ({position})\n"
        texte += "\n"
    return texte

# ------------------------------------------------------------
# 10. SAUVEGARDE DES PRONOSTICS
# ------------------------------------------------------------
def save_prediction(home, away, market, prob_h, prob_d, prob_a, pred, user_id=None):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO predictions (date, home_team, away_team, market, prob_home, prob_draw, prob_away, prediction, user_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().strftime("%Y-%m-%d"),
        home, away, market, prob_h, prob_d, prob_a, pred, user_id,
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

def get_stats(user_id=None):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    if user_id:
        cursor.execute('''
            SELECT COUNT(*), SUM(CASE WHEN actual_result = prediction THEN 1 ELSE 0 END)
            FROM predictions WHERE user_id = ? AND actual_result IS NOT NULL
        ''', (user_id,))
    else:
        cursor.execute('''
            SELECT COUNT(*), SUM(CASE WHEN actual_result = prediction THEN 1 ELSE 0 END)
            FROM predictions WHERE actual_result IS NOT NULL
        ''')
    total, correct = cursor.fetchone()
    conn.close()
    if total and total > 0:
        return f"📊 *Statistiques*\n\nPronostics enregistrés : {total}\nPronostics justes : {correct or 0}\nTaux de réussite : {((correct or 0) / total * 100):.1f}%"
    else:
        return "📊 Aucune donnée statistique disponible."

# ------------------------------------------------------------
# 11. NOTIFICATIONS AUTOMATIQUES
# ------------------------------------------------------------
def send_notifications():
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT user_id FROM followed_teams')
    users = cursor.fetchall()
    for (user_id,) in users:
        teams = get_followed_teams(user_id)
        for team_name, league_name in teams:
            matches = get_all_matches()
            for match in matches:
                if team_name.lower() in match['home_team'].lower() or team_name.lower() in match['away_team'].lower():
                    pred = get_market_predictions(match, "1x2")
                    if "error" not in pred:
                        msg = f"🔔 *Match de {team_name}*\n\n"
                        msg += f"⚽ {match['home_team']} vs {match['away_team']}\n"
                        msg += f"🏠 {match['home_team']} : {pred['prob_home']:.1f}%\n"
                        msg += f"🤝 Nul : {pred['prob_draw']:.1f}%\n"
                        msg += f"✈️ {match['away_team']} : {pred['prob_away']:.1f}%\n"
                        msg += f"✅ *Pronostic : {pred['prediction']}*"
                        try:
                            bot.send_message(user_id, msg, parse_mode="Markdown")
                        except Exception as e:
                            print(f"Erreur notification {user_id}: {e}")
    conn.close()

def run_scheduler_notifications():
    schedule.every().day.at("08:00").do(send_notifications)
    while True:
        schedule.run_pending()
        time.sleep(60)

# ------------------------------------------------------------
# 12. MENUS
# ------------------------------------------------------------
def menu_options():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton("🔮 Pronostics du jour")
    btn2 = KeyboardButton("🏆 Par championnat")
    btn3 = KeyboardButton("📅 Matchs à venir")
    btn4 = KeyboardButton("⚽ Rechercher une équipe")
    btn5 = KeyboardButton("📊 Statistiques")
    btn6 = KeyboardButton("📡 En direct")
    btn7 = KeyboardButton("🔔 Suivre une équipe")
    btn8 = KeyboardButton("📈 Backtesting")
    btn9 = KeyboardButton("📊 Mes tendances")
    btn10 = KeyboardButton("❓ Aide")
    btn11 = KeyboardButton("🔄 Réinitialiser")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10, btn11)
    return markup

def menu_ligues_inline():
    markup = InlineKeyboardMarkup(row_width=2)
    sports = {
        "Premier League": "premier league",
        "Ligue 1": "ligue 1",
        "Bundesliga": "bundesliga",
        "La Liga": "la liga",
        "Serie A": "serie a",
        "MLS": "mls",
        "Brasil Serie A": "brasil serie a",
        "Coupe du Monde": "world cup"
    }
    for nom, cle in sports.items():
        matches, error = get_matches_for_league(cle)
        if error or not matches:
            continue
        markup.add(InlineKeyboardButton(nom, callback_data=f"league_{cle}"))
    markup.add(InlineKeyboardButton("🔙 Retour", callback_data="menu_back"))
    return markup

def menu_matchs_inline(league_key, matches):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, m in enumerate(matches[:10]):
        markup.add(InlineKeyboardButton(
            f"⚽ {m['home_team']} vs {m['away_team']}",
            callback_data=f"match_{league_key}_{i}"
        ))
    markup.add(InlineKeyboardButton("🔙 Retour", callback_data="choose_league"))
    return markup

def menu_matchs_jour(matches):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, m in enumerate(matches[:20]):
        date = m.get("commence_time", "")[:10] if m.get("commence_time") else "Date inconnue"
        markup.add(InlineKeyboardButton(
            f"📅 {date} | {m['league_name']} : {m['home_team']} vs {m['away_team']}",
            callback_data=f"match_day_{i}"
        ))
    markup.add(InlineKeyboardButton("🔙 Retour", callback_data="menu_back"))
    return markup

def menu_matchs_semaine(matches):
    markup = InlineKeyboardMarkup(row_width=1)
    for i, m in enumerate(matches[:30]):
        date = m.get("commence_time", "")[:10] if m.get("commence_time") else "Date inconnue"
        markup.add(InlineKeyboardButton(
            f"📅 {date} | {m['league_name']} : {m['home_team']} vs {m['away_team']}",
            callback_data=f"match_week_{i}"
        ))
    markup.add(InlineKeyboardButton("🔙 Retour", callback_data="menu_back"))
    return markup

def menu_match_actions(match_id):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔮 1X2", callback_data=f"market_{match_id}_1x2"))
    markup.add(InlineKeyboardButton("📈 Over/Under", callback_data=f"market_{match_id}_over_under_25"))
    markup.add(InlineKeyboardButton("⚽ BTTS", callback_data=f"market_{match_id}_btts"))
    markup.add(InlineKeyboardButton("🔄 Double Chance", callback_data=f"market_{match_id}_double_chance"))
    markup.add(InlineKeyboardButton("🏁 Corners", callback_data=f"market_{match_id}_total_corners"))
    markup.add(InlineKeyboardButton("🤖 ML Prediction", callback_data=f"ml_{match_id}"))
    markup.add(InlineKeyboardButton("📊 Classement", callback_data=f"table_{match_id}"))
    markup.add(InlineKeyboardButton("📊 Comparateur cotes", callback_data=f"odds_{match_id}"))
    markup.add(InlineKeyboardButton("🏆 Meilleures cotes", callback_data=f"bestodds_{match_id}"))
    markup.add(InlineKeyboardButton("📈 Tendances équipe", callback_data=f"trend_{match_id}"))
    markup.add(InlineKeyboardButton("📊 Statistiques", callback_data=f"stats_{match_id}"))
    markup.add(InlineKeyboardButton("📋 Compositions", callback_data=f"lineups_{match_id}"))
    markup.add(InlineKeyboardButton("🔙 Retour aux matchs", callback_data="back_to_matches"))
    return markup

# ------------------------------------------------------------
# 13. BOT TELEGRAM
# ------------------------------------------------------------
bot = telebot.TeleBot(TELEGRAM_TOKEN)
bot.match_cache = {}
bot.day_matches = []
bot.week_matches = []
bot.current_match_data = {}

def send_welcome_message(message):
    bot.reply_to(message,
        "👋 *Bienvenue sur KING NI Predict Bot !*\n\n"
        "Choisis une option ci-dessous :",
        parse_mode="Markdown", reply_markup=menu_options())

@bot.message_handler(commands=['start'])
def handle_start(message):
    register_user(message.from_user.id, message.chat.id, message.from_user.username)
    bot.match_cache = {}
    bot.day_matches = []
    bot.week_matches = []
    bot.current_match_data = {}
    send_welcome_message(message)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        user_id = call.from_user.id

        # --- RETOUR MENU ---
        if call.data == "menu_back":
            bot.send_message(chat_id, "👋 *Menu principal*", parse_mode="Markdown", reply_markup=menu_options())
            return
        if call.data == "choose_league":
            bot.send_message(chat_id, "🏆 *Choisis un championnat :*", parse_mode="Markdown",
                             reply_markup=menu_ligues_inline())
            return
        if call.data == "back_to_matches":
            if bot.day_matches:
                bot.send_message(chat_id, f"🔮 *Pronostics du jour*\n\n{len(bot.day_matches)} matchs :",
                                 parse_mode="Markdown", reply_markup=menu_matchs_jour(bot.day_matches))
            elif bot.week_matches:
                bot.send_message(chat_id, f"📅 *Matchs à venir*\n\n{len(bot.week_matches)} matchs :",
                                 parse_mode="Markdown", reply_markup=menu_matchs_semaine(bot.week_matches))
            else:
                bot.send_message(chat_id, "👋 Retour aux championnats.", parse_mode="Markdown",
                                 reply_markup=menu_ligues_inline())
            return

        # --- CHAMPIONNAT ---
        if call.data.startswith("league_") and not call.data.startswith("league_match"):
            league_key = call.data.replace("league_", "")
            nom_ligue = league_key.title()
            loading = bot.send_message(chat_id, "⏳ *Chargement...*", parse_mode="Markdown")
            matches, error = get_matches_for_league(league_key)
            if error or not matches:
                bot.edit_message_text(error or "⚠️ Aucun match.", chat_id, loading.message_id, parse_mode="Markdown")
                return
            for i, m in enumerate(matches[:10]):
                bot.match_cache[f"match_{league_key}_{i}"] = m
            bot.delete_message(chat_id, loading.message_id)
            bot.send_message(chat_id, f"⚽ *{nom_ligue}*\n\nChoisis un match :",
                             parse_mode="Markdown", reply_markup=menu_matchs_inline(league_key, matches))
            return

        # --- PRONOSTICS DU JOUR ---
        if call.data == "predict_all":
            loading = bot.send_message(chat_id, "⏳ *Récupération...*", parse_mode="Markdown")
            matches = get_all_matches()
            if not matches:
                bot.edit_message_text("⚠️ Aucun match aujourd'hui.", chat_id, loading.message_id, parse_mode="Markdown")
                return
            bot.day_matches = matches[:20]
            for i, m in enumerate(bot.day_matches):
                bot.match_cache[f"match_day_{i}"] = m
            bot.delete_message(chat_id, loading.message_id)
            bot.send_message(chat_id, f"🔮 *Pronostics du jour*\n\n{len(bot.day_matches)} matchs :",
                             parse_mode="Markdown", reply_markup=menu_matchs_jour(bot.day_matches))
            return

        # --- MATCHS À VENIR ---
        if call.data == "predict_week":
            loading = bot.send_message(chat_id, "⏳ *Récupération...*", parse_mode="Markdown")
            matches = get_matches_next_days(7)
            if not matches:
                bot.edit_message_text("⚠️ Aucun match dans les 7 jours.", chat_id, loading.message_id, parse_mode="Markdown")
                return
            bot.week_matches = matches[:30]
            for i, m in enumerate(bot.week_matches):
                bot.match_cache[f"match_week_{i}"] = m
            bot.delete_message(chat_id, loading.message_id)
            bot.send_message(chat_id, f"📅 *Matchs à venir*\n\n{len(bot.week_matches)} matchs :",
                             parse_mode="Markdown", reply_markup=menu_matchs_semaine(bot.week_matches))
            return

        # --- SÉLECTION MATCH ---
        if call.data.startswith("match_"):
            match = bot.match_cache.get(call.data)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.", reply_markup=menu_options())
                return
            bot.current_match_data[call.data] = match
            bot.send_message(chat_id, f"⚽ *{match['home_team']} vs {match['away_team']}*\n\nChoisis une action :",
                             parse_mode="Markdown", reply_markup=menu_match_actions(call.data))
            return

        # --- STATISTIQUES ---
        if call.data.startswith("stats_"):
            match_id = call.data.replace("stats_", "")
            match = bot.current_match_data.get(match_id) or bot.match_cache.get(match_id)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.", reply_markup=menu_options())
                return
            stats = get_match_statistics(match.get("id"))
            texte = format_statistics(stats)
            bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_match_actions(match_id))
            return

        # --- COMPOSITIONS ---
        if call.data.startswith("lineups_"):
            match_id = call.data.replace("lineups_", "")
            match = bot.current_match_data.get(match_id) or bot.match_cache.get(match_id)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.", reply_markup=menu_options())
                return
            lineups = get_match_lineups(match.get("id"))
            texte = format_lineups(lineups)
            bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_match_actions(match_id))
            return

        # --- CLASSEMENT ---
        if call.data.startswith("table_"):
            match_id = call.data.replace("table_", "")
            match = bot.current_match_data.get(match_id) or bot.match_cache.get(match_id)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.", reply_markup=menu_options())
                return
            league = match.get("league_name", "")
            table = get_league_table(league)
            texte = format_league_table(table, match.get("home_team"))
            bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_match_actions(match_id))
            return

        # --- COMPARATEUR DE COTES ---
        if call.data.startswith("odds_"):
            match_id = call.data.replace("odds_", "")
            match = bot.current_match_data.get(match_id) or bot.match_cache.get(match_id)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.", reply_markup=menu_options())
                return
            texte = get_odds_comparison(match)
            bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_match_actions(match_id))
            return

        # --- MEILLEURES COTES ---
        if call.data.startswith("bestodds_"):
            match_id = call.data.replace("bestodds_", "")
            match = bot.current_match_data.get(match_id) or bot.match_cache.get(match_id)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.", reply_markup=menu_options())
                return
            texte = get_best_odds(match)
            bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_match_actions(match_id))
            return

        # --- TENDANCES ÉQUIPE ---
        if call.data.startswith("trend_"):
            match_id = call.data.replace("trend_", "")
            match = bot.current_match_data.get(match_id) or bot.match_cache.get(match_id)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.", reply_markup=menu_options())
                return
            # Analyser les deux équipes
            texte = "📈 *Tendances des équipes*\n\n"
            texte += analyze_team_trends(match['home_team'])
            texte += "\n"
            texte += analyze_team_trends(match['away_team'])
            bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_match_actions(match_id))
            return

        # --- PRÉDICTION ML ---
        if call.data.startswith("ml_"):
            match_id = call.data.replace("ml_", "")
            match = bot.current_match_data.get(match_id) or bot.match_cache.get(match_id)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.", reply_markup=menu_options())
                return
            pred = get_ml_prediction(match.get("id"))
            texte = format_ml_prediction(pred, match.get("home_team"), match.get("away_team"))
            bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_match_actions(match_id))
            return

        # --- MARCHÉS ---
        if call.data.startswith("market_"):
            parts = call.data.replace("market_", "").split("_")
            if len(parts) >= 3:
                market_type = "_".join(parts[-1:])
                match_id = "_".join(parts[:-1])
            else:
                market_type = parts[-1]
                match_id = parts[0]
            match = bot.current_match_data.get(match_id) or bot.match_cache.get(match_id)
            if not match:
                bot.send_message(chat_id, "❌ Match introuvable.", reply_markup=menu_options())
                return
            pred = get_market_predictions(match, market_type)
            if "error" in pred:
                bot.send_message(chat_id, f"❌ *Erreur :*\n{pred['error']}", parse_mode="Markdown", reply_markup=menu_options())
                return
            save_prediction(match['home_team'], match['away_team'], pred.get('type', market_type),
                            pred.get('prob_home', 0), pred.get('prob_draw', 0), pred.get('prob_away', 0),
                            pred['prediction'], user_id)
            texte = f"⚽ *{match['home_team']} vs {match['away_team']}*\n"
            texte += f"📊 *Marché : {pred.get('type', market_type).upper()}*\n\n"
            texte += f"{pred['display']}\n\n"
            texte += f"✅ *PRONOSTIC : {pred['prediction']}*"
            if market_type == "1x2" and 'prob_home' in pred:
                probs = [pred['prob_home'], pred['prob_draw'], pred['prob_away']]
                labels = [match['home_team'], 'Nul', match['away_team']]
                img = generate_probability_chart(probs, labels)
                bot.send_photo(chat_id, img, caption=texte, parse_mode="Markdown", reply_markup=menu_options())
            else:
                bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_options())
            return

        # --- SUIVI D'ÉQUIPE ---
        if call.data.startswith("follow_"):
            team_name = call.data.replace("follow_", "").replace("_", " ")
            add_followed_team(user_id, team_name, "Inconnu")
            bot.send_message(chat_id, f"✅ Tu suis maintenant *{team_name}*.", parse_mode="Markdown", reply_markup=menu_options())
            return

        if call.data.startswith("unfollow_"):
            team_name = call.data.replace("unfollow_", "").replace("_", " ")
            remove_followed_team(user_id, team_name)
            bot.send_message(chat_id, f"❌ Tu ne suis plus *{team_name}*.", parse_mode="Markdown", reply_markup=menu_options())
            return

        # --- EN DIRECT ---
        if call.data == "live":
            events = get_live_events()
            texte = format_live_events(events)
            bot.send_message(chat_id, texte, parse_mode="Markdown", reply_markup=menu_options())
            return

    except Exception as e:
        print(f"❌ Erreur callback: {e}")
        try:
            bot.send_message(call.message.chat.id, f"❌ *Erreur :*\n{str(e)}",
                             parse_mode="Markdown", reply_markup=menu_options())
        except:
            pass

# ------------------------------------------------------------
# 14. GESTION DES MESSAGES TEXTE
# ------------------------------------------------------------
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id

    if text.startswith('/'):
        return

    if text == "🔄 Réinitialiser":
        bot.match_cache = {}
        bot.day_matches = []
        bot.week_matches = []
        bot.current_match_data = {}
        send_welcome_message(message)
        return

    if text == "🔮 Pronostics du jour":
        loading = bot.reply_to(message, "⏳ *Récupération...*", parse_mode="Markdown")
        matches = get_all_matches()
        if not matches:
            bot.edit_message_text("⚠️ Aucun match aujourd'hui.", chat_id, loading.message_id, parse_mode="Markdown")
            return
        bot.day_matches = matches[:20]
        for i, m in enumerate(bot.day_matches):
            bot.match_cache[f"match_day_{i}"] = m
        bot.delete_message(chat_id, loading.message_id)
        bot.send_message(chat_id, f"🔮 *Pronostics du jour*\n\n{len(bot.day_matches)} matchs :",
                         parse_mode="Markdown", reply_markup=menu_matchs_jour(bot.day_matches))
        return

    if text == "📅 Matchs à venir":
        loading = bot.reply_to(message, "⏳ *Récupération...*", parse_mode="Markdown")
        matches = get_matches_next_days(7)
        if not matches:
            bot.edit_message_text("⚠️ Aucun match dans les 7 jours.", chat_id, loading.message_id, parse_mode="Markdown")
            return
        bot.week_matches = matches[:30]
        for i, m in enumerate(bot.week_matches):
            bot.match_cache[f"match_week_{i}"] = m
        bot.delete_message(chat_id, loading.message_id)
        bot.send_message(chat_id, f"📅 *Matchs à venir*\n\n{len(bot.week_matches)} matchs :",
                         parse_mode="Markdown", reply_markup=menu_matchs_semaine(bot.week_matches))
        return

    if text == "🏆 Par championnat":
        bot.reply_to(message, "🏆 *Choisis un championnat :*", parse_mode="Markdown", reply_markup=menu_ligues_inline())
        return

    if text == "⚽ Rechercher une équipe":
        bot.reply_to(message, "⚽ *Recherche d'équipe*\n\nEnvoie le nom d'une équipe (ex: `Arsenal`, `PSG`).",
                     parse_mode="Markdown", reply_markup=menu_options())
        return

    if text == "📈 Backtesting":
        stats = calculate_backtest(user_id, 30)
        bot.reply_to(message, stats, parse_mode="Markdown", reply_markup=menu_options())
        return

    if text == "📊 Mes tendances":
        followed = get_followed_teams(user_id)
        if not followed:
            bot.reply_to(message, "🔔 Tu ne suis aucune équipe. Utilise '🔔 Suivre une équipe' d'abord.",
                         parse_mode="Markdown", reply_markup=menu_options())
            return
        texte = "📈 *Tendances de vos équipes suivies*\n\n"
        for team, league in followed:
            texte += analyze_team_trends(team) + "\n"
        bot.reply_to(message, texte, parse_mode="Markdown", reply_markup=menu_options())
        return

    if text == "❓ Aide":
        bot.reply_to(message,
                     "❓ *Aide*\n\n"
                     "🔮 *Pronostics du jour* : Matchs du jour.\n"
                     "📅 *Matchs à venir* : Matchs des 7 prochains jours.\n"
                     "🏆 *Par championnat* : Choisis une ligue.\n"
                     "⚽ *Recherche équipe* : Tape le nom d'une équipe.\n"
                     "📊 *Statistiques* : Taux de réussite.\n"
                     "📡 *En direct* : Scores en temps réel.\n"
                     "🔔 *Suivre une équipe* : Reçois des notifications.\n"
                     "📈 *Backtesting* : Taux de réussite sur 30 jours.\n"
                     "📊 *Mes tendances* : Tendances de vos équipes suivies.\n\n"
                     "📊 *Marchés disponibles :*\n"
                     "   🔮 1X2\n"
                     "   📈 Over/Under\n"
                     "   ⚽ BTTS\n"
                     "   🔄 Double Chance\n"
                     "   🏁 Corners\n"
                     "   🤖 ML Prediction (CatBoost)\n\n"
                     "📅 Pronostics basés sur les cotes des bookmakers.",
                     parse_mode="Markdown", reply_markup=menu_options())
        return

    if text == "📊 Statistiques":
        stats = get_stats(user_id)
        bot.reply_to(message, stats, parse_mode="Markdown", reply_markup=menu_options())
        return

    if text == "📡 En direct":
        events = get_live_events()
        texte = format_live_events(events)
        bot.reply_to(message, texte, parse_mode="Markdown", reply_markup=menu_options())
        return

    if text == "🔔 Suivre une équipe":
        followed = get_followed_teams(user_id)
        if followed:
            liste = "\n".join([f"- {team}" for team, league in followed])
            markup = InlineKeyboardMarkup()
            for team, league in followed:
                markup.add(InlineKeyboardButton(f"❌ Ne plus suivre {team}", callback_data=f"unfollow_{team.replace(' ', '_')}"))
            bot.reply_to(message, f"📋 *Équipes suivies :*\n{liste}\n\nClique pour arrêter de suivre :",
                         parse_mode="Markdown", reply_markup=markup)
        else:
            bot.reply_to(message, "🔔 *Suivre une équipe*\n\nEnvoie le nom de l'équipe que tu veux suivre.",
                         parse_mode="Markdown", reply_markup=menu_options())
        return

    # --- RECHERCHE D'ÉQUIPE (texte libre) ---
    if not text.startswith('/'):
        if text.lower().startswith("suivre "):
            team_name = text[7:].strip()
            add_followed_team(user_id, team_name, "Inconnu")
            bot.reply_to(message, f"✅ Tu suis maintenant *{team_name}*.", parse_mode="Markdown", reply_markup=menu_options())
            return
        loading = bot.reply_to(message, f"⏳ *Recherche pour {text}...*", parse_mode="Markdown")
        result = search_team(text)
        if len(result) > 4000:
            result = result[:4000] + "\n... (trop long)"
        bot.edit_message_text(result, chat_id, loading.message_id, parse_mode="Markdown", reply_markup=menu_options())
        return

# ------------------------------------------------------------
# 15. LANCEMENT
# ------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("✅ Base de données initialisée.")
    threading.Thread(target=run_scheduler_notifications, daemon=True).start()
    print("⏰ Notifications programmées à 8h.")
    print("✅ Bot démarré.")
    try:
        bot.send_message(CHAT_ID, "🔄 *Bot redémarré avec toutes les améliorations !*\n\n"
                         "✅ A. Classements et forme\n"
                         "✅ B. Comparateur de cotes\n"
                         "✅ C. Graphiques\n"
                         "✅ D. Prédictions ML\n"
                         "✅ E. Notifications personnalisées\n"
                         "✅ F. Événements en direct\n"
                         "✅ 1. Backtesting\n"
                         "✅ 2. Tendances\n"
                         "✅ 3. Meilleures cotes",
                         parse_mode="Markdown", reply_markup=menu_options())
    except Exception as e:
        print(f"⚠️ Erreur envoi message démarrage: {e}")
    bot.infinity_polling()