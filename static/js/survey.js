// Survey page JavaScript functionality

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Survey JavaScript loaded');
    
    // Consent popup logic
    const consentPopup = document.getElementById('consent-popup');
    const consentAgreeBtn = document.getElementById('consent-agree-btn');
    const consentQuitBtn = document.getElementById('consent-quit-btn');
    const quitConfirmPopup = document.getElementById('quit-confirm-popup');
    const quitConfirmYesBtn = document.getElementById('quit-confirm-yes-btn');
    const quitConfirmNoBtn = document.getElementById('quit-confirm-no-btn');

    // Debug logging
    console.log('Consent popup element:', consentPopup);
    console.log('Consent agree button:', consentAgreeBtn);
    console.log('Consent quit button:', consentQuitBtn);

    // Get quit redirection link from template variable (will be injected by server)
    const quitRedirectionLink = window.quitRedirectionLink || "https://www.prolific.com/";
    console.log('Quit redirection link:', quitRedirectionLink);

    // Consent handling
    let consentGiven = false;

    // Ensure consent popup is visible on load
    if (consentPopup) {
        consentPopup.style.display = 'flex';
        console.log('Consent popup should be visible');
    }

    if (consentAgreeBtn) {
        consentAgreeBtn.onclick = function() {
            console.log('Consent agreed');
            consentPopup.style.display = 'none';
            document.getElementById('survey-form').style.pointerEvents = 'auto';
            document.getElementById('survey-form').style.opacity = '1';
            consentGiven = true;
            updateNextButton();
        };
    }

    if (consentQuitBtn) {
        consentQuitBtn.onclick = function() {
            console.log('Consent quit clicked - showing confirmation');
            if (quitConfirmPopup) {
                quitConfirmPopup.classList.remove('survey-hidden');
                quitConfirmPopup.style.display = 'flex';
            }
        };
    }

    if (quitConfirmNoBtn) {
        quitConfirmNoBtn.onclick = function() {
            console.log('Quit cancelled - hiding confirmation');
            if (quitConfirmPopup) {
                quitConfirmPopup.classList.add('survey-hidden');
                quitConfirmPopup.style.display = 'none';
            }
        };
    }

    if (quitConfirmYesBtn) {
        quitConfirmYesBtn.onclick = function() {
            console.log('Quit confirmed - redirecting to:', quitRedirectionLink);
            window.location.href = quitRedirectionLink;
        };
    }

    // Prevent form interaction until consent
    const surveyForm = document.getElementById('survey-form');
    if (surveyForm) {
        surveyForm.style.pointerEvents = 'none';
        surveyForm.style.opacity = '0.5';
        console.log('Survey form disabled until consent');
    }
    
    // JS Demo Button (if exists - for backward compatibility)
    const jsDemoBtn = document.getElementById('js-demo-btn');
    if (jsDemoBtn) {
        jsDemoBtn.onclick = function() {
            document.getElementById('js-demo-result').textContent = "Javascript is working!";
        };
    }

    // Next button functionality
    const nextBtn = document.getElementById('next-btn');
    const nextDisclaimer = document.getElementById('next-disclaimer');

    // Function to check if all form sections are completed dynamically
    function checkFormCompletion() {
        if (!consentGiven) return false;

        const form = document.getElementById('survey-form');
        const requiredFields = form.querySelectorAll('[required]');
        
        for (let field of requiredFields) {
            if (field.type === 'radio') {
                // For radio buttons, check if any in the group is selected
                const radioGroup = form.querySelectorAll(`[name="${field.name}"]`);
                let isChecked = false;
                for (let radio of radioGroup) {
                    if (radio.checked) {
                        isChecked = true;
                        break;
                    }
                }
                if (!isChecked) return false;
            } else if (field.type === 'checkbox') {
                if (!field.checked) return false;
            } else {
                if (!field.value.trim()) return false;
            }
        }
        
        return true;
    }

    // Function to show/hide next button
    function updateNextButton() {
        if (checkFormCompletion()) {
            nextBtn.classList.remove('survey-hidden');
            nextDisclaimer.style.display = 'none';
        } else {
            nextBtn.classList.add('survey-hidden');
            nextDisclaimer.style.display = 'block';
        }
    }

    // Add event listeners to all form inputs for dynamic validation
    function addFormListeners() {
        const form = document.getElementById('survey-form');
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            if (input.type === 'radio' || input.type === 'checkbox') {
                input.addEventListener('change', updateNextButton);
            } else {
                input.addEventListener('input', updateNextButton);
                input.addEventListener('change', updateNextButton);
            }
        });
    }

    // Initialize form listeners
    addFormListeners();

    // Form submission handling
    document.getElementById('survey-form').onsubmit = function(e) {
        e.preventDefault();
        
        // Check if form is completed
        if (checkFormCompletion()) {
            submitSurvey();
        } else {
            alert("Please complete all sections of the form before submitting.");
        }
    };

    // Next button click handler
    if (nextBtn) {
        nextBtn.onclick = function() {
            if (checkFormCompletion()) {
                submitSurvey();
            } else {
                alert("Please complete all sections of the form before proceeding.");
            }
        };
    }

    // Survey submission function
    function submitSurvey() {
        const formData = new FormData(document.getElementById('survey-form'));
        
        // Submit form data via AJAX
        fetch('/survey', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Survey completed! Redirecting to chat...");
                window.location.href = data.redirect_url;
            } else {
                alert("Error submitting survey: " + (data.error || "Unknown error"));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("Error submitting survey. Please try again.");
        });
    }

    // Initial button state update
    updateNextButton();
});