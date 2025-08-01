import sqlite3
from flask import Flask, jsonify, render_template, request, session as flask_session, redirect, url_for, flash, send_from_directory, abort
from API_LLM import API_Call, get_available_models
import sys
import os
import json
from datetime import datetime
import csv
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initializing the flask app
app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY']

#### This is for selecting which model to use with the unified API
# Initialize the unified API
API = API_Call()
current_model = "gpt-4o"  # Default model

@app.route('/select-model', methods=['POST'])
def select_model():
    """Select a specific model to use"""
    data = request.json
    model_name = data.get('model_name')
    global current_model
    
    if model_name:
        current_model = model_name
        return jsonify({'message': f'Model updated to {model_name}'}), 200
    else:
        return jsonify({'error': 'No model specified'}), 400

@app.route('/get-available-models', methods=['GET'])
def get_models():
    """Return list of available models"""
    models = get_available_models()
    return jsonify({'models': models, 'current_model': current_model}), 200

# Legacy API selection for backward compatibility
@app.route('/select-api', methods=['POST'])
def select_api():
    """Legacy endpoint for API selection - now maps to model selection"""
    data = request.json
    api_name = data.get('api_name')
    global current_model
    
    # Map old API names to default models (expanded)
    api_model_mapping = {
        'API_Call_openai': 'gpt-4o',
        'API_Call_anthropic': 'claude-3-5-sonnet',
        'API_Call_google': 'gemini-1.5-pro',
        'API_Call_xai': 'grok-2-latest',
        # New expanded mappings
        'groq': 'groq-llama-3.1-70b',
        'perplexity': 'perplexity-llama-3.1-sonar-large',
        'mistral': 'mistral-large',
        'azure': 'azure-gpt-4o',
        'ollama': 'ollama-llama3.1',
        'cohere': 'cohere-command-r-plus',
        'together': 'together-llama-3.1-70b',
        'replicate': 'replicate-llama-3-70b',
        'deepseek': 'deepseek-chat',
        'ai21': 'ai21-jamba-1.5-large',
        'fireworks': 'fireworks-llama-3.1-70b',
        'cerebras': 'cerebras-llama-3.1-70b'
    }
    
    if api_name in api_model_mapping:
        current_model = api_model_mapping[api_name]
        return jsonify({'message': f'API updated to use {current_model}'}), 200
    else:
        return jsonify({'error': 'Invalid API name'}), 400


# database initialization for usernames, password conditions, and conversation history
# It first queries database to update passwords dictionary. 

def init_db():
    conn = sqlite3.connect('users.db')
    conn.text_factory = str
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 username TEXT NOT NULL UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 password TEXT NOT NULL,
                 message TEXT NOT NULL,
                 response TEXT NOT NULL,
                 timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (user_id) REFERENCES users (id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS passwords 
                 (password TEXT PRIMARY KEY, 
                 agent TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def add_passwords():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT password, agent FROM passwords')
    rows = c.fetchall()
    
    passwords = {password: agent for password, agent in rows}

    # These are the default passwords/agents from startup 
    static_passwords = {
        'hat': '1_TEMP_high',       #OpenAI models
        'lake': '1_TEMP_low',
        'music': '1_TEMP_mid',
        'red': '2_TEMP_high',
        'blue': '2_TEMP_low',
        'orange': '2_TEMP_mid',
        'apple': '1_PROMPT_high',
        'dingo': '1_PROMPT_low',
        'swim': '2_PROMPT_high',
        'run': '2_PROMPT_low',
        'jump': 'PILOT_1_temp_0_2',
        'skip': 'PILOT_1_temp_0_5',
        'hop': 'PILOT_1_temp_1_2',
        'purple': 'PILOT_1_temp_1_5',
        'tree': 'PILOT_1_temp_1',
        'flower': 'PILOT_2_temp_0_2',
        'butter': 'PILOT_2_temp_0_5',
        'drive': 'PILOT_2_temp_1_2',
        'walk': 'PILOT_2_temp_1_5',
        'sand': 'PILOT_2_temp_1',
        'cloud': 'anthropic_1_TEMP_high',   #Anthropic models
        'stone': 'anthropic_1_TEMP_low',
        'river': 'anthropic_1_TEMP_mid',
        'light': 'anthropic_2_TEMP_high',
        'grass': 'anthropic_2_TEMP_low',
        'trail': 'anthropic_2_TEMP_mid',
        'chair': 'anthropic_1_PROMPT_high',
        'table': 'anthropic_1_PROMPT_low',
        'shore': 'anthropic_2_PROMPT_high',
        'water': 'anthropic_2_PROMPT_low',
        'plant': 'anthropic_PILOT_1_temp_0_2',
        'creek': 'anthropic_PILOT_1_temp_0_4',
        'shell': 'anthropic_PILOT_1_temp_0_6',
        'field': 'anthropic_PILOT_1_temp_0_8',
        'grain': 'anthropic_PILOT_1_temp_1',
        'lemon': 'anthropic_PILOT_2_temp_0_2',
        'melon': 'anthropic_PILOT_2_temp_0_4',
        'baker': 'anthropic_PILOT_2_temp_0_6',
        'grove': 'anthropic_PILOT_2_temp_0_8',
        'cliff': 'anthropic_PILOT_2_temp_1',
        'chatPsych123': 'default',             #Random models
        'elderberry': 'experimental',
        'gpt4o': 'llm_gpt4o',
        'anthropic35': 'default_anthropic',
        'one_sentence35': 'one_sentence_claude',
        'socrates': 'socrates3'
    }

    for password, agent in static_passwords.items():
        c.execute('INSERT OR REPLACE INTO passwords (password, agent) VALUES (?, ?)', (password, agent))
       
    conn.commit()
    conn.close()

init_db()
add_passwords()

# Function to calculate joint log probability in models that can call logprobs
def calculate_joint_log_probability(logprobs):
    if not logprobs:
        return 0
    return sum(logprobs)

# For logging interactions.json, interactions_backup.csv
def log_user_data(data):

    try:
        with open('interactions.json', 'r') as f:
            file_content = f.read().strip()
            interactions = json.loads(file_content) if file_content else {"users": {}}
    except (FileNotFoundError, json.JSONDecodeError):
        interactions = {"users": {}}

    username = data['username']
    if username not in interactions["users"]:
        interactions["users"][username] = {
            "user_id": data.get('user_id', ''),
            "interactions": []
        }

    interaction_content = {k: v for k, v in data.items() if k not in ['username', 'user_id']}
    interaction_content['password'] = flask_session.get('password', 'N/A')

    if 'logprobs' in data:
        logprobs = data.get('logprobs', [])
        interaction_content['relativeSequenceJointLogProbability'] = calculate_joint_log_probability(logprobs)
        all_logprobs = [lp for interaction in interactions["users"][username]["interactions"] if 'logprobs' in interaction for lp in interaction['logprobs']]
        all_logprobs.extend(logprobs)
        interaction_content['relativeInteractionJointLogProbability'] = calculate_joint_log_probability(all_logprobs)

    interactions["users"][username]["interactions"].append(interaction_content)

    with open('interactions.json', 'w') as f:
        json.dump(interactions, f, indent=4)

    csv_headers = [
        "timestamp", "user_id", "username", "password", "interaction_type", 
        "message", "response", "model", "temperature", "logprobs"
    ]
    interaction_data = [
        data.get('timestamp', ''),
        data.get('user_id', ''),
        data.get('username', ''),
        flask_session.get('password', 'N/A'),
        data.get('interaction_type', ''),
        data.get('message', ''),
        data.get('response', ''),
        data.get('model', ''),
        data.get('temperature', ''),
        data.get('logprobs', [])
    ]

    csv_file = 'interactions_backup.csv'
    write_headers = not os.path.exists(csv_file)

    with open(csv_file, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if write_headers:
            writer.writerow(csv_headers)
        writer.writerow(interaction_data)
   
def add_user(username):
    conn = sqlite3.connect('users.db')
    conn.text_factory = str
    c = conn.cursor()
    c.execute('INSERT INTO users (username) VALUES (?)', (username,))
    conn.commit()
    conn.close()

def add_message(user_id, password, message, response, model, temperature, prompt_tokens, completion_tokens, total_tokens, logprobs_list):
    conn = sqlite3.connect('users.db')
    conn.text_factory = str
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_id, password, message, response) VALUES (?, ?, ?, ?)', 
              (user_id, password, message, response))
    conn.commit()
    conn.close()
    log_user_data({
        'user_id': user_id,
        'username': flask_session.get('username'),
        'interaction_type': 'message',
        'message': message,
        'response': response,
        'model': model,
        'temperature': temperature,
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens': total_tokens,
        'logprobs': logprobs_list,
        'timestamp': str(datetime.now())
    })

# For conversation history in the API calls
def get_messages(user_id, password):
    conn = sqlite3.connect('users.db')
    conn.text_factory = str
    conversation = []
    c = conn.cursor()
    c.execute('SELECT * FROM messages WHERE user_id = ? AND password = ? ORDER BY timestamp', (user_id, password))
    messages = c.fetchall()
    for message in messages:
        conversation.append({"role": "user", "content": message[3]})
        conversation.append({"role": "assistant", "content": message[4]})
    conn.close()
    return conversation

# MAIN flask app route for chatPsych
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        if user:
            user_id = user[0]
        else:
            c.execute('INSERT INTO users (username) VALUES (?)', (username,))
            user_id = c.lastrowid
            conn.commit()
        c.execute('SELECT agent FROM passwords WHERE password = ?', (password,))
        agent = c.fetchone()
        if agent:
            flask_session['user_id'] = user_id
            flask_session['username'] = username
            flask_session['password'] = password
            flask_session['agent'] = agent[0]
            API.update_agent(f"agents/{agent[0]}.json")
            flash('', 'success')
            conn.close()
            return redirect(url_for('chat'))
        else:
            flash('Invalid password', 'error')
            conn.close()
            return redirect(url_for('login'))
    return render_template('login.html')

# CHAT route 
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
    show_popup = openai_api_key is None or anthropic_api_key is None

    if 'username' not in flask_session:
        return redirect(url_for('login'))

    try:
        agent = flask_session.get('agent', 'default')
        API.update_agent(f"agents/{agent}.json")
        conversation = get_messages(flask_session['user_id'], flask_session['password'])

        if request.method == 'POST':
            message = request.form.get('message')
            if not message:
                flash('Message cannot be empty', 'error')
                return jsonify({'error': 'Message cannot be empty'}), 400
            
            # Use the agent's model primarily, only fall back to global model if agent doesn't specify one
            model = API.agent_data.get("model") or current_model or "gpt-4o"
            try:
                conversation, prompt_tokens, completion_tokens, total_tokens, logprobs_list = API.thinkAbout(message, conversation, model=model)
                response = conversation[-1]["content"]
            except Exception as e:
                app.logger.error(f"Error processing message: {e}")
                return jsonify({'error': 'Error processing message'}), 500

            user_id = flask_session['user_id']
            password = flask_session['password']
            add_message(user_id, password, message, str(response), model, API.agent_data.get("temperature", 1), prompt_tokens, completion_tokens, total_tokens, logprobs_list)
            return jsonify({'response': response})

        # Get timer settings for the template
        timer_duration = int(os.environ.get('TIMER_DURATION_MINUTES', '10'))
        return render_template('chat.html', username=flask_session['username'], messages=conversation, show_popup=show_popup, timer_duration=timer_duration)
    except Exception as ex:
        app.logger.error(f"Unexpected error occurred: {ex}")
        return jsonify({'error': 'Unexpected error occurred'}), 500

#### Researcher access routes
@app.route('/researcher', methods=['POST'])
def researcher_login():
    researcher_username = request.form['researcher_username']
    researcher_password = request.form['researcher_password']
    if authenticate_researcher(researcher_username, researcher_password):
        flask_session['researcher'] = True
        return jsonify({'success': True}), 200
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/research_dashboard', methods=['GET'])
def research_dashboard():
    if not flask_session.get('researcher'):
        return redirect(url_for('researcher_login'))
    return render_template('research_dashboard.html')

def authenticate_researcher(researcher_username, researcher_password):
    return (researcher_username == os.environ.get('researcher_username') and 
            researcher_password == os.environ.get('researcher_password'))

# These are both for loading in Agent JSON files and reviewing the conditions in the researcher access
AGENTS_FOLDER = os.path.join(os.path.dirname(__file__), 'agents')
@app.route('/list-json-files')
def list_json_files():
    files = [f for f in os.listdir(AGENTS_FOLDER) if f.endswith('.json')]
    return jsonify(files)

@app.route('/get-file-content')
def get_file_content():
    filename = request.args.get('name')
    try:
        if filename and filename.endswith('.json'):
            return send_from_directory(AGENTS_FOLDER, filename)
        else:
            return 'Invalid file name', 400
    except FileNotFoundError:
        return 'File not found', 404

# This is for creating Agent conditions in the researcher access
@app.route('/create-json', methods=['POST'])
def create_json_file():
    data = request.json
    filename = data["filename"]
    
    # ToDo -> I might validate the filename here to avoid injections

    with open(f'agents/{filename}.json', 'w') as jsonfile:
        json.dump(data, jsonfile, indent=2)

    return jsonify({"message": "File created successfully"}), 201

# This is for updating the condition passwords in the researcher access
def update_password_dict():
    global passwords
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT password, agent FROM passwords')
    rows = c.fetchall()
    passwords = {password: agent for password, agent in rows}
    conn.close()

add_passwords()
update_password_dict()

@app.route('/update-passwords', methods=['POST'])
def update_passwords():
    data = request.json
    password = data.get('password')
    agent = data.get('agent')
    
    if not password or not agent:
        return jsonify({'error': 'Invalid data'}), 400

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO passwords (password, agent) VALUES (?, ?)', (password, agent))
        conn.commit()
        conn.close()

        update_password_dict()
        
        return jsonify({'message': 'Password updated successfully'}), 200
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500

# This is for reviewing conditions with their passwords in researcher access
@app.route('/get-passwords', methods=['GET'])
def get_passwords():
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    query = "SELECT * FROM passwords"
    cursor.execute(query)

    passwords = [{"agent": row[0], "password": row[1]} for row in cursor.fetchall()]

    connection.close()
    
    return jsonify(passwords)

# This is for local download of data files in researcher access
@app.route('/download/<filename>')
def download_file(filename):
    directory = '.'  # Specifies root directory

    if not os.path.exists(os.path.join(directory, filename)):
        abort(404)  

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    if not os.path.exists('download_log.json'):
        with open('download_log.json', 'w') as log_file:
            log_file.write('')

    with open('download_log.json', 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(directory, filename, as_attachment=True)

# Timer settings routes
@app.route('/get-timer-settings', methods=['GET'])
def get_timer_settings():
    """Get current timer settings"""
    timer_settings = {
        'duration_minutes': int(os.environ.get('TIMER_DURATION_MINUTES', '10'))
    }
    return jsonify(timer_settings)

@app.route('/update-timer-settings', methods=['POST'])
def update_timer_settings():
    """Update timer settings"""
    data = request.json
    duration_minutes = data.get('duration_minutes', 10)
    
    # Validate duration (between 1 and 120 minutes)
    if not isinstance(duration_minutes, int) or duration_minutes < 1 or duration_minutes > 120:
        return jsonify({'error': 'Duration must be between 1 and 120 minutes'}), 400
    
    # Store settings in environment variables (in a real app, you'd use a database)
    os.environ['TIMER_DURATION_MINUTES'] = str(duration_minutes)
    
    return jsonify({'message': 'Timer settings updated successfully'})

# URL configuration routes
@app.route('/get-url-settings', methods=['GET'])
def get_url_settings():
    """Get current URL settings"""
    url_settings = {
        'quit_url': os.environ.get('QUIT_URL', 'https://www.prolific.com/'),
        'redirect_url': os.environ.get('REDIRECT_URL', 'https://adelaideuniwide.qualtrics.com/jfe/form/SV_cuyJvIsumG4zjMy')
    }
    return jsonify(url_settings)

@app.route('/update-url-settings', methods=['POST'])
def update_url_settings():
    """Update URL settings"""
    data = request.json
    quit_url = data.get('quit_url', '')
    redirect_url = data.get('redirect_url', '')
    
    # Validate URLs
    if not quit_url or not redirect_url:
        return jsonify({'error': 'Both quit_url and redirect_url are required'}), 400
    
    try:
        # Basic URL validation
        from urllib.parse import urlparse
        quit_parsed = urlparse(quit_url)
        redirect_parsed = urlparse(redirect_url)
        
        if not all([quit_parsed.scheme, quit_parsed.netloc]) or not all([redirect_parsed.scheme, redirect_parsed.netloc]):
            return jsonify({'error': 'Invalid URL format. URLs must include protocol (http:// or https://)'}), 400
    except Exception as e:
        return jsonify({'error': 'Invalid URL format'}), 400
    
    # Store settings in environment variables
    os.environ['QUIT_URL'] = quit_url
    os.environ['REDIRECT_URL'] = redirect_url
    
    return jsonify({'success': True, 'message': 'URL settings updated successfully'})

@app.route('/get-redirect-urls', methods=['GET'])
def get_redirect_urls():
    """API endpoint for the chat interface to get current redirect URLs"""
    return jsonify({
        'quit_url': os.environ.get('QUIT_URL', 'https://www.prolific.com/'),
        'redirect_url': os.environ.get('REDIRECT_URL', 'https://adelaideuniwide.qualtrics.com/jfe/form/SV_cuyJvIsumG4zjMy')
    })

if __name__ == '__main__':
    pass