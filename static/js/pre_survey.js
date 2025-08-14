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

    // Function to check if all form sections are completed
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
        
        // Show submission modal
        showSubmissionModal("Submitting survey...", "Please wait while we process your responses.");
        
        // Submit form data via AJAX
        fetch('/survey', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSubmissionModal("Survey submitted successfully!", "You will now be connected to the AI system.");
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 2000);
            } else {
                hideSubmissionModal();
                alert("Error submitting survey: " + (data.error || "Unknown error"));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            hideSubmissionModal();
            alert("Error submitting survey. Please try again.");
        });
    }

    function showSubmissionModal(message, detail) {
        const modal = document.getElementById('submission-modal');
        const messageElement = document.getElementById('submission-message');
        const detailElement = document.getElementById('submission-detail');
        
        if (modal && messageElement && detailElement) {
            messageElement.textContent = message;
            detailElement.textContent = detail;
            modal.classList.remove('survey-hidden');
        }
    }

    function hideSubmissionModal() {
        const modal = document.getElementById('submission-modal');
        if (modal) {
            modal.classList.add('survey-hidden');
        }
    }
});