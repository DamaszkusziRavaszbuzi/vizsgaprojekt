#==========================
#         Imports
#==========================

from flask import Flask, request, jsonify, render_template, session, redirect
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash 
import random
import requests
import os
import json

#==========================
#          Init
#==========================

app = Flask(__name__)

app.secret_key = 'furryfemboy'

DATABASE = 'database.db'

def get_confidence_index(word_row):
    # word_row: (id, userID, word, translation, pass, passWithHelp, fail, failWithHelp)
    return (word_row[4] * 2) + (word_row[5]) - (word_row[6]) - (word_row[7] * 2)

verboseLogging = True
def debMes(msg):  # debug message
    if verboseLogging:
        print(msg)


def init_db():
    """Initialize the database with the required tables."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            theme TEXT DEFAULT 'themeDark'
        );
    ''')

    # Create words table with foreign key reference to users
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


DICTIONARY_FILE = "dictionary.json"

def get_random_dictionary_entry():
    with open(DICTIONARY_FILE, "r", encoding='utf-8') as f:
        data = json.load(f)
        entries = data["dictionary"]
    return random.choice(entries)

def get_random_english_word():
    entry = get_random_dictionary_entry()
    return entry["english"]

def translate_to_hungarian(word):
    # We'll use the dictionary.json now, not an API
    with open(DICTIONARY_FILE, "r", encoding='utf-8') as f:
        data = json.load(f)
        for entry in data["dictionary"]:
            if entry["english"].lower() == word.lower():
                return entry["hungarian"]
    return ""

#==========================
#          Routes
#==========================


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
    if 'userID' not in session:  # Check if the user is logged in
        return redirect('/login')  # Redirect to login if not logged in
    return redirect('/home')

@app.route('/home')
def routeToIndex():
    if 'userID' not in session:  # Check if the user is logged in
        return redirect('/login')  # Redirect to login if not logged in
    return render_template('index.html')

@app.route('/new')
def routeToNew():
    if 'userID' not in session:  # Check if the user is logged in
        return redirect('/login')  # Redirect to login if not logged in
    return render_template('new.html')

@app.route('/newRandom')
def routeToNewRandom():
    if 'userID' not in session:  # Check if the user is logged in
        return redirect('/login')  # Redirect to login if not logged in
    return render_template('autonew.html')

@app.route('/practice')
def routeToPractice():
    if 'userID' not in session:  # Check if the user is logged in
        return redirect('/login')  # Redirect to login if not logged in
    return render_template('practice.html')

@app.route('/cards')
def routeToCards():
    if 'userID' not in session:  # Check if the user is logged in
        return redirect('/login')  # Redirect to login if not logged in
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
    """Endpoint to register a new user."""
    username = request.form.get('username')
    password = request.form.get('password')

    # Check if user already exists
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    if user:
        return jsonify({"status": "error", "message": "Username already exists!"}), 400

    # Hash the password and store the user in the database
    hashed_password = password
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()

    return redirect('/login')




@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()

    if user and (user[2] == password):
        session['userID'] = user[0]
        # user schema: (id, username, password, [theme]) -- theme at index 3 if added
        # if theme column exists:
        if len(user) > 3 and user[3]:
            session['theme'] = user[3]
        else:
            session['theme'] = 'themeDark'
        return redirect('/home')
    else:
        error_msg = "Hibás felhasználónév vagy jelszó!"
        return render_template('landing.html', login_error=error_msg)

@app.route('/logout', methods=['GET','POST'])
def logout():
    """Endpoint to logout a user."""
    session.pop('userID', None)  # Remove userID from session
    return jsonify({"status": "success", "message": "Logout successful!"}), 200

@app.route('/add_word', methods=['POST'])
def add_word():
    """Endpoint to add a word for a user."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400
    
    user_id = session['userID']  # Get userID from session
    debMes(f"Received userID: {user_id}")  # debug logging
    word = request.form.get('word')
    translation = request.form.get('translation')
    passCount = request.form.get('pass', 0)  # Default to 0
    passWithHelp = request.form.get('passWithHelp', 0)  # Default to 0
    failCount = request.form.get('fail', 0)  # Default to 0
    failWithHelp = request.form.get('failWithHelp', 0)  # Default to 0

    # Debugging: Print out all the form values
    debMes(f"Received word: {word}")
    debMes(f"Received translation: {translation}")
    debMes(f"Received passCount: {passCount}")
    debMes(f"Received passWithHelp: {passWithHelp}")
    debMes(f"Received failCount: {failCount}")
    debMes(f"Received failWithHelp: {failWithHelp}")

    if word and translation:
        conn = sqlite3.connect(DATABASE)
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
    """Fetch a random word from the user's dictionary."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    # Check if the user has any words in their dictionary
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM words WHERE userID = ?', (user_id,))
    words = cursor.fetchall()

    if not words:
        return jsonify({"status": "error", "message": "No words found for the user!"}), 400

    # Choose a random word
    random_word = random.choice(words)
    word = random_word[2]  # Word
    translation = random_word[3]  # Translation
    word_id = random_word[0] #ID
    debMes(word_id)
    debMes(random_word[0])

    # Return the word and translation
    return jsonify({"word": word, "translation": translation, "word_id": word_id}), 200

@app.route('/get_word_count', methods=['GET'])
def get_word_count():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    # Check if the user has any words in their dictionary
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM words WHERE userID = ?', (user_id,))
    words = cursor.fetchall()
    wordCount = len(words)

    if not words:
        return jsonify({"status": "error", "message": "No words found for the user!"}), 400
    return jsonify({"count": wordCount})

@app.route('/update_score', methods=['POST'])
def update_score():
    """Update the user's score for the word."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    word_id = request.json.get('word_id')
    status = request.json.get('status')  # Can be 'pass', 'fail', 'failWithHelp', etc.

    if not word_id:
        return jsonify({"status": "error", "message": "Missing word_id!"}), 400
    if not status:
        return jsonify({"status": "error", "message": "Missing status!"}), 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Update the word's score based on the status
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
    """Toggle the translation direction."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    # You can track the current direction in the session or database
    # For simplicity, let's toggle a session variable for this example
    if 'translation_direction' in session:
        session['translation_direction'] = not session['translation_direction']
    else:
        session['translation_direction'] = True  # Default to word-to-translation

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



    passCount = 0
    passWithHelp = 0
    failCount = 0
    failWithHelp = 0

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO words (userID, word, translation, pass, passWithHelp, fail, failWithHelp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, word, translation, passCount, passWithHelp, failCount, failWithHelp))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Word accepted and added!"}), 200

@app.route('/recommend_word', methods=['GET'])
def recommend_word():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    entry = get_random_dictionary_entry()
    english_word = entry["english"]
    translation = entry["hungarian"]

    return jsonify({
        "status": "success",
        "word": english_word,
        "translation": translation
    })

@app.route('/get_choices', methods=['POST'])
def get_choices():
    """
    Given a word_id and direction, return the correct answer and 3 random other answers.
    direction: true (word->translation), false (translation->word)
    """
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    data = request.get_json()
    word_id = data.get('word_id')
    direction = data.get('direction') # true: word->translation, false: translation->word

    if word_id is None or direction is None:
        return jsonify({"status": "error", "message": "Missing parameters!"}), 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Get the correct answer
    cursor.execute('SELECT word, translation FROM words WHERE id=? AND userID=?', (word_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "Word not found!"}), 404

    correct = row[1] if direction else row[0]

    # Get all possible choices, excluding the correct one
    if direction:
        cursor.execute('SELECT translation FROM words WHERE userID=? AND id <> ?', (user_id, word_id))
        all_choices = [r[0] for r in cursor.fetchall()]
    else:
        cursor.execute('SELECT word FROM words WHERE userID=? AND id <> ?', (user_id, word_id))
        all_choices = [r[0] for r in cursor.fetchall()]
    conn.close()

    # Pick 3 random incorrect ones (or fewer if not enough)
    import random
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
    """Get a list of word_ids for learning mode (negative confidence, or lowest confidence)."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM words WHERE userID = ?', (user_id,))
    words = cursor.fetchall()
    conn.close()

    if not words:
        return jsonify({"status": "error", "message": "No words found for the user!"}), 400

    # Calculate confidenceIndex for each word
    word_infos = []
    for w in words:
        ci = get_confidence_index(w)
        word_infos.append({'word_id': w[0], 'confidenceIndex': ci})

    negative = [x for x in word_infos if x['confidenceIndex'] < 0]
    # If less than 5 negative, add up to 10 words with lowest confidenceIndex
    if len(negative) < 5:
        word_infos_sorted = sorted(word_infos, key=lambda x: x['confidenceIndex'])
        # avoid duplicates
        added = {w['word_id'] for w in negative}
        for w in word_infos_sorted:
            if len(negative) >= 10:
                break
            if w['word_id'] not in added:
                negative.append(w)
                added.add(w['word_id'])

    # Only return the word_ids
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

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM words WHERE id = ? AND userID = ?', (word_id, user_id))
    word = cursor.fetchone()
    conn.close()
    if not word:
        return jsonify({"status": "error", "message": "Word not found!"}), 404

    return jsonify({
        "status": "success",
        "word_id": word[0],
        "word": word[2],
        "translation": word[3]
    })

import math

@app.route('/recommend_smart_word', methods=['GET'])
def recommend_smart_word():
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']

    # Get user's current English words
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT word FROM words WHERE userID = ?', (user_id,))
    user_words = set(row[0].strip().lower() for row in cursor.fetchall())
    conn.close()

    # Calculate average length
    if not user_words:
        avg_len = 5  # fallback, e.g., if user has no words yet
    else:
        avg_len = sum(len(w) for w in user_words) / len(user_words)

    # Get 10 random words from dictionary.json not already in user's list
    with open(DICTIONARY_FILE, "r", encoding='utf-8') as f:
        data = json.load(f)
        all_entries = [entry for entry in data["dictionary"] if entry["english"].strip().lower() not in user_words]

    if not all_entries:
        return jsonify({"status": "error", "message": "No more new words to recommend!"}), 400

    sample_entries = random.sample(all_entries, min(10, len(all_entries)))

    # Find the entry with length closest to avg_len
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
    if 'userID' not in session:  # Check if the user is logged in
        return redirect('/login')  # Redirect to login if not logged in
    return render_template('edit.html')

@app.route('/get_user_words', methods=['GET'])
def get_user_words():
    """Get all words for the current user."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, word, translation FROM words WHERE userID = ? ORDER BY word', (user_id,))
    words = cursor.fetchall()
    conn.close()

    return jsonify({
        "status": "success",
        "words": [{"id": w[0], "word": w[1], "translation": w[2]} for w in words]
    })

@app.route('/delete_word', methods=['POST'])
def delete_word():
    """Delete a word from the database."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    word_id = request.json.get('word_id')
    
    if not word_id:
        return jsonify({"status": "error", "message": "Missing word_id!"}), 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM words WHERE id = ? AND userID = ?', (word_id, user_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Word deleted successfully!"})

@app.route('/update_word', methods=['POST'])
def update_word():
    """Update a word in the database."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    word_id = request.json.get('word_id')
    new_word = request.json.get('word')
    new_translation = request.json.get('translation')
    
    if not all([word_id, new_word, new_translation]):
        return jsonify({"status": "error", "message": "Missing required fields!"}), 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE words 
        SET word = ?, translation = ? 
        WHERE id = ? AND userID = ?
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
    """Get all words with their statistics for the current user."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, word, translation, pass, passWithHelp, fail, failWithHelp 
        FROM words 
        WHERE userID = ? 
        ORDER BY word
    ''', (user_id,))
    words = cursor.fetchall()
    conn.close()

    word_stats = []
    for w in words:
        confidence_index = (w[3] * 2) + w[4] - w[5] - (w[6] * 2)
        word_stats.append({
            "id": w[0],
            "word": w[1],
            "translation": w[2],
            "pass": w[3],
            "passWithHelp": w[4],
            "fail": w[5],
            "failWithHelp": w[6],
            "confidenceIndex": confidence_index
        })

    return jsonify({
        "status": "success",
        "words": word_stats
    })

# Add the following routes somewhere after your existing routes (e.g., near the other page routes)

@app.route('/settings')
def routeToSettings():
    if 'userID' not in session:  # require login
        return redirect('/login')
    return render_template('settings.html')

@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    """Return the current user's username (for pre-filling the settings form)."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"status": "error", "message": "User not found!"}), 404

    return jsonify({"status": "success", "user": {"id": row[0], "username": row[1]}})

@app.route('/update_user', methods=['POST'])
def update_user():
    """Update the current user's username and/or password. userID remains unchanged."""
    if 'userID' not in session:
        return jsonify({"status": "error", "message": "User not logged in!"}), 400

    user_id = session['userID']
    data = request.get_json() or {}
    new_username = data.get('username', '').strip()
    new_password = data.get('password', '').strip()

    if not new_username and not new_password:
        return jsonify({"status": "error", "message": "Nothing to update!"}), 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # If username is changing, ensure it's not used by another user
    if new_username:
        cursor.execute('SELECT id FROM users WHERE username = ?', (new_username,))
        existing = cursor.fetchone()
        if existing and existing[0] != user_id:
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
        params.append(new_password)  # Note: your app stores plain passwords currently; adapt to hashing if desired

    if updates:
        params.append(user_id)
        query = f'UPDATE users SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(query, tuple(params))
        conn.commit()

    conn.close()
    return jsonify({"status": "success", "message": "User updated successfully!"}), 200

# --- Add / modify in your existing Flask app ---

# 1) When user logs in, read user's theme and set it in session


# 2) Inject theme into templates so you can use {{ theme }} in <link>
@app.context_processor
def inject_theme():
    # priority: session -> default
    theme = session.get('theme', 'themeDark')
    return dict(theme=theme)

# 3) Endpoint to set theme (updates DB if logged in, always stores to session)
@app.route('/set_theme', methods=['POST'])
def set_theme():
    data = request.get_json() or {}
    theme = data.get('theme')
    if not theme:
        return jsonify({"status": "error", "message": "Missing theme"}), 400

    # Save to session
    session['theme'] = theme

    # If user logged in, persist to DB
    if 'userID' in session:
        user_id = session['userID']
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        # Safe update even if column didn't exist; if you added column this will work
        cursor.execute('UPDATE users SET theme = ? WHERE id = ?', (theme, user_id))
        conn.commit()
        conn.close()

    return jsonify({"status": "success", "message": "Theme set", "theme": theme}), 200
#==========================
#           Run
#==========================

if __name__ == '__main__':
    init_db()  # Initialize the database with the tables
    app.run(host='0.0.0.0', debug=True)