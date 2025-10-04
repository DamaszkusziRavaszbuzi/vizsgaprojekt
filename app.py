
#==========================
#         Imports
#==========================

from flask import Flask, request, jsonify, render_template, session, redirect
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash 
import random

#==========================
#          Init
#==========================

app = Flask(__name__)

app.secret_key = 'ILoveHotGayFurryFemboys'

DATABASE = 'database.db'

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
            password TEXT NOT NULL
        );
    ''')

    # Create words table with foreign key reference to users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userID INTEGER NOT NULL,
            word TEXT NOT NULL,
            translation TEXT NOT NULL,
            definition TEXT,
            origin TEXT NOT NULL, 
            date DATE DEFAULT (CURRENT_DATE),
            pass INTEGER DEFAULT 0,
            passWithHelp INTEGER DEFAULT 0,
            fail INTEGER DEFAULT 0,
            failWithHelp INTEGER DEFAULT 0,
            FOREIGN KEY (userID) REFERENCES users(id)
        );
    ''')

    conn.commit()
    conn.close()




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

    return jsonify({"status": "success", "message": "User registered successfully!"}), 201




@app.route('/login', methods=['POST'])
def login():
    """Endpoint to login a user."""
    username = request.form.get('username')
    password = request.form.get('password')

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()

    if user and (user[2] == password):  # user[2] is the password
        # Store userID in session
        session['userID'] = user[0]  # user[0] is the user ID
        return jsonify({"status": "success", "message": "Login successful!"}), 200
    else:
        return jsonify({"status": "error", "message": "Invalid credentials!"}), 400

@app.route('/logout', methods=['POST'])
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
    definition = request.form.get('definition')  # can be None
    origin = "user"
    date = request.form.get('date', 0)  # Default to current date
    passCount = request.form.get('pass', 0)  # Default to 0
    passWithHelp = request.form.get('passWithHelp', 0)  # Default to 0
    failCount = request.form.get('fail', 0)  # Default to 0
    failWithHelp = request.form.get('failWithHelp', 0)  # Default to 0

    # Debugging: Print out all the form values
    debMes(f"Received word: {word}")
    debMes(f"Received translation: {translation}")
    debMes(f"Received definition: {definition}")
    debMes(f"Received origin: {origin}")
    debMes(f"Received date: {date}")
    debMes(f"Received passCount: {passCount}")
    debMes(f"Received passWithHelp: {passWithHelp}")
    debMes(f"Received failCount: {failCount}")
    debMes(f"Received failWithHelp: {failWithHelp}")

    if word and translation:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO words (userID, word, translation, definition, origin, date, pass, passWithHelp, fail, failWithHelp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, word, translation, definition, origin, date, passCount, passWithHelp, failCount, failWithHelp))

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



#==========================
#           Run
#==========================

if __name__ == '__main__':
    init_db()  # Initialize the database with the tables
    app.run(debug=True)

