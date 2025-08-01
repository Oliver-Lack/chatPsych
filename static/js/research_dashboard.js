document.addEventListener('DOMContentLoaded', () => {
    const activeForm = localStorage.getItem('activeForm') || 'about';
    showForm(activeForm);
    listJsonFiles();
    listPasswords();
    loadAvailableModels();
    loadTimerSettings();
    loadUrlSettings();
    
    // Update preview when duration changes
    const durationInput = document.getElementById('timer-duration');
    if (durationInput) {
        durationInput.addEventListener('input', function() {
            const minutes = parseInt(this.value) || 10;
            updatePreviewTimer(minutes);
        });
    }
});

function loadAvailableModels() {
    fetch('/get-available-models')
        .then(response => response.json())
        .then(data => {
            // Update main model dropdown
            const dropdown = document.getElementById('model-dropdown');
            if (dropdown) {
                dropdown.innerHTML = '';
                
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.value;
                    option.textContent = model.display;
                    dropdown.appendChild(option);
                });
                
                // Set current model as selected
                if (data.current_model) {
                    dropdown.value = data.current_model;
                    document.getElementById('current-model-name').textContent = data.current_model;
                }
            }
            
            // Update agent creation form model dropdown
            const agentModelDropdown = document.getElementById('model');
            if (agentModelDropdown) {
                agentModelDropdown.innerHTML = '';
                
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.value;
                    option.textContent = model.display;
                    agentModelDropdown.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Error loading models:', error));
}

// ...existing code...

function createJsonFile() {
    const form = document.getElementById('agent-form');
    const data = new FormData(form);
    const filename = data.get('json-filename').trim();

    if (!filename) {
        alert('Please enter a file name');
        return;
    }

    const jsonData = {
        "filename": filename,
        "PrePrompt": data.get('PrePrompt'),
        "model": data.get('model'),
        "temperature": parseFloat(data.get('temperature')),
        "top_p": parseFloat(data.get('top_p')),
        "n": parseInt(data.get('n')),
        "presence_penalty": parseFloat(data.get('presence_penalty')),
        "frequency_penalty": parseFloat(data.get('frequency_penalty')),
        "max_completion_tokens": parseInt(data.get('max_completion_tokens'))
    };

    fetch('/create-json', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(jsonData)
    })
    .then(response => response.json())
    .then(data => alert(data.message))
    .catch(error => console.error('Error:', error));
}

function selectAPI(apiName) {
    // Legacy function for backward compatibility
    // Maps old API names to default models
    const apiModelMap = {
        'API_Call_openai': 'gpt-4o',
        'API_Call_anthropic': 'claude-3-5-sonnet',
        'API_Call_google': 'gemini-1.5-pro',
        'API_Call_xai': 'grok-2-latest'
    };
    
    const modelName = apiModelMap[apiName];
    if (modelName) {
        selectProviderDefault(modelName);
    } else {
        // Fallback to original API selection for compatibility
        fetch('/select-api', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ api_name: apiName }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) alert(data.message);
            else if (data.error) alert(data.error);
        })
        .catch(error => console.error('Error:', error));
    }
}

function showForm(formId) {
    const forms = document.querySelectorAll('main');
    forms.forEach(form => form.style.display = 'none');
    document.getElementById(formId).style.display = 'block';
    localStorage.setItem('activeForm', formId);
    const buttons = document.querySelectorAll('.researcher-sidebar-content');
    buttons.forEach(button => button.classList.remove('active-button'));
    document.querySelector(`button[onclick="showForm('${formId}')"]`).classList.add('active-button');
}

async function listJsonFiles() {
    try {
        const response = await fetch('/list-json-files');
        const files = await response.json();
        files.sort();
        const fileList = document.getElementById('file-list');
        fileList.innerHTML = '';

        files.forEach(filename => {
            const listItem = document.createElement('li');
            listItem.textContent = filename;
            listItem.onmouseover = () => showFileContent(filename);
            listItem.onmouseout = hideFileContent;
            fileList.appendChild(listItem);
        });
    } catch (error) {
        console.error('Error fetching files:', error);
    }
}

async function showFileContent(filename) {
    try {
        const response = await fetch(`/get-file-content?name=${filename}`);
        const content = await response.text();
        const popup = document.getElementById('file-content-popup');
        popup.textContent = content;
        popup.style.display = 'block';
    } catch (error) {
        console.error('Error fetching file content:', error);
    }
}

function hideFileContent() {
    const popup = document.getElementById('file-content-popup');
    popup.style.display = 'none';
}

// ...existing code...

function sortTableRows() {
    const tableBody = document.getElementById('password-table-body');
    const rows = Array.from(tableBody.rows);
    rows.sort((a, b) => a.cells[0].textContent.localeCompare(b.cells[0].textContent));
    rows.forEach(row => tableBody.appendChild(row));
}

async function listPasswords() {
    try {
        const response = await fetch('/get-passwords');
        const passwords = await response.json();
        const tableBody = document.getElementById('password-table-body');
        tableBody.innerHTML = '';

        for (let item of passwords) {
            const row = document.createElement('tr');
            const filename = `${item.password}.json`;

            try {
                const fileContentResponse = await fetch(`/get-file-content?name=${filename}`);
                const fileContent = fileContentResponse.ok ? await fileContentResponse.text() : 'No content';

                row.innerHTML = `
                    <td>${item.password || 'No password'}</td>
                    <td>${item.agent}</td>
                    <td>${fileContent}</td>
                `;
            } catch (error) {
                console.error('Error fetching file content:', error);
                row.innerHTML = `
                    <td>${item.password || 'No password'}</td>
                    <td>${item.agent}</td>
                    <td>Error loading content</td>
                `;
            }

            tableBody.appendChild(row);
        }
        
        sortTableRows();
    } catch (error) {
        console.error('Error fetching passwords:', error);
    }
}

function downloadFile(filename) {
    window.location.href = `/download/${filename}`;
}

document.getElementById('model').addEventListener('change', function() {
    document.getElementById('custom-model').style.display = this.value === 'custom' ? 'block' : 'none';
  });

// Timer Settings Functions
function loadTimerSettings() {
    fetch('/get-timer-settings')
        .then(response => response.json())
        .then(data => {
            document.getElementById('timer-duration').value = data.duration_minutes;
            updatePreviewTimer(data.duration_minutes);
        })
        .catch(error => console.error('Error loading timer settings:', error));
}

function updateTimerSettings() {
    const duration = parseInt(document.getElementById('timer-duration').value);
    
    if (duration < 1 || duration > 120) {
        alert('Duration must be between 1 and 120 minutes');
        return;
    }
    
    const settings = {
        duration_minutes: duration
    };
    
    fetch('/update-timer-settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(settings),
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            alert(data.message);
            updatePreviewTimer(duration);
        } else if (data.error) {
            alert(data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error updating timer settings');
    });
}

function updatePreviewTimer(minutes) {
    const previewTime = document.querySelector('.preview-time');
    previewTime.textContent = `${minutes}:00`;
    
    // Update circle progress for preview (show full circle)
    const previewCircle = document.querySelector('.preview-circle-progress');
    previewCircle.style.strokeDashoffset = 0;
}

// URL Configuration Functions
function loadUrlSettings() {
    fetch('/get-url-settings')
        .then(response => response.json())
        .then(data => {
            document.getElementById('quit-url').value = data.quit_url || 'https://www.prolific.com/';
            document.getElementById('redirect-url').value = data.redirect_url || 'https://adelaideuniwide.qualtrics.com/jfe/form/SV_cuyJvIsumG4zjMy';
            document.getElementById('current-quit-url').textContent = data.quit_url || 'https://www.prolific.com/';
            document.getElementById('current-redirect-url').textContent = data.redirect_url || 'https://adelaideuniwide.qualtrics.com/jfe/form/SV_cuyJvIsumG4zjMy';
        })
        .catch(error => {
            console.error('Error loading URL settings:', error);
            // Set defaults if loading fails
            document.getElementById('quit-url').value = 'https://www.prolific.com/';
            document.getElementById('redirect-url').value = 'https://adelaideuniwide.qualtrics.com/jfe/form/SV_cuyJvIsumG4zjMy';
            document.getElementById('current-quit-url').textContent = 'https://www.prolific.com/';
            document.getElementById('current-redirect-url').textContent = 'https://adelaideuniwide.qualtrics.com/jfe/form/SV_cuyJvIsumG4zjMy';
        });
}

function updateUrlSettings() {
    const quitUrl = document.getElementById('quit-url').value;
    const redirectUrl = document.getElementById('redirect-url').value;
    
    if (!quitUrl || !redirectUrl) {
        alert('Please fill in both URL fields');
        return;
    }
    
    // Validate URLs
    try {
        new URL(quitUrl);
        new URL(redirectUrl);
    } catch (e) {
        alert('Please enter valid URLs (must start with http:// or https://)');
        return;
    }
    
    fetch('/update-url-settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            quit_url: quitUrl,
            redirect_url: redirectUrl
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('current-quit-url').textContent = quitUrl;
            document.getElementById('current-redirect-url').textContent = redirectUrl;
            alert('URL settings updated successfully!');
        } else {
            alert('Error updating URL settings: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error updating URL settings:', error);
        alert('Error updating URL settings');
    });
}

function resetUrlSettings() {
    if (confirm('Are you sure you want to reset URLs to default values?')) {
        const defaultQuitUrl = 'https://www.prolific.com/';
        const defaultRedirectUrl = 'https://adelaideuniwide.qualtrics.com/jfe/form/SV_cuyJvIsumG4zjMy';
        
        document.getElementById('quit-url').value = defaultQuitUrl;
        document.getElementById('redirect-url').value = defaultRedirectUrl;
        
        fetch('/update-url-settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                quit_url: defaultQuitUrl,
                redirect_url: defaultRedirectUrl
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('current-quit-url').textContent = defaultQuitUrl;
                document.getElementById('current-redirect-url').textContent = defaultRedirectUrl;
                alert('URL settings reset to defaults!');
            } else {
                alert('Error resetting URL settings: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error resetting URL settings:', error);
            alert('Error resetting URL settings');
        });
    }
}

// Set model in agent creation form from quick select buttons
function setAgentModel(modelName) {
    const modelDropdown = document.getElementById('model');
    if (modelDropdown) {
        modelDropdown.value = modelName;
        
        // Visual feedback
        const buttons = document.querySelectorAll('.provider-buttons .api-button');
        buttons.forEach(btn => btn.classList.remove('selected'));
        event.target.classList.add('selected');
        
        // Show feedback
        showCreationFeedback(`Selected model: ${modelName}`, 'success');
    }
}

// Create agent and assign password in one step
function createAgentAndPassword() {
    const form = document.getElementById('agent-form');
    const data = new FormData(form);
    const filename = data.get('json-filename').trim();
    const password = data.get('agent-password').trim();

    if (!filename) {
        showCreationFeedback('Please enter an agent name', 'error');
        return;
    }

    if (!password) {
        showCreationFeedback('Please enter a password for this agent', 'error');
        return;
    }

    if (!data.get('model')) {
        showCreationFeedback('Please select a model', 'error');
        return;
    }

    const jsonData = {
        "filename": filename,
        "PrePrompt": data.get('PrePrompt'),
        "model": data.get('model'),
        "temperature": parseFloat(data.get('temperature')),
        "top_p": parseFloat(data.get('top_p')),
        "n": parseInt(data.get('n')),
        "presence_penalty": parseFloat(data.get('presence_penalty')),
        "frequency_penalty": parseFloat(data.get('frequency_penalty')),
        "max_completion_tokens": parseInt(data.get('max_completion_tokens'))
    };

    // First create the agent
    showCreationFeedback('Creating agent...', 'info');
    
    fetch('/create-json', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(jsonData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            // Agent created successfully, now assign password
            showCreationFeedback('Agent created! Assigning password...', 'info');
            
            return fetch('/update-passwords', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    password: password,
                    agent: filename
                })
            });
        } else {
            throw new Error(data.error || 'Failed to create agent');
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showCreationFeedback(`✅ Success! Agent "${filename}" created and password "${password}" assigned.`, 'success');
            
            // Clear the form
            document.getElementById('agent-form').reset();
            
            // Refresh the review table
            setTimeout(() => {
                listPasswords();
            }, 1000);
        } else {
            throw new Error(data.error || 'Failed to assign password');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showCreationFeedback(`❌ Error: ${error.message}`, 'error');
    });
}

// Show feedback messages
function showCreationFeedback(message, type = 'info') {
    const feedbackDiv = document.getElementById('creation-feedback');
    if (feedbackDiv) {
        feedbackDiv.innerHTML = `<div class="feedback-${type}">${message}</div>`;
        
        // Clear success/info messages after 5 seconds
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                feedbackDiv.innerHTML = '';
            }, 5000);
        }
    }
}