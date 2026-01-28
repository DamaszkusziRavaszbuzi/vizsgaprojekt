#==========================
#         Imports
#==========================
from flask import Flask, request, jsonify, render_template, session, redirect
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import hashlib
import hmac
import threading
import time
import re
import random
import ollama 
from concurrent.futures import ThreadPoolExecutor
import argparse

#==========================
#          Init
#==========================
app = Flask(__name__)

# Secret key fallback is defined here for local development.
# For secure deployments, set the SECRET_KEY environment variable.
app.secret_key = os.environ.get('SECRET_KEY', 'furryfemboy')

DATABASE = 'database.db'
VERBOSE_LOGGING = True
HMAC_FILE = DATABASE + ".hmac"

# Ollama settings
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '180'))  # seconds for timeouts/polling

# Maximum concurrent workers for precaching at startup
PRECACHE_WORKERS = int(os.environ.get("PRECACHE_WORKERS", "4"))

def get_db_connection():
    """Open a sqlite3 connection using the configured DATABASE path.
    Uses Row factory so returned rows behave like dicts in code.
    """
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def deb_mes(msg):
    """Simple debug print controlled by VERBOSE_LOGGING."""
    if VERBOSE_LOGGING:
        print(msg)

def _hmac_key_bytes():
    """Build HMAC key bytes from environment or app secret."""
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
    """Verify HMAC on startup to detect database integrity changes."""
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
    """Commit a sqlite connection, close it and update HMAC afterwards."""
    conn.commit()
    conn.close()
    update_db_hmac()

def get_confidence_index(word_row):
    """Calculate a 'confidence index' for a word from its statistics."""
    return (word_row['pass'] * 2) + word_row['passWithHelp'] - word_row['fail'] - (word_row['failWithHelp'] * 2)

def init_db():
    """Create tables if they don't exist. Idempotent."""
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
    # Table to hold per-user suggestion buffers (random and smart).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suggestions (
            userID INTEGER PRIMARY KEY,
            random_buffer TEXT DEFAULT '[]',
            smart_buffer TEXT DEFAULT '[]',
            FOREIGN KEY (userID) REFERENCES users(id)
        );
    ''')
    commit_and_update(conn)

# =========================
#  Ollama / AI integration
# =========================

def _extract_response_from_obj(res):
    """
    Try to extract textual response from various shapes returned by ollama.generate:
    - dict-like: keys 'response','text','output','content'
    - attribute: res.response
    - plain string
    - repr containing response='...'
    Returns string or None.
    """
    if res is None:
        return None

    if isinstance(res, dict):
        for key in ('response', 'text', 'output', 'content'):
            val = res.get(key)
            if val:
                return str(val).strip()

    try:
        val = getattr(res, 'response', None)
        if val:
            return str(val).strip()
    except Exception:
        pass

    if isinstance(res, str):
        s = res.strip()
        if s:
            return s

    s = str(res)
    m = re.search(r"response\s*=\s*'([^']*)'", s, flags=re.DOTALL)
    if not m:
        m = re.search(r'response\s*=\s*"([^"]*)"', s, flags=re.DOTALL)
    if m:
        return m.group(1).strip()

    return None

def ollama_generate(prompt):
    """
    Generate using the ollama python client. Wait/poll for a textual response up to OLLAMA_TIMEOUT seconds.
    Returns the response text or None on failure/timeout.
    """
    start = time.time()
    try:
        first = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
    except Exception as e:
        deb_mes(f"ollama.generate initial call exception: {e}")
        return None

    # quick extraction
    resp = _extract_response_from_obj(first)
    if resp:
        return resp

    # If iterable/stream-like, try consuming chunks
    try:
        if hasattr(first, "__iter__") and not isinstance(first, (str, bytes, dict)):
            acc = []
            for chunk in first:
                try:
                    acc.append(str(chunk))
                except Exception:
                    pass
                combined = "".join(acc)
                r = _extract_response_from_obj(combined)
                if r:
                    return r
                if time.time() - start > OLLAMA_TIMEOUT:
                    deb_mes("ollama_generate: iterable stream timed out")
                    return None
    except Exception as e:
        deb_mes(f"ollama_generate: iter consume failed: {e}")

    # If the object contains an id, poll ollama.get(id) if available
    id_ = None
    if isinstance(first, dict):
        id_ = first.get("id")
    else:
        try:
            id_ = getattr(first, "id", None)
        except Exception:
            id_ = None

    ollama_get = getattr(ollama, "get", None)
    if id_ and callable(ollama_get):
        deb_mes(f"ollama_generate: polling ollama.get for id {id_}")
        while time.time() - start <= OLLAMA_TIMEOUT:
            try:
                polled = ollama_get(id_)
                r = _extract_response_from_obj(polled)
                if r:
                    return r
            except Exception as e:
                deb_mes(f"ollama.get exception while polling id {id_}: {e}")
            time.sleep(1.0)

    # Retry generate calls until timeout
    retry_sleep = 1.0
    while time.time() - start <= OLLAMA_TIMEOUT:
        try:
            deb_mes("ollama_generate: retrying ollama.generate to wait for completion")
            candidate = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
            r = _extract_response_from_obj(candidate)
            if r:
                return r
        except Exception as e:
            deb_mes(f"ollama.generate retry exception: {e}")
        time.sleep(retry_sleep)

    deb_mes("ollama_generate: timed out without receiving response")
    return None

def parse_ai_pairs(text):
    """
    Parse AI output into a list of (english, hungarian) pairs.
    Expected format: lines of "word:translation".
    Accepts minor numbering/punctuation. Returns list only if exactly 4 valid pairs are parsed.
    """
    if not text:
        return []
    pairs = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        line = re.sub(r'^\s*\d+\.\s*', '', line)  # remove leading numbering
        if ":" not in line:
            continue
        eng, hun = line.split(":", 1)
        eng = eng.strip().strip('.,;:')
        hun = hun.strip().strip('.,;:')
        if eng and hun:
            pairs.append({"word": eng, "translation": hun})
    if len(pairs) == 4:
        return pairs
    deb_mes(f"parse_ai_pairs: expected 4 pairs, got {len(pairs)}; raw: {text[:500]!r}")
    return []

def ai_generate_random_pairs(user_id):
    """
    Generate 4 random pairs via AI, then filter out words already present for the user.
    Returns list of pairs (may be less than 4 if filtering removed some) or None on failure.
    """
    out = ollama_generate(
        "Give me 4 completely random English word. Also give the words' translation in Hungarian, "
        "separate the word and it's translation by a \":\". Begin the next word in a new line. "
        "Don't think for long. Pick words that have exact translations."
    )
    if out is None:
        return None
    parsed = parse_ai_pairs(out)
    if not parsed:
        return None

    # Filter out words already in user's dictionary (case-insensitive)
    filtered = []
    existing = _get_user_words_set_lower(user_id)
    for p in parsed:
        if p['word'].strip().lower() in existing:
            deb_mes(f"ai_generate_random_pairs: removing already-known word '{p['word']}' for user {user_id}")
            continue
        filtered.append(p)
    # Return filtered list (may be empty)
    return filtered

def ai_generate_smart_pairs(user_id, user_words):
    """
    Generate 4 smart pairs via AI, using up to 40 sample words if user has many.
    Filter out words already present for the user before returning.
    """
    # If user has more than 40 words, pick 40 randomly for the prompt
    sample = user_words
    if len(user_words) > 40:
        sample = random.sample(user_words, 40)
    words_list = ", ".join(sample) if sample else ""
    prompt = (
        "A set of words is given. Give me 4 completely random English word that matches the commonness/level "
        "of the given words. Also give the words' translation in Hungarian, separate the word and the translation "
        "by a \":\". Begin the next word in a new line. The given words are: [{}]. "
        "Don't think for long. Pick words that have exact translations."
    ).format(words_list)

    out = ollama_generate(prompt)
    if out is None:
        return None
    parsed = parse_ai_pairs(out)
    if not parsed:
        return None

    # Filter against user's existing words
    filtered = []
    existing = _get_user_words_set_lower(user_id)
    for p in parsed:
        if p['word'].strip().lower() in existing:
            deb_mes(f"ai_generate_smart_pairs: removing already-known word '{p['word']}' for user {user_id}")
            continue
        filtered.append(p)
    return filtered

# =========================
#  Suggestion buffer and concurrency control
# =========================

generation_lock = threading.Lock()
generation_in_progress = {}  # keys are tuples (user_id, kind)

def mark_generation(user_id, kind, value):
    with generation_lock:
        generation_in_progress[(user_id, kind)] = bool(value)

def is_generating(user_id, kind):
    with generation_lock:
        return generation_in_progress.get((user_id, kind), False)

def get_suggestion_row(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT random_buffer, smart_buffer FROM suggestions WHERE userID = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def ensure_suggestion_row(user_id):
    """Ensure suggestions row exists for user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO suggestions (userID, random_buffer, smart_buffer) VALUES (?, ?, ?)', (user_id, '[]', '[]'))
    commit_and_update(conn)

def read_buffer(user_id, kind):
    """Return list of items for kind in ['random','smart']"""
    row = get_suggestion_row(user_id)
    if not row:
        return []
    raw = row['random_buffer'] if kind == 'random' else row['smart_buffer']
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []

def write_buffer(user_id, kind, items):
    """Overwrite buffer with items (list)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    col = 'random_buffer' if kind == 'random' else 'smart_buffer'
    cursor.execute(f'UPDATE suggestions SET {col} = ? WHERE userID = ?', (json.dumps(items, ensure_ascii=False), user_id))
    commit_and_update(conn)

def append_to_buffer(user_id, kind, items):
    """Append items (list) to existing buffer"""
    if not items:
        return
    # Filter items that are already in user's DB before appending
    existing = _get_user_words_set_lower(user_id)
    new_items = [i for i in items if i['word'].strip().lower() not in existing]
    if not new_items:
        deb_mes(f"append_to_buffer: nothing new to append for user {user_id} kind {kind}")
        return
    buf = read_buffer(user_id, kind)
    buf.extend(new_items)
    write_buffer(user_id, kind, buf)

def pop_from_buffer(user_id, kind):
    """
    Pop and return the first item from buffer that is NOT already present in user's dictionary.
    Removes any already-present items encountered in the process.
    Returns (item or None, buffer_was_non_empty_bool).
    """
    buf = read_buffer(user_id, kind)
    if not buf:
        return None, False

    existing = _get_user_words_set_lower(user_id)
    new_buf = []
    popped_item = None

    for idx, item in enumerate(buf):
        wlower = item.get('word', '').strip().lower()
        if wlower in existing:
            deb_mes(f"pop_from_buffer: removing already-known buffered word '{item.get('word')}' for user {user_id}")
            continue
        # first not-known item: return it, and keep remaining items
        popped_item = item
        new_buf = buf[idx+1:]
        break

    # If we popped nothing, all buffered items were known; clear buffer
    if popped_item is None:
        write_buffer(user_id, kind, [])
        return None, False

    # Write back remainder of buffer (already filtered)
    write_buffer(user_id, kind, new_buf)
    return popped_item, True

def _get_user_words_set_lower(user_id):
    """Return a set of user's words (lowercased, stripped) for quick membership checks."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT word FROM words WHERE userID = ?', (user_id,))
    rows = cur.fetchall()
    conn.close()
    return {r['word'].strip().lower() for r in rows if r['word']}

def generate_and_append_for_user(user_id, kind, user_words=None):
    """
    Generate items with AI and append to user's buffer of given kind.
    Respects generation_in_progress to avoid duplicates. Filters out already-known words.
    """
    if is_generating(user_id, kind):
        deb_mes(f"Generation already in progress for user {user_id} kind {kind}")
        return
    try:
        mark_generation(user_id, kind, True)
        if kind == 'random':
            new_items = ai_generate_random_pairs(user_id)
        else:
            new_items = ai_generate_smart_pairs(user_id, user_words or [])
        # If AI generation failed, do nothing
        if new_items is None:
            deb_mes(f"generate_and_append_for_user: AI generation failed for user {user_id} kind {kind}")
            return
        # If filtered out to empty list, nothing to append
        if not new_items:
            deb_mes(f"generate_and_append_for_user: no new unique items generated for user {user_id} kind {kind}")
            return
        append_to_buffer(user_id, kind, new_items)
    except Exception as e:
        deb_mes(f"Error generating/appending suggestions for user {user_id} kind {kind}: {e}")
    finally:
        mark_generation(user_id, kind, False)

# =========================
#  Precache on startup
# =========================

def precache_suggestions_for_all_users():
    """
    Pre-generate and append suggestions for both random and smart for every existing user.
    Uses a ThreadPoolExecutor to limit concurrency (PRECACHE_WORKERS).
    Runs in background as a daemon thread started from __main__.
    """
    deb_mes("Precache: starting precache for all users")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM users')
    user_rows = c.fetchall()
    conn.close()
    if not user_rows:
        deb_mes("Precache: no users found, skipping")
        return

    user_ids = [r['id'] for r in user_rows]
    deb_mes(f"Precache: found {len(user_ids)} users, starting ThreadPool with {PRECACHE_WORKERS} workers")

    def task_for_user(uid):
        try:
            ensure_suggestion_row(uid)
            # prepare user's current words for the smart prompt
            cconn = get_db_connection()
            cur = cconn.cursor()
            cur.execute('SELECT word FROM words WHERE userID = ?', (uid,))
            user_words = [r['word'] for r in cur.fetchall()]
            cconn.close()
            # Generate random suggestions and smart suggestions sequentially for this user
            generate_and_append_for_user(uid, 'random', None)
            generate_and_append_for_user(uid, 'smart', user_words)
        except Exception as e:
            deb_mes(f"Precache: exception for user {uid}: {e}")

    # Use ThreadPoolExecutor to limit concurrent AI calls
    with ThreadPoolExecutor(max_workers=PRECACHE_WORKERS) as executor:
        futures = [executor.submit(task_for_user, uid) for uid in user_ids]
        # Wait for all tasks to finish. This will block the background thread only.
        for f in futures:
            try:
                f.result()
            except Exception as e:
                deb_mes(f"Precache worker exception: {e}")

    deb_mes("Precache: completed precache for all users")

# =========================
#         Routes
# =========================

def validateLogin(destination):
    """Helper used by many routes that return templates."""
    if 'userID' not in session:
        return redirect('/login')
    return render_template(destination)

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
    return render_template('xd.html')

@app.route('/makeCoffee')
def coffe():
    """Easter-egg returning HTCPCP teapot code in template."""
    return render_template('coffee.html', code=418)

@app.route('/register', methods=['POST'])
def register():
    """Register a new user."""
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
    """Authenticate user and create a session."""
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
        ensure_suggestion_row(user['id'])
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
    """Add a new word for the logged in user."""
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
    """Return a random word record for the logged in user (from user's own words)."""
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
    """Increment the appropriate statistic column for a word."""
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
    session['translation_direction'] = not session.get('translation_direction', True)
    return jsonify({"status": "success", "message": "Translation direction switched!"}), 200

@app.route('/accept_word', methods=['POST'])
def accept_word():
    """Accept a suggested word and add it to the user's word list."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    word = request.json.get('word')
    translation = request.json.get('translation')
    if not word or not translation:
        return jsonify({"status": "error", "message": "Missing word or translation!"}), 400

    # Prevent inserting duplicates (case-insensitive)
    existing = _get_user_words_set_lower(user_id)
    if word.strip().lower() in existing:
        return jsonify({"status": "error", "message": "Word already exists in your dictionary."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO words (userID, word, translation, pass, passWithHelp, fail, failWithHelp)
        VALUES (?, ?, ?, 0, 0, 0, 0)
    ''', (user_id, word, translation))
    commit_and_update(conn)

    # Trigger background generation for both buffers so the user keeps seeing fresh suggestions.
    try:
        threading.Thread(target=generate_and_append_for_user, args=(user_id, 'random', None), daemon=True).start()
        conn2 = get_db_connection()
        cur2 = conn2.cursor()
        cur2.execute('SELECT word FROM words WHERE userID = ?', (user_id,))
        user_words = [r['word'] for r in cur2.fetchall()]
        conn2.close()
        threading.Thread(target=generate_and_append_for_user, args=(user_id, 'smart', user_words), daemon=True).start()
    except Exception as e:
        deb_mes(f"Error starting background generation threads: {e}")

    return jsonify({"status": "success", "message": "Word accepted and added!"}), 200

@app.route('/recommend_word', methods=['GET'])
def recommend_word():
    """
    Return a suggestion from the per-user random buffer.
    If buffer empty:
      - If generation in progress: respond with 'busy' so client can wait.
      - Otherwise, attempt synchronous generation (which will filter duplicates).
      - No fallback words are provided.
    """
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    ensure_suggestion_row(user_id)

    # Try to pop existing buffer (will skip/remove already-known words)
    item, used = pop_from_buffer(user_id, 'random')
    if used and item:
        # Start background replenishment (non-blocking)
        try:
            threading.Thread(target=generate_and_append_for_user, args=(user_id, 'random', None), daemon=True).start()
        except Exception as e:
            deb_mes(f"Error starting background generation thread after pop: {e}")
        return jsonify({"status": "success", "word": item['word'], "translation": item['translation']}), 200

    # Buffer empty
    if is_generating(user_id, 'random'):
        return jsonify({"status": "busy", "message": "AI is generating suggestions — please wait."}), 202

    # Start synchronous generation
    mark_generation(user_id, 'random', True)
    try:
        new_items = ai_generate_random_pairs(user_id)
        if new_items is None:
            return jsonify({"status": "error", "message": "AI is not available or returned invalid output."}), 503
        # new_items may be fewer than 4 after filtering; if empty -> treat as no suggestions
        if not new_items:
            return jsonify({"status": "error", "message": "AI returned only words already in your dictionary."}), 503
        write_buffer(user_id, 'random', new_items)
        item, _ = pop_from_buffer(user_id, 'random')
        if not item:
            return jsonify({"status": "error", "message": "Failed to prepare suggestions."}), 500
        try:
            threading.Thread(target=generate_and_append_for_user, args=(user_id, 'random', None), daemon=True).start()
        except Exception as e:
            deb_mes(f"Error starting background generation thread after sync fill: {e}")
        return jsonify({"status": "success", "word": item['word'], "translation": item['translation']}), 200
    finally:
        mark_generation(user_id, 'random', False)

@app.route('/recommend_smart_word', methods=['GET'])
def recommend_smart_word():
    """
    Return a suggestion from the per-user smart buffer.
    If user has >40 words, only a random sample of 40 is included in the prompt.
    Duplicates in buffer/AI output are filtered out.
    """
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    user_id = session['userID']
    ensure_suggestion_row(user_id)

    # Collect user's current words for prompt
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT word FROM words WHERE userID = ?', (user_id,))
    user_words = [r['word'] for r in cursor.fetchall()]
    conn.close()

    # Try to pop existing buffered suggestion (skips any that became duplicates)
    item, used = pop_from_buffer(user_id, 'smart')
    if used and item:
        try:
            threading.Thread(target=generate_and_append_for_user, args=(user_id, 'smart', user_words), daemon=True).start()
        except Exception as e:
            deb_mes(f"Error starting background generation thread after pop (smart): {e}")
        return jsonify({"status": "success", "word": item['word'], "translation": item['translation']}), 200

    if is_generating(user_id, 'smart'):
        return jsonify({"status": "busy", "message": "AI is generating suggestions — please wait."}), 202

    # Start synchronous generation
    mark_generation(user_id, 'smart', True)
    try:
        new_items = ai_generate_smart_pairs(user_id, user_words)
        if new_items is None:
            return jsonify({"status": "error", "message": "AI is not available or returned invalid output."}), 503
        if not new_items:
            return jsonify({"status": "error", "message": "AI returned only words already in your dictionary."}), 503
        write_buffer(user_id, 'smart', new_items)
        item, _ = pop_from_buffer(user_id, 'smart')
        if not item:
            return jsonify({"status": "error", "message": "Failed to prepare suggestions."}), 500
        try:
            threading.Thread(target=generate_and_append_for_user, args=(user_id, 'smart', user_words), daemon=True).start()
        except Exception as e:
            deb_mes(f"Error starting background generation thread after sync fill (smart): {e}")
        return jsonify({"status": "success", "word": item['word'], "translation": item['translation']}), 200
    finally:
        mark_generation(user_id, 'smart', False)

# The remainder of the routes are unchanged and operate on user's stored words/settings.
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
    commit_and_update(conn)
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
    commit_and_update(conn)
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
        commit_and_update(conn)
        return jsonify({"status": "success", "message": "Theme set", "theme": theme}), 200
    return jsonify({"status": "success", "message": "Theme set", "theme": theme}), 200

#==========================
#           Run
#==========================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the Flask app.")
    parser.add_argument('--precache', action='store_true', help='Start background precache of AI suggestions on startup')
    args = parser.parse_args()

    verify_db_hmac()
    init_db()

    # Start background precache for all users only when --precache is provided
    if args.precache:
        try:
            t = threading.Thread(target=precache_suggestions_for_all_users, daemon=True)
            t.start()
            deb_mes("Started background precache thread")
        except Exception as e:
            deb_mes(f"Failed to start precache thread: {e}")
    else:
        deb_mes("Precache skipped (run with --precache to enable)")

    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host='0.0.0.0', debug=debug_mode)
