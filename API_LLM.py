# This is the API script to AI model providers. It uses the LiteLLM library to unify handling.

import os
import json
import warnings
import litellm
from litellm import completion

# Validate critical environment variables
required_keys = ['FLASK_SECRET_KEY']
missing_keys = [key for key in required_keys if not os.getenv(key)]
if missing_keys:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")

api_keys = [
    'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'XAI_API_KEY', 'GEMINI_API_KEY',
    'GROQ_API_KEY', 'PERPLEXITY_API_KEY', 'MISTRAL_API_KEY',
    'COHERE_API_KEY', 'AI21_API_KEY', 'TOGETHER_API_KEY', 'FIREWORKS_API_KEY', 
    'REPLICATE_API_TOKEN', 'CEREBRAS_API_KEY', 'DEEPSEEK_API_KEY',
    'AZURE_OPENAI_API_KEY', 'HUGGINGFACE_API_KEY', 'NVIDIA_NIM_API_KEY', 'OPENROUTER_API_KEY'
]
missing_api_keys = [key for key in api_keys if not os.getenv(key)]
available_api_keys = [key for key in api_keys if os.getenv(key)]

# Only show API key info if there are any missing keys or if all primary providers aren't available
primary_keys = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY', 'XAI_API_KEY']
missing_primary = [key for key in primary_keys if not os.getenv(key)]
available_primary = [key for key in primary_keys if os.getenv(key)]

# Check for the research dashboard credentials
researcher_username_set = bool(os.getenv('researcher_username'))
researcher_password_set = bool(os.getenv('researcher_password'))
flask_secret_set = bool(os.getenv('FLASK_SECRET_KEY'))

# Only show startup status once (avoid repetition in multi-worker setups)
import multiprocessing
if not hasattr(multiprocessing.current_process(), '_startup_logged'):
    multiprocessing.current_process()._startup_logged = True
    
    print(f"AI System Ready: {len(available_api_keys)}/{len(api_keys)} providers configured")
    print(f"Primary providers: {', '.join([key.replace('_API_KEY', '') for key in available_primary])} ({len(available_primary)}/4)")
    print(f"Research dashboard: {'Enabled' if (researcher_username_set and researcher_password_set and flask_secret_set) else 'Missing credentials'}")

    # Show missing keys if any
    if missing_api_keys:
        missing_names = [key.replace('_API_KEY', '').replace('_API_TOKEN', '') for key in missing_api_keys]
        print(f"ℹ Missing optional providers: {missing_names}")

    # Only show warnings for critical issues
    if len(missing_primary) == len(primary_keys):
        print("⚠ Warning: No primary AI providers found. Add at least one:")
        print("  - Set OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, or XAI_API_KEY in your .env file")
    elif not (researcher_username_set and researcher_password_set):
        print("⚠ Warning: Research dashboard credentials incomplete. Set researcher_username and researcher_password in .env")

# This hides some technical warning messages
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

def load_agent(filepath):
    with open(filepath, 'r') as file:
        return json.load(file)

# Common names for AI models that users will see in the interface
MODEL_DISPLAY_NAMES = {
    # OpenAI
    "gpt-4o": "GPT-4o",
    "gpt-4.1": "GPT-4.1 (2025)",
    "gpt-4-turbo": "GPT-4 Turbo",
    "gpt-4": "GPT-4",
    "gpt-3.5-turbo": "GPT-3.5 Turbo",
    "o1": "OpenAI o1",
    "o1-preview": "OpenAI o1 Preview",
    "o1-mini": "OpenAI o1 Mini",
    "o3": "OpenAI o3",
    "o4-mini": "OpenAI o4 Mini",
    
    # Anthropic
    "claude-3-5-sonnet": "Claude 3.5 Sonnet",
    "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet (Oct 2024)",
    "claude-3-sonnet": "Claude 3 Sonnet",
    "claude-3-sonnet-20240229": "Claude 3 Sonnet (Feb 2024)",
    "claude-3-haiku": "Claude 3 Haiku",
    "claude-3-haiku-20240307": "Claude 3 Haiku (Mar 2024)",
    "claude-opus-4-20250514": "Claude Opus 4 (May 2025)",
    "claude-sonnet-4-20250514": "Claude Sonnet 4 (May 2025)",
    "claude-3-7-sonnet-20250219": "Claude 3.7 Sonnet (Feb 2025)",
    
    # Google AI Studio models
    "gemini/gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini/gemini-2.5-flash": "Gemini 2.5 Flash", 
    "gemini/gemini-2.0-flash": "Gemini 2.0 Flash",
    "gemini/gemini-1.5-pro": "Gemini 1.5 Pro",
    "gemini/gemini-1.5-flash": "Gemini 1.5 Flash",
    "gemini/gemini-pro": "Gemini Pro",
    
    # XAI
    "xai/grok-4": "Grok 4",
    "xai/grok-3": "Grok 3",
    "xai/grok-3-mini-beta": "Grok 3 Mini Beta",
    "xai/grok-2-latest": "Grok 2 (Latest)",
    "xai/grok-2": "Grok 2",
    "xai/grok-beta": "Grok Beta",
    
    # Groq
    "groq/llama-3.1-405b-reasoning": "Groq Llama 3.1 405B (Ultra-fast)",
    "groq/llama-3.1-70b-versatile": "Groq Llama 3.1 70B (Fast)",  
    "groq/llama-3.1-8b-instant": "Groq Llama 3.1 8B (Instant)",
    "groq/mixtral-8x7b-32768": "Groq Mixtral 8x7B (Fast)",
    "groq/gemma-7b-it": "Groq Gemma 7B (Fast)",
    
    # Perplexity
    "perplexity/sonar-pro": "Perplexity Sonar Pro (Online)",
    "perplexity/sonar": "Perplexity Sonar (Online)",
    "perplexity/sonar-reasoning": "Perplexity Sonar Reasoning (Online)",
    "perplexity/r1-1776": "Perplexity R1-1776",
    
    # Mistral
    "mistral/mistral-large-latest": "Mistral Large (Latest)",
    "mistral/mistral-medium-latest": "Mistral Medium",
    "mistral/mistral-small-latest": "Mistral Small",
    "mistral/codestral-latest": "Codestral (Code Specialist)",
    "mistral/open-mistral-7b": "Mistral 7B (Open)",
    "mistral/open-mixtral-8x7b": "Mixtral 8x7B (Open)",
    "mistral/open-mixtral-8x22b": "Mixtral 8x22B (Open)",
    
    # Microsoft Azure 
    "azure-gpt-4o": "Azure GPT-4o",
    "azure-gpt-4-turbo": "Azure GPT-4 Turbo",
    "azure-gpt-35-turbo": "Azure GPT-3.5 Turbo",
    
    # Ollama models
    "ollama-llama3.1": "Ollama Llama 3.1 (Local)",
    "ollama-llama3": "Ollama Llama 3 (Local)",
    "ollama-llama2": "Ollama Llama 2 (Local)",
    "ollama-codellama": "Ollama CodeLlama (Local)",
    "ollama-mistral": "Ollama Mistral (Local)",
    "ollama-phi3": "Ollama Phi-3 (Local)",
    
    # Cohere
    "command-r-plus": "Cohere Command R+ (Enterprise)",
    "command-r": "Cohere Command R (Enterprise)", 
    "command-a-03-2025": "Cohere Command A (Mar 2025)",
    
    # Together
    "together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": "Together AI Llama 3.1 405B",
    "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": "Together AI Llama 3.1 70B",
    "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": "Together AI Llama 3.1 8B",
    "together_ai/mistralai/Mixtral-8x7B-Instruct-v0.1": "Together AI Mixtral 8x7B",
    
    # Replicate
    "replicate/meta/meta-llama-3-70b-instruct": "Replicate Llama 3 70B",
    "replicate/meta/meta-llama-3-8b-instruct": "Replicate Llama 3 8B",
    "replicate/mistralai/mistral-7b-instruct-v0.1": "Replicate Mistral 7B",
    
    # DeepSeek
    "deepseek/deepseek-chat": "DeepSeek Chat",
    "deepseek/deepseek-coder": "DeepSeek Coder",
    "deepseek/deepseek-reasoner": "DeepSeek Reasoner",
    
    # AI21
    "ai21/jamba-1.5-large": "AI21 Jamba 1.5 Large",
    "ai21/jamba-1.5-mini": "AI21 Jamba 1.5 Mini",
    
    # Fireworks
    "fireworks_ai/accounts/fireworks/models/llama-v3p2-90b-instruct": "Fireworks AI Llama 3.2 90B",
    "fireworks_ai/accounts/fireworks/models/llama-v3p1-70b-instruct": "Fireworks AI Llama 3.1 70B",
    
    # Cerebras
    "cerebras/llama3.1-70b": "Cerebras Llama 3.1 70B (Ultra-fast)",
    "cerebras/llama3.1-8b": "Cerebras Llama 3.1 8B (Ultra-fast)"
}

def get_available_models():
    """Get a list of all AI models that can be used in the interface"""
    return [{"value": model, "display": MODEL_DISPLAY_NAMES.get(model, model)} 
            for model in MODEL_DISPLAY_NAMES.keys()]

def get_available_providers():
    """Get a list of providers that have API keys configured"""
    provider_keys = {
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY", 
        "Google AI Studio": "GEMINI_API_KEY",
        "XAI": "XAI_API_KEY",
        "Groq": "GROQ_API_KEY",
        "Perplexity": "PERPLEXITY_API_KEY", 
        "Mistral": "MISTRAL_API_KEY",
        "Cohere": "COHERE_API_KEY",
        "AI21": "AI21_API_KEY",
        "Together": "TOGETHER_API_KEY",
        "Fireworks": "FIREWORKS_API_KEY",
        "Replicate": "REPLICATE_API_TOKEN",
        "Cerebras": "CEREBRAS_API_KEY",
        "DeepSeek": "DEEPSEEK_API_KEY",
        "Azure": "AZURE_OPENAI_API_KEY",
        "Hugging Face": "HUGGINGFACE_API_KEY",
        "NVIDIA": "NVIDIA_NIM_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY",
        "Ollama": "LOCAL"
    }
    # checking for keys for the provider list in the dashboard
    available = []
    for provider, key in provider_keys.items():
        if key == "LOCAL":
            available.append(provider)
        elif provider == "Google AI Studio":
            if os.getenv("GEMINI_API_KEY"):
                available.append(provider)
        elif provider == "Perplexity":
            if os.getenv("PERPLEXITY_API_KEY") or os.getenv("PERPLEXITYAI_API_KEY"):
                available.append(provider)
        elif provider == "Together":
            if os.getenv("TOGETHER_API_KEY") or os.getenv("TOGETHERAI_API_KEY"):
                available.append(provider)
        elif provider == "Fireworks":
            if os.getenv("FIREWORKS_API_KEY") or os.getenv("FIREWORKS_AI_API_KEY"):
                available.append(provider)
        elif provider == "Replicate":
            if os.getenv("REPLICATE_API_TOKEN") or os.getenv("REPLICATE_API_KEY"):
                available.append(provider)
        elif os.getenv(key):
            available.append(provider)
    
    return available

def get_provider_status():
    """Get detailed status of each provider (configured or not) - SECURE VERSION
    
    Returns a dictionary with provider names as keys and their configuration status.
    This function is designed to be secure and NEVER exposes actual API keys.
    """
    provider_keys = {
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY", 
        "Google AI Studio": "GEMINI_API_KEY",
        "XAI": "XAI_API_KEY",
        "Groq": "GROQ_API_KEY",
        "Perplexity": "PERPLEXITY_API_KEY",
        "Mistral": "MISTRAL_API_KEY",
        "Cohere": "COHERE_API_KEY",
        "AI21": "AI21_API_KEY",
        "Together": "TOGETHER_API_KEY",
        "Fireworks": "FIREWORKS_API_KEY",
        "Replicate": "REPLICATE_API_TOKEN",
        "Cerebras": "CEREBRAS_API_KEY",
        "DeepSeek": "DEEPSEEK_API_KEY",
        "Azure": "AZURE_OPENAI_API_KEY",
        "Hugging Face": "HUGGINGFACE_API_KEY",
        "NVIDIA": "NVIDIA_NIM_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY",
        "Ollama": "LOCAL"
    }
    
    provider_status = {}
    
    for provider, env_key in provider_keys.items():
        if env_key == "LOCAL":
            provider_status[provider] = {
                "configured": True,
                "status": "Available (Local)",
                "category": "Local AI"
            }
        else:
            is_configured = False
            
            if provider == "Perplexity":
                is_configured = bool((os.getenv("PERPLEXITY_API_KEY") or os.getenv("PERPLEXITYAI_API_KEY", "")).strip())
            elif provider == "Together":
                is_configured = bool((os.getenv("TOGETHER_API_KEY") or os.getenv("TOGETHERAI_API_KEY", "")).strip())
            elif provider == "Fireworks":
                is_configured = bool((os.getenv("FIREWORKS_API_KEY") or os.getenv("FIREWORKS_AI_API_KEY", "")).strip())
            elif provider == "Replicate":
                is_configured = bool((os.getenv("REPLICATE_API_TOKEN") or os.getenv("REPLICATE_API_KEY", "")).strip())
            else:
                api_key = os.getenv(env_key)
                is_configured = bool(api_key and api_key.strip())
            
            provider_status[provider] = {
                "configured": is_configured,
                "status": "Configured" if is_configured else "Not Configured",
                "category": get_provider_category(provider)
            }
    
    return provider_status

def get_provider_category(provider_name):
    """Categorize providers for better organization"""
    categories = {
        "OpenAI": "Primary Provider",
        "Anthropic": "Primary Provider", 
        "Google AI Studio": "Primary Provider",
        "XAI": "Primary Provider",
        "Groq": "Other",
        "Perplexity": "Other",
        "Mistral": "Other",
        "Cohere": "Other",
        "AI21": "Other",
        "Together": "Other",
        "Fireworks": "Other",
        "Replicate": "Other",
        "Cerebras": "Other",
        "DeepSeek": "Other",
        "Azure": "Other",
        "Hugging Face": "Other",
        "NVIDIA": "Other",
        "OpenRouter": "Other",
        "Ollama": "Local"
    }
    return categories.get(provider_name, "Other")

def litellm_api_request(model="gpt-4.1",
                       messages=None,
                       temperature=1,
                       top_p=1,
                       presence_penalty=0,
                       frequency_penalty=0,
                       max_tokens=300,
                       logprobs=True):
    
    if messages is None:
        messages = []
    
    try:
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        }
        
        if "gpt" in model or "o1" in model:
            # OpenAI stuff
            params["presence_penalty"] = presence_penalty
            params["frequency_penalty"] = frequency_penalty
            if logprobs and "o1" not in model:
                params["logprobs"] = True
        elif "claude" in model:
            # Anthropic models don't support presence/frequency penalties
            pass
        elif "grok" in model:
            # XAI models - some support penalties, others don't
            if "grok-4" not in model:
                # Most Grok models support penalties except grok-4
                params["presence_penalty"] = presence_penalty
                params["frequency_penalty"] = frequency_penalty
            # grok-4 currently only supports basic parameters
        elif any(provider in model for provider in ["groq", "perplexity", "mistral", "cohere"]):
            pass
        elif any(provider in model for provider in ["together", "replicate", "fireworks", "cerebras"]):
            pass
        elif "ollama" in model:
            pass
        elif any(provider in model for provider in ["azure", "bedrock"]):
            if "azure" in model:
                params["presence_penalty"] = presence_penalty
                params["frequency_penalty"] = frequency_penalty
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            warnings.simplefilter("ignore", DeprecationWarning)
            
            import litellm
            
            original_drop_params = getattr(litellm, 'drop_params', None)
            litellm.drop_params = True
            
            try:
                response = completion(**params)
            finally:
                if original_drop_params is not None:
                    litellm.drop_params = original_drop_params
        
        usage = getattr(response, 'usage', None)
        prompt_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0
        completion_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0
        total_tokens = getattr(usage, 'total_tokens', 0) if usage else 0
        
        # This is trying to get logprobs. However, a lot of companies are deprecating this feature.
        logprobs_list = []
        try:
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'logprobs') and choice.logprobs:
                    if hasattr(choice.logprobs, 'content') and choice.logprobs.content:
                        logprobs_list = [
                            getattr(content, 'logprob', 0) 
                            for content in choice.logprobs.content 
                            if hasattr(content, 'logprob')
                        ]
        except (AttributeError, IndexError, TypeError):
            # If we can't get probability scores, just use empty list
            logprobs_list = []
        
        # Get the AI's response text safely
        try:
            response_content = response.choices[0].message.content
        except (AttributeError, IndexError):
            response_content = "Error: Could not extract response content"
        
        # Package the response in a standard format
        formatted_response = {
            "choices": [{
                "message": {
                    "content": response_content
                }
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            "model": model  # Return the actual model used (same as requested)
        }
        
        return formatted_response, prompt_tokens, completion_tokens, total_tokens, logprobs_list, model
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error with model {model}: {error_msg}")
        
        # error response
        error_response = {
            "choices": [{
                "message": {
                    "content": f"Error: {error_msg}"
                }
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "model": model
        }
        return error_response, 0, 0, 0, [], model

class API_Call():
    def __init__(self, agent=None):
        # Set up connections to AI providers
        self._setup_litellm()
        
        if agent is None:
            self.agent_data = load_agent("agents/default.json")
        else:
            self.agent_data = load_agent(f"agents/{agent}.json")
    
    def _setup_litellm(self):
        """Set up connections to various AI services using saved passwords"""
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
        
        gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        if gemini_api_key:
            os.environ["GEMINI_API_KEY"] = gemini_api_key
            os.environ["GOOGLE_API_KEY"] = gemini_api_key
        
        os.environ["XAI_API_KEY"] = os.getenv("XAI_API_KEY", "")
        
        xai_api_key = os.getenv("XAI_API_KEY", "")
        if xai_api_key:
            os.environ["XAI_API_BASE"] = os.getenv("XAI_API_BASE", "https://api.x.ai/v1")
        
        os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
        
        perplexity_key = os.getenv("PERPLEXITY_API_KEY", "")
        if perplexity_key:
            os.environ["PERPLEXITYAI_API_KEY"] = perplexity_key
        os.environ["PERPLEXITYAI_API_KEY"] = os.getenv("PERPLEXITYAI_API_KEY", os.getenv("PERPLEXITY_API_KEY", ""))
        
        os.environ["MISTRAL_API_KEY"] = os.getenv("MISTRAL_API_KEY", "")
        
        azure_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        azure_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        if azure_key and azure_endpoint:
            os.environ["AZURE_API_KEY"] = azure_key
            os.environ["AZURE_API_BASE"] = azure_endpoint
            os.environ["AZURE_API_VERSION"] = azure_version
        
        ollama_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        os.environ["OLLAMA_API_BASE"] = ollama_base
        
        optional_providers = {
            "COHERE_API_KEY": "COHERE_API_KEY",
            "AI21_API_KEY": "AI21_API_KEY",
            
            "TOGETHER_API_KEY": "TOGETHERAI_API_KEY", 
            "FIREWORKS_API_KEY": "FIREWORKS_AI_API_KEY", 
            "REPLICATE_API_TOKEN": "REPLICATE_API_KEY", 
            "CEREBRAS_API_KEY": "CEREBRAS_API_KEY",
            
            "DEEPSEEK_API_KEY": "DEEPSEEK_API_KEY",
            
            "HUGGINGFACE_API_KEY": "HUGGINGFACE_API_KEY",
            "NVIDIA_NIM_API_KEY": "NVIDIA_NIM_API_KEY",
            "OPENROUTER_API_KEY": "OPENROUTER_API_KEY",
            
            "AWS_ACCESS_KEY_ID": "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY": "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION_NAME": "AWS_REGION_NAME"
        }
        
        for env_key, litellm_key in optional_providers.items():
            value = os.getenv(env_key, "")
            if value:
                os.environ[litellm_key] = value
        
        provider_mappings = {
            "BEDROCK_AWS_REGION": os.getenv("AWS_REGION_NAME", "us-east-1")
        }
        
        for key, value in provider_mappings.items():
            if value:
                os.environ[key] = value
        
        try:
            litellm.drop_params = True  # Ignore unsupported settings instead of showing errors
            litellm.set_verbose = False  # Turn off technical messages (set to True for debugging)
            
        except Exception as e:
            print(f"Warning: Could not configure litellm advanced settings: {e}")
        
        # Hide technical warning messages that users don't need to see
        warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.main")
        warnings.filterwarnings("ignore", category=UserWarning, module="litellm")
        warnings.filterwarnings("ignore", category=UserWarning, module="openai")
        
    def update_agent(self, filename):
        self.agent_data = load_agent(filename)
   
    def thinkAbout(self, message, conversation, model=None, debug=False):
        if model is None:
            model = self.agent_data.get("model", "gpt-4.1")
        
        # Make a copy of the conversation to avoid changing the original
        working_conversation = conversation.copy()
        
        # Add the system message (pre_prompt)
        system_prompt = self.agent_data.get("PrePrompt", "")
        if system_prompt:
            working_conversation.insert(0, {"role": "system", "content": system_prompt})

        # Add the user's new message
        formatted_message = {"role": "user", "content": message}
        working_conversation.append(formatted_message)

        try:
            # Hide technical warnings during AI conversation. Use for debuggin if nneeded.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                response, prompt_tokens, completion_tokens, total_tokens, logprobs_list, actual_model = litellm_api_request(
                    model=model,
                    messages=working_conversation,
                    temperature=self.agent_data.get("temperature", 1),
                    frequency_penalty=self.agent_data.get("frequency_penalty", 0),
                    presence_penalty=self.agent_data.get("presence_penalty", 0),
                    top_p=self.agent_data.get("top_p", 1),
                    max_tokens=self.agent_data.get("max_completion_tokens", 300)
                )
        except Exception as e:
            # If something goes wrong, return an error message
            print(f"Unexpected error in thinkAbout: {str(e)}")
            response = {
                'choices': [{'message': {'content': f"Error: {str(e)}"}}], 
                'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            }
            prompt_tokens, completion_tokens, total_tokens, logprobs_list, actual_model = 0, 0, 0, [], model

        # Handle error responses from the AI
        if "error" in response:
            conversation.append({"role": "assistant", "content": response["error"]["message"]})
            return conversation, 0, 0, 0, [], model

        # Add the AI's response to the conversation
        assistant_message = response['choices'][0]['message']['content']
        conversation.append({"role": "assistant", "content": assistant_message})

        # Some debugging logs stuff
        if debug:
            with open("logs.txt", "w", encoding="utf-8") as file:
                for i in conversation:
                    file.write(str(i) + "\n")

        # Debuggin for logprobs stuff
        if not logprobs_list and debug:
            print("Logprobs are empty. Response:", response)

        return conversation, prompt_tokens, completion_tokens, total_tokens, logprobs_list, actual_model