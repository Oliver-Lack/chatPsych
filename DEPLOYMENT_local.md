# How to Run chatPsych Locally

## Prerequisites

Ensure you have Python 3.8+ installed:
```bash
python3 --version
```

## Install Dependencies

Navigate to the chatPsych directory and install requirements:
```bash
cd /Users/a1809024/Desktop/PMC/AI_Interface/chatPsych
pip install -r requirements.txt
```

## Setup Environment Variables

Create a `.env` file from the example:
```bash
cp .env.example .env
```
Edit the `.env` file with your actual values:

### Local Deployment:

```bash
gunicorn -w 4 -b 0.0.0.0:8080 chatPsych:app
```


## Login Information

- Deployment password list set in the chatPsych.py script
- Any username is accepted, but the password must match one of the deployment passwords.
- Default login password: 'chatPsych123'

**Researcher Dashboard Default Login:**
researcher_username="wordie"
researcher_password="laplace666$"

## Available Models

AI Models and other settings can be set in the researcher dashboard.  
With the expanded integration, you now have access to 65+ models across 18 providers:  

- **OpenAI**: GPT-4o, GPT-4, GPT-3.5, O1 series
- **Anthropic**: Claude 3.5 Sonnet, Claude 3 series
- **Google**: Gemini 2.0, Gemini 1.5 series
- **Groq**: Ultra-fast Llama models
- **many, many, many more...**