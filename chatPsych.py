import sqlite3
from flask import Flask, jsonify, render_template, request, session as flask_session, redirect, url_for, flash, send_from_directory, send_file, abort
from API_LLM import API_Call, get_available_models
import sys
import os
import json
import random
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
        'onesentence': 'default',
        'openai': 'openai_default',
        'google': 'google_default',           
        'anthropic': 'anthropic_default',
        'socrates': 'socrates'
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
            return redirect(url_for('survey'))
        else:
            flash('Invalid password', 'error')
            conn.close()
            return redirect(url_for('login'))
    return render_template('login.html')

# SURVEY route - users must complete survey before accessing chat
@app.route('/survey', methods=['GET', 'POST'])
def survey():
    if 'username' not in flask_session:
        return redirect(url_for('login'))
    
    # Check if user has already completed the survey
    if flask_session.get('survey_completed'):
        return redirect(url_for('chat'))
    
    if request.method == 'POST':
        # Handle survey submission
        try:
            # Get survey configuration to determine which fields to collect
            survey_config = load_survey_config()
            
            # Collect survey data dynamically based on configuration
            survey_data = collect_dynamic_survey_data(request.form, survey_config)
            
            # Add standardized survey completion data
            survey_end_timestamp = str(datetime.now())
            survey_data.update({
                'user_id': flask_session['user_id'],
                'username': flask_session['username'],
                'password': flask_session['password'],
                'survey_start_timestamp': flask_session.get('survey_start_timestamp', ''),
                'survey_end_timestamp': survey_end_timestamp,
                'survey_completed': 'yes',
                'timestamp': survey_end_timestamp  # Keep for backward compatibility
            })
            
            # Log survey completion data
            log_survey_data(survey_data)
            
            # Mark survey as completed
            flask_session['survey_completed'] = True
            
            return jsonify({'success': True, 'redirect_url': url_for('chat')}), 200
            
        except Exception as e:
            app.logger.error(f"Error processing survey: {e}")
            return jsonify({'error': 'Error processing survey'}), 500
    
    # GET request - show survey form and log survey start
    try:
        # Log survey start
        log_survey_start(flask_session['username'], flask_session['password'], flask_session['user_id'])
    except Exception as e:
        app.logger.error(f"Error logging survey start: {e}")
    
    quit_redirection_link = os.environ.get('QUIT_URL', 'https://www.prolific.com/')
    
    # Check if dynamic survey configuration exists
    survey_config = load_survey_config()
    if survey_config:
        # Generate dynamic survey HTML
        try:
            html_content = generate_survey_html_content(survey_config)
            return html_content, 200, {'Content-Type': 'text/html'}
        except Exception as e:
            app.logger.error(f"Error generating dynamic survey: {e}")
            # Fall back to static template on error
            return render_template('survey.html', quit_redirection_link=quit_redirection_link)
    else:
        # Use static template if no configuration exists
        return render_template('survey.html', quit_redirection_link=quit_redirection_link)

# Function to log survey data to dedicated survey files
def log_survey_data(data):
    """Log survey responses to dedicated survey JSON and CSV files"""
    try:
        # Load existing survey data
        try:
            with open('survey.json', 'r') as f:
                file_content = f.read().strip()
                survey_data = json.loads(file_content) if file_content else {"survey_responses": []}
        except (FileNotFoundError, json.JSONDecodeError):
            survey_data = {"survey_responses": []}

        # Create survey entry with standardized structure
        survey_entry = {
            'username': data.get('username', ''),
            'password': data.get('password', ''),
            'user_id': data.get('user_id', ''),
            'survey_start_timestamp': data.get('survey_start_timestamp', ''),
            'survey_end_timestamp': data.get('survey_end_timestamp', ''),
            'survey_completed': data.get('survey_completed', 'no'),
            'interaction_type': 'survey'
        }
        
        # Add all other survey fields dynamically
        for key, value in data.items():
            if key not in ['username', 'password', 'user_id', 'survey_start_timestamp', 'survey_end_timestamp', 'survey_completed']:
                survey_entry[key] = value

        # Add to survey responses list
        survey_data["survey_responses"].append(survey_entry)

        # Save to survey JSON
        with open('survey.json', 'w') as f:
            json.dump(survey_data, f, indent=4)

        # Create standardized CSV headers
        csv_headers = [
            "username", "password", "user_id", "survey_start_timestamp", 
            "survey_end_timestamp", "survey_completed", "interaction_type"
        ]
        csv_data = [
            survey_entry.get('username', ''),
            survey_entry.get('password', ''),
            survey_entry.get('user_id', ''),
            survey_entry.get('survey_start_timestamp', ''),
            survey_entry.get('survey_end_timestamp', ''),
            survey_entry.get('survey_completed', ''),
            'survey'
        ]
        
        # Add all other survey fields dynamically to headers and data
        for key, value in survey_entry.items():
            if key not in csv_headers:
                csv_headers.append(key)
                csv_data.append(value)

        csv_file = 'survey.csv'
        write_headers = not os.path.exists(csv_file)

        with open(csv_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if write_headers:
                writer.writerow(csv_headers)
            writer.writerow(csv_data)
            
    except Exception as e:
        app.logger.error(f"Error logging survey data: {e}")

# Function to log survey start
def log_survey_start(username, password, user_id):
    """Log when a user starts the survey"""
    try:
        survey_start_data = {
            'username': username,
            'password': password,
            'user_id': user_id,
            'survey_start_timestamp': str(datetime.now()),
            'survey_end_timestamp': '',
            'survey_completed': 'no',
            'interaction_type': 'survey_start'
        }
        
        # Store in session for later completion
        flask_session['survey_start_timestamp'] = survey_start_data['survey_start_timestamp']
        
    except Exception as e:
        app.logger.error(f"Error logging survey start: {e}")

def load_survey_config():
    """Load survey configuration from file, return None if not found"""
    try:
        with open('survey_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        app.logger.error(f"Error loading survey config: {e}")
        return None

def collect_dynamic_survey_data(form_data, survey_config):
    """Collect survey data dynamically based on configuration"""
    survey_data = {}
    
    if not survey_config:
        # Fallback to static field collection
        return {
            'age': form_data.get('age'),
            'gender': form_data.get('gender'),
            'tech_enjoy': form_data.get('tech_enjoy'),
            'share_opinion': form_data.get('share_opinion'),
            'free_text_response': form_data.get('free_text_response')
        }
    
    sections = survey_config.get('sections', {})
    
    # Collect demographics data
    if sections.get('demographics', {}).get('enabled', False):
        demographics_fields = sections['demographics'].get('fields', {})
        if demographics_fields.get('age', {}).get('enabled', False):
            survey_data['age'] = form_data.get('age')
        if demographics_fields.get('gender', {}).get('enabled', False):
            survey_data['gender'] = form_data.get('gender')
    
    # Collect Likert scale data
    if sections.get('likert', {}).get('enabled', False):
        items = sections['likert'].get('items', [])
        for i, item in enumerate(items):
            field_name = f"likert_item_{i}"
            if field_name in form_data:
                survey_data[f"likert_{i}_{item[:30]}"] = form_data.get(field_name)
    
    # Collect free text data
    if sections.get('freetext', {}).get('enabled', False):
        questions = sections['freetext'].get('questions', [])
        for i, question_config in enumerate(questions):
            field_name = f"free_text_response_{i}"
            if field_name in form_data:
                survey_data[field_name] = form_data.get(field_name)
    
    # Collect any other form fields not already captured
    for key, value in form_data.items():
        if key not in survey_data and value:
            survey_data[key] = value
    
    return survey_data

# CHAT route 
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'username' not in flask_session:
        return redirect(url_for('login'))
    
    # Check if user has completed the survey
    if not flask_session.get('survey_completed'):
        return redirect(url_for('survey'))

    openai_api_key = os.environ.get('OPENAI_API_KEY')
    anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
    show_popup = openai_api_key is None or anthropic_api_key is None

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

# Survey data download routes
@app.route('/download-survey-json')
def download_survey_json():
    """Download survey.json file"""
    filename = 'survey.json'
    directory = '.'

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

@app.route('/download-survey-csv')
def download_survey_csv():
    """Download survey.csv file"""
    filename = 'survey.csv'
    directory = '.'

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

# Survey Configuration Routes
@app.route('/save-survey-config', methods=['POST'])
def save_survey_config():
    """Save survey configuration to file"""
    try:
        config = request.json
        
        # Validate configuration
        validation_error = validate_survey_config(config)
        if validation_error:
            return jsonify({'success': False, 'error': validation_error}), 400
        
        # Save configuration to JSON file
        with open('survey_config.json', 'w') as f:
            json.dump(config, f, indent=4)
        
        # Generate updated survey.html based on configuration
        try:
            generate_survey_html(config)
        except Exception as e:
            app.logger.error(f"Error generating survey HTML: {e}")
            # Don't fail the save if HTML generation fails
        
        return jsonify({'success': True, 'message': 'Survey configuration saved successfully'})
    except Exception as e:
        app.logger.error(f"Error saving survey config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def validate_survey_config(config):
    """Validate survey configuration structure"""
    if not isinstance(config, dict):
        return "Configuration must be a valid JSON object"
    
    # Check required fields
    if 'title' not in config:
        return "Survey title is required"
    
    # Validate sections if they exist
    sections = config.get('sections', {})
    if sections:
        # Validate demographics section
        if sections.get('demographics', {}).get('enabled', False):
            demo_fields = sections['demographics'].get('fields', {})
            if not demo_fields:
                return "Demographics section is enabled but has no fields configured"
        
        # Validate likert section
        if sections.get('likert', {}).get('enabled', False):
            likert_items = sections['likert'].get('items', [])
            if not likert_items:
                return "Likert section is enabled but has no items configured"
        
        # Validate freetext section
        if sections.get('freetext', {}).get('enabled', False):
            freetext_questions = sections['freetext'].get('questions', [])
            if not freetext_questions:
                return "Free text section is enabled but has no questions configured"
    
    return None  # No validation errors

@app.route('/get-survey-config', methods=['GET'])
def get_survey_config():
    """Get current survey configuration"""
    try:
        with open('survey_config.json', 'r') as f:
            config = json.load(f)
        return jsonify(config)
    except FileNotFoundError:
        return jsonify(None)
    except Exception as e:
        app.logger.error(f"Error loading survey config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/reset-survey-config', methods=['POST'])
def reset_survey_config():
    """Reset survey to default configuration"""
    try:
        # Remove custom configuration file
        if os.path.exists('survey_config.json'):
            os.remove('survey_config.json')
        
        # Remove custom uploaded files
        upload_dir = 'static/uploads'
        if os.path.exists(upload_dir):
            for filename in ['information_form.pdf', 'consent_form.pdf']:
                filepath = os.path.join(upload_dir, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
        
        return jsonify({'success': True, 'message': 'Survey configuration reset to default'})
    except Exception as e:
        app.logger.error(f"Error resetting survey config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/survey-system-status', methods=['GET'])
def survey_system_status():
    """Get status of survey system for debugging"""
    try:
        status = {
            'has_custom_config': os.path.exists('survey_config.json'),
            'config_readable': False,
            'uploaded_files': {},
            'static_template_exists': os.path.exists('templates/survey.html'),
            'survey_js_exists': os.path.exists('static/js/survey.js')
        }
        
        # Check if config is readable
        if status['has_custom_config']:
            try:
                with open('survey_config.json', 'r') as f:
                    config = json.load(f)
                status['config_readable'] = True
                status['config_sections'] = list(config.get('sections', {}).keys())
            except Exception:
                status['config_readable'] = False
        
        # Check uploaded files
        upload_dir = 'static/uploads'
        if os.path.exists(upload_dir):
            for filename in ['information_form.pdf', 'consent_form.pdf']:
                filepath = os.path.join(upload_dir, filename)
                status['uploaded_files'][filename] = os.path.exists(filepath)
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/preview-survey', methods=['POST'])
def preview_survey():
    """Generate survey preview HTML"""
    try:
        config = request.json
        html = generate_survey_html_content(config, preview=True)
        return html, 200, {'Content-Type': 'text/html'}
    except Exception as e:
        return f"Error generating preview: {str(e)}", 500

@app.route('/download-form-file/<file_type>')
def download_form_file(file_type):
    """Download uploaded form files"""
    try:
        if file_type not in ['information', 'consent']:
            abort(404)
        
        filename = f"{file_type}_form.pdf"
        filepath = os.path.join('static', 'uploads', filename)
        
        if not os.path.exists(filepath):
            abort(404)
        
        return send_file(filepath, as_attachment=True, download_name=f"{file_type}_form.pdf")
    except Exception as e:
        app.logger.error(f"Error downloading form file: {e}")
        abort(500)

@app.route('/upload-form-file', methods=['POST'])
def upload_form_file():
    """Upload information sheet or consent form files"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        file_type = request.form.get('type')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Validate file type
        if not file_type or file_type not in ['information', 'consent']:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        # Validate file extension and content type
        if not (file and file.filename.lower().endswith('.pdf') and 
                file.content_type == 'application/pdf'):
            return jsonify({'success': False, 'error': 'Only PDF files are allowed'}), 400
        
        # Validate file size (max 10MB)
        file.seek(0, 2)  # Seek to end of file
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            return jsonify({'success': False, 'error': 'File size too large (max 10MB)'}), 400
        
        # Create uploads directory if it doesn't exist
        upload_dir = 'static/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file with type-based naming (prevents directory traversal)
        filename = f"{file_type}_form.pdf"
        filepath = os.path.join(upload_dir, filename)
        
        # Save the file
        file.save(filepath)
        
        # Verify the file was saved correctly
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File upload failed'}), 500
        
        return jsonify({'success': True, 'filename': filename})
            
    except Exception as e:
        app.logger.error(f"Error uploading form file: {e}")
        return jsonify({'success': False, 'error': 'File upload failed'}), 500

def generate_survey_html(config):
    """Generate survey.html file based on configuration"""
    try:
        html_content = generate_survey_html_content(config)
        
        # Write to survey.html template
        with open('templates/survey.html', 'w') as f:
            f.write(html_content)
            
    except Exception as e:
        app.logger.error(f"Error generating survey HTML: {e}")
        raise

def generate_survey_html_content(config, preview=False):
    """Generate the actual HTML content for the survey"""
    # This is a comprehensive function to generate the survey HTML
    # based on the configuration object
    
    # Check if PDF files exist
    info_file_exists = os.path.exists('static/uploads/information_form.pdf')
    consent_file_exists = os.path.exists('static/uploads/consent_form.pdf')
    
    # Build download links only if files exist
    download_links = ""
    if info_file_exists or consent_file_exists:
        download_links = '<div class="form-downloads">'
        if info_file_exists:
            if preview:
                download_links += '<a href="#" class="download-link">📄 Download Information Sheet</a>'
            else:
                download_links += '<a href="/download-form-file/information" class="download-link">📄 Download Information Sheet</a>'
        if consent_file_exists:
            if preview:
                download_links += '<a href="#" class="download-link">📄 Download Consent Form</a>'
            else:
                download_links += '<a href="/download-form-file/consent" class="download-link">📄 Download Consent Form</a>'
        download_links += '</div>'
    
    # Handle template syntax for preview vs production
    if preview:
        css_link = '/static/css/styles.css'
        js_link = '/static/js/survey.js'
        quit_link_var = 'window.quitRedirectionLink = "#";'
    else:
        css_link = '{{ url_for(\'static\', filename=\'css/styles.css\') }}'
        js_link = '{{ url_for(\'static\', filename=\'js/survey.js\') }}'
        quit_link_var = 'window.quitRedirectionLink = "{{ quit_redirection_link }}";'
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{config.get('title', 'Survey Form')}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="{css_link}">
</head>
<body class="survey-page">
    <!-- Survey Consent Popup -->
    <div id="consent-popup" class="survey-consent-popup">
        <div class="survey-popup-content">
            <h2>{config.get('information', {}).get('title', 'Information and Consent Form')}</h2>
            <div class="consent-content">
                {format_consent_content(config.get('information', {}).get('content', ''))}
            </div>
            
            {download_links}
            
            <button id="consent-agree-btn" class="survey-btn survey-btn-agree">Agree</button>
            <button id="consent-quit-btn" class="survey-btn survey-btn-quit">Quit</button>
        </div>
    </div>

    <!-- Survey Quit Confirmation Popup -->
    <div id="quit-confirm-popup" class="survey-quit-confirm-popup survey-hidden">
        <div class="survey-popup-content">
            <h3>Are you sure you want to quit participation in this study?</h3>
            <button id="quit-confirm-yes-btn" class="survey-btn survey-btn-quit">Yes, Quit</button>
            <button id="quit-confirm-no-btn" class="survey-btn survey-btn-cancel">No, Go Back</button>
        </div>
    </div>

    <div class="survey-container">
        <div class="survey-header">
            <h1>{config.get('title', 'Survey Form')}</h1>
        </div>
        
        <div class="survey-content">
            <form id="survey-form">
'''
    
    # Add sections based on configuration
    sections = config.get('sections', {})
    settings = config.get('settings', {})
    randomize_items = settings.get('randomizeItems', False)
    
    # Handle both old and new section formats
    # Process all sections dynamically
    for section_id, section_config in sections.items():
        if not section_config.get('enabled', False):
            continue
            
        section_type = section_config.get('type', section_id.split('-')[0])
        
        if section_type == 'demographics':
            html += generate_demographics_section(section_config)
        elif section_type == 'likert':
            html += generate_likert_section(section_config, randomize_items)
        elif section_type == 'freetext':
            html += generate_freetext_section(section_config, randomize_items)
        elif section_type == 'custom':
            html += generate_custom_section(section_config)
    
    html += '''
                <div class="submit-section">
                    <button type="submit" id="submit-btn">Submit Survey</button>
                </div>
            </form>

            <!-- Next Button Section -->
            <div class="survey-section" id="next-button-section">
                <p id="next-disclaimer">
                    Next button will appear once all sections of the form are completed.
                </p>
                <div style="text-align: center;">
                    <button type="button" class="survey-hidden" id="next-btn">Next</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Make quit redirection link available to external JS
        ''' + quit_link_var + '''
    </script>
    <script src="''' + js_link + '''"></script>
</body>
</html>'''
    
    return html

def format_consent_content(content):
    """Format consent content with proper HTML"""
    if not content:
        return "<p>Please read the information about this study.</p>"
    
    # Convert line breaks to HTML and wrap in paragraph tags
    lines = content.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            if line.startswith('•') or line.startswith('-'):
                if not formatted_lines or not formatted_lines[-1].startswith('<ul>'):
                    formatted_lines.append('<ul>')
                formatted_lines.append(f'<li>{line[1:].strip()}</li>')
            else:
                if formatted_lines and formatted_lines[-1] == '<ul>':
                    formatted_lines.append('</ul>')
                formatted_lines.append(f'<p>{line}</p>')
    
    if formatted_lines and formatted_lines[-1] == '<ul>':
        formatted_lines.append('</ul>')
    
    return '\n'.join(formatted_lines)

def generate_demographics_section(config):
    """Generate demographics section HTML"""
    html = f'''
        <!-- Demographics Section -->
        <div class="survey-section" id="demographics-section">
            <div class="survey-section-title">{config.get('title', 'Demographics')}</div>
'''
    
    fields = config.get('fields', {})
    
    # Age field
    if fields.get('age', {}).get('enabled', False):
        age_config = fields['age']
        html += f'''
            <label for="demographics-age">Age:</label>
            <input type="number" id="demographics-age" name="age" min="{age_config.get('min', 18)}" max="{age_config.get('max', 99)}" required><br><br>
'''
    
    # Gender field
    if fields.get('gender', {}).get('enabled', False):
        gender_config = fields['gender']
        html += '''
            <label for="demographics-gender">Gender:</label>
            <select id="demographics-gender" name="gender" required>
                <option value="">Select...</option>
'''
        for option in gender_config.get('options', ['Female', 'Male', 'Other', 'Prefer not to say']):
            html += f'                <option value="{option.lower().replace(" ", "_")}">{option}</option>\n'
        
        html += '            </select><br><br>\n'
    
    html += '        </div>\n'
    return html

def generate_likert_section(config, randomize_items=False):
    """Generate Likert scale section HTML"""
    html = f'''
        <!-- Likert Scale Section -->
        <div class="survey-section" id="likert-scale-section">
            <div class="survey-section-title">{config.get('title', 'Likert Scale Items')}</div>
            <table class="survey-likert-table" style="width:100%;">
                <tr>
                    <th>Statement</th>
'''
    
    # Add scale headers
    scale_labels = config.get('scaleLabels', 'Strongly Disagree,Disagree,Neutral,Agree,Strongly Agree').split(',')
    for label in scale_labels:
        html += f'                    <th>{label.strip()}</th>\n'
    
    html += '                </tr>\n'
    
    # Get items and randomize if requested
    items = config.get('items', [])
    if randomize_items and items:
        items = items.copy()  # Create a copy to avoid modifying the original
        random.shuffle(items)
    
    # Add items
    for i, item in enumerate(items):
        html += f'''                <tr>
                    <td>{item}</td>
'''
        item_name = f"likert_item_{i}"
        for j, _ in enumerate(scale_labels):
            required = 'required' if j == 0 else ''
            html += f'                    <td><input type="radio" name="{item_name}" value="{j+1}" {required}></td>\n'
        html += '                </tr>\n'
    
    html += '''            </table>
        </div>
    '''
    return html

def generate_freetext_section(config, randomize_items=False):
    """Generate free text section HTML"""
    html = f'''
        <!-- Free Form Text Section -->
        <div class="survey-section" id="free-form-text-section">
            <div class="survey-section-title">{config.get('title', 'Free Form Text')}</div>
'''
    
    # Get questions and randomize if requested
    questions = config.get('questions', [])
    if randomize_items and questions:
        questions = questions.copy()  # Create a copy to avoid modifying the original
        random.shuffle(questions)
    
    for i, question_config in enumerate(questions):
        question = question_config.get('question', '')
        rows = question_config.get('rows', 4)
        field_id = f"free-text-response-{i}"
        
        html += f'''            <label for="{field_id}">{question}</label><br>
            <textarea id="{field_id}" name="free_text_response_{i}" rows="{rows}" cols="50" required></textarea><br><br>
'''
    
    html += '        </div>\n'
    return html

def generate_custom_section(config):
    """Generate custom section HTML"""
    html = f'''
        <!-- Custom Section -->
        <div class="survey-section" id="custom-section">
            <div class="survey-section-title">{config.get('title', 'Custom Section')}</div>
'''
    
    # Add description if provided
    description = config.get('description', '')
    if description:
        html += f'            <div class="survey-section-description">{description}</div>\n'
    
    # Generate fields
    fields = config.get('fields', [])
    for i, field_config in enumerate(fields):
        field_id = f"custom-field-{i}"
        field_label = field_config.get('label', f'Field {i+1}')
        field_type = field_config.get('type', 'text')
        field_options = field_config.get('options', '')
        field_required = field_config.get('required', False)
        required_attr = 'required' if field_required else ''
        
        html += f'            <label for="{field_id}">{field_label}</label><br>\n'
        
        if field_type == 'textarea':
            html += f'            <textarea id="{field_id}" name="{field_id}" rows="4" {required_attr}></textarea><br><br>\n'
        elif field_type == 'select':
            html += f'            <select id="{field_id}" name="{field_id}" {required_attr}>\n'
            for option in field_options.split(','):
                option = option.strip()
                if option:
                    html += f'                <option value="{option}">{option}</option>\n'
            html += '            </select><br><br>\n'
        elif field_type == 'radio':
            for j, option in enumerate(field_options.split(',')):
                option = option.strip()
                if option:
                    radio_id = f"{field_id}-{j}"
                    html += f'            <input type="radio" id="{radio_id}" name="{field_id}" value="{option}" {required_attr}>\n'
                    html += f'            <label for="{radio_id}">{option}</label><br>\n'
            html += '<br>\n'
        elif field_type == 'checkbox':
            for j, option in enumerate(field_options.split(',')):
                option = option.strip()
                if option:
                    checkbox_id = f"{field_id}-{j}"
                    html += f'            <input type="checkbox" id="{checkbox_id}" name="{field_id}" value="{option}">\n'
                    html += f'            <label for="{checkbox_id}">{option}</label><br>\n'
            html += '<br>\n'
        else:  # text, number, email
            html += f'            <input type="{field_type}" id="{field_id}" name="{field_id}" {required_attr}><br><br>\n'
    
    html += '        </div>\n'
    return html

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)