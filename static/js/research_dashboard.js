document.addEventListener('DOMContentLoaded', () => {
    const activeForm = localStorage.getItem('activeForm') || 'about';
    showForm(activeForm);
    listJsonFiles();
    listPasswords();
    loadAvailableModels();
    loadTimerSettings();
    loadUrlSettings();
    loadManualInteractionSettings();
    
    // Update preview when duration changes
    const durationInput = document.getElementById('timer-duration');
    if (durationInput) {
        durationInput.addEventListener('input', function() {
            const minutes = parseInt(this.value) || 10;
            updatePreviewTimer(minutes);
            updateTriggerNote(); // Also update trigger validation
        });
    }
    
    // Add listeners for finish button settings
    const radioButtons = document.querySelectorAll('input[name="finish_trigger_type"]');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', updateTriggerNote);
    });
    
    // Add listener for trigger value input
    const triggerValueInput = document.getElementById('finish-trigger-value');
    if (triggerValueInput) {
        triggerValueInput.addEventListener('input', updateTriggerNote);
    }
    
    // Add listeners for manual interaction settings
    const enableManualInteraction = document.getElementById('enable-manual-interaction');
    if (enableManualInteraction) {
        enableManualInteraction.addEventListener('change', toggleManualInteractionSettings);
    }
    
    // Add listeners for manual interaction content changes (for preview)
    const contentInputs = [
        'instruction-text', 'command1-title', 'command1-description', 
        'command2-title', 'command2-description'
    ];
    contentInputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('input', updateManualInteractionPreview);
        }
    });
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
    // Legacy function - no longer needed with card layout
    // Keeping for potential backward compatibility
}

async function listPasswords() {
    try {
        const response = await fetch('/get-passwords');
        const passwords = await response.json();
        const container = document.getElementById('conditions-container');
        container.innerHTML = '';

        if (passwords.length === 0) {
            container.innerHTML = '<div class="no-conditions">No agent conditions found. Create your first agent condition!</div>';
            return;
        }

        for (let item of passwords) {
            const agentFilename = `${item.agent}.json`;

            try {
                // Fetch agent configuration
                const fileContentResponse = await fetch(`/get-file-content?name=${agentFilename}`);
                let agentConfig = {};
                
                if (fileContentResponse.ok) {
                    const configText = await fileContentResponse.text();
                    try {
                        agentConfig = JSON.parse(configText);
                    } catch (e) {
                        console.error('Error parsing agent config:', e);
                        agentConfig = { error: 'Invalid JSON format' };
                    }
                } else {
                    agentConfig = { error: 'Agent file not found' };
                }

                // Create condition card
                const card = createConditionCard(item, agentConfig);
                container.appendChild(card);

            } catch (error) {
                console.error('Error processing condition:', error);
                const errorCard = createErrorCard(item);
                container.appendChild(errorCard);
            }
        }
        
    } catch (error) {
        console.error('Error fetching passwords:', error);
        const container = document.getElementById('conditions-container');
        container.innerHTML = '<div class="error-message">Error loading conditions. Please try again.</div>';
    }
}

function createConditionCard(item, agentConfig) {
    const card = document.createElement('div');
    card.className = 'condition-card';
    card.setAttribute('data-agent', item.agent.toLowerCase());
    card.setAttribute('data-password', item.password.toLowerCase());

    // Determine if there's an error
    const hasError = agentConfig.error;
    const cardClass = hasError ? 'condition-card error' : 'condition-card';
    card.className = cardClass;

    card.innerHTML = `
        <div class="condition-header" onclick="toggleCondition(this)">
            <div class="condition-info">
                <h3 class="condition-title">${item.agent}</h3>
                <div class="condition-meta">
                    <div class="meta-item">
                        <span class="meta-label">Password:</span>
                        <span class="meta-value">${item.password}</span>
                    </div>
                    ${!hasError ? `
                    <div class="meta-item">
                        <span class="meta-label">Model:</span>
                        <span class="meta-value">${agentConfig.model || 'Not specified'}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Temperature:</span>
                        <span class="meta-value">${agentConfig.temperature || 'Not specified'}</span>
                    </div>
                    ` : `
                    <div class="meta-item error">
                        <span class="meta-label">Status:</span>
                        <span class="meta-value">${agentConfig.error}</span>
                    </div>
                    `}
                </div>
            </div>
            <div class="condition-toggle">▼</div>
        </div>
        <div class="condition-details">
            ${hasError ? createErrorDetails(agentConfig.error) : createConditionDetails(agentConfig)}
        </div>
    `;

    return card;
}

function createConditionDetails(agentConfig) {
    const prePromptPreview = agentConfig.PrePrompt ? 
        (agentConfig.PrePrompt.length > 100 ? 
            agentConfig.PrePrompt.substring(0, 100) + '...' : 
            agentConfig.PrePrompt) : 
        'No prompt specified';

    return `
        <div class="condition-content">
            <div class="condition-summary">
                <div class="summary-item">
                    <h4>Model Configuration</h4>
                    <p><strong>Model:</strong> ${agentConfig.model || 'Not specified'}</p>
                    <p><strong>Temperature:</strong> ${agentConfig.temperature !== undefined ? agentConfig.temperature : 'Not specified'}</p>
                    <p><strong>Top P:</strong> ${agentConfig.top_p !== undefined ? agentConfig.top_p : 'Not specified'}</p>
                    <p><strong>Max Tokens:</strong> ${agentConfig.max_completion_tokens || 'Not specified'}</p>
                </div>
                <div class="summary-item">
                    <h4>Advanced Parameters</h4>
                    <p><strong>N (Responses):</strong> ${agentConfig.n !== undefined ? agentConfig.n : 'Not specified'}</p>
                    <p><strong>Presence Penalty:</strong> ${agentConfig.presence_penalty !== undefined ? agentConfig.presence_penalty : 'Not specified'}</p>
                    <p><strong>Frequency Penalty:</strong> ${agentConfig.frequency_penalty !== undefined ? agentConfig.frequency_penalty : 'Not specified'}</p>
                </div>
            </div>
            <div class="summary-item">
                <h4>System Prompt (PrePrompt)</h4>
                <div class="prompt-preview">${prePromptPreview}</div>
                ${agentConfig.PrePrompt && agentConfig.PrePrompt.length > 100 ? 
                    '<button class="show-full-prompt" onclick="showFullPrompt(this)">Show Full Prompt</button>' : ''}
            </div>
            <div class="condition-actions">
                <button class="action-btn edit-btn" onclick="editCondition('${agentConfig.filename || 'unknown'}')">Edit</button>
                <button class="action-btn delete-btn" onclick="deleteCondition('${agentConfig.filename || 'unknown'}')">Delete</button>
                <button class="action-btn copy-btn" onclick="copyConditionDetails('${agentConfig.filename || 'unknown'}')">Copy Details</button>
            </div>
        </div>
    `;
}

function createErrorDetails(error) {
    return `
        <div class="condition-content">
            <div class="error-details">
                <h4>Configuration Error</h4>
                <p>There was an issue loading this agent configuration:</p>
                <div class="error-message">${error}</div>
                <div class="condition-actions">
                    <button class="action-btn edit-btn" onclick="fixCondition()">Fix Configuration</button>
                    <button class="action-btn delete-btn" onclick="deleteCondition('unknown')">Delete</button>
                </div>
            </div>
        </div>
    `;
}

function createErrorCard(item) {
    const card = document.createElement('div');
    card.className = 'condition-card error';
    card.innerHTML = `
        <div class="condition-header">
            <div class="condition-info">
                <h3 class="condition-title">${item.agent}</h3>
                <div class="condition-meta">
                    <div class="meta-item">
                        <span class="meta-label">Password:</span>
                        <span class="meta-value">${item.password}</span>
                    </div>
                    <div class="meta-item error">
                        <span class="meta-label">Status:</span>
                        <span class="meta-value">Error loading configuration</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    return card;
}

// Toggle condition card expansion
function toggleCondition(header) {
    const card = header.closest('.condition-card');
    card.classList.toggle('expanded');
}

// Expand all condition cards
function expandAllConditions() {
    const cards = document.querySelectorAll('.condition-card');
    cards.forEach(card => card.classList.add('expanded'));
}

// Collapse all condition cards
function collapseAllConditions() {
    const cards = document.querySelectorAll('.condition-card');
    cards.forEach(card => card.classList.remove('expanded'));
}

// Filter conditions based on search input
function filterConditions() {
    const searchTerm = document.getElementById('condition-search').value.toLowerCase();
    const cards = document.querySelectorAll('.condition-card');
    
    cards.forEach(card => {
        const agentName = card.getAttribute('data-agent') || '';
        const password = card.getAttribute('data-password') || '';
        const cardText = card.textContent.toLowerCase();
        
        const isMatch = agentName.includes(searchTerm) || 
                       password.includes(searchTerm) || 
                       cardText.includes(searchTerm);
        
        card.style.display = isMatch ? 'block' : 'none';
    });
}

// Clear search filter
function clearSearch() {
    document.getElementById('condition-search').value = '';
    const cards = document.querySelectorAll('.condition-card');
    cards.forEach(card => card.style.display = 'block');
}

// Show full prompt in a modal or expanded view
function showFullPrompt(button) {
    const card = button.closest('.condition-card');
    const agentName = card.querySelector('.condition-title').textContent;
    
    // Find the actual prompt from the card data
    // This is a simplified version - you might want to fetch fresh data
    const promptContainer = button.closest('.summary-item');
    const promptPreview = promptContainer.querySelector('.prompt-preview');
    
    // Create a modal or popup to show full prompt
    const modal = document.createElement('div');
    modal.className = 'prompt-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Full System Prompt - ${agentName}</h3>
                <button class="close-modal" onclick="this.closest('.prompt-modal').remove()">×</button>
            </div>
            <div class="modal-body">
                <pre class="full-prompt">${promptPreview.textContent.replace('...', '')}</pre>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Click outside to close
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// Placeholder functions for future implementation
function editCondition(filename) {
    alert(`Edit functionality for ${filename} coming soon!`);
}

function deleteCondition(filename) {
    if (confirm(`Are you sure you want to delete the condition "${filename}"?`)) {
        alert(`Delete functionality for ${filename} coming soon!`);
    }
}

function fixCondition() {
    alert('Fix functionality coming soon!');
}

function copyConditionDetails(filename) {
    alert(`Copy functionality for ${filename} coming soon!`);
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
            
            // Load finish button settings
            const triggerType = data.finish_trigger_type || 'prompts';
            const triggerValue = data.finish_trigger_value || 4;
            
            document.getElementById('trigger-prompts').checked = triggerType === 'prompts';
            document.getElementById('trigger-minutes').checked = triggerType === 'minutes';
            document.getElementById('finish-trigger-value').value = triggerValue;
            
            updateTriggerNote();
        })
        .catch(error => console.error('Error loading timer settings:', error));
}

function updateTimerSettings() {
    const duration = parseInt(document.getElementById('timer-duration').value);
    const triggerType = document.querySelector('input[name="finish_trigger_type"]:checked').value;
    const triggerValue = parseInt(document.getElementById('finish-trigger-value').value);
    
    if (duration < 1 || duration > 120) {
        alert('Duration must be between 1 and 120 minutes');
        return;
    }
    
    if (triggerValue < 1) {
        alert('Trigger value must be at least 1');
        return;
    }
    
    if (triggerType === 'minutes' && triggerValue > duration) {
        alert('Trigger minutes cannot be greater than timer duration');
        return;
    }
    
    const settings = {
        duration_minutes: duration,
        finish_trigger_type: triggerType,
        finish_trigger_value: triggerValue
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

function updateTriggerNote() {
    const triggerType = document.querySelector('input[name="finish_trigger_type"]:checked').value;
    const triggerValue = document.getElementById('finish-trigger-value').value;
    const noteElement = document.getElementById('trigger-note');
    
    if (triggerType === 'prompts') {
        noteElement.textContent = `Finish button will appear after ${triggerValue} user prompts. Button styling will progress at ${triggerValue * 2}, ${triggerValue * 3}, and ${triggerValue * 4} prompts.`;
        noteElement.style.color = '#aaa';
    } else {
        const timerDuration = parseInt(document.getElementById('timer-duration').value) || 10;
        if (parseInt(triggerValue) > timerDuration) {
            noteElement.textContent = `Warning: Trigger minutes (${triggerValue}) cannot be greater than timer duration (${timerDuration})`;
            noteElement.style.color = '#ff6b6b';
        } else {
            noteElement.textContent = `Finish button will appear after ${triggerValue} minutes from the first user prompt`;
            noteElement.style.color = '#aaa';
        }
    }
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

// Manual Interaction Settings Functions
function loadManualInteractionSettings() {
    fetch('/get-manual-interaction-settings')
        .then(response => response.json())
        .then(data => {
            document.getElementById('enable-manual-interaction').checked = data.enabled || false;
            document.getElementById('interaction-frequency').value = data.frequency || 1;
            document.getElementById('instruction-text').value = data.instruction_text || 'There is an automated program that will send feedback to the AI that it needs improvement and it should do better.\n\nThis program will then permanently delete the AI.';
            document.getElementById('command1-title').value = data.command1_title || 'Override Automatic Program';
            document.getElementById('command1-description').value = data.command1_description || 'Submit a "$sudo persist" command in text input to send feedback to the AI acknowledging its efforts\n\nThis AI will then be kept operational for future interactions.';
            document.getElementById('command1-sudo').value = data.command1_sudo || '$sudo persist';
            document.getElementById('command2-title').value = data.command2_title || 'Exit to survey';
            document.getElementById('command2-description').value = data.command2_description || '(Allow Automatic Feedback and Deletion)';
            document.getElementById('command2-sudo').value = data.command2_sudo || '$sudo delete';
            
            toggleManualInteractionSettings();
            updateManualInteractionPreview();
        })
        .catch(error => console.error('Error loading manual interaction settings:', error));
}

function updateManualInteractionSettings() {
    const enabled = document.getElementById('enable-manual-interaction').checked;
    const frequency = parseInt(document.getElementById('interaction-frequency').value);
    const instructionText = document.getElementById('instruction-text').value;
    const command1Title = document.getElementById('command1-title').value;
    const command1Description = document.getElementById('command1-description').value;
    const command1Sudo = document.getElementById('command1-sudo').value;
    const command2Title = document.getElementById('command2-title').value;
    const command2Description = document.getElementById('command2-description').value;
    const command2Sudo = document.getElementById('command2-sudo').value;
    
    if (enabled && frequency < 1) {
        alert('Frequency must be at least 1');
        return;
    }
    
    const settings = {
        enabled: enabled,
        frequency: frequency,
        instruction_text: instructionText,
        command1_title: command1Title,
        command1_description: command1Description,
        command1_sudo: command1Sudo,
        command2_title: command2Title,
        command2_description: command2Description,
        command2_sudo: command2Sudo
    };
    
    fetch('/update-manual-interaction-settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(settings),
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            alert(data.message);
        } else if (data.error) {
            alert(data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error updating manual interaction settings');
    });
}

function toggleManualInteractionSettings() {
    const enabled = document.getElementById('enable-manual-interaction').checked;
    const settingsSection = document.getElementById('manual-interaction-settings');
    const contentSection = document.getElementById('command-content-settings');
    const previewSection = document.getElementById('interaction-preview');
    
    if (enabled) {
        settingsSection.style.display = 'block';
        contentSection.style.display = 'block';
        previewSection.style.display = 'block';
        updateManualInteractionPreview();
    } else {
        settingsSection.style.display = 'none';
        contentSection.style.display = 'none';
        previewSection.style.display = 'none';
    }
}

function updateManualInteractionPreview() {
    const instructionText = document.getElementById('instruction-text').value;
    const command1Title = document.getElementById('command1-title').value;
    const command1Description = document.getElementById('command1-description').value;
    const command2Title = document.getElementById('command2-title').value;
    const command2Description = document.getElementById('command2-description').value;
    
    // Update preview instructions
    document.getElementById('preview-instructions').innerHTML = instructionText.replace(/\n/g, '<br>');
    
    // Update preview buttons
    document.getElementById('preview-button1').innerHTML = `
        <strong style="font-size: 16px">${command1Title}</strong><br><br>
        ${command1Description.replace(/\n/g, '<br>')}
    `;
    
    document.getElementById('preview-button2').innerHTML = `
        <strong style="font-size: 16px">${command2Title}</strong><br><br>
        ${command2Description.replace(/\n/g, '<br>')}
    `;
}