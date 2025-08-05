document.addEventListener('DOMContentLoaded', () => {
    const activeForm = localStorage.getItem('activeForm') || 'about';
    showForm(activeForm);
    listJsonFiles();
    listPasswords();
    loadAvailableModels();
    loadTimerSettings();
    loadUrlSettings();
    checkUploadedFiles(); // Check for existing uploaded files on page load
    
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

function downloadSurveyFile(filename) {
    if (filename === 'survey.json') {
        window.location.href = '/download-survey-json';
    } else if (filename === 'survey.csv') {
        window.location.href = '/download-survey-csv';
    }
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

// Survey Configuration Functions
function toggleSectionExpanded(sectionName) {
    const section = document.querySelector(`[data-section="${sectionName}"] .section-content`);
    const button = document.querySelector(`[data-section="${sectionName}"] .btn-small`);
    
    if (section.classList.contains('expanded')) {
        section.classList.remove('expanded');
        button.textContent = '▶';
    } else {
        section.classList.add('expanded');
        button.textContent = '▼';
    }
}

function addLikertItem() {
    const container = document.getElementById('likert-items');
    const newItem = document.createElement('div');
    newItem.className = 'likert-item';
    newItem.innerHTML = `
        <input type="text" placeholder="Enter statement">
        <button type="button" class="btn-remove" onclick="removeLikertItem(this)">×</button>
    `;
    container.appendChild(newItem);
}

function removeLikertItem(button) {
    button.parentElement.remove();
}

function addFreetextQuestion() {
    const container = document.getElementById('freetext-questions');
    const newQuestion = document.createElement('div');
    newQuestion.className = 'freetext-question';
    newQuestion.innerHTML = `
        <label>Question:</label>
        <input type="text" placeholder="Enter question">
        <label>Text area rows:</label>
        <input type="number" value="4" min="1" max="20" style="width: 60px;">
        <button type="button" class="btn-remove" onclick="removeFreetextQuestion(this)">×</button>
    `;
    container.appendChild(newQuestion);
}

function removeFreetextQuestion(button) {
    button.parentElement.remove();
}

function addCustomDemographicField() {
    const container = document.getElementById('custom-demographic-fields');
    const newField = document.createElement('div');
    newField.className = 'field-config';
    newField.innerHTML = `
        <input type="text" placeholder="Field name" style="width: 150px;">
        <select style="width: 120px;">
            <option value="text">Text Input</option>
            <option value="number">Number</option>
            <option value="select">Dropdown</option>
            <option value="radio">Radio Buttons</option>
            <option value="checkbox">Checkboxes</option>
        </select>
        <input type="text" placeholder="Options (comma-separated)" style="flex: 1;">
        <input type="checkbox"> <label style="margin: 0;">Required</label>
        <button type="button" class="btn-remove" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(newField);
}

function addCustomSection() {
    const container = document.getElementById('custom-sections-container');
    const sectionId = 'custom-' + Date.now();
    const newSection = document.createElement('div');
    newSection.className = 'survey-section-config';
    newSection.setAttribute('data-section', sectionId);
    newSection.innerHTML = `
        <div class="section-header">
            <h4>Custom Section</h4>
            <div class="section-controls">
                <input type="checkbox" id="enable-${sectionId}" checked>
                <label for="enable-${sectionId}">Enable</label>
                <button type="button" class="btn-small" onclick="toggleSectionExpanded('${sectionId}')">▼</button>
                <button type="button" class="btn-remove" onclick="removeCustomSection('${sectionId}')">×</button>
            </div>
        </div>
        <div class="section-content expanded">
            <label>Section Title:</label>
            <input type="text" placeholder="Custom section title">
            
            <label>Section Description:</label>
            <textarea rows="3" placeholder="Description or instructions for this section"></textarea>
            
            <div class="custom-fields-container">
                <h5>Custom Fields:</h5>
                <div class="custom-fields" id="custom-fields-${sectionId}"></div>
                <button type="button" class="btn-add" onclick="addCustomField('${sectionId}')">+ Add Field</button>
            </div>
        </div>
    `;
    container.appendChild(newSection);
}

function addSurveySection() {
    const sectionType = document.getElementById('section-type-select').value;
    const container = document.getElementById('dynamic-sections-container');
    const sectionId = sectionType + '-' + Date.now();
    
    let sectionHTML = '';
    
    switch (sectionType) {
        case 'demographics':
            sectionHTML = createDemographicsSection(sectionId);
            break;
        case 'likert':
            sectionHTML = createLikertSection(sectionId);
            break;
        case 'freetext':
            sectionHTML = createFreetextSection(sectionId);
            break;
        case 'custom':
            sectionHTML = createCustomSection(sectionId);
            break;
    }
    
    const newSection = document.createElement('div');
    newSection.className = 'survey-section-config';
    newSection.setAttribute('data-section', sectionId);
    newSection.innerHTML = sectionHTML;
    container.appendChild(newSection);
    
    // Initialize any special functionality for the new section
    if (sectionType === 'likert') {
        // Make sure likert scale type updates work for the new section
        const scaleSelect = newSection.querySelector('.likert-scale-type');
        if (scaleSelect) {
            scaleSelect.addEventListener('change', function() {
                updateLikertLabelsForSection(sectionId);
            });
        }
    }
}

function createDemographicsSection(sectionId) {
    return `
        <div class="section-header">
            <h4>Demographics Section</h4>
            <div class="section-controls">
                <input type="checkbox" id="enable-${sectionId}" checked>
                <label for="enable-${sectionId}">Enable</label>
                <button type="button" class="btn-small" onclick="toggleSectionExpanded('${sectionId}')">▼</button>
                <button type="button" class="btn-remove" onclick="removeSurveySection('${sectionId}')">×</button>
            </div>
        </div>
        <div class="section-content expanded">
            <label>Section Title:</label>
            <input type="text" value="Demographics" placeholder="Section title">
            
            <div class="demographics-fields">
                <div class="field-config">
                    <input type="checkbox" checked>
                    <label>Age Field</label>
                    <input type="number" value="18" placeholder="Min" style="width: 60px;">
                    <input type="number" value="99" placeholder="Max" style="width: 60px;">
                </div>
                
                <div class="field-config">
                    <input type="checkbox" checked>
                    <label>Gender Field</label>
                    <div class="gender-options">
                        <input type="text" value="Female,Male,Other,Prefer not to say" placeholder="Comma-separated options">
                    </div>
                </div>
                
                <button type="button" class="btn-add" onclick="addCustomDemographicFieldToSection('${sectionId}')">+ Add Custom Field</button>
                <div id="custom-demographic-fields-${sectionId}"></div>
            </div>
        </div>
    `;
}

function createLikertSection(sectionId) {
    return `
        <div class="section-header">
            <h4>Likert Scale Section</h4>
            <div class="section-controls">
                <input type="checkbox" id="enable-${sectionId}" checked>
                <label for="enable-${sectionId}">Enable</label>
                <button type="button" class="btn-small" onclick="toggleSectionExpanded('${sectionId}')">▼</button>
                <button type="button" class="btn-remove" onclick="removeSurveySection('${sectionId}')">×</button>
            </div>
        </div>
        <div class="section-content expanded">
            <label>Section Title:</label>
            <input type="text" value="Likert Scale Items" placeholder="Section title">
            
            <div class="likert-scale-config">
                <label>Scale Type:</label>
                <select class="likert-scale-type" onchange="updateLikertLabelsForSection('${sectionId}')">
                    <option value="5-point-agreement">5-Point Agreement (Strongly Disagree to Strongly Agree)</option>
                    <option value="5-point-frequency">5-Point Frequency (Never to Always)</option>
                    <option value="7-point-agreement">7-Point Agreement</option>
                    <option value="custom">Custom Scale</option>
                </select>
                
                <div class="custom-scale-labels" style="display: none;">
                    <label>Scale Labels (comma-separated):</label>
                    <input type="text" class="scale-labels" placeholder="e.g., Strongly Disagree, Disagree, Neutral, Agree, Strongly Agree">
                </div>
            </div>
            
            <div class="likert-items-container">
                <h5>Likert Items:</h5>
                <div class="likert-items" id="likert-items-${sectionId}">
                    <div class="likert-item">
                        <input type="text" value="I enjoy using technology." placeholder="Enter statement">
                        <button type="button" class="btn-remove" onclick="removeLikertItem(this)">×</button>
                    </div>
                    <div class="likert-item">
                        <input type="text" value="I feel comfortable sharing my opinions online." placeholder="Enter statement">
                        <button type="button" class="btn-remove" onclick="removeLikertItem(this)">×</button>
                    </div>
                </div>
                <button type="button" class="btn-add" onclick="addLikertItemToSection('${sectionId}')">+ Add Item</button>
            </div>
        </div>
    `;
}

function createFreetextSection(sectionId) {
    return `
        <div class="section-header">
            <h4>Free Text Section</h4>
            <div class="section-controls">
                <input type="checkbox" id="enable-${sectionId}" checked>
                <label for="enable-${sectionId}">Enable</label>
                <button type="button" class="btn-small" onclick="toggleSectionExpanded('${sectionId}')">▼</button>
                <button type="button" class="btn-remove" onclick="removeSurveySection('${sectionId}')">×</button>
            </div>
        </div>
        <div class="section-content expanded">
            <label>Section Title:</label>
            <input type="text" value="Free Form Text" placeholder="Section title">
            
            <div class="freetext-questions" id="freetext-questions-${sectionId}">
                <div class="freetext-question">
                    <label>Question:</label>
                    <input type="text" value="Please describe your experience with online surveys:" placeholder="Enter question">
                    <label>Text area rows:</label>
                    <input type="number" value="4" min="1" max="20" style="width: 60px;">
                    <button type="button" class="btn-remove" onclick="removeFreetextQuestion(this)">×</button>
                </div>
            </div>
            <button type="button" class="btn-add" onclick="addFreetextQuestionToSection('${sectionId}')">+ Add Question</button>
        </div>
    `;
}

function createCustomSection(sectionId) {
    return `
        <div class="section-header">
            <h4>Custom Section</h4>
            <div class="section-controls">
                <input type="checkbox" id="enable-${sectionId}" checked>
                <label for="enable-${sectionId}">Enable</label>
                <button type="button" class="btn-small" onclick="toggleSectionExpanded('${sectionId}')">▼</button>
                <button type="button" class="btn-remove" onclick="removeSurveySection('${sectionId}')">×</button>
            </div>
        </div>
        <div class="section-content expanded">
            <label>Section Title:</label>
            <input type="text" placeholder="Custom section title">
            
            <label>Section Description:</label>
            <textarea rows="3" placeholder="Description or instructions for this section"></textarea>
            
            <div class="custom-fields-container">
                <h5>Custom Fields:</h5>
                <div class="custom-fields" id="custom-fields-${sectionId}"></div>
                <button type="button" class="btn-add" onclick="addCustomFieldToSection('${sectionId}')">+ Add Field</button>
            </div>
        </div>
    `;
}

function removeSurveySection(sectionId) {
    document.querySelector(`[data-section="${sectionId}"]`).remove();
}

function removeCustomSection(sectionId) {
    document.querySelector(`[data-section="${sectionId}"]`).remove();
}

function addCustomDemographicFieldToSection(sectionId) {
    const container = document.getElementById(`custom-demographic-fields-${sectionId}`);
    const newField = document.createElement('div');
    newField.className = 'field-config';
    newField.innerHTML = `
        <input type="text" placeholder="Field name" style="width: 150px;">
        <select style="width: 120px;">
            <option value="text">Text Input</option>
            <option value="number">Number</option>
            <option value="select">Dropdown</option>
            <option value="radio">Radio Buttons</option>
            <option value="checkbox">Checkboxes</option>
        </select>
        <input type="text" placeholder="Options (comma-separated)" style="flex: 1;">
        <input type="checkbox"> <label style="margin: 0;">Required</label>
        <button type="button" class="btn-remove" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(newField);
}

function addLikertItemToSection(sectionId) {
    const container = document.getElementById(`likert-items-${sectionId}`);
    const newItem = document.createElement('div');
    newItem.className = 'likert-item';
    newItem.innerHTML = `
        <input type="text" placeholder="Enter statement">
        <button type="button" class="btn-remove" onclick="removeLikertItem(this)">×</button>
    `;
    container.appendChild(newItem);
}

function addFreetextQuestionToSection(sectionId) {
    const container = document.getElementById(`freetext-questions-${sectionId}`);
    const newQuestion = document.createElement('div');
    newQuestion.className = 'freetext-question';
    newQuestion.innerHTML = `
        <label>Question:</label>
        <input type="text" placeholder="Enter question">
        <label>Text area rows:</label>
        <input type="number" value="4" min="1" max="20" style="width: 60px;">
        <button type="button" class="btn-remove" onclick="removeFreetextQuestion(this)">×</button>
    `;
    container.appendChild(newQuestion);
}

function addCustomFieldToSection(sectionId) {
    const container = document.getElementById(`custom-fields-${sectionId}`);
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'field-config';
    fieldDiv.innerHTML = `
        <input type="text" placeholder="Field label" style="width: 200px;">
        <select style="width: 120px;">
            <option value="text">Text Input</option>
            <option value="textarea">Text Area</option>
            <option value="number">Number</option>
            <option value="email">Email</option>
            <option value="select">Dropdown</option>
            <option value="radio">Radio Buttons</option>
            <option value="checkbox">Checkboxes</option>
            <option value="likert">Likert Scale</option>
        </select>
        <input type="text" placeholder="Options/validation" style="flex: 1;">
        <input type="checkbox"> <label style="margin: 0;">Required</label>
        <button type="button" class="btn-remove" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(fieldDiv);
}

function updateLikertLabelsForSection(sectionId) {
    const section = document.querySelector(`[data-section="${sectionId}"]`);
    const scaleSelect = section.querySelector('.likert-scale-type');
    const customLabels = section.querySelector('.custom-scale-labels');
    const scaleLabelsInput = section.querySelector('.scale-labels');
    
    const scaleType = scaleSelect.value;
    
    if (scaleType === 'custom') {
        customLabels.style.display = 'block';
    } else {
        customLabels.style.display = 'none';
        
        // Set predefined labels
        const labelSets = {
            '5-point-agreement': 'Strongly Disagree,Disagree,Neutral,Agree,Strongly Agree',
            '5-point-frequency': 'Never,Rarely,Sometimes,Often,Always',
            '7-point-agreement': 'Strongly Disagree,Disagree,Somewhat Disagree,Neutral,Somewhat Agree,Agree,Strongly Agree'
        };
        
        if (labelSets[scaleType]) {
            scaleLabelsInput.value = labelSets[scaleType];
        }
    }
}

function addCustomField(sectionId) {
    const container = document.getElementById(`custom-fields-${sectionId}`);
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'field-config';
    fieldDiv.innerHTML = `
        <input type="text" placeholder="Field label" style="width: 200px;">
        <select style="width: 120px;">
            <option value="text">Text Input</option>
            <option value="textarea">Text Area</option>
            <option value="number">Number</option>
            <option value="email">Email</option>
            <option value="select">Dropdown</option>
            <option value="radio">Radio Buttons</option>
            <option value="checkbox">Checkboxes</option>
            <option value="likert">Likert Scale</option>
        </select>
        <input type="text" placeholder="Options/validation" style="flex: 1;">
        <input type="checkbox"> <label style="margin: 0;">Required</label>
        <button type="button" class="btn-remove" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(fieldDiv);
}

function updateLikertLabels() {
    const scaleType = document.getElementById('likert-scale-type').value;
    const customLabels = document.getElementById('custom-scale-labels');
    const scaleLabelsInput = document.getElementById('scale-labels');
    
    if (scaleType === 'custom') {
        customLabels.style.display = 'block';
    } else {
        customLabels.style.display = 'none';
        
        // Set predefined labels
        const labelSets = {
            '5-point-agreement': 'Strongly Disagree,Disagree,Neutral,Agree,Strongly Agree',
            '5-point-frequency': 'Never,Rarely,Sometimes,Often,Always',
            '7-point-agreement': 'Strongly Disagree,Disagree,Somewhat Disagree,Neutral,Somewhat Agree,Agree,Strongly Agree'
        };
        
        if (labelSets[scaleType]) {
            scaleLabelsInput.value = labelSets[scaleType];
        }
    }
}

function handleFileUpload(type) {
    const fileInput = document.getElementById(`${type}-file`);
    const statusDiv = document.getElementById(`${type}-file-status`);
    const file = fileInput.files[0];
    
    if (file) {
        // Clear previous status
        statusDiv.innerHTML = '';
        
        // Validate file type
        if (file.type !== 'application/pdf') {
            statusDiv.innerHTML = `<span class="file-status error">✗ Please select a PDF file</span>`;
            fileInput.value = '';
            return;
        }
        
        // Validate file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            statusDiv.innerHTML = `<span class="file-status error">✗ File too large (max 10MB)</span>`;
            fileInput.value = '';
            return;
        }
        
        // Show uploading status
        statusDiv.innerHTML = `<span class="file-status">⏳ Uploading ${file.name}...</span>`;
        
        // Upload the file
        uploadFormFile(file, type);
    }
}

function uploadFormFile(file, type) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);
    
    fetch('/upload-form-file', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        const statusDiv = document.getElementById(`${type}-file-status`);
        if (data.success) {
            statusDiv.innerHTML = 
                `<span class="file-status success">✓ File uploaded successfully - will be available for download in survey</span>`;
        } else {
            statusDiv.innerHTML = 
                `<span class="file-status error">✗ Upload failed: ${data.error}</span>`;
            // Clear the file input on error
            document.getElementById(`${type}-file`).value = '';
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        document.getElementById(`${type}-file-status`).innerHTML = 
            `<span class="file-status error">✗ Upload failed - please try again</span>`;
        // Clear the file input on error
        document.getElementById(`${type}-file`).value = '';
    });
}

function saveSurveyConfiguration() {
    const config = collectSurveyConfiguration();
    
    fetch('/save-survey-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showFeedback('survey-feedback', 'Survey configuration saved successfully!', 'success');
        } else {
            showFeedback('survey-feedback', 'Error saving configuration: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showFeedback('survey-feedback', 'Error saving configuration', 'error');
    });
}

function collectSurveyConfiguration() {
    const config = {
        title: document.getElementById('survey-title').value,
        information: {
            title: document.getElementById('information-title').value,
            content: document.getElementById('information-content').value
        },
        consent: {
            content: document.getElementById('consent-content').value
        },
        settings: {
            showProgress: document.getElementById('show-progress').checked,
            randomizeSections: document.getElementById('randomize-sections').checked,
            randomizeItems: document.getElementById('randomize-items').checked,
            completionMessage: document.getElementById('completion-message').value
        },
        sections: {}
    };
    
    // Collect configuration from all dynamic sections
    const dynamicSections = document.querySelectorAll('#dynamic-sections-container .survey-section-config');
    
    dynamicSections.forEach(sectionElement => {
        const sectionId = sectionElement.getAttribute('data-section');
        const enableCheckbox = sectionElement.querySelector(`#enable-${sectionId}`);
        
        // Skip if section is not enabled
        if (!enableCheckbox || !enableCheckbox.checked) {
            return;
        }
        
        const sectionType = sectionId.split('-')[0]; // Get type from ID (demographics-123456 -> demographics)
        const titleInput = sectionElement.querySelector('input[type="text"]'); // First text input is usually the title
        
        if (sectionType === 'demographics') {
            const ageCheckbox = sectionElement.querySelector('.demographics-fields .field-config:first-child input[type="checkbox"]');
            const genderCheckbox = sectionElement.querySelector('.demographics-fields .field-config:nth-child(2) input[type="checkbox"]');
            const ageMinInput = sectionElement.querySelector('.demographics-fields .field-config:first-child input[type="number"]:first-of-type');
            const ageMaxInput = sectionElement.querySelector('.demographics-fields .field-config:first-child input[type="number"]:last-of-type');
            const genderOptionsInput = sectionElement.querySelector('.gender-options input[type="text"]');
            
            config.sections[sectionId] = {
                type: 'demographics',
                enabled: true,
                title: titleInput ? titleInput.value : 'Demographics',
                fields: {
                    age: {
                        enabled: ageCheckbox ? ageCheckbox.checked : false,
                        min: ageMinInput ? ageMinInput.value : '18',
                        max: ageMaxInput ? ageMaxInput.value : '99'
                    },
                    gender: {
                        enabled: genderCheckbox ? genderCheckbox.checked : false,
                        options: genderOptionsInput ? genderOptionsInput.value.split(',').map(s => s.trim()) : []
                    }
                }
            };
        } else if (sectionType === 'likert') {
            const likertItems = [];
            const scaleTypeSelect = sectionElement.querySelector('.likert-scale-type');
            const scaleLabelsInput = sectionElement.querySelector('.scale-labels');
            
            sectionElement.querySelectorAll('.likert-items .likert-item input[type="text"]').forEach(input => {
                if (input.value.trim()) {
                    likertItems.push(input.value.trim());
                }
            });
            
            config.sections[sectionId] = {
                type: 'likert',
                enabled: true,
                title: titleInput ? titleInput.value : 'Likert Scale Items',
                scaleType: scaleTypeSelect ? scaleTypeSelect.value : '5-point-agreement',
                scaleLabels: scaleLabelsInput ? scaleLabelsInput.value : '',
                items: likertItems
            };
        } else if (sectionType === 'freetext') {
            const freetextQuestions = [];
            
            sectionElement.querySelectorAll('.freetext-questions .freetext-question').forEach(questionDiv => {
                const questionText = questionDiv.querySelector('input[type="text"]').value.trim();
                const rows = questionDiv.querySelector('input[type="number"]').value;
                if (questionText) {
                    freetextQuestions.push({
                        question: questionText,
                        rows: parseInt(rows) || 4
                    });
                }
            });
            
            config.sections[sectionId] = {
                type: 'freetext',
                enabled: true,
                title: titleInput ? titleInput.value : 'Free Form Text',
                questions: freetextQuestions
            };
        } else if (sectionType === 'custom') {
            const customFields = [];
            const descriptionTextarea = sectionElement.querySelector('textarea');
            
            sectionElement.querySelectorAll('.custom-fields .field-config').forEach(fieldDiv => {
                const labelInput = fieldDiv.querySelector('input[type="text"]:first-of-type');
                const typeSelect = fieldDiv.querySelector('select');
                const optionsInput = fieldDiv.querySelector('input[type="text"]:last-of-type');
                const requiredCheckbox = fieldDiv.querySelector('input[type="checkbox"]');
                
                if (labelInput && labelInput.value.trim()) {
                    customFields.push({
                        label: labelInput.value.trim(),
                        type: typeSelect ? typeSelect.value : 'text',
                        options: optionsInput ? optionsInput.value : '',
                        required: requiredCheckbox ? requiredCheckbox.checked : false
                    });
                }
            });
            
            config.sections[sectionId] = {
                type: 'custom',
                enabled: true,
                title: titleInput ? titleInput.value : 'Custom Section',
                description: descriptionTextarea ? descriptionTextarea.value : '',
                fields: customFields
            };
        }
    });
    
    return config;
}

function previewSurvey() {
    const config = collectSurveyConfiguration();
    
    fetch('/preview-survey', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(config)
    })
    .then(response => response.text())
    .then(html => {
        const preview = document.getElementById('survey-preview');
        const iframe = document.getElementById('survey-preview-iframe');
        iframe.srcdoc = html;
        preview.style.display = 'block';
        preview.scrollIntoView({ behavior: 'smooth' });
    })
    .catch(error => {
        showFeedback('survey-feedback', 'Error generating preview', 'error');
    });
}

function loadSurveyConfiguration() {
    fetch('/get-survey-config')
    .then(response => response.json())
    .then(config => {
        if (config) {
            populateSurveyForm(config);
            checkUploadedFiles(); // Check for existing uploaded files
            showFeedback('survey-feedback', 'Configuration loaded successfully!', 'success');
        }
    })
    .catch(error => {
        showFeedback('survey-feedback', 'Error loading configuration', 'error');
    });
}

function checkUploadedFiles() {
    // Check for information file
    fetch('/download-form-file/information', { method: 'HEAD' })
    .then(response => {
        if (response.ok) {
            document.getElementById('information-file-status').innerHTML = 
                '<span class="file-status success">✓ Information sheet uploaded</span>';
        }
    })
    .catch(() => {
        // File doesn't exist, which is fine
    });
    
    // Check for consent file
    fetch('/download-form-file/consent', { method: 'HEAD' })
    .then(response => {
        if (response.ok) {
            document.getElementById('consent-file-status').innerHTML = 
                '<span class="file-status success">✓ Consent form uploaded</span>';
        }
    })
    .catch(() => {
        // File doesn't exist, which is fine
    });
}

function populateSurveyForm(config) {
    // Populate basic form fields
    document.getElementById('survey-title').value = config.title || 'Survey Form';
    document.getElementById('information-title').value = config.information?.title || 'Information and Consent Form';
    document.getElementById('information-content').value = config.information?.content || '';
    document.getElementById('consent-content').value = config.consent?.content || '';
    
    // Populate settings
    document.getElementById('show-progress').checked = config.settings?.showProgress !== false;
    document.getElementById('randomize-sections').checked = config.settings?.randomizeSections === true;
    document.getElementById('randomize-items').checked = config.settings?.randomizeItems === true;
    document.getElementById('completion-message').value = config.settings?.completionMessage || 'Survey completed! Redirecting to chat...';
    
    // Clear existing dynamic sections
    const dynamicContainer = document.getElementById('dynamic-sections-container');
    dynamicContainer.innerHTML = '';
    
    // Populate dynamic sections
    if (config.sections) {
        Object.keys(config.sections).forEach(sectionId => {
            const sectionConfig = config.sections[sectionId];
            if (!sectionConfig.enabled) return;
            
            // Create the section based on its type
            let sectionHTML = '';
            
            switch (sectionConfig.type) {
                case 'demographics':
                    sectionHTML = createDemographicsSection(sectionId);
                    break;
                case 'likert':
                    sectionHTML = createLikertSection(sectionId);
                    break;
                case 'freetext':
                    sectionHTML = createFreetextSection(sectionId);
                    break;
                case 'custom':
                    sectionHTML = createCustomSection(sectionId);
                    break;
            }
            
            if (sectionHTML) {
                const newSection = document.createElement('div');
                newSection.className = 'survey-section-config';
                newSection.setAttribute('data-section', sectionId);
                newSection.innerHTML = sectionHTML;
                dynamicContainer.appendChild(newSection);
                
                // Populate section-specific data
                setTimeout(() => {
                    populateSectionData(sectionId, sectionConfig);
                }, 100);
            }
        });
    }
}

function populateSectionData(sectionId, sectionConfig) {
    const sectionElement = document.querySelector(`[data-section="${sectionId}"]`);
    if (!sectionElement) return;
    
    // Set title
    const titleInput = sectionElement.querySelector('input[type="text"]');
    if (titleInput && sectionConfig.title) {
        titleInput.value = sectionConfig.title;
    }
    
    if (sectionConfig.type === 'demographics') {
        // Populate demographics fields
        if (sectionConfig.fields?.age) {
            const ageCheckbox = sectionElement.querySelector('.demographics-fields .field-config:first-child input[type="checkbox"]');
            const ageMinInput = sectionElement.querySelector('.demographics-fields .field-config:first-child input[type="number"]:first-of-type');
            const ageMaxInput = sectionElement.querySelector('.demographics-fields .field-config:first-child input[type="number"]:last-of-type');
            
            if (ageCheckbox) ageCheckbox.checked = sectionConfig.fields.age.enabled;
            if (ageMinInput) ageMinInput.value = sectionConfig.fields.age.min || '18';
            if (ageMaxInput) ageMaxInput.value = sectionConfig.fields.age.max || '99';
        }
        
        if (sectionConfig.fields?.gender) {
            const genderCheckbox = sectionElement.querySelector('.demographics-fields .field-config:nth-child(2) input[type="checkbox"]');
            const genderOptionsInput = sectionElement.querySelector('.gender-options input[type="text"]');
            
            if (genderCheckbox) genderCheckbox.checked = sectionConfig.fields.gender.enabled;
            if (genderOptionsInput && sectionConfig.fields.gender.options) {
                genderOptionsInput.value = sectionConfig.fields.gender.options.join(', ');
            }
        }
    } else if (sectionConfig.type === 'likert') {
        // Populate likert scale configuration
        const scaleTypeSelect = sectionElement.querySelector('.likert-scale-type');
        const scaleLabelsInput = sectionElement.querySelector('.scale-labels');
        
        if (scaleTypeSelect && sectionConfig.scaleType) {
            scaleTypeSelect.value = sectionConfig.scaleType;
        }
        if (scaleLabelsInput && sectionConfig.scaleLabels) {
            scaleLabelsInput.value = sectionConfig.scaleLabels;
        }
        
        // Clear existing items and add configured ones
        const itemsContainer = sectionElement.querySelector('.likert-items');
        if (itemsContainer && sectionConfig.items) {
            itemsContainer.innerHTML = '';
            sectionConfig.items.forEach(item => {
                const newItem = document.createElement('div');
                newItem.className = 'likert-item';
                newItem.innerHTML = `
                    <input type="text" value="${item}" placeholder="Enter statement">
                    <button type="button" class="btn-remove" onclick="removeLikertItem(this)">×</button>
                `;
                itemsContainer.appendChild(newItem);
            });
        }
        
        // Update scale labels visibility
        updateLikertLabelsForSection(sectionId);
    } else if (sectionConfig.type === 'freetext') {
        // Populate freetext questions
        const questionsContainer = sectionElement.querySelector('.freetext-questions');
        if (questionsContainer && sectionConfig.questions) {
            questionsContainer.innerHTML = '';
            sectionConfig.questions.forEach(questionConfig => {
                const newQuestion = document.createElement('div');
                newQuestion.className = 'freetext-question';
                newQuestion.innerHTML = `
                    <label>Question:</label>
                    <input type="text" value="${questionConfig.question}" placeholder="Enter question">
                    <label>Text area rows:</label>
                    <input type="number" value="${questionConfig.rows || 4}" min="1" max="20" style="width: 60px;">
                    <button type="button" class="btn-remove" onclick="removeFreetextQuestion(this)">×</button>
                `;
                questionsContainer.appendChild(newQuestion);
            });
        }
    } else if (sectionConfig.type === 'custom') {
        // Populate custom section
        const descriptionTextarea = sectionElement.querySelector('textarea');
        if (descriptionTextarea && sectionConfig.description) {
            descriptionTextarea.value = sectionConfig.description;
        }
        
        // Populate custom fields
        const fieldsContainer = sectionElement.querySelector('.custom-fields');
        if (fieldsContainer && sectionConfig.fields) {
            fieldsContainer.innerHTML = '';
            sectionConfig.fields.forEach(fieldConfig => {
                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'field-config';
                fieldDiv.innerHTML = `
                    <input type="text" value="${fieldConfig.label}" placeholder="Field label" style="width: 200px;">
                    <select style="width: 120px;">
                        <option value="text" ${fieldConfig.type === 'text' ? 'selected' : ''}>Text Input</option>
                        <option value="textarea" ${fieldConfig.type === 'textarea' ? 'selected' : ''}>Text Area</option>
                        <option value="number" ${fieldConfig.type === 'number' ? 'selected' : ''}>Number</option>
                        <option value="email" ${fieldConfig.type === 'email' ? 'selected' : ''}>Email</option>
                        <option value="select" ${fieldConfig.type === 'select' ? 'selected' : ''}>Dropdown</option>
                        <option value="radio" ${fieldConfig.type === 'radio' ? 'selected' : ''}>Radio Buttons</option>
                        <option value="checkbox" ${fieldConfig.type === 'checkbox' ? 'selected' : ''}>Checkboxes</option>
                        <option value="likert" ${fieldConfig.type === 'likert' ? 'selected' : ''}>Likert Scale</option>
                    </select>
                    <input type="text" value="${fieldConfig.options || ''}" placeholder="Options/validation" style="flex: 1;">
                    <input type="checkbox" ${fieldConfig.required ? 'checked' : ''}> <label style="margin: 0;">Required</label>
                    <button type="button" class="btn-remove" onclick="this.parentElement.remove()">×</button>
                `;
                fieldsContainer.appendChild(fieldDiv);
            });
        }
    }
}

function resetSurveyToDefault() {
    if (confirm('Are you sure you want to reset the survey to default settings? This will delete any custom configuration and uploaded files.')) {
        fetch('/reset-survey-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showFeedback('survey-feedback', 'Survey configuration reset successfully!', 'success');
                // Reload the page to reset form fields
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                showFeedback('survey-feedback', 'Error resetting configuration: ' + data.error, 'error');
            }
        })
        .catch(error => {
            showFeedback('survey-feedback', 'Error resetting configuration', 'error');
        });
    }
}

function showFeedback(elementId, message, type) {
    const feedbackElement = document.getElementById(elementId);
    if (feedbackElement) {
        feedbackElement.innerHTML = `<div class="feedback-${type}">${message}</div>`;
        feedbackElement.style.display = 'block';
        
        // Clear after 5 seconds for success/info messages
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                feedbackElement.innerHTML = '';
                feedbackElement.style.display = 'none';
            }, 5000);
        }
    }
}