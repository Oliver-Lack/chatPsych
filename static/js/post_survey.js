// Post-Survey page JavaScript functionality

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Post-Survey JavaScript loaded');

    // Get redirection links from template variables
    const finishRedirectionLink = window.finishRedirectionLink || "https://www.prolific.com/";
    const completionCode = window.completionCode || "xxxx";
    const completionInstructions = window.completionInstructions || "The study is now complete. Thank you for your participation. If required, your completion code is: xxxx";
    const finishButtonText = window.finishButtonText || "Finish";
    
    console.log('Finish redirection link:', finishRedirectionLink);
    console.log('Completion code:', completionCode);

    // Initialize survey immediately
    initializeSurvey();

    // Form completion check
    function checkFormCompletion() {
        const form = document.getElementById('survey-form');
        if (!form) return false;

        // Check required fields
        const requiredInputs = form.querySelectorAll('[required]');
        for (let input of requiredInputs) {
            if (!input.value || (input.type === 'checkbox' && !input.checked)) {
                console.log('Required field not completed:', input);
                return false;
            }
        }

        // Check required checkboxes in groups
        const checkboxGroups = form.querySelectorAll('.checkbox-group[data-required="true"]');
        for (let group of checkboxGroups) {
            const checkboxes = group.querySelectorAll('input[type="checkbox"]:checked');
            if (checkboxes.length === 0) {
                console.log('Required checkbox group not completed:', group);
                return false;
            }
        }

        return true;
    }

    // Initialize survey functionality
    function initializeSurvey() {
        console.log('Initializing survey');
        updateProgressIndicator();
    }

    // Update progress indicator
    function updateProgressIndicator() {
        const progressIndicator = document.getElementById('progress-indicator');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        if (!progressIndicator || !progressFill || !progressText) {
            return;
        }

        const sections = document.querySelectorAll('.survey-section');
        const totalSections = sections.length;
        
        if (totalSections === 0) {
            progressIndicator.style.display = 'none';
            return;
        }

        // For simplicity, show 100% progress since it's a single page
        progressFill.style.width = '100%';
        progressText.textContent = `Survey Form`;
    }

    // Form submission
    const nextBtn = document.querySelector('.next-btn');
    
    // Form submit handler
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
        fetch('/post-survey', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSubmissionModal("Survey submitted successfully!", "Processing completion...");
                setTimeout(() => {
                    hideSubmissionModal();
                    showCompletionModal();
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
        const messageEl = document.getElementById('submission-message');
        const detailEl = document.getElementById('submission-detail');
        
        if (modal && messageEl && detailEl) {
            messageEl.textContent = message;
            detailEl.textContent = detail;
            modal.classList.remove('survey-hidden');
            modal.style.display = 'flex';
        }
    }

    function hideSubmissionModal() {
        const modal = document.getElementById('submission-modal');
        if (modal) {
            modal.classList.add('survey-hidden');
            modal.style.display = 'none';
        }
    }

    function showCompletionModal() {
        const modal = document.getElementById('completion-modal');
        const instructionsEl = document.getElementById('completion-instructions');
        const finishBtn = document.getElementById('final-finish-btn');
        
        if (modal && instructionsEl && finishBtn) {
            // Replace xxxx with actual completion code in instructions
            let instructions = completionInstructions.replace(/xxxx/g, completionCode);
            instructionsEl.innerHTML = `<p>${instructions}</p>`;
            
            // Set button text
            finishBtn.textContent = finishButtonText;
            
            // Show modal
            modal.classList.remove('survey-hidden');
            modal.style.display = 'flex';
            
            // Add click handler for finish button
            finishBtn.onclick = function() {
                console.log('Final finish button clicked, redirecting to:', finishRedirectionLink);
                window.location.href = finishRedirectionLink;
            };
        }
    }
});
