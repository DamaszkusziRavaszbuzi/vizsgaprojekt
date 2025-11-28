#==========================
#         Imports
#==========================
from flask import Flask, request, jsonify, render_template, session, redirect
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
import json

#==========================
#          Init
#==========================
app = Flask(__name__)

# Use environment variable for secret in production; fallback for development
app.secret_key = os.environ.get('SECRET_KEY', 'furryfemboy')

DATABASE = 'database.db'
DICTIONARY_FILE = "dictionary.json"
VERBOSE_LOGGING = False

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # For dict-like row access
    return conn

def deb_mes(msg):
    if VERBOSE_LOGGING:
        print(msg)

def get_confidence_index(word_row):
    # word_row: dict (from row_factory)
    return (word_row['pass'] * 2) + word_row['passWithHelp'] - word_row['fail'] - (word_row['failWithHelp'] * 2)

def init_db():
    """Initialize the database with the required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            theme TEXT DEFAULT 'themeDark'
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userID INTEGER NOT NULL,
            word TEXT NOT NULL,
            translation TEXT NOT NULL,
            pass INTEGER DEFAULT 0,
            passWithHelp INTEGER DEFAULT 0,
            fail INTEGER DEFAULT 0,
            failWithHelp INTEGER DEFAULT 0,
            FOREIGN KEY (userID) REFERENCES users(id)
        );
    ''')
    conn.commit()
    conn.close()

def get_random_dictionary_entry():
    with open(DICTIONARY_FILE, "r", encoding='utf-8') as f:
        data = json.load(f)
        entries = data["dictionary"]
    return random.choice(entries)

def get_random_english_word():
    entry = get_random_dictionary_entry()
    return entry["english"]

def translate_to_hungarian(word):
    with open(DICTIONARY_FILE, "r", encoding='utf-8') as f:
        data = json.load(f)
        for entry in data["dictionary"]:
            if entry["english"].lower() == word.lower():
                return entry["hungarian"]
    return ""

#=======================
#         Routes
#=======================

#========= Pages ==========
@app.route('/ping')
def ping():
    return redirect('/pong', code=302)
@app.route('/pong')
def pong():
    return redirect('/ping', code=302)

@app.route('/login')
def routeToLogin():
    return render_template('landing.html')

@app.route('/')
def redirectToHome():
    if 'userID' not in session:
        return redirect('/login')
    return redirect('/home')

@app.route('/home')
def routeToIndex():
    if 'userID' not in session:
        return redirect('/login')
    return render_template('index.html')

@app.route('/new')
def routeToNew():
    if 'userID' not in session:
        return redirect('/login')
    return render_template('new.html')

@app.route('/newRandom')
def routeToNewRandom():
    if 'userID' not in session:
        return redirect('/login')
    return render_template('autonew.html')

@app.route('/practice')
def routeToPractice():
    if 'userID' not in session:
        return redirect('/login')
    return render_template('practice.html')

@app.route('/cards')
def routeToCards():
    if 'userID' not in session:
        return redirect('/login')
    return render_template('cards2.html')

@app.route('/forgotPassword')
def xd():
    return render_template('xd.html')

@app.route('/makeCoffee')
def coffe():
    return render_template('coffee.html', code=418)

#========= APIs ==========

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    if not username or not password:
        return jsonify({"status": "error", "message": "Missing username or password"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Username already exists!"}), 400

    hashed_password = generate_password_hash(password)
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()
    return redirect('/login')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    if not username or not password:
        return render_template('landing.html', login_error="Missing username or password!")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        session['userID'] = user['id']
        session['theme'] = user['theme'] if 'theme' in user.keys() else 'themeDark'
        return redirect('/home')
    else:
        return render_template('landing.html', login_error="Hibás felhasználónév vagy jelszó!")

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('userID', None)
    session.pop('theme', None)
    return jsonify({"status": "success", "message": "Logout successful!"}), 200

@app.route('/add_word', methods=['POST'])
def add_word():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    word = request.form.get('word')
    translation = request.form.get('translation')
    passCount = int(request.form.get('pass', 0))
    passWithHelp = int(request.form.get('passWithHelp', 0))
    failCount = int(request.form.get('fail', 0))
    failWithHelp = int(request.form.get('failWithHelp', 0))

    if word and translation:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO words (userID, word, translation, pass, passWithHelp, fail, failWithHelp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, word, translation, passCount, passWithHelp, failCount, failWithHelp))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Word added successfully!"}), 200
    else:
        return jsonify({"status": "error", "message": "Missing input fields!"}), 400

@app.route('/get_random_word', methods=['GET'])
def get_random_word():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM words WHERE userID = ?', (user_id,))
    words = cursor.fetchall()
    if not words:
        return jsonify({"status": "error", "message": "No words found for the user!"}), 400
    random_word = random.choice(words)
    word = random_word['word']
    translation = random_word['translation']
    word_id = random_word['id']
    return jsonify({"word": word, "translation": translation, "word_id": word_id}), 200

@app.route('/get_word_count', methods=['GET'])
def get_word_count():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM words WHERE userID = ?', (user_id,))
    count = cursor.fetchone()[0]
    if count == 0:
        return jsonify({"status": "error", "message": "No words found for the user!"}), 400
    return jsonify({"count": count})

@app.route('/update_score', methods=['POST'])
def update_score():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    word_id = request.json.get('word_id')
    status = request.json.get('status')
    if not word_id:
        return jsonify({"status": "error", "message": "Missing word_id!"}), 400
    if not status:
        return jsonify({"status": "error", "message": "Missing status!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    if status == 'fail':
        cursor.execute('UPDATE words SET fail = fail + 1 WHERE id = ? AND userID = ?', (word_id, user_id))
    elif status == 'pass':
        cursor.execute('UPDATE words SET pass = pass + 1 WHERE id = ? AND userID = ?', (word_id, user_id))
    elif status == 'failWithHelp':
        cursor.execute('UPDATE words SET failWithHelp = failWithHelp + 1 WHERE id = ? AND userID = ?', (word_id, user_id))
    elif status == 'passWithHelp':
        cursor.execute('UPDATE words SET passWithHelp = passWithHelp + 1 WHERE id = ? AND userID = ?', (word_id, user_id))
    else:
        conn.close()
        return jsonify({"status": "error", "message": "Unknown status!"}), 400
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Score updated successfully!"}), 200

@app.route('/switch_translation', methods=['POST'])
def switch_translation():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    session['translation_direction'] = not session.get('translation_direction', True)
    return jsonify({"status": "success", "message": "Translation direction switched!"}), 200

@app.route('/accept_word', methods=['POST'])
def accept_word():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    word = request.json.get('word')
    translation = request.json.get('translation')
    if not word or not translation:
        return jsonify({"status": "error", "message": "Missing word or translation!"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO words (userID, word, translation, pass, passWithHelp, fail, failWithHelp)
        VALUES (?, ?, ?, 0, 0, 0, 0)
    ''', (user_id, word, translation))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Word accepted and added!"}), 200

@app.route('/recommend_word', methods=['GET'])
def recommend_word():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    entry = get_random_dictionary_entry()
    return jsonify({
        "status": "success",
        "word": entry["english"],
        "translation": entry["hungarian"]
    })

@app.route('/get_choices', methods=['POST'])
def get_choices():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    data = request.get_json()
    word_id = data.get('word_id')
    direction = data.get('direction')
    if word_id is None or direction is None:
        return jsonify({"status": "error", "message": "Missing parameters!"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT word, translation FROM words WHERE id=? AND userID=?', (word_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "Word not found!"}), 404
    correct = row['translation'] if direction else row['word']
    # Get all possible choices, excluding the correct one
    if direction:
        cursor.execute('SELECT translation FROM words WHERE userID=? AND id <> ?', (user_id, word_id))
        all_choices = [r['translation'] for r in cursor.fetchall()]
    else:
        cursor.execute('SELECT word FROM words WHERE userID=? AND id <> ?', (user_id, word_id))
        all_choices = [r['word'] for r in cursor.fetchall()]
    conn.close()
    random.shuffle(all_choices)
    choices = all_choices[:3]
    choices.append(correct)
    random.shuffle(choices)
    return jsonify({
        "status": "success",
        "choices": choices,
        "correct": correct
    }), 200

@app.route('/get_learning_words', methods=['GET'])
def get_learning_words():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM words WHERE userID = ?', (user_id,))
    words = cursor.fetchall()
    conn.close()
    if not words:
        return jsonify({"status": "error", "message": "No words found for the user!"}), 400
    word_infos = []
    for w in words:
        ci = get_confidence_index(w)
        word_infos.append({'word_id': w['id'], 'confidenceIndex': ci})
    negative = [x for x in word_infos if x['confidenceIndex'] < 0]
    if len(negative) < 5:
        word_infos_sorted = sorted(word_infos, key=lambda x: x['confidenceIndex'])
        added = {w['word_id'] for w in negative}
        for w in word_infos_sorted:
            if len(negative) >= 10:
                break
            if w['word_id'] not in added:
                negative.append(w)
                added.add(w['word_id'])
    return jsonify({
        "status": "success",
        "word_ids": [x['word_id'] for x in negative]
    })

@app.route('/get_word_by_id', methods=['POST'])
def get_word_by_id():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    word_id = request.json.get('word_id')
    if not word_id:
        return jsonify({"status": "error", "message": "Missing word_id!"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM words WHERE id = ? AND userID = ?', (word_id, user_id))
    word = cursor.fetchone()
    conn.close()
    if not word:
        return jsonify({"status": "error", "message": "Word not found!"}), 404
    return jsonify({
        "status": "success",
        "word_id": word['id'],
        "word": word['word'],
        "translation": word['translation']
    })

@app.route('/recommend_smart_word', methods=['GET'])
def recommend_smart_word():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT word FROM words WHERE userID = ?', (user_id,))
    user_words = set(row['word'].strip().lower() for row in cursor.fetchall())
    conn.close()
    avg_len = 5 if not user_words else sum(len(w) for w in user_words) / len(user_words)
    with open(DICTIONARY_FILE, "r", encoding='utf-8') as f:
        data = json.load(f)
        all_entries = [entry for entry in data["dictionary"] if entry["english"].strip().lower() not in user_words]
    if not all_entries:
        return jsonify({"status": "error", "message": "No more new words to recommend!"}), 400
    sample_entries = random.sample(all_entries, min(10, len(all_entries)))
    def length_metric(entry):
        return abs(len(entry["english"]) - avg_len)
    best_entry = min(sample_entries, key=length_metric)
    return jsonify({
        "status": "success",
        "word": best_entry["english"],
        "translation": best_entry["hungarian"]
    })

@app.route('/edit')
def routeToEdit():
    if 'userID' not in session:
        return redirect('/login')
    return render_template('edit.html')

@app.route('/get_user_words', methods=['GET'])
def get_user_words():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, word, translation FROM words WHERE userID = ? ORDER BY word', (user_id,))
    words = cursor.fetchall()
    conn.close()
    return jsonify({
        "status": "success",
        "words": [{"id": w['id'], "word": w['word'], "translation": w['translation']} for w in words]
    })

@app.route('/delete_word', methods=['POST'])
def delete_word():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    word_id = request.json.get('word_id')
    if not word_id:
        return jsonify({"status": "error", "message": "Missing word_id!"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM words WHERE id = ? AND userID = ?', (word_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Word deleted successfully!"})

@app.route('/update_word', methods=['POST'])
def update_word():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    word_id = request.json.get('word_id')
    new_word = request.json.get('word')
    new_translation = request.json.get('translation')
    if not all([word_id, new_word, new_translation]):
        return jsonify({"status": "error", "message": "Missing required fields!"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE words SET word = ?, translation = ? WHERE id = ? AND userID = ?
    ''', (new_word, new_translation, word_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Word updated successfully!"})

@app.route('/statistics')
def routeToStatistics():
    if 'userID' not in session:
        return redirect('/login')
    return render_template('statistics.html')

@app.route('/get_word_statistics', methods=['GET'])
def get_word_statistics():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, word, translation, pass, passWithHelp, fail, failWithHelp 
        FROM words WHERE userID = ? ORDER BY word
    ''', (user_id,))
    words = cursor.fetchall()
    conn.close()
    word_stats = []
    for w in words:
        confidence_index = (w['pass'] * 2) + w['passWithHelp'] - w['fail'] - (w['failWithHelp'] * 2)
        word_stats.append({
            "id": w['id'],
            "word": w['word'],
            "translation": w['translation'],
            "pass": w['pass'],
            "passWithHelp": w['passWithHelp'],
            "fail": w['fail'],
            "failWithHelp": w['failWithHelp'],
            "confidenceIndex": confidence_index
        })
    return jsonify({
        "status": "success",
        "words": word_stats
    })

@app.route('/settings')
def routeToSettings():
    if 'userID' not in session:
        return redirect('/login')
    return render_template('settings.html')

@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"status": "error", "message": "User not found!"}), 404
    return jsonify({"status": "success", "user": {"id": row['id'], "username": row['username']}})

@app.route('/update_user', methods=['POST'])
def update_user():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    data = request.get_json() or {}
    new_username = data.get('username', '').strip()
    new_password = data.get('password', '').strip()
    if not new_username and not new_password:
        return jsonify({"status": "error", "message": "Nothing to update!"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    if new_username:
        cursor.execute('SELECT id FROM users WHERE username = ?', (new_username,))
        existing = cursor.fetchone()
        if existing and existing['id'] != user_id:
            conn.close()
            return jsonify({"status": "error", "message": "Username already taken!"}), 400
    # Build update query dynamically
    updates = []
    params = []
    if new_username:
        updates.append('username = ?')
        params.append(new_username)
    if new_password:
        updates.append('password = ?')
        params.append(generate_password_hash(new_password))
    if updates:
        params.append(user_id)
        query = f'UPDATE users SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(query, tuple(params))
        conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "User updated successfully!"}), 200

@app.context_processor
def inject_theme():
    theme = session.get('theme', 'themeDark')
    return dict(theme=theme)

@app.route('/set_theme', methods=['POST'])
def set_theme():
    data = request.get_json() or {}
    theme = data.get('theme')
    if not theme:
        return jsonify({"status": "error", "message": "Missing theme"}), 400
    session['theme'] = theme
    if 'userID' in session:
        user_id = session['userID']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET theme = ? WHERE id = ?', (theme, user_id))
        conn.commit()
        conn.close()
    return jsonify({"status": "success", "message": "Theme set", "theme": theme}), 200

#==========================
#           Run
#==========================
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0')
