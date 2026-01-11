#==========================
#         Imports
#==========================
from flask import Flask, request, jsonify, render_template, session, redirect
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
import json
import hashlib
import hmac

#==========================
#          Init
#==========================
app = Flask(__name__)

# Secret key fallback is defined here for local development.
# For secure deployments, set the SECRET_KEY environment variable.
app.secret_key = os.environ.get('SECRET_KEY', 'furryfemboy')

DATABASE = 'database.db'
DICTIONARY_FILE = "dictionary.json"
VERBOSE_LOGGING = False
HMAC_FILE = DATABASE + ".hmac"

def get_db_connection():
    """Open a sqlite3 connection using the configured DATABASE path.
    Uses Row factory so returned rows behave like dicts in code.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def deb_mes(msg):
    """Simple debug print controlled by VERBOSE_LOGGING."""
    if VERBOSE_LOGGING:
        print(msg)

def _hmac_key_bytes():
    """Build HMAC key bytes from environment or app secret.
    This is used to compute an integrity HMAC of the SQLite file so accidental tampering can be detected.
    """
    key = os.environ.get('DB_HMAC_KEY') or app.secret_key or ''
    return key.encode('utf-8')

def compute_db_hmac():
    """Compute HMAC-SHA256 over the database file using the configured key.
    Returns empty string if database file doesn't exist.
    """
    key = _hmac_key_bytes()
    if not os.path.exists(DATABASE):
        return ''
    with open(DATABASE, "rb") as f:
        data = f.read()
    return hmac.new(key, data, hashlib.sha256).hexdigest()

def write_db_hmac(h):
    """Write computed HMAC to the HMAC_FILE."""
    with open(HMAC_FILE, "w") as f:
        f.write(h)

def verify_db_hmac():
    """Verify HMAC on startup to detect database integrity changes.
    - If database doesn't exist: allow (likely first run).
    - If HMAC file doesn't exist: write current HMAC (bootstrap).
    - If mismatch: raise RuntimeError to avoid running with tampered DB.
    Note: This is a lightweight integrity check, not a substitute for proper backups.
    """
    if not os.path.exists(DATABASE):
        return True
    current = compute_db_hmac()
    if not os.path.exists(HMAC_FILE):
        write_db_hmac(current)
        return True
    with open(HMAC_FILE, "r") as f:
        stored = f.read().strip()
    if stored != current:
        raise RuntimeError("Database integrity check failed: HMAC mismatch")
    return True

def update_db_hmac():
    """Recompute and persist the HMAC after database modifications."""
    h = compute_db_hmac()
    write_db_hmac(h)

def commit_and_update(conn):
    """Commit a sqlite connection, close it and update HMAC afterwards.
    Centralizes commit + integrity update to ensure consistency.
    """
    conn.commit()
    conn.close()
    update_db_hmac()

def get_confidence_index(word_row):
    """Calculate a 'confidence index' for a word from its statistics.
    A higher number means the user knows the word better.
    Formula reflects different weights for passes vs fails and with/without help.
    """
    return (word_row['pass'] * 2) + word_row['passWithHelp'] - word_row['fail'] - (word_row['failWithHelp'] * 2)

def init_db():
    """Create tables if they don't exist.
    This function is idempotent and can be safely called on startup.
    """
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
    commit_and_update(conn)

def load_dictionary():
    """Load a JSON dictionary file containing English-Hungarian entries.
    Returns an empty list if the file cannot be read or parsed.
    """
    try:
        with open(DICTIONARY_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
            return data.get("dictionary", [])
    except Exception:
        return []

def get_random_dictionary_entry():
    """Return a random entry from the dictionary. If dictionary is empty, return an empty pair."""
    entries = load_dictionary()
    if not entries:
        return {"english": "", "hungarian": ""}
    return random.choice(entries)

def get_random_english_word():
    """Convenience wrapper to get the english field from a random dictionary entry."""
    entry = get_random_dictionary_entry()
    return entry.get("english", "")

def translate_to_hungarian(word):
    """Simple lookup from english to hungarian using the dictionary file.
    Case-insensitive comparison.
    """
    entries = load_dictionary()
    for entry in entries:
        if entry.get("english", "").lower() == word.lower():
            return entry.get("hungarian", "")
    return ""

def validateLogin(destination):
    """Helper used by many routes that return templates.
    If user is not logged in, redirect to login. Otherwise render the requested template.
    """
    if 'userID' not in session:
        return redirect('/login')
    return render_template(destination)

#=======================
#         Routes
#=======================

@app.route('/login')
def routeToLogin():
    """GET /login - landing page."""
    return render_template('landing.html')

@app.route('/')
def redirectToHome():
    """Root redirects to /home."""
    return redirect('/home')

@app.route('/home')
def routeToIndex():
    """Main authenticated home page."""
    return validateLogin('index.html')

@app.route('/new')
def routeToNew():
    """Add new word page (authenticated)."""
    return validateLogin('new.html')

@app.route('/newRandom')
def routeToNewRandom():
    """Auto-suggested new word page (authenticated)."""
    return validateLogin('autonew.html')

@app.route('/practice')
def routeToPractice():
    """Practice page (authenticated)."""
    return validateLogin('practice.html')

@app.route('/cards')
def routeToCards():
    """Cards (visual) page (authenticated)."""
    return validateLogin('cards2.html')

@app.route('/forgotPassword')
def xd():
    """Placeholder forgot password page."""
    return render_template('xd.html')

@app.route('/makeCoffee')
def coffe():
    """Easter-egg returning HTTP teapot code in template."""
    return render_template('coffee.html', code=418)

@app.route('/register', methods=['POST'])
def register():
    """Register a new user.
    - Validates input presence
    - Ensures username uniqueness
    - Stores hashed password
    Returns redirect to login on success.
    """
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
    commit_and_update(conn)
    return redirect('/login')

@app.route('/login', methods=['POST'])
def login():
    """Authenticate user and create a session.
    Uses Werkzeug's password hash checking.
    """
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
        # persist theme in session; legacy code checks user.keys() for theme
        session['theme'] = user['theme'] if 'theme' in user.keys() else 'themeDark'
        return redirect('/home')
    else:

        return render_template('landing.html', login_error="Hibás felhasználónév vagy jelszó!")

@app.route('/logout', methods=['GET'])
def logout():
    """Clear session values on logout and show landing page with success message."""
    session.pop('userID', None)
    session.pop('theme', None)
    return render_template('landing.html', login_error="Sikeres kijelentkezés!")

@app.route('/add_word', methods=['POST'])
def add_word():
    """Add a new word for the logged in user.
    Accepts counts for statistics as optional form fields (used when importing).
    """
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
        commit_and_update(conn)
        return jsonify({"status": "success", "message": "Word added successfully!"}), 200
    else:
        return jsonify({"status": "error", "message": "Missing input fields!"}), 400

@app.route('/get_random_word', methods=['GET'])
def get_random_word():
    """Return a random word record for the logged in user.
    If the user has no words, returns an error JSON.
    """
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
    random_word = random.choice(words)
    word = random_word['word']
    translation = random_word['translation']
    word_id = random_word['id']
    return jsonify({"word": word, "translation": translation, "word_id": word_id}), 200

@app.route('/get_word_count', methods=['GET'])
def get_word_count():
    """Return how many words the user has. Used by cards UI to limit creation."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM words WHERE userID = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    if count == 0:
        return jsonify({"status": "error", "message": "No words found for the user!"}), 400
    return jsonify({"count": count})

@app.route('/update_score', methods=['POST'])
def update_score():
    """Increment the appropriate statistic column for a word.
    Expects JSON with word_id and status in {'fail','pass','failWithHelp','passWithHelp'}.
    """
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
    commit_and_update(conn)
    return jsonify({"status": "success", "message": "Score updated successfully!"}), 200

@app.route('/switch_translation', methods=['POST'])
def switch_translation():
    """Toggle translation direction for practice. Stored in session as boolean."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    # Default True means english -> hungarian
    session['translation_direction'] = not session.get('translation_direction', True)
    return jsonify({"status": "success", "message": "Translation direction switched!"}), 200

@app.route('/accept_word', methods=['POST'])
def accept_word():
    """Accept a suggested word and add it to the user's word list.
    Expects JSON {word, translation}
    """
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
    commit_and_update(conn)
    return jsonify({"status": "success", "message": "Word accepted and added!"}), 200

@app.route('/recommend_word', methods=['GET'])
def recommend_word():
    """Return a random dictionary entry for user to consider adding."""
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
    """Provide multiple-choice alternatives for a given word id.
    direction=True means english->hungarian so we pick other translations as distractors,
    direction=False means hungarian->english.
    The function excludes the correct word from distractor selection.
    """
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
    # Choose correct field based on requested direction
    correct = row['translation'] if direction else row['word']
    if direction:
        cursor.execute('SELECT translation FROM words WHERE userID=? AND id <> ?', (user_id, word_id))
        all_choices = [r['translation'] for r in cursor.fetchall()]
    else:
        cursor.execute('SELECT word FROM words WHERE userID=? AND id <> ?', (user_id, word_id))
        all_choices = [r['word'] for r in cursor.fetchall()]
    conn.close()
    # Shuffle and pick up to 3 distractors
    random.shuffle(all_choices)
    choices = all_choices[:3]
    # Add correct option and shuffle again so correct isn't always last
    choices.append(correct)
    random.shuffle(choices)
    return jsonify({
        "status": "success",
        "choices": choices,
        "correct": correct
    }), 200

@app.route('/get_learning_words', methods=['GET'])
def get_learning_words():
    """Return a list of word IDs the user should practice next.
    Logic:
      - Compute confidence index for every word
      - Negative confidence indices are prioritized (user struggles with them)
      - Ensure we return up to 10 items: always include negative ones, then fill with lowest confidence words
    """
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
    # If not enough negative words, include additional low-confidence words until we have up to 10
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
    """Return full word record (word + translation) by ID for the current user."""
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
    """Try to recommend a 'smart' word not already in the user's list.
    Strategy:
      - Compute average length of user's words (or use 5 as default)
      - Filter dictionary entries to those not already learned by the user
      - Sample up to 10 candidates and pick the one whose length is closest to the average
    This is a heuristic to suggest words of similar complexity to the user's current vocabulary.
    """
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT word FROM words WHERE userID = ?', (user_id,))
    user_words = set(row['word'].strip().lower() for row in cursor.fetchall())
    conn.close()
    avg_len = 5 if not user_words else sum(len(w) for w in user_words) / len(user_words)
    entries = load_dictionary()
    all_entries = [entry for entry in entries if entry.get("english", "").strip().lower() not in user_words]
    if not all_entries:
        return jsonify({"status": "error", "message": "No more new words to recommend!"}), 400
    sample_entries = random.sample(all_entries, min(10, len(all_entries)))
    def length_metric(entry):
        return abs(len(entry.get("english", "")) - avg_len)
    best_entry = min(sample_entries, key=length_metric)
    return jsonify({
        "status": "success",
        "word": best_entry.get("english", ""),
        "translation": best_entry.get("hungarian", "")
    })

@app.route('/edit')
def routeToEdit():
    """Words edit page (authenticated)."""
    if 'userID' not in session:
        return redirect('/login')
    return render_template('edit.html')

@app.route('/get_user_words', methods=['GET'])
def get_user_words():
    """Return all user's words as a list with id, word and translation.
    Used by the edit UI to populate the table.
    """
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
    """Delete a word owned by the current user."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    word_id = request.json.get('word_id')
    if not word_id:
        return jsonify({"status": "error", "message": "Missing word_id!"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM words WHERE id = ? AND userID = ?', (word_id, user_id))
    commit_and_update(conn)
    return jsonify({"status": "success", "message": "Word deleted successfully!"})

@app.route('/update_word', methods=['POST'])
def update_word():
    """Update a word and its translation. Checks user ownership."""
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
    commit_and_update(conn)
    return jsonify({"status": "success", "message": "Word updated successfully!"})

@app.route('/statistics')
def routeToStatistics():
    """Statistics dashboard (authenticated)."""
    if 'userID' not in session:
        return redirect('/login')
    return render_template('statistics.html')

@app.route('/get_word_statistics', methods=['GET'])
def get_word_statistics():
    """Return full statistics for all words owned by current user.
    Also computes confidence index on the server side for consistency with client.
    """
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
    """User settings page (authenticated)."""
    if 'userID' not in session:
        return redirect('/login')
    return render_template('settings.html')

@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    """Return basic user info (id, username) for the settings UI."""
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
    """Update username and/or password for the current user.
    - Checks for username uniqueness when changing username.
    - Hashes password before storing.
    """
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
        commit_and_update(conn)
        return jsonify({"status": "success", "message": "User updated successfully!"}), 200
    conn.close()
    return jsonify({"status": "error", "message": "Nothing to update!"}), 400

@app.context_processor
def inject_theme():
    """Make the current theme available in templates as `theme`."""
    theme = session.get('theme', 'themeDark')
    return dict(theme=theme)

@app.route('/set_theme', methods=['POST'])
def set_theme():
    """Set theme preference in session and persist in DB if user is logged in.
    Expects JSON {theme: "themeName"}.
    """
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
        commit_and_update(conn)
        return jsonify({"status": "success", "message": "Theme set", "theme": theme}), 200
    return jsonify({"status": "success", "message": "Theme set", "theme": theme}), 200

#==========================
#           Run
#==========================
if __name__ == '__main__':
    # On startup, verify DB integrity and initialize tables if needed.
    verify_db_hmac()
    init_db()
    app.run(host='0.0.0.0')
