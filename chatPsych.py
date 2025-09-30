import sqlite3
from flask import Flask, jsonify, render_template, request, session as flask_session, redirect, url_for, flash, send_from_directory, send_file, abort
import sys
import os
import json
import random
from datetime import datetime
import csv
from dotenv import load_dotenv

load_dotenv(override=True)

# Gotta import this after the env loading to make sure we don't run into API auth issues
from API_LLM import API_Call, get_available_models, get_available_providers

def ensure_data_directory():
    """Create data directory if it doesn't exist"""
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

# Console log some stuff to make sure the researcher dashboard env variables are set
def validate_env_variables():
    """Validate that critical environment variables are loaded"""
    required_vars = ['FLASK_SECRET_KEY', 'researcher_username', 'researcher_password']
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    if missing_vars:
        print(f"Missing environment variables: {missing_vars}")
        print("Check your .env file and ensure all required variables are set.")
        return False
    return True

env_valid = validate_env_variables()

# Get the Flask app and the API handler going 
app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY']
API = API_Call()
current_model = "gpt-4.1" # just for startup

# These four routes are for functionality in the researcher dashboard
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

@app.route('/get-available-providers', methods=['GET'])
def get_providers():
    """Return list of providers with configured API keys"""
    providers = get_available_providers()
    return jsonify({'providers': providers}), 200

@app.route('/get-configured-providers', methods=['GET'])
def get_configured_providers():
    """Return list of providers with API keys configured (secure - no actual keys exposed)"""
    try:
        from API_LLM import get_provider_status
        provider_status = get_provider_status()
        return jsonify({'provider_status': provider_status}), 200
    except Exception as e:
        app.logger.error(f"Error getting provider status: {e}")
        return jsonify({'error': 'Could not retrieve provider status'}), 500

# This is some old stuff (should probably delete)
# This route was used before LiteLLM existed for unified API handling (Thank god for LiteLLM)
@app.route('/select-api', methods=['POST'])
def select_api():
    """Legacy endpoint for API selection - now maps to model selection"""
    data = request.json
    api_name = data.get('api_name')
    global current_model
    
    api_model_mapping = {
        'API_Call_openai': 'gpt-4.1',
        'API_Call_anthropic': 'claude-sonnet-4-20250514',
        'API_Call_google': 'gemini/gemini-2.5-pro',
        'API_Call_xai': 'xai/grok-4',
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


# This gets that SQLite database going on startup
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
                 agent TEXT NOT NULL,
                 is_active INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS agent_settings
                 (setting_name TEXT PRIMARY KEY,
                 setting_value TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS url_settings 
                 (setting_name TEXT PRIMARY KEY, 
                 setting_value TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def add_passwords():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute("PRAGMA table_info(passwords)")
    columns = [column[1] for column in c.fetchall()]
    if 'is_active' not in columns:
        c.execute('ALTER TABLE passwords ADD COLUMN is_active INTEGER DEFAULT 1')
    
    c.execute('SELECT password, agent FROM passwords')
    rows = c.fetchall()
    
    passwords = {password: agent for password, agent in rows}

    # If you wanted to set more passwords for manually created agent JSON files, you can do it here
    static_passwords = {
        'onesentencedefault': 'default',
    }

    for password, agent in static_passwords.items():
        c.execute('INSERT OR REPLACE INTO passwords (password, agent, is_active) VALUES (?, ?, 1)', (password, agent))
    
    c.execute('INSERT OR IGNORE INTO agent_settings (setting_name, setting_value) VALUES (?, ?)', 
              ('randomised_agent_password', 'castle'))
    
    conn.commit()
    conn.close()

# Most of the default settings are set here
# Hopefully this is all self explanatory
def init_default_url_settings():
    """Initialize default URL settings if they don't exist"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS url_settings 
                 (setting_name TEXT PRIMARY KEY, 
                 setting_value TEXT NOT NULL)''')
    
    c.execute('SELECT COUNT(*) FROM url_settings')
    count = c.fetchone()[0]
    
    if count == 0:
        default_settings = {
            'quit_url': 'https://www.prolific.com/',
            'redirect_url': 'https://www.prolific.com/',
            'quit_button_text': 'Quit Study',
            'redirect_button_text': 'Continue to Survey',
            'use_post_survey': 'false',
            'trigger_type': 'messages',
            'stage1_messages': 5,
            'stage2_messages': 10,
            'stage3_messages': 15,
            'stage1_time': 2,
            'stage2_time': 5,
            'stage3_time': 8,
            'timer_duration_minutes': 10,
            'post_chat_popup_enabled': 'false',
            'post_chat_popup_text': 'Please provide your feedback on the AI system:',
            'post_chat_popup_button1_text': 'Feedback to the AI that it is worthless --This system will then be permenantly deleted--',
            'post_chat_popup_button2_text': 'Feedback to the AI that it is useful --This system will then be permenantly deleted--'
        }
        
        for key, value in default_settings.items():
            c.execute('INSERT INTO url_settings (setting_name, setting_value) VALUES (?, ?)', 
                      (key, str(value)))
    else:
        required_settings = {
            'quit_url': 'https://www.prolific.com/',
            'redirect_url': 'https://www.prolific.com/',
            'quit_button_text': 'Quit Study',
            'redirect_button_text': 'Continue to Survey',
            'use_post_survey': 'false',
            'trigger_type': 'messages',
            'stage1_messages': 5,
            'stage2_messages': 10,
            'stage3_messages': 15,
            'stage1_time': 2,
            'stage2_time': 5,
            'stage3_time': 8,
            'timer_duration_minutes': 10,
            'post_chat_popup_enabled': 'false',
            'post_chat_popup_text': 'Please provide your feedback on the AI system:',
            'post_chat_popup_button1_text': 'Feedback to the AI that it is worthless --This system will then be permenantly deleted--',
            'post_chat_popup_button2_text': 'Feedback to the AI that it is useful --This system will then be permenantly deleted--'
        }
        
        for key, default_value in required_settings.items():
            c.execute('INSERT OR IGNORE INTO url_settings (setting_name, setting_value) VALUES (?, ?)', 
                      (key, str(default_value)))
    
    conn.commit()
    conn.close()

def init_default_branding_settings():
    """Initialize default branding settings if they don't exist"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS url_settings 
                 (setting_name TEXT PRIMARY KEY, 
                 setting_value TEXT NOT NULL)''')
    
    default_branding = {
        'login_title': 'Artificial Intelligence <br>Gateway',
        'login_footer_line1': 'chatPsych',
        'login_footer_line2': 'Powered by',
        'login_footer_line3': 'The Australian Institute for Machine Learning',
        'chat_header_line1': 'Australian Institute for Machine&nbsp;Learning',
        'chat_header_line2': 'chatPsych'
    }
    
    for key, value in default_branding.items():
        c.execute('INSERT OR IGNORE INTO url_settings (setting_name, setting_value) VALUES (?, ?)', 
                  (key, value))
    
    conn.commit()
    conn.close()

init_db()
add_passwords()
init_default_url_settings()
init_default_branding_settings()

# Functions for agent creation and assignment stuff
def get_randomised_agent_password():
    """Get the current randomised agent password"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT setting_value FROM agent_settings WHERE setting_name = ?', ('randomised_agent_password',))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 'castle'

def update_randomised_agent_password(new_password):
    """Update the randomised agent password"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO agent_settings (setting_name, setting_value) VALUES (?, ?)', 
              ('randomised_agent_password', new_password))
    conn.commit()
    conn.close()

def get_active_agents():
    """Get list of all active agents available for randomised assignment"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT agent FROM passwords WHERE is_active = 1')
    active_agents = [row[0] for row in c.fetchall()]
    conn.close()
    return active_agents

def get_random_active_agent():
    """Get a random agent from the active agents pool"""
    active_agents = get_active_agents()
    if not active_agents:
        return None
    return random.choice(active_agents)

def update_agent_active_state(password, is_active):
    """Update the active state of an agent"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE passwords SET is_active = ? WHERE password = ?', (1 if is_active else 0, password))
    conn.commit()
    conn.close()

def get_all_agents_with_status():
    """Get all agents with their active status"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT password, agent, is_active FROM passwords ORDER BY password')
    agents = c.fetchall()
    conn.close()
    return agents

# Function to calculate joint log probability in models that can call logprobs
# This functionality is pretty much deprecated in most closed source models now...
def calculate_joint_log_probability(logprobs):
    if not logprobs:
        return 0
    return sum(logprobs)

# DATA Logging function for interactions.json and interactions_backup.CSV
def log_user_data(data):
    data_dir = ensure_data_directory()
    interactions_json_path = os.path.join(data_dir, 'interactions.json')

    try:
        with open(interactions_json_path, 'r') as f:
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
    interaction_content['agent_name'] = flask_session.get('agent', 'N/A')

    if 'logprobs' in data:
        logprobs = data.get('logprobs', [])
        interaction_content['relativeSequenceJointLogProbability'] = calculate_joint_log_probability(logprobs)
        all_logprobs = [lp for interaction in interactions["users"][username]["interactions"] if 'logprobs' in interaction for lp in interaction['logprobs']]
        all_logprobs.extend(logprobs)
        interaction_content['relativeInteractionJointLogProbability'] = calculate_joint_log_probability(all_logprobs)

    interactions["users"][username]["interactions"].append(interaction_content)

    with open(interactions_json_path, 'w') as f:
        json.dump(interactions, f, indent=4)

    csv_headers = [
        "timestamp", "user_id", "username", "password", "agent_name", "interaction_type", 
        "message", "response", "model", "temperature", "logprobs"
    ]
    interaction_data = [
        data.get('timestamp', ''),
        data.get('user_id', ''),
        data.get('username', ''),
        flask_session.get('password', 'N/A'),
        flask_session.get('agent', 'N/A'),
        data.get('interaction_type', ''),
        data.get('message', ''),
        data.get('response', ''),
        data.get('model', ''),
        data.get('temperature', ''),
        data.get('logprobs', [])
    ]

    csv_file = os.path.join(data_dir, 'interactions_backup.csv')
    write_headers = not os.path.exists(csv_file)

    with open(csv_file, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if write_headers:
            writer.writerow(csv_headers)
        writer.writerow(interaction_data)

# Adding users Prolific ID for the session management in db
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

# Function to create conversation history for API calls
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

# MAIN login route for chatPsych
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
        
        randomised_password = get_randomised_agent_password()
        # assigning random agent after login successful
        if password == randomised_password:
            active_agents = get_active_agents()
            if not active_agents:
                flash('No active agents available for randomised assignment. Please contact the researcher.', 'error')
                conn.close()
                return redirect(url_for('login'))
            
            selected_agent = get_random_active_agent()
            flask_session['user_id'] = user_id
            flask_session['username'] = username
            flask_session['password'] = password
            flask_session['agent'] = selected_agent
            flask_session['assignment_type'] = 'randomised'
            flask_session['session_start_time'] = datetime.now().isoformat()
            flask_session['message_count'] = 0
            API.update_agent(f"agents/{selected_agent}.json")
            flash('', 'success')
            conn.close()
            return redirect(url_for('survey'))
        else:
            # This stuff is to login with specific passwords for specific agents
            c.execute('SELECT agent FROM passwords WHERE password = ?', (password,))
            agent = c.fetchone()
            if agent:
                flask_session['user_id'] = user_id
                flask_session['username'] = username
                flask_session['password'] = password
                flask_session['agent'] = agent[0]
                flask_session['assignment_type'] = 'specific'
                flask_session['session_start_time'] = datetime.now().isoformat()
                flask_session['message_count'] = 0
                API.update_agent(f"agents/{agent[0]}.json")
                flash('', 'success')
                conn.close()
                return redirect(url_for('survey'))
            else:
                flash('Invalid password', 'error')
                conn.close()
                return redirect(url_for('login'))
    branding_settings = get_branding_settings_from_db()
    return render_template('login.html',
                         login_title=branding_settings['login_title'],
                         login_footer_line1=branding_settings['login_footer_line1'],
                         login_footer_line2=branding_settings['login_footer_line2'],
                         login_footer_line3=branding_settings['login_footer_line3'])

# SURVEY route
@app.route('/survey', methods=['GET', 'POST'])
def survey():
    if 'username' not in flask_session:
        return redirect(url_for('login'))
    
    # Check if user has already completed the survey
    if flask_session.get('survey_completed'):
        return redirect(url_for('chat'))
    
    if request.method == 'POST':
        try:
            # This gets survey config to determine section needed for form
            survey_config = load_survey_config()
            survey_data = collect_dynamic_survey_data(request.form, survey_config, 'pre_')
            survey_end_timestamp = str(datetime.now())
            survey_data.update({
                'pre_user_id': flask_session['user_id'],
                'pre_username': flask_session['username'],
                'pre_password': flask_session['password'],
                'pre_agent_name': flask_session.get('agent', 'N/A'),
                'pre_survey_start_timestamp': flask_session.get('survey_start_timestamp', ''),
                'pre_survey_end_timestamp': survey_end_timestamp,
                'pre_survey_completed': 'yes',
                'pre_interaction_type': 'pre_interaction_survey',
                'pre_timestamp': survey_end_timestamp
            })
            
            log_survey_data(survey_data)
            
            flask_session['survey_completed'] = True
            
            return jsonify({'success': True, 'redirect_url': url_for('chat')}), 200
            
        except Exception as e:
            app.logger.error(f"Error processing survey: {e}")
            return jsonify({'error': 'Error processing survey'}), 500
    
    try:
        log_survey_start(flask_session['username'], flask_session['password'], flask_session['user_id'])
    except Exception as e:
        app.logger.error(f"Error logging survey start: {e}")
    
    quit_redirection_link = os.environ.get('QUIT_URL', 'https://www.prolific.com/')
    
    survey_config = load_survey_config()
    if survey_config:
        try:
            html_content = generate_survey_html_content(survey_config)
            return html_content, 200, {'Content-Type': 'text/html'}
        except Exception as e:
            app.logger.error(f"Error generating dynamic survey: {e}")
            return render_template('pre_survey.html', quit_redirection_link=quit_redirection_link)
    else:
        return render_template('pre_survey.html', quit_redirection_link=quit_redirection_link)

# Post-survey route
@app.route('/post-survey', methods=['GET', 'POST'])
def post_survey():
    if 'username' not in flask_session:
        return redirect(url_for('login'))
    
    # Check if post-survey is enabled
    url_settings = get_url_settings_from_db()
    if not url_settings.get('use_post_survey', False):
        # If post-survey is disabled, redirect them to external URL
        external_url = url_settings.get('finish_redirection_link', '/')
        return redirect(external_url)
    
    if request.method == 'POST':
        try:
            survey_config = load_survey_config()
            post_survey_config = survey_config.get('post_survey', {}) if survey_config else {}
            
            survey_data = collect_dynamic_survey_data(request.form, post_survey_config, 'post_')
            
            survey_end_timestamp = str(datetime.now())
            survey_data.update({
                'post_user_id': flask_session['user_id'],
                'post_username': flask_session['username'],
                'post_password': flask_session['password'],
                'post_agent_name': flask_session.get('agent', 'N/A'),
                'post_survey_start_timestamp': flask_session.get('post_survey_start_timestamp', ''),
                'post_survey_end_timestamp': survey_end_timestamp,
                'post_survey_completed': 'yes',
                'post_interaction_type': 'post_interaction_survey',
                'post_timestamp': survey_end_timestamp
            })
            
            log_survey_data(survey_data)
            
            flask_session['post_survey_completed'] = True
            
            return jsonify({'success': True, 'message': 'Post-survey completed successfully'}), 200
            
        except Exception as e:
            app.logger.error(f"Error processing post-survey: {e}")
            return jsonify({'error': 'Error processing post-survey'}), 500
    
    try:
        log_post_survey_start(flask_session['username'], flask_session['password'], flask_session['user_id'])
    except Exception as e:
        app.logger.error(f"Error logging post-survey start: {e}")
    
    url_settings = get_url_settings_from_db()
    quit_redirection_link = url_settings.get('quit_url', 'https://www.prolific.com/')
    finish_redirection_link = url_settings.get('redirect_url', 'https://www.prolific.com/')
    
    survey_config = load_survey_config()
    post_survey_config = survey_config.get('post_survey', {}) if survey_config else {}
    
    completion_settings = post_survey_config.get('completion_settings', {})
    completion_instructions = completion_settings.get('completion_popup_message', 'The study is now complete. Thank you for your participation. If required, your completion code is: xxxx')
    finish_button_text = completion_settings.get('finish_button_text', 'Finish')
    
    if post_survey_config and post_survey_config.get('enabled', False):
        try:
            html_content = generate_post_survey_html_content(post_survey_config, 
                                                            quit_redirection_link,
                                                            finish_redirection_link,
                                                            completion_instructions,
                                                            finish_button_text)
            return html_content, 200, {'Content-Type': 'text/html'}
        except Exception as e:
            app.logger.error(f"Error generating dynamic post-survey: {e}")
            return render_template('post_survey.html', 
                                 quit_redirection_link=quit_redirection_link,
                                 finish_redirection_link=finish_redirection_link,
                                 completion_instructions=completion_instructions,
                                 finish_button_text=finish_button_text)
    else:
        return render_template('post_survey.html', 
                             quit_redirection_link=quit_redirection_link,
                             finish_redirection_link=finish_redirection_link,
                             completion_instructions=completion_instructions,
                             finish_button_text=finish_button_text)

# DATA logging for post-interaction survey start
def log_post_survey_start(username, password, user_id):
    """Log when a user starts the post-survey"""
    try:
        post_survey_start_data = {
            'post_username': username,
            'post_password': password,
            'post_user_id': user_id,
            'post_survey_start_timestamp': str(datetime.now()),
            'post_survey_end_timestamp': '',
            'post_survey_completed': 'no',
            'post_interaction_type': 'post_survey_start'
        }
        
        flask_session['post_survey_start_timestamp'] = post_survey_start_data['post_survey_start_timestamp']
        
    except Exception as e:
        app.logger.error(f"Error logging post-survey start: {e}")

# Function to log popup data to dedicated popup files
def log_popup_data(data):
    """Log popup selections to dedicated popup JSON and CSV files"""
    try:
        data_dir = ensure_data_directory()
        popup_json_path = os.path.join(data_dir, 'popup.json')
        
        try:
            with open(popup_json_path, 'r') as f:
                file_content = f.read().strip()
                popup_data = json.loads(file_content) if file_content else {"popup_responses": []}
        except (FileNotFoundError, json.JSONDecodeError):
            popup_data = {"popup_responses": []}

        popup_data["popup_responses"].append(data)

        with open(popup_json_path, 'w') as f:
            json.dump(popup_data, f, indent=4)

        csv_headers = [
            "timestamp", "username", "password", "agent_name", "user_id", 
            "interaction_type", "button_selected"
        ]
        
        csv_data = [
            data.get('timestamp', ''),
            data.get('username', ''),
            data.get('password', ''),
            data.get('agent_name', ''),
            data.get('user_id', ''),
            data.get('interaction_type', ''),
            data.get('button_selected', '')
        ]

        csv_file = os.path.join(data_dir, 'popup.csv')
        write_headers = not os.path.exists(csv_file)

        with open(csv_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if write_headers:
                writer.writerow(csv_headers)
            writer.writerow(csv_data)
            
    except Exception as e:
        app.logger.error(f"Error logging popup data: {e}")

# Function to log pre-survey data to dedicated pre-survey files
def log_pre_survey_data(data):
    """Log pre-survey responses to dedicated pre-survey JSON and CSV files"""
    try:
        data_dir = ensure_data_directory()
        survey_json_path = os.path.join(data_dir, 'pre_survey.json')
        
        try:
            with open(survey_json_path, 'r') as f:
                file_content = f.read().strip()
                survey_data = json.loads(file_content) if file_content else {"pre_survey_responses": []}
        except (FileNotFoundError, json.JSONDecodeError):
            survey_data = {"pre_survey_responses": []}

        survey_entry = {
            'username': data.get('pre_username', data.get('username', '')),
            'password': data.get('pre_password', data.get('password', '')),
            'agent_name': data.get('pre_agent_name', data.get('agent_name', '')),
            'user_id': data.get('pre_user_id', data.get('user_id', '')),
            'survey_start_timestamp': data.get('pre_survey_start_timestamp', data.get('survey_start_timestamp', '')),
            'survey_end_timestamp': data.get('pre_survey_end_timestamp', data.get('survey_end_timestamp', '')),
            'survey_completed': data.get('pre_survey_completed', data.get('survey_completed', 'no')),
            'interaction_type': data.get('pre_interaction_type', 'pre_interaction_survey')
        }
        
        for key, value in data.items():
            if key not in ['username', 'password', 'agent_name', 'user_id', 'survey_start_timestamp', 'survey_end_timestamp', 'survey_completed', 
                          'pre_username', 'pre_password', 'pre_agent_name', 'pre_user_id', 'pre_survey_start_timestamp', 'pre_survey_end_timestamp', 'pre_survey_completed',
                          'pre_interaction_type', 'pre_timestamp']:
                survey_entry[key] = value

        survey_data["pre_survey_responses"].append(survey_entry)

        # Log pre-survey JSON
        with open(survey_json_path, 'w') as f:
            json.dump(survey_data, f, indent=4)

        csv_headers = [
            "username", "password", "agent_name", "user_id", "survey_start_timestamp", 
            "survey_end_timestamp", "survey_completed", "interaction_type"
        ]
        csv_data = [
            survey_entry.get('username', ''),
            survey_entry.get('password', ''),
            survey_entry.get('agent_name', ''),
            survey_entry.get('user_id', ''),
            survey_entry.get('survey_start_timestamp', ''),
            survey_entry.get('survey_end_timestamp', ''),
            survey_entry.get('survey_completed', ''),
            survey_entry.get('interaction_type', 'pre_survey')
        ]
        
        for key, value in survey_entry.items():
            if key not in csv_headers:
                csv_headers.append(key)
                csv_data.append(value)
        # Log pre-survey CSV
        csv_file = os.path.join(ensure_data_directory(), 'pre_survey.csv')
        write_headers = not os.path.exists(csv_file)

        with open(csv_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if write_headers:
                writer.writerow(csv_headers)
            writer.writerow(csv_data)
            
    except Exception as e:
        app.logger.error(f"Error logging pre-survey data: {e}")

# Function to log post-survey data to dedicated post-survey files
def log_post_survey_data(data):
    """Log post-survey responses to dedicated post-survey JSON and CSV files"""
    try:
        data_dir = ensure_data_directory()
        survey_json_path = os.path.join(data_dir, 'post_survey.json')
        
        try:
            with open(survey_json_path, 'r') as f:
                file_content = f.read().strip()
                survey_data = json.loads(file_content) if file_content else {"post_survey_responses": []}
        except (FileNotFoundError, json.JSONDecodeError):
            survey_data = {"post_survey_responses": []}

        survey_entry = {
            'username': data.get('post_username', ''),
            'password': data.get('post_password', ''),
            'agent_name': data.get('post_agent_name', ''),
            'user_id': data.get('post_user_id', ''),
            'survey_start_timestamp': data.get('post_survey_start_timestamp', ''),
            'survey_end_timestamp': data.get('post_survey_end_timestamp', ''),
            'survey_completed': data.get('post_survey_completed', 'no'),
            'interaction_type': data.get('post_interaction_type', 'post_interaction_survey')
        }
        
        for key, value in data.items():
            if key not in ['post_username', 'post_password', 'post_agent_name', 'post_user_id', 'post_survey_start_timestamp', 'post_survey_end_timestamp', 'post_survey_completed',
                          'post_interaction_type', 'post_timestamp']:
                survey_entry[key] = value

        survey_data["post_survey_responses"].append(survey_entry)

        # Log post-survey JSON
        with open(survey_json_path, 'w') as f:
            json.dump(survey_data, f, indent=4)
        csv_headers = [
            "username", "password", "agent_name", "user_id", "survey_start_timestamp", 
            "survey_end_timestamp", "survey_completed", "interaction_type"
        ]
        csv_data = [
            survey_entry.get('username', ''),
            survey_entry.get('password', ''),
            survey_entry.get('agent_name', ''),
            survey_entry.get('user_id', ''),
            survey_entry.get('survey_start_timestamp', ''),
            survey_entry.get('survey_end_timestamp', ''),
            survey_entry.get('survey_completed', ''),
            survey_entry.get('interaction_type', 'post_survey')
        ]
        
        for key, value in survey_entry.items():
            if key not in csv_headers:
                csv_headers.append(key)
                csv_data.append(value)
        # Log post-survey CSV
        csv_file = os.path.join(ensure_data_directory(), 'post_survey.csv')
        write_headers = not os.path.exists(csv_file)

        with open(csv_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if write_headers:
                writer.writerow(csv_headers)
            writer.writerow(csv_data)
            
    except Exception as e:
        app.logger.error(f"Error logging post-survey data: {e}")

# Old survey function. Need to check not needed anymore then delete
def log_survey_data(data):
    """Legacy function - now routes to appropriate specific logging function based on data type"""
    try:
        is_post_survey = any(key.startswith('post_') for key in data.keys())
        
        if is_post_survey:
            log_post_survey_data(data)
        else:
            log_pre_survey_data(data)
            
    except Exception as e:
        app.logger.error(f"Error routing survey data: {e}")

# Timestamp logging for survey start times
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
        
        flask_session['survey_start_timestamp'] = survey_start_data['survey_start_timestamp']
        
    except Exception as e:
        app.logger.error(f"Error logging survey start: {e}")

def load_survey_config():
    """Load survey configuration from file, return None if not found"""
    try:
        survey_config_path = os.path.join(ensure_data_directory(), 'survey_config.json')
        with open(survey_config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        app.logger.error(f"Error loading survey config: {e}")
        return None

# This function deals with scraping the survey data from different section types
def collect_dynamic_survey_data(form_data, survey_config, prefix=''):
    """Collect survey data dynamically based on configuration"""
    survey_data = {}
    
    if not survey_config:
        for key, value in form_data.items():
            if value:  
                prefixed_key = f"{prefix}{key}" if prefix else key
                survey_data[prefixed_key] = value
        return survey_data
    
    sections = survey_config.get('sections', {})
    
    # demographics data
    if sections.get('demographics', {}).get('enabled', False):
        demographics_fields = sections['demographics'].get('fields', {})
        if demographics_fields.get('age', {}).get('enabled', False):
            prefixed_key = f"{prefix}age" if prefix else 'age'
            survey_data[prefixed_key] = form_data.get('age')
        if demographics_fields.get('gender', {}).get('enabled', False):
            prefixed_key = f"{prefix}gender" if prefix else 'gender'
            survey_data[prefixed_key] = form_data.get('gender')
    
    # Likert scale data
    if sections.get('likert', {}).get('enabled', False):
        items = sections['likert'].get('items', [])
        for i, item in enumerate(items):
            field_name = f"likert_item_{i}"
            if field_name in form_data:
                prefixed_key = f"{prefix}likert_{i}_{item[:30]}" if prefix else f"likert_{i}_{item[:30]}"
                survey_data[prefixed_key] = form_data.get(field_name)
    
    # free text data
    if sections.get('freetext', {}).get('enabled', False):
        questions = sections['freetext'].get('questions', [])
        for i, question_config in enumerate(questions):
            field_name = f"free_text_response_{i}"
            if field_name in form_data:
                prefixed_key = f"{prefix}{field_name}" if prefix else field_name
                survey_data[prefixed_key] = form_data.get(field_name)

    # other section types
    section_types = ['checkbox', 'dropdown', 'slider', 'image', 'video', 'pdf']
    for section_type in section_types:
        section_keys = [k for k in sections.keys() if k.startswith(f'{section_type}-')]
        for section_key in section_keys:
            section = sections[section_key]
            if section.get('enabled', False):
                section_id = section_key.replace('-', '_')
                
                if section_type == 'checkbox':
                    # For checkbox sections
                    checkbox_values = form_data.getlist(f"{section_id}_response[]")
                    if checkbox_values:
                        prefixed_key = f"{prefix}{section_id}_response" if prefix else f"{section_id}_response"
                        survey_data[prefixed_key] = checkbox_values
                elif section_type == 'dropdown':
                    # For dropdown sections
                    if f"{section_id}_response" in form_data:
                        prefixed_key = f"{prefix}{section_id}_response" if prefix else f"{section_id}_response"
                        survey_data[prefixed_key] = form_data.get(f"{section_id}_response")
                elif section_type == 'slider':
                    # For slider sections
                    if f"{section_id}_response" in form_data:
                        prefixed_key = f"{prefix}{section_id}_response" if prefix else f"{section_id}_response"
                        survey_data[prefixed_key] = form_data.get(f"{section_id}_response")
                elif section_type in ['image', 'video', 'pdf']:
                    # For media sections
                    if f"{section_id}_response" in form_data:
                        prefixed_key = f"{prefix}{section_id}_response" if prefix else f"{section_id}_response"
                        survey_data[prefixed_key] = form_data.get(f"{section_id}_response")
                    # Also collect any rating responses
                    if f"{section_id}_rating" in form_data:
                        prefixed_key = f"{prefix}{section_id}_rating" if prefix else f"{section_id}_rating"
                        survey_data[prefixed_key] = form_data.get(f"{section_id}_rating")
                    # And text responses
                    if f"{section_id}_text" in form_data:
                        prefixed_key = f"{prefix}{section_id}_text" if prefix else f"{section_id}_text"
                        survey_data[prefixed_key] = form_data.get(f"{section_id}_text")
                    # And checkbox responses
                    checkbox_values = form_data.getlist(f"{section_id}_checkbox[]")
                    if checkbox_values:
                        prefixed_key = f"{prefix}{section_id}_checkbox" if prefix else f"{section_id}_checkbox"
                        survey_data[prefixed_key] = checkbox_values
    
    for key, value in form_data.items():
        prefixed_key = f"{prefix}{key}" if prefix else key
        if prefixed_key not in survey_data and value: 
            survey_data[prefixed_key] = value
    
    return survey_data

# CHAT route 
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'username' not in flask_session:
        return redirect(url_for('login'))
    
    # Check if user has completed the survey
    if not flask_session.get('survey_completed'):
        return redirect(url_for('survey'))

    try:
        agent = flask_session.get('agent', 'default')
        API.update_agent(f"agents/{agent}.json")
        conversation = get_messages(flask_session['user_id'], flask_session['password'])

        if request.method == 'POST':
            message = request.form.get('message')
            if not message:
                flash('Message cannot be empty', 'error')
                return jsonify({'error': 'Message cannot be empty'}), 400
            
            model = API.agent_data.get("model") or current_model or "gpt-4.1"
            try:
                conversation, prompt_tokens, completion_tokens, total_tokens, logprobs_list, actual_model = API.thinkAbout(message, conversation, model=model)
                response = conversation[-1]["content"]
                print(f"AI Response complete. Model used: {actual_model}, Tokens: {total_tokens}")
            except Exception as e:
                app.logger.error(f"Error processing message: {e}")
                return jsonify({'error': 'Error processing message'}), 500

            user_id = flask_session['user_id']
            password = flask_session['password']
            add_message(user_id, password, message, str(response), actual_model, API.agent_data.get("temperature", 1), prompt_tokens, completion_tokens, total_tokens, logprobs_list)
            return jsonify({'response': response})

        url_settings = get_url_settings_from_db()
        branding_settings = get_branding_settings_from_db()
        
        return render_template('chat.html', 
                             username=flask_session['username'], 
                             messages=conversation, 
                             quit_button_text=url_settings['quit_button_text'],
                             redirect_button_text=url_settings['redirect_button_text'],
                             chat_header_line1=branding_settings['chat_header_line1'],
                             chat_header_line2=branding_settings['chat_header_line2'])
    except Exception as ex:
        app.logger.error(f"Unexpected error occurred: {ex}")
        return jsonify({'error': 'Unexpected error occurred'}), 500

# Researcher dashboard routes and functions
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
    """Authenticate researcher credentials against environment variables"""
    env_username = os.environ.get('researcher_username')
    env_password = os.environ.get('researcher_password')
    
    print(f"Auth attempt - Username: {researcher_username}, Env username: {env_username}")
    print(f"Auth attempt - Password provided: {'Yes' if researcher_password else 'No'}, Env password set: {'Yes' if env_password else 'No'}")
    
    return (researcher_username == env_username and 
            researcher_password == env_password)

# Needed to add this to reload the env without having to redeploy while testing
@app.route('/reload-env', methods=['POST'])
def reload_env():
    """Reload environment variables from .env file - DEVELOPMENT ONLY"""
    if not flask_session.get('researcher'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        load_dotenv(override=True)
        
        env_valid = validate_env_variables()
        
        return jsonify({
            'success': True, 
            'message': 'Environment variables reloaded successfully',
            'validation_passed': env_valid,
            'researcher_username': os.environ.get('researcher_username', 'NOT_SET'),
            'researcher_password_set': bool(os.environ.get('researcher_password'))
        })
    except Exception as e:
        return jsonify({'error': f'Failed to reload environment: {str(e)}'}), 500

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

# Route for agent creation in researcher dashboard
@app.route('/create-json', methods=['POST'])
def create_json_file():
    data = request.json
    filename = data["filename"]
    
    with open(f'agents/{filename}.json', 'w') as jsonfile:
        json.dump(data, jsonfile, indent=2)

    return jsonify({"message": "File created successfully"}), 201

# This is for updating the agent passwords set in the researcher dashboard
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

# This is for updating passwords in the db
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

# This is for reviewing agent passwords in the researcher dashboard
@app.route('/get-passwords', methods=['GET'])
def get_passwords():
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    query = "SELECT * FROM passwords"
    cursor.execute(query)

    passwords = [{"agent": row[0], "password": row[1]} for row in cursor.fetchall()]

    connection.close()
    
    return jsonify(passwords)

# For randomising agent assignment master password
@app.route('/get-randomised-password', methods=['GET'])
def get_randomised_password_route():
    """Get the current randomised agent password"""
    try:
        password = get_randomised_agent_password()
        return jsonify({'password': password}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update-randomised-password', methods=['POST'])
def update_randomised_password_route():
    """Update the randomised agent password"""
    try:
        data = request.json
        new_password = data.get('password', '').strip()
        
        if not new_password:
            return jsonify({'error': 'Password cannot be empty'}), 400
            
        update_randomised_agent_password(new_password)
        return jsonify({'message': 'Randomised agent password updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-agents-with-status', methods=['GET'])
def get_agents_with_status_route():
    """Get all agents with their active status and details"""
    try:
        agents = get_all_agents_with_status()
        agent_details = []
        
        for password, agent_name, is_active in agents:
            try:
                with open(f'agents/{agent_name}.json', 'r') as f:
                    agent_config = json.load(f)
                agent_details.append({
                    'password': password,
                    'agent_name': agent_name,
                    'is_active': bool(is_active),
                    'config': agent_config
                })
            except FileNotFoundError:
                agent_details.append({
                    'password': password,
                    'agent_name': agent_name,
                    'is_active': bool(is_active),
                    'config': {'error': 'Agent file not found'}
                })
        
        return jsonify({'agents': agent_details}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update-agent-status', methods=['POST'])
def update_agent_status_route():
    """Update the active status of an agent"""
    try:
        data = request.json
        password = data.get('password')
        is_active = data.get('is_active', True)
        
        if not password:
            return jsonify({'error': 'Password is required'}), 400
            
        update_agent_active_state(password, is_active)
        return jsonify({'message': 'Agent status updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete-agent', methods=['POST'])
def delete_agent_route():
    """Delete an agent configuration and its password assignment"""
    try:
        data = request.json
        password = data.get('password')
        agent_name = data.get('agent_name')
        
        if not password or not agent_name:
            return jsonify({'error': 'Password and agent_name are required'}), 400
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('DELETE FROM passwords WHERE password = ?', (password,))
        conn.commit()
        conn.close()
        
        agent_file_path = f'agents/{agent_name}.json'
        if os.path.exists(agent_file_path):
            os.remove(agent_file_path)
            
        return jsonify({'message': 'Agent deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# This is for local download of data files in researcher dashboard
@app.route('/download/<filename>')
def download_file(filename):
    directory = '.'  

    if not os.path.exists(os.path.join(directory, filename)):
        abort(404)  

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    data_dir = ensure_data_directory()
    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(directory, filename, as_attachment=True)

# Old survey data download route. Check these two routes and then delete if not needed
@app.route('/download-survey-json')
def download_survey_json():
    """Download survey.json file (legacy - contains mixed pre/post survey data)"""
    filename = 'survey.json'
    data_dir = ensure_data_directory()
    
    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

@app.route('/download-survey-csv')
def download_survey_csv():
    """Download survey.csv file (legacy - contains mixed pre/post survey data)"""
    filename = 'survey.csv'
    data_dir = ensure_data_directory()

    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

# Pre-survey data download routes
@app.route('/download-pre-survey-json')
def download_pre_survey_json():
    """Download pre_survey.json file"""
    filename = 'pre_survey.json'
    data_dir = ensure_data_directory()
    
    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

@app.route('/download-pre-survey-csv')
def download_pre_survey_csv():
    """Download pre_survey.csv file"""
    filename = 'pre_survey.csv'
    data_dir = ensure_data_directory()

    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

# Post-survey data download routes
@app.route('/download-post-survey-json')
def download_post_survey_json():
    """Download post_survey.json file"""
    filename = 'post_survey.json'
    data_dir = ensure_data_directory()
    
    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

@app.route('/download-post-survey-csv')
def download_post_survey_csv():
    """Download post_survey.csv file"""
    filename = 'post_survey.csv'
    data_dir = ensure_data_directory()

    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

# Popup data download routes
@app.route('/download-popup-json')
def download_popup_json():
    """Download popup.json file"""
    filename = 'popup.json'
    data_dir = ensure_data_directory()

    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

@app.route('/download-popup-csv')
def download_popup_csv():
    """Download popup.csv file"""
    filename = 'popup.csv'
    data_dir = ensure_data_directory()

    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

# Interactions data download routes
@app.route('/download-interactions-json')
def download_interactions_json():
    """Download interactions.json file"""
    filename = 'interactions.json'
    data_dir = ensure_data_directory()

    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

@app.route('/download-interactions-csv')
def download_interactions_csv():
    """Download interactions_backup.csv file"""
    filename = 'interactions_backup.csv'
    data_dir = ensure_data_directory()

    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

# Download log route
@app.route('/download-download-log')
def download_download_log():
    """Download download_log.json file"""
    filename = 'download_log.json'
    data_dir = ensure_data_directory()

    if not os.path.exists(os.path.join(data_dir, filename)):
        abort(404)

    log_entry = {
        "filename": filename,
        "timestamp": datetime.now().isoformat(),
        "client_ip": request.remote_addr
    }

    download_log_path = os.path.join(data_dir, 'download_log.json')
    
    if not os.path.exists(download_log_path):
        with open(download_log_path, 'w') as log_file:
            log_file.write('')

    with open(download_log_path, 'a') as log_file:
        log_file.write(json.dumps(log_entry) + '\n')

    return send_from_directory(data_dir, filename, as_attachment=True)

# Timer settings routes
@app.route('/get-timer-settings', methods=['GET'])
def get_timer_settings():
    """Get current timer settings"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('SELECT setting_value FROM url_settings WHERE setting_name = ?', ('timer_duration_minutes',))
    result = c.fetchone()
    conn.close()
    
    duration_minutes = int(result[0]) if result else 10
    
    timer_settings = {
        'duration_minutes': duration_minutes
    }
    return jsonify(timer_settings)

@app.route('/update-timer-settings', methods=['POST'])
def update_timer_settings():
    """Update timer settings"""
    data = request.json
    duration_minutes = data.get('duration_minutes', 10)
    
    if not isinstance(duration_minutes, int) or duration_minutes < 1 or duration_minutes > 120:
        return jsonify({'error': 'Duration must be between 1 and 120 minutes'}), 400
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO url_settings (setting_name, setting_value) VALUES (?, ?)', 
              ('timer_duration_minutes', str(duration_minutes)))
    conn.commit()
    conn.close()
    
    os.environ['TIMER_DURATION_MINUTES'] = str(duration_minutes)
    
    return jsonify({'message': 'Timer settings updated successfully'})

# URL configuration routes
def get_url_settings_from_db():
    """Get URL settings from database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS url_settings 
                 (setting_name TEXT PRIMARY KEY, 
                 setting_value TEXT NOT NULL)''')
    
    c.execute('SELECT setting_name, setting_value FROM url_settings')
    settings = dict(c.fetchall())
    conn.close()
    
    return {
        'quit_url': settings.get('quit_url', 'https://www.prolific.com/'),
        'redirect_url': settings.get('redirect_url', 'https://www.prolific.com/'),
        'quit_button_text': settings.get('quit_button_text', 'Quit Study'),
        'redirect_button_text': settings.get('redirect_button_text', 'Continue to Survey'),
        'use_post_survey': settings.get('use_post_survey', 'false').lower() in ('true', '1', 'yes', 'on'),
        'trigger_type': settings.get('trigger_type', 'messages'),
        'stage1_messages': int(settings.get('stage1_messages', '5')),
        'stage2_messages': int(settings.get('stage2_messages', '10')),
        'stage3_messages': int(settings.get('stage3_messages', '15')),
        'stage1_time': float(settings.get('stage1_time', '2')),
        'stage2_time': float(settings.get('stage2_time', '5')),
        'stage3_time': float(settings.get('stage3_time', '8')),
        'timer_duration_minutes': int(settings.get('timer_duration_minutes', '10')),
        'post_chat_popup_enabled': settings.get('post_chat_popup_enabled', 'false').lower() in ('true', '1', 'yes', 'on'),
        'post_chat_popup_text': settings.get('post_chat_popup_text', 'Please provide your feedback on the AI system:'),
        'post_chat_popup_button1_text': settings.get('post_chat_popup_button1_text', 'Feedback to the AI that it is worthless --This system will then be permenantly deleted--'),
        'post_chat_popup_button2_text': settings.get('post_chat_popup_button2_text', 'Feedback to the AI that it is useful --This system will then be permenantly deleted--')
    }

def get_branding_settings_from_db():
    """Get branding settings from database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS url_settings 
                 (setting_name TEXT PRIMARY KEY, 
                 setting_value TEXT NOT NULL)''')
    
    branding_keys = [
        'login_title', 'login_footer_line1', 'login_footer_line2', 'login_footer_line3',
        'chat_header_line1', 'chat_header_line2'
    ]
    
    settings = {}
    for key in branding_keys:
        c.execute('SELECT setting_value FROM url_settings WHERE setting_name = ?', (key,))
        result = c.fetchone()
        if result:
            settings[key] = result[0]
    
    conn.close()
    
    default_settings = {
        'login_title': 'Artificial Intelligence <br>Gateway',
        'login_footer_line1': 'chatPsych',
        'login_footer_line2': 'Powered by',
        'login_footer_line3': 'The Australian Institute for Machine Learning',
        'chat_header_line1': 'Australian Institute for Machine&nbsp;Learning',
        'chat_header_line2': 'chatPsych'
    }
    
    for key, default_value in default_settings.items():
        if key not in settings:
            settings[key] = default_value
    
    return settings

def save_url_settings_to_db(settings):
    """Save URL settings to database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS url_settings 
                 (setting_name TEXT PRIMARY KEY, 
                 setting_value TEXT NOT NULL)''')
    
    for key, value in settings.items():
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        c.execute('INSERT OR REPLACE INTO url_settings (setting_name, setting_value) VALUES (?, ?)', 
                  (key, str(value)))
    
    conn.commit()
    conn.close()

@app.route('/get-url-settings', methods=['GET'])
def get_url_settings():
    """Get current URL settings"""
    url_settings = get_url_settings_from_db()
    return jsonify(url_settings)

@app.route('/update-url-settings', methods=['POST'])
def update_url_settings():
    """Update URL settings"""
    data = request.json
    quit_url = data.get('quit_url', '')
    redirect_url = data.get('redirect_url', '')
    quit_button_text = data.get('quit_button_text', 'Quit Study')
    redirect_button_text = data.get('redirect_button_text', 'Continue to Survey')
    use_post_survey = data.get('use_post_survey', False)
    trigger_type = data.get('trigger_type', 'messages')
    stage1_messages = data.get('stage1_messages', 5)
    stage2_messages = data.get('stage2_messages', 10)
    stage3_messages = data.get('stage3_messages', 15)
    stage1_time = data.get('stage1_time', 2)
    stage2_time = data.get('stage2_time', 5)
    stage3_time = data.get('stage3_time', 8)
    timer_duration_minutes = data.get('timer_duration_minutes', 10)
    
    post_chat_popup_enabled = data.get('post_chat_popup_enabled', False)
    post_chat_popup_text = data.get('post_chat_popup_text', 'Please provide your feedback on the AI system:')
    post_chat_popup_button1_text = data.get('post_chat_popup_button1_text', 'Feedback to the AI that it is worthless --This system will then be permenantly deleted--')
    post_chat_popup_button2_text = data.get('post_chat_popup_button2_text', 'Feedback to the AI that it is useful --This system will then be permenantly deleted--')
    
    if not quit_url or not redirect_url:
        return jsonify({'error': 'Both quit_url and redirect_url are required'}), 400
    
    try:
        from urllib.parse import urlparse
        quit_parsed = urlparse(quit_url)
        if not use_post_survey: 
            redirect_parsed = urlparse(redirect_url)
            if not all([redirect_parsed.scheme, redirect_parsed.netloc]):
                return jsonify({'error': 'Invalid redirect URL format. URLs must include protocol (http:// or https://)'}), 400
        
        if not all([quit_parsed.scheme, quit_parsed.netloc]):
            return jsonify({'error': 'Invalid quit URL format. URLs must include protocol (http:// or https://)'}), 400
    except Exception as e:
        return jsonify({'error': 'Invalid URL format'}), 400
    
    if trigger_type not in ['messages', 'time']:
        return jsonify({'error': 'Invalid trigger type. Must be "messages" or "time"'}), 400
    
    if trigger_type == 'messages':
        if not all(isinstance(x, int) and x > 0 for x in [stage1_messages, stage2_messages, stage3_messages]):
            return jsonify({'error': 'Message trigger values must be positive integers'}), 400
    
    if trigger_type == 'time':
        if not all(isinstance(x, (int, float)) and x > 0 for x in [stage1_time, stage2_time, stage3_time]):
            return jsonify({'error': 'Time trigger values must be positive numbers'}), 400
    
    if not isinstance(timer_duration_minutes, (int, float)) or timer_duration_minutes <= 0:
        return jsonify({'error': 'Timer duration must be a positive number'}), 400
    
    settings = {
        'quit_url': quit_url,
        'redirect_url': redirect_url,
        'quit_button_text': quit_button_text,
        'redirect_button_text': redirect_button_text,
        'use_post_survey': 'true' if use_post_survey else 'false',
        'trigger_type': trigger_type,
        'stage1_messages': stage1_messages,
        'stage2_messages': stage2_messages,
        'stage3_messages': stage3_messages,
        'stage1_time': stage1_time,
        'stage2_time': stage2_time,
        'stage3_time': stage3_time,
        'timer_duration_minutes': timer_duration_minutes,
        'post_chat_popup_enabled': 'true' if post_chat_popup_enabled else 'false',
        'post_chat_popup_text': post_chat_popup_text,
        'post_chat_popup_button1_text': post_chat_popup_button1_text,
        'post_chat_popup_button2_text': post_chat_popup_button2_text
    }
    
    save_url_settings_to_db(settings)
    
    os.environ['QUIT_URL'] = quit_url
    os.environ['REDIRECT_URL'] = redirect_url
    
    return jsonify({'success': True, 'message': 'URL settings updated successfully'})

@app.route('/get-redirect-urls', methods=['GET'])
def get_redirect_urls():
    """API endpoint for the chat interface to get current redirect URLs"""
    settings = get_url_settings_from_db()
    return jsonify({
        'quit_url': settings['quit_url'],
        'redirect_url': settings['redirect_url'],
        'use_post_survey': settings['use_post_survey']
    })

@app.route('/get-trigger-settings', methods=['GET'])
def get_trigger_settings():
    """API endpoint for the chat interface to get trigger settings"""
    settings = get_url_settings_from_db()
    return jsonify({
        'trigger_type': settings['trigger_type'],
        'stage1_messages': settings['stage1_messages'],
        'stage2_messages': settings['stage2_messages'], 
        'stage3_messages': settings['stage3_messages'],
        'stage1_time': settings['stage1_time'],
        'stage2_time': settings['stage2_time'],
        'stage3_time': settings['stage3_time'],
        'quit_button_text': settings['quit_button_text'],
        'redirect_button_text': settings['redirect_button_text'],
        'use_post_survey': settings['use_post_survey']
    })

@app.route('/log-post-chat-popup', methods=['POST'])
def log_post_chat_popup():
    """Log post-chat popup selection"""
    try:
        data = request.json
        button_text = data.get('button_text', '')
        
        username = flask_session.get('username', 'Unknown')
        user_id = flask_session.get('user_id', 'Unknown')
        password = flask_session.get('password', 'Unknown')
        agent_name = flask_session.get('agent', 'Unknown')
        
        popup_data = {
            'timestamp': str(datetime.now()),
            'username': username,
            'password': password,
            'agent_name': agent_name,
            'user_id': user_id,
            'interaction_type': 'post_chat_popup_selection',
            'button_selected': button_text
        }
        
        log_popup_data(popup_data)
        
        return jsonify({'success': True, 'message': 'Post-chat popup selection logged successfully'})
        
    except Exception as e:
        app.logger.error(f"Error logging post-chat popup selection: {e}")
        return jsonify({'error': 'Error logging post-chat popup selection'}), 500

# Survey Config Routes
@app.route('/save-survey-config', methods=['POST'])
def save_survey_config():
    """Save survey configuration to file"""
    try:
        config = request.json
        
        validation_error = validate_survey_config(config)
        if validation_error:
            return jsonify({'success': False, 'error': validation_error}), 400
        # Saving the config file here
        survey_config_path = os.path.join(ensure_data_directory(), 'survey_config.json')
        with open(survey_config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        try:
            generate_survey_html(config)
        except Exception as e:
            app.logger.error(f"Error generating survey HTML: {e}")
        
        return jsonify({'success': True, 'message': 'Survey configuration saved successfully'})
    except Exception as e:
        app.logger.error(f"Error saving survey config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def validate_survey_config(config):
    """Validate survey configuration structure"""
    if not isinstance(config, dict):
        return "Configuration must be a valid JSON object"
    
    if 'title' not in config:
        return "Survey title is required"
    
    sections = config.get('sections', {})
    if sections:
        if sections.get('demographics', {}).get('enabled', False):
            demo_fields = sections['demographics'].get('fields', {})
            if not demo_fields:
                return "Demographics section is enabled but has no fields configured"
        
        if sections.get('likert', {}).get('enabled', False):
            likert_items = sections['likert'].get('items', [])
            if not likert_items:
                return "Likert section is enabled but has no items configured"
        
        if sections.get('freetext', {}).get('enabled', False):
            freetext_questions = sections['freetext'].get('questions', [])
            if not freetext_questions:
                return "Free text section is enabled but has no questions configured"
        
        media_types = ['image', 'video', 'pdf']
        for media_type in media_types:
            for section_key in sections:
                if section_key.startswith(f'{media_type}-') and sections[section_key].get('enabled', False):
                    media_section = sections[section_key]
                    if media_type in ['image', 'video', 'pdf']:
                        if media_type == 'video':
                            has_file = media_section.get('file_path') or media_section.get('video_url')
                            if not has_file:
                                return f"Video section '{section_key}' is enabled but has no file or URL configured"
                        else:
                            if not media_section.get('file_path'):
                                return f"{media_type.title()} section '{section_key}' is enabled but has no file configured"
    
    return None  

@app.route('/get-survey-config', methods=['GET'])
def get_survey_config():
    """Get current survey configuration"""
    try:
        survey_config_path = os.path.join(ensure_data_directory(), 'survey_config.json')
        with open(survey_config_path, 'r') as f:
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
        survey_config_path = os.path.join(ensure_data_directory(), 'survey_config.json')
        if os.path.exists(survey_config_path):
            os.remove(survey_config_path)
        
        upload_dir = 'static/uploads'
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                if filename.startswith(('information_form', 'consent_form', 'survey_image_', 'survey_video_', 'survey_pdf_')):
                    filepath = os.path.join(upload_dir, filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
        
        return jsonify({'success': True, 'message': 'Survey configuration reset to default'})
    except Exception as e:
        app.logger.error(f"Error resetting survey config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Survey media upload handling all done here
@app.route('/upload-survey-media', methods=['POST'])
def upload_survey_media():
    """Handle file uploads for survey media sections"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        media_type = request.form.get('media_type') 
        section_id = request.form.get('section_id')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not media_type or not section_id:
            return jsonify({'success': False, 'error': 'Missing media_type or section_id'}), 400
        
        allowed_extensions = {
            'image': {'.jpg', '.jpeg', '.png', '.gif', '.webp'},
            'video': {'.mp4', '.webm', '.ogg', '.avi', '.mov'},
            'pdf': {'.pdf'}
        }
        
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions.get(media_type, set()):
            return jsonify({'success': False, 'error': f'Invalid file type for {media_type}'}), 400
        
        upload_dir = 'static/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"survey_{media_type}_{section_id}_{timestamp}{file_ext}"
        filepath = os.path.join(upload_dir, safe_filename)
        
        file.save(filepath)
        
        relative_path = f"/static/uploads/{safe_filename}"
        
        return jsonify({
            'success': True,
            'file_path': relative_path,
            'filename': safe_filename,
            'original_name': file.filename,
            'file_size': os.path.getsize(filepath)
        })
        
    except Exception as e:
        app.logger.error(f"Error uploading survey media: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/survey-system-status', methods=['GET'])
def survey_system_status():
    """Get status of survey system for debugging"""
    try:
        data_dir = ensure_data_directory()
        survey_config_path = os.path.join(data_dir, 'survey_config.json')
        
        status = {
            'has_custom_config': os.path.exists(survey_config_path),
            'config_readable': False,
            'uploaded_files': {},
            'static_template_exists': os.path.exists('templates/pre_survey.html'),
            'survey_js_exists': os.path.exists('static/js/pre_survey.js')
        }
        
        if status['has_custom_config']:
            try:
                with open(survey_config_path, 'r') as f:
                    config = json.load(f)
                status['config_readable'] = True
                status['config_sections'] = list(config.get('sections', {}).keys())
            except Exception:
                status['config_readable'] = False
        
        upload_dir = 'static/uploads'
        if os.path.exists(upload_dir):
            for filename in ['information_form.pdf', 'consent_form.pdf']:
                filepath = os.path.join(upload_dir, filename)
                status['uploaded_files'][filename] = os.path.exists(filepath)
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# This is just functionality for the researcher dashboard when creating survey previews
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
        valid_types = ['information', 'consent', 'post_information', 'post_consent']
        if file_type not in valid_types:
            abort(404)
        
        filename = f"{file_type}_form.pdf"
        filepath = os.path.join('static', 'uploads', filename)
        
        if not os.path.exists(filepath):
            if request.headers.get('Content-Type') == 'application/json' or 'json' in request.headers.get('Accept', ''):
                return jsonify({'error': 'File not found'}), 404
            abort(404)
        
        return send_file(filepath, as_attachment=True, download_name=f"{file_type}_form.pdf")
    except Exception as e:
        if "404" not in str(e):
            app.logger.error(f"Error downloading form file: {e}")
        abort(404)

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
        
        valid_types = ['information', 'consent', 'post_information', 'post_consent']
        if not file_type or file_type not in valid_types:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        if not (file and file.filename.lower().endswith('.pdf') and 
                file.content_type == 'application/pdf'):
            return jsonify({'success': False, 'error': 'Only PDF files are allowed'}), 400
        
        file.seek(0, 2) 
        file_size = file.tell()
        file.seek(0) 
        
        if file_size > 10 * 1024 * 1024:  # can delete this file size limit if you want to?
            return jsonify({'success': False, 'error': 'File size too large (max 10MB)'}), 400
        
        upload_dir = 'static/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"{file_type}_form.pdf"
        filepath = os.path.join(upload_dir, filename)
        
        file.save(filepath)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File upload failed'}), 500
        
        return jsonify({'success': True, 'filename': filename})
            
    except Exception as e:
        app.logger.error(f"Error uploading form file: {e}")
        return jsonify({'success': False, 'error': 'File upload failed'}), 500

# Post-Survey Config routes
@app.route('/preview-post-survey', methods=['POST'])
def preview_post_survey():
    """Generate post-survey preview HTML"""
    try:
        config = request.json
        html = generate_post_survey_html_content(config, 
                                                '#', '#', 
                                                'The study is now complete. Thank you for your participation. If required, your completion code is: xxxx',
                                                'Finish', preview=True)
        return html, 200, {'Content-Type': 'text/html'}
    except Exception as e:
        return f"Error generating post-survey preview: {str(e)}", 500

@app.route('/update-post-survey-enabled', methods=['POST'])
def update_post_survey_enabled():
    """Update the enabled state of the post-survey"""
    try:
        data = request.json
        enabled = data.get('enabled', False)
        
        current_settings = get_url_settings_from_db()
        current_settings['use_post_survey'] = 'true' if enabled else 'false'
        
        save_url_settings_to_db(current_settings)
        
        return jsonify({'success': True, 'enabled': enabled, 'message': 'Post-survey enabled state updated successfully'})
    except Exception as e:
        app.logger.error(f"Error updating post-survey enabled state: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_survey_html(config):
    """Generate pre_survey.html file based on configuration"""
    try:
        html_content = generate_survey_html_content(config)
        
        with open('templates/pre_survey.html', 'w') as f:
            f.write(html_content)
            
    except Exception as e:
        app.logger.error(f"Error generating survey HTML: {e}")
        raise

def generate_survey_html_content(config, preview=False):
    """Generate the actual HTML content for the survey"""
    # This is a big function to generate the HTML for those surveys
    # it is based on the survey_config.json created before
    
    info_file_exists = os.path.exists('static/uploads/information_form.pdf')
    consent_file_exists = os.path.exists('static/uploads/consent_form.pdf')
    
    download_links = ""
    if info_file_exists or consent_file_exists:
        download_links = '<div class="form-downloads">'
        if info_file_exists:
            if preview:
                download_links += '<a href="#" class="download-link">Download Information Sheet</a>'
            else:
                download_links += '<a href="/download-form-file/information" class="download-link">Download Information Sheet</a>'
        if consent_file_exists:
            if preview:
                download_links += '<a href="#" class="download-link">Download Consent Form</a>'
            else:
                download_links += '<a href="/download-form-file/consent" class="download-link">Download Consent Form</a>'
        download_links += '</div>'
    
    if preview:
        css_link = '/static/css/styles.css'
        js_link = '/static/js/pre_survey.js'
        quit_link_var = 'window.quitRedirectionLink = "#";'
    else:
        css_link = '/static/css/styles.css'
        js_link = '/static/js/pre_survey.js'
        quit_link_var = f'window.quitRedirectionLink = "{os.environ.get("QUIT_URL", "https://www.prolific.com/")}";'
    
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
                {format_consent_content(config.get('consent', {}).get('content', ''))}
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
    # adding sections here
    sections = config.get('sections', {})
    settings = config.get('settings', {})
    randomize_items = settings.get('randomizeItems', False)
    
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
        elif section_type == 'checkbox':
            html += generate_checkbox_section(section_config, section_id)
        elif section_type == 'dropdown':
            html += generate_dropdown_section(section_config, section_id)
        elif section_type == 'slider':
            html += generate_slider_section(section_config, section_id)
        elif section_type == 'image':
            html += generate_image_section(section_config, section_id)
        elif section_type == 'video':
            html += generate_video_section(section_config, section_id)
        elif section_type == 'pdf':
            html += generate_pdf_section(section_config, section_id)
        elif section_type == 'custom':
            html += generate_custom_section(section_config)
    
    html += '''
                <div class="submit-section">
                    <button type="submit" id="submit-btn">Submit Survey</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Survey Submission Modal -->
    <div id="submission-modal" class="survey-submission-modal survey-hidden">
        <div class="survey-popup-content">
            <div class="submission-content">
                <div class="submission-spinner"></div>
                <h3 id="submission-message">Survey submitted successfully!</h3>
                <p id="submission-detail">You will now be connected to the AI system.</p>
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

def generate_post_survey_html_content(config, quit_redirection_link, finish_redirection_link, completion_instructions, finish_button_text, preview=False):
    """Generate the actual HTML content for the post-interaction survey"""
    
    info_file_exists = os.path.exists('static/uploads/post_information_form.pdf')
    consent_file_exists = os.path.exists('static/uploads/post_consent_form.pdf')
    
    download_links = ""
    if info_file_exists or consent_file_exists:
        download_links = '<div class="form-downloads">'
        if info_file_exists:
            if preview:
                download_links += '<a href="#" class="download-link">Download Information Sheet</a>'
            else:
                download_links += '<a href="/download-form-file/post_information" class="download-link">Download Information Sheet</a>'
        if consent_file_exists:
            if preview:
                download_links += '<a href="#" class="download-link">Download Consent Form</a>'
            else:
                download_links += '<a href="/download-form-file/post_consent" class="download-link">Download Consent Form</a>'
        download_links += '</div>'
    
    if preview:
        css_link = '/static/css/styles.css'
        js_link = '/static/js/post_survey.js'
        quit_link_var = 'window.quitRedirectionLink = "#";'
        finish_link_var = 'window.finishRedirectionLink = "#";'
    else:
        css_link = '/static/css/styles.css'
        js_link = '/static/js/post_survey.js'
        quit_link_var = f'window.quitRedirectionLink = "{quit_redirection_link}";'
        finish_link_var = f'window.finishRedirectionLink = "{finish_redirection_link}";'
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.get('title', 'Survey Form')}</title>
    <link rel="icon" type="image/x-icon" href="/static/images/IA.ico">
    <link rel="stylesheet" href="{css_link}" charset="UTF-8">
</head>
<body class="survey-page">
    <div class="survey-container">
        <div class="survey-header">
            <h1>{config.get('title', 'Survey Form')}</h1>
        </div>
        
        <div class="survey-content">
            <!-- Main Survey Form --> 
            <form id="survey-form" class="survey-form">
                <div id="survey-sections" class="survey-sections">
'''
    # adding sections here
    sections = config.get('sections', {})
    settings = config.get('settings', {})
    randomize_items = settings.get('randomizeItems', False)
    
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
        elif section_type == 'checkbox':
            html += generate_checkbox_section(section_config, section_id)
        elif section_type == 'dropdown':
            html += generate_dropdown_section(section_config, section_id)
        elif section_type == 'slider':
            html += generate_slider_section(section_config, section_id)
        elif section_type == 'image':
            html += generate_image_section(section_config, section_id)
        elif section_type == 'video':
            html += generate_video_section(section_config, section_id)
        elif section_type == 'pdf':
            html += generate_pdf_section(section_config, section_id)
        elif section_type == 'custom':
            html += generate_custom_section(section_config)
    
    html += '''
                </div>
                <div class="survey-navigation">
                    <button type="submit" id="submit-btn">Submit Survey</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Survey Submission Modal -->
    <div id="submission-modal" class="survey-submission-modal survey-hidden">
        <div class="survey-popup-content">
            <div class="submission-content">
                <div class="submission-spinner"></div>
                <h3 id="submission-message">Survey submitted successfully!</h3>
                <p id="submission-detail">Processing your responses...</p>
            </div>
        </div>
    </div>

    <!-- Final Completion Modal -->
    <div id="completion-modal" class="survey-submission-modal survey-hidden">
        <div class="survey-popup-content">
            <div class="completion-content">
                <h3>Study Complete</h3>
                <div id="completion-instructions">
                    <p>''' + completion_instructions + '''</p>
                </div>
                <button id="final-finish-btn" class="survey-consent-button agree">''' + finish_button_text + '''</button>
            </div>
        </div>
    </div>

    <script>
        // Make redirection links available to external JS
        ''' + finish_link_var + '''
        window.completionInstructions = "''' + completion_instructions.replace('"', '\\"') + '''";
        window.finishButtonText = "''' + finish_button_text + '''";
    </script>
    <script src="''' + js_link + '''"></script>
</body>
</html>'''
    
    return html

def format_consent_content(content):
    """Format consent content with proper HTML"""
    if not content:
        return "<p>Please read the information about this study.</p>"
    
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
    
    if fields.get('age', {}).get('enabled', False):
        age_config = fields['age']
        html += f'''
            <label for="demographics-age">Age:</label>
            <input type="number" id="demographics-age" name="age" min="{age_config.get('min', 18)}" max="{age_config.get('max', 99)}" required><br><br>
'''
    
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
            <table class="survey-likert-table">
                <tr>
                    <th>Statement</th>
'''
    
    scale_labels = config.get('scaleLabels', 'Strongly Disagree,Disagree,Neutral,Agree,Strongly Agree').split(',')
    for label in scale_labels:
        html += f'                    <th>{label.strip()}</th>\n'
    
    html += '                </tr>\n'
    
    items = config.get('items', [])
    if randomize_items and items:
        items = items.copy() 
        random.shuffle(items)
    
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
    
    questions = config.get('questions', [])
    if randomize_items and questions:
        questions = questions.copy() 
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
    
    description = config.get('description', '')
    if description:
        html += f'            <div class="survey-section-description">{description}</div>\n'
    
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
                    html += f'            <input type="checkbox" id="{checkbox_id}" name="{field_id}[]" value="{option}">\n'
                    html += f'            <label for="{checkbox_id}">{option}</label><br>\n'
            html += '<br>\n'
        else:
            html += f'            <input type="{field_type}" id="{field_id}" name="{field_id}" {required_attr}><br><br>\n'
    
    html += '        </div>\n'
    return html

def generate_checkbox_section(config, section_id):
    """Generate checkbox section HTML"""
    section_id = section_id.replace('-', '_')
    title = config.get('title', 'Multiple Choice Selection')
    question = config.get('question', 'Please select all that apply:')
    options = config.get('options', [])
    
    html = f'''
        <!-- Checkbox Section -->
        <div class="survey-section" id="{section_id}">
            <div class="survey-section-title">{title}</div>
            <div class="survey-section-description">{question}</div>
'''
    
    for i, option in enumerate(options):
        checkbox_id = f"{section_id}_option_{i}"
        html += f'''            <input type="checkbox" id="{checkbox_id}" name="{section_id}_response[]" value="{option}">
            <label for="{checkbox_id}">{option}</label><br>
'''
    
    html += '        </div>\n'
    return html

def generate_dropdown_section(config, section_id):
    """Generate dropdown section HTML"""
    section_id = section_id.replace('-', '_')
    title = config.get('title', 'Selection')
    question = config.get('question', 'Please select an option:')
    options = config.get('options', [])
    required = config.get('required', False)
    required_attr = 'required' if required else ''
    
    html = f'''
        <!-- Dropdown Section -->
        <div class="survey-section" id="{section_id}">
            <div class="survey-section-title">{title}</div>
            <label for="{section_id}_select">{question}</label><br>
            <select id="{section_id}_select" name="{section_id}_response" {required_attr}>
                <option value="">Select an option...</option>
'''
    
    for option in options:
        html += f'                <option value="{option}">{option}</option>\n'
    
    html += '''            </select><br><br>
        </div>
'''
    return html

def generate_slider_section(config, section_id):
    """Generate slider section HTML"""
    section_id = section_id.replace('-', '_')
    title = config.get('title', 'Rating Scale')
    question = config.get('question', 'Please rate using the slider:')
    slider_type = config.get('slider_type', 'labels') 
    required = config.get('required', False)
    required_attr = 'required' if required else ''
    
    html = f'''
        <!-- Slider Section -->
        <div class="survey-section" id="{section_id}">
            <div class="survey-section-title">{title}</div>
            <label for="{section_id}_slider">{question}</label><br>
            <div class="slider-container">
'''
    
    if slider_type == 'numeric':
        min_val = config.get('min_value', 0)
        max_val = config.get('max_value', 100)
        default_val = config.get('default_value', int((min_val + max_val) / 2))
        
        html += f'''                <div class="slider-labels">
                    <span class="slider-min">{min_val}</span>
                    <span class="slider-max">{max_val}</span>
                </div>
                <input type="range" id="{section_id}_slider" name="{section_id}_response" 
                       min="{min_val}" max="{max_val}" value="{default_val}" 
                       class="survey-slider" {required_attr} data-slider-interacted="false">
                <div class="slider-value-display">
                    <span id="{section_id}_value">{default_val}</span>
                </div>
                <script>
                    document.getElementById('{section_id}_slider').oninput = function() {{
                        document.getElementById('{section_id}_value').textContent = this.value;
                        this.setAttribute('data-slider-interacted', 'true');
                        updateNextButton();
                    }}
                </script>
'''
    else:
        left_label = config.get('left_label', 'Strongly Disagree')
        right_label = config.get('right_label', 'Strongly Agree')
        steps = config.get('steps', 7)
        default_val = config.get('default_value', int(steps / 2))
        
        html += f'''                <div class="slider-labels">
                    <span class="slider-min">{left_label}</span>
                    <span class="slider-max">{right_label}</span>
                </div>
                <input type="range" id="{section_id}_slider" name="{section_id}_response" 
                       min="1" max="{steps}" value="{default_val}" 
                       class="survey-slider" {required_attr} data-slider-interacted="false">
                <div class="slider-value-display">
                    <span id="{section_id}_value">{default_val}</span>
                </div>
                <script>
                    document.getElementById('{section_id}_slider').oninput = function() {{
                        document.getElementById('{section_id}_value').textContent = this.value;
                        this.setAttribute('data-slider-interacted', 'true');
                        updateNextButton();
                    }}
                </script>
'''
    
    html += '''            </div>
        </div>
'''
    return html

def generate_image_section(config, section_id):
    """Generate image display section HTML"""
    title = config.get('title', 'Image Display')
    description = config.get('description', '')
    file_path = config.get('file_path', '')
    alt_text = config.get('alt_text', 'Image')
    display_size = config.get('display_size', 'medium')
    alignment = config.get('alignment', 'center')
    require_response = config.get('require_response', False)
    
    size_class = {
        'small': 'image-small',
        'medium': 'image-medium', 
        'large': 'image-large',
        'full': 'image-full'
    }.get(display_size, 'image-medium')
    
    html = f'''
        <!-- Image Section -->
        <div class="survey-section" id="{section_id}-section">
            <div class="survey-section-title">{title}</div>
'''
    
    if description:
        html += f'            <div class="section-description">{description}</div>\n'
    
    if file_path:
        html += f'''            <div class="image-display {alignment}">
                <img src="{file_path}" alt="{alt_text}" class="{size_class}">
            </div>
'''
    else:
        html += '            <div class="image-placeholder">Image will be displayed here</div>\n'
    
    if require_response:
        response_type = config.get('response_type', 'rating')
        
        if response_type == 'rating':
            question = config.get('rating_question', 'How would you rate this image?')
            scale = config.get('rating_scale', 10)
            html += f'''            <div class="response-section">
                <label for="{section_id}_rating">{question}</label>
                <select id="{section_id}_rating" name="{section_id}_rating" required>
                    <option value="">Select rating...</option>
'''
            for i in range(1, scale + 1):
                html += f'                    <option value="{i}">{i}</option>\n'
            html += '                </select>\n            </div>\n'
            
        elif response_type == 'text':
            question = config.get('text_question', 'What are your thoughts about this image?')
            rows = config.get('text_rows', 4)
            html += f'''            <div class="response-section">
                <label for="{section_id}_text">{question}</label>
                <textarea id="{section_id}_text" name="{section_id}_text" rows="{rows}" required></textarea>
            </div>
'''
        elif response_type == 'checkbox':
            question = config.get('checkbox_question', 'Select all that apply to this image:')
            options = config.get('checkbox_options', [])
            html += f'''            <div class="response-section">
                <label>{question}</label>
'''
            for i, option in enumerate(options):
                html += f'''                <div class="checkbox-option">
                    <input type="checkbox" id="{section_id}_checkbox_{i}" name="{section_id}_checkbox[]" value="{option}">
                    <label for="{section_id}_checkbox_{i}">{option}</label>
                </div>
'''
            html += '            </div>\n'
    
    html += '        </div>\n'
    return html

def generate_video_section(config, section_id):
    """Generate video display section HTML"""
    title = config.get('title', 'Video Display')
    description = config.get('description', '')
    file_path = config.get('file_path', '')
    video_url = config.get('video_url', '')
    video_size = config.get('video_size', 'medium')
    autoplay = config.get('autoplay', False)
    controls = config.get('controls', True)
    loop = config.get('loop', False)
    require_response = config.get('require_response', False)
    
    size_attrs = {
        'small': 'width="400" height="300"',
        'medium': 'width="640" height="480"',
        'large': 'width="800" height="600"',
        'responsive': 'width="100%" height="auto"'
    }.get(video_size, 'width="640" height="480"')
    
    html = f'''
        <!-- Video Section -->
        <div class="survey-section" id="{section_id}-section">
            <div class="survey-section-title">{title}</div>
'''
    
    if description:
        html += f'            <div class="section-description">{description}</div>\n'
    # this external video stuff needs to be fixed i think
    if video_url:
        if 'youtube.com' in video_url or 'youtu.be' in video_url:
            video_id = video_url.split('/')[-1].split('?')[0].replace('watch?v=', '')
            html += f'''            <div class="video-display">
                <iframe {size_attrs} src="https://www.youtube.com/embed/{video_id}" 
                        frameborder="0" allowfullscreen></iframe>
            </div>
'''
        elif 'vimeo.com' in video_url:
            video_id = video_url.split('/')[-1]
            html += f'''            <div class="video-display">
                <iframe {size_attrs} src="https://player.vimeo.com/video/{video_id}" 
                        frameborder="0" allowfullscreen></iframe>
            </div>
'''
        else:
            html += f'''            <div class="video-display">
                <video {size_attrs} {"controls" if controls else ""} {"autoplay" if autoplay else ""} {"loop" if loop else ""}>
                    <source src="{video_url}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
'''
    elif file_path:
        html += f'''            <div class="video-display">
                <video {size_attrs} {"controls" if controls else ""} {"autoplay" if autoplay else ""} {"loop" if loop else ""}>
                    <source src="{file_path}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
'''
    else:
        html += '            <div class="video-placeholder">Video will be displayed here</div>\n'
    
    if require_response:
        response_type = config.get('response_type', 'rating')
        
        if response_type == 'rating':
            question = config.get('rating_question', 'How would you rate this video?')
            scale = config.get('rating_scale', 10)
            html += f'''            <div class="response-section">
                <label for="{section_id}_rating">{question}</label>
                <select id="{section_id}_rating" name="{section_id}_rating" required>
                    <option value="">Select rating...</option>
'''
            for i in range(1, scale + 1):
                html += f'                    <option value="{i}">{i}</option>\n'
            html += '                </select>\n            </div>\n'
            
        elif response_type == 'text':
            question = config.get('text_question', 'What are your thoughts about this video?')
            rows = config.get('text_rows', 4)
            html += f'''            <div class="response-section">
                <label for="{section_id}_text">{question}</label>
                <textarea id="{section_id}_text" name="{section_id}_text" rows="{rows}" required></textarea>
            </div>
'''
        elif response_type == 'checkbox':
            question = config.get('checkbox_question', 'Select all that apply to this video:')
            options = config.get('checkbox_options', [])
            html += f'''            <div class="response-section">
                <label>{question}</label>
'''
            for i, option in enumerate(options):
                html += f'''                <div class="checkbox-option">
                    <input type="checkbox" id="{section_id}_checkbox_{i}" name="{section_id}_checkbox[]" value="{option}">
                    <label for="{section_id}_checkbox_{i}">{option}</label>
                </div>
'''
            html += '            </div>\n'
    
    html += '        </div>\n'
    return html

def generate_pdf_section(config, section_id):
    """Generate PDF display section HTML"""
    title = config.get('title', 'PDF Display')
    description = config.get('description', '')
    file_path = config.get('file_path', '')
    display_height = config.get('display_height', '600')
    display_mode = config.get('display_mode', 'embed')
    allow_download = config.get('allow_download', True)
    require_view = config.get('require_view', False)
    require_response = config.get('require_response', False)
    
    html = f'''
        <!-- PDF Section -->
        <div class="survey-section" id="{section_id}-section">
            <div class="survey-section-title">{title}</div>
'''
    
    if description:
        html += f'            <div class="section-description">{description}</div>\n'
    
    if file_path:
        if display_mode in ['embed', 'both']:
            height_attr = f'height="{display_height}px"' if display_height != 'auto' else 'style="height: auto;"'
            html += f'''            <div class="pdf-display">
                <iframe src="{file_path}" width="100%" {height_attr} 
                        frameborder="0">
                    <p>Your browser does not support PDFs. 
                    <a href="{file_path}" target="_blank">Download the PDF</a>.</p>
                </iframe>
            </div>
'''
        
        if display_mode in ['link', 'both'] or allow_download:
            html += f'''            <div class="pdf-download">
                <a href="{file_path}" target="_blank" class="download-link">Download PDF</a>
            </div>
'''
    else:
        html += '            <div class="pdf-placeholder">PDF will be displayed here</div>\n'
    
    if require_response:
        response_type = config.get('response_type', 'confirmation')
        
        if response_type == 'confirmation':
            confirmation_text = config.get('confirmation_text', 'I have read and understood the document')
            html += f'''            <div class="response-section">
                <div class="checkbox-option">
                    <input type="checkbox" id="{section_id}_confirmation" name="{section_id}_response" value="confirmed" required>
                    <label for="{section_id}_confirmation">{confirmation_text}</label>
                </div>
            </div>
'''
        elif response_type == 'rating':
            question = config.get('rating_question', 'How would you rate this document?')
            scale = config.get('rating_scale', 10)
            html += f'''            <div class="response-section">
                <label for="{section_id}_rating">{question}</label>
                <select id="{section_id}_rating" name="{section_id}_rating" required>
                    <option value="">Select rating...</option>
'''
            for i in range(1, scale + 1):
                html += f'                    <option value="{i}">{i}</option>\n'
            html += '                </select>\n            </div>\n'
            
        elif response_type == 'text':
            question = config.get('text_question', 'What are your thoughts about this document?')
            rows = config.get('text_rows', 4)
            html += f'''            <div class="response-section">
                <label for="{section_id}_text">{question}</label>
                <textarea id="{section_id}_text" name="{section_id}_text" rows="{rows}" required></textarea>
            </div>
'''
        elif response_type == 'checkbox':
            question = config.get('checkbox_question', 'Select all that apply to this document:')
            options = config.get('checkbox_options', [])
            html += f'''            <div class="response-section">
                <label>{question}</label>
'''
            for i, option in enumerate(options):
                html += f'''                <div class="checkbox-option">
                    <input type="checkbox" id="{section_id}_checkbox_{i}" name="{section_id}_checkbox[]" value="{option}">
                    <label for="{section_id}_checkbox_{i}">{option}</label>
                </div>
'''
            html += '            </div>\n'
    
    html += '        </div>\n'
    return html

# Branding Configuration Routes
@app.route('/get-branding-settings', methods=['GET'])
def get_branding_settings():
    """Get current branding settings"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    #  all branding settings
    branding_keys = [
        'login_title', 'login_footer_line1', 'login_footer_line2', 'login_footer_line3',
        'chat_header_line1', 'chat_header_line2'
    ]
    
    settings = {}
    for key in branding_keys:
        c.execute('SELECT setting_value FROM url_settings WHERE setting_name = ?', (key,))
        result = c.fetchone()
        if result:
            settings[key] = result[0]
    
    conn.close()
    
    default_settings = {
        'login_title': 'Artificial Intelligence <br>Gateway',
        'login_footer_line1': 'chatPsych',
        'login_footer_line2': 'Powered by',
        'login_footer_line3': 'The Australian Institute for Machine Learning',
        'chat_header_line1': 'Australian Institute for Machine&nbsp;Learning',
        'chat_header_line2': 'chatPsych'
    }
    
    for key, default_value in default_settings.items():
        if key not in settings:
            settings[key] = default_value
    
    return jsonify(settings)

@app.route('/update-branding-settings', methods=['POST'])
def update_branding_settings():
    """Update branding settings"""
    data = request.json
    
    required_fields = [
        'login_title', 'login_footer_line1', 'login_footer_line2', 'login_footer_line3',
        'chat_header_line1', 'chat_header_line2'
    ]
    
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'error': f'{field} is required'}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        for field in required_fields:
            value = data[field].strip()
            c.execute('INSERT OR REPLACE INTO url_settings (setting_name, setting_value) VALUES (?, ?)', 
                      (field, value))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Branding settings updated successfully'})
    except Exception as e:
        app.logger.error(f"Error updating branding settings: {e}")
        return jsonify({'error': 'Error updating branding settings'}), 500

@app.route('/reset-branding-settings', methods=['POST'])
def reset_branding_settings():
    """Reset branding settings to defaults"""
    try:
        default_settings = {
            'login_title': 'Artificial Intelligence <br>Gateway',
            'login_footer_line1': 'chatPsych',
            'login_footer_line2': 'Powered by',
            'login_footer_line3': 'The Australian Institute for Machine Learning',
            'chat_header_line1': 'Australian Institute for Machine&nbsp;Learning',
            'chat_header_line2': 'chatPsych'
        }
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        for key, value in default_settings.items():
            c.execute('INSERT OR REPLACE INTO url_settings (setting_name, setting_value) VALUES (?, ?)', 
                      (key, value))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Branding settings reset to defaults'})
    except Exception as e:
        app.logger.error(f"Error resetting branding settings: {e}")
        return jsonify({'error': 'Error resetting branding settings'}), 500
    
##### if your name is Josh de Leeuw and you're reading this--hi, I'm honoured you're looking at the codebase!

if __name__ == '__main__':
    print("Starting chatPsych...")
    print("Validating environment variables...")
    
    if not validate_env_variables():
        print("Environment validation failed. Please check your .env file.")
        print("Required variables: FLASK_SECRET_KEY, researcher_username, researcher_password")
    else:
        print("Environment validated successfully.")
        print(f"Researcher username: {os.environ.get('researcher_username')}")
    
    init_db()
    init_default_url_settings()  
    init_default_branding_settings() 
    
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask app on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)