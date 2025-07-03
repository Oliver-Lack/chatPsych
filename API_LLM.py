import os
import json
import warnings
import litellm
from litellm import completion
from dotenv import load_dotenv

# Load settings from the .env file
load_dotenv()

# Hide technical warning messages that users don't need to see
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

def load_agent(filepath):
    with open(filepath, 'r') as file:
        return json.load(file)

# Model fallbacks if the main AI doesn't work. Tries similar alternatives automatically.
MODEL_FALLBACKS = {
    # OpenAI AI models
    "gpt-4o": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    "gpt-4.1": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    "gpt-4-turbo": ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    "gpt-4": ["gpt-4", "gpt-3.5-turbo"],
    "gpt-3.5-turbo": ["gpt-3.5-turbo"],
    "o1": ["o1-preview", "o1-mini", "gpt-4o"],
    "o1-preview": ["o1-preview", "o1-mini", "gpt-4o"],
    "o1-mini": ["o1-mini", "gpt-4o"],
    "o3": ["o3", "o1-preview", "o1-mini", "gpt-4o"],
    "o4-mini": ["o4-mini", "o1-mini", "gpt-4o"],
    
    # Anthropic AI models
    "claude-3-5-sonnet": ["claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "claude-3-5-sonnet-20241022": ["claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "claude-3-sonnet": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "claude-3-sonnet-20240229": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "claude-3-haiku": ["claude-3-haiku-20240307"],
    "claude-3-haiku-20240307": ["claude-3-haiku-20240307"],
    "claude-opus-4-20250514": ["claude-opus-4-20250514", "claude-sonnet-4-20250514", "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022"],
    "claude-sonnet-4-20250514": ["claude-sonnet-4-20250514", "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022"],
    "claude-3-7-sonnet-20250219": ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229"],
    
    # Google AI models
    "gemini-2-0-flash": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
    "gemini-2-0-pro-exp-02-05": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
    "gemini-1.5-pro": ["gemini-1.5-pro", "gemini-1.5-flash"],
    "gemini-1.5-flash": ["gemini-1.5-flash"],
    "gemini-pro": ["gemini-1.5-pro", "gemini-1.5-flash"],
    
    # XAI (formerly Twitter) AI models
    "grok-2-latest": ["grok-2-1212", "grok-2"],
    "grok-2": ["grok-2", "grok-beta"],
    "grok-beta": ["grok-beta"],
    
    # Groq AI models (very fast responses)
    "groq-llama-3.1-405b": ["llama-3.1-405b-reasoning", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
    "groq-llama-3.1-70b": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
    "groq-llama-3.1-8b": ["llama-3.1-8b-instant"],
    "groq-mixtral-8x7b": ["mixtral-8x7b-32768"],
    "groq-gemma-7b": ["gemma-7b-it"],
    
    # Perplexity AI models (can search the internet for answers)
    "perplexity-llama-3.1-sonar-large": ["llama-3.1-sonar-large-128k-online", "llama-3.1-sonar-small-128k-online"],
    "perplexity-llama-3.1-sonar-small": ["llama-3.1-sonar-small-128k-online"],
    "perplexity-llama-3.1-70b": ["llama-3.1-70b-instruct", "llama-3.1-8b-instruct"],
    "perplexity-llama-3.1-8b": ["llama-3.1-8b-instruct"],
    
    # Mistral AI models (European company)
    "mistral-large": ["mistral-large-latest", "mistral-medium", "mistral-small"],
    "mistral-medium": ["mistral-medium", "mistral-small"],
    "mistral-small": ["mistral-small"],
    "codestral": ["codestral-latest"],
    "mistral-7b": ["open-mistral-7b"],
    "mixtral-8x7b": ["open-mixtral-8x7b"],
    "mixtral-8x22b": ["open-mixtral-8x22b"],
    
    # Microsoft Azure hosted OpenAI models
    "azure-gpt-4o": ["azure/gpt-4o", "azure/gpt-4-turbo", "azure/gpt-35-turbo"],
    "azure-gpt-4-turbo": ["azure/gpt-4-turbo", "azure/gpt-35-turbo"],
    "azure-gpt-35-turbo": ["azure/gpt-35-turbo"],
    
    # Ollama models (run privately on your own computer)
    "ollama-llama3.1": ["ollama/llama3.1", "ollama/llama3", "ollama/llama2"],
    "ollama-llama3": ["ollama/llama3", "ollama/llama2"],
    "ollama-llama2": ["ollama/llama2"],
    "ollama-codellama": ["ollama/codellama"],
    "ollama-mistral": ["ollama/mistral"],
    "ollama-phi3": ["ollama/phi3"],
    
    # Cohere AI models (designed for business use)
    "cohere-command-r-plus": ["command-r-plus", "command-r", "command"],
    "cohere-command-r": ["command-r", "command"],
    "cohere-command": ["command"],
    
    # Together AI models (hosting open-source AI models)
    "together-llama-3.1-405b": ["together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"],
    "together-llama-3.1-70b": ["together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"],
    "together-llama-3.1-8b": ["together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"],
    "together-mixtral-8x7b": ["together_ai/mistralai/Mixtral-8x7B-Instruct-v0.1"],
    
    # Replicate AI models (community-hosted models)
    "replicate-llama-3-70b": ["replicate/meta/meta-llama-3-70b-instruct", "replicate/meta/meta-llama-3-8b-instruct"],
    "replicate-llama-3-8b": ["replicate/meta/meta-llama-3-8b-instruct"],
    "replicate-mistral-7b": ["replicate/mistralai/mistral-7b-instruct-v0.1"],
    
    # DeepSeek AI models (Chinese company with competitive models)
    "deepseek-chat": ["deepseek-chat", "deepseek-coder"],
    "deepseek-coder": ["deepseek-coder"],
    
    # AI21 models (Jurassic language models)
    "ai21-jamba-1.5-large": ["ai21/jamba-1.5-large", "ai21/jamba-1.5-mini"],
    "ai21-jamba-1.5-mini": ["ai21/jamba-1.5-mini"],
    
    # Fireworks AI models (optimized for speed)
    "fireworks-llama-3.1-405b": ["fireworks_ai/accounts/fireworks/models/llama-v3p1-405b-instruct", "fireworks_ai/accounts/fireworks/models/llama-v3p1-70b-instruct"],
    "fireworks-llama-3.1-70b": ["fireworks_ai/accounts/fireworks/models/llama-v3p1-70b-instruct"],
    
    # Cerebras AI models (using special computer chips for extra speed)
    "cerebras-llama-3.1-70b": ["cerebras/llama3.1-70b", "cerebras/llama3.1-8b"],
    "cerebras-llama-3.1-8b": ["cerebras/llama3.1-8b"]
}

# Friendly names for AI models that users will see in the interface
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
    
    # Google AI models
    "gemini-2-0-flash": "Gemini 2.0 Flash",
    "gemini-2-0-pro-exp-02-05": "Gemini 2.0 Pro",
    "gemini-1.5-pro": "Gemini 1.5 Pro",
    "gemini-1.5-flash": "Gemini 1.5 Flash",
    "gemini-pro": "Gemini Pro",
    
    # XAI (formerly Twitter) AI models
    "grok-2-latest": "Grok 2 (Latest)",
    "grok-2": "Grok 2",
    "grok-beta": "Grok Beta",
    
    # Groq AI models (very fast responses)
    "groq-llama-3.1-405b": "Groq Llama 3.1 405B (Ultra-fast)",
    "groq-llama-3.1-70b": "Groq Llama 3.1 70B (Fast)",
    "groq-llama-3.1-8b": "Groq Llama 3.1 8B (Instant)",
    "groq-mixtral-8x7b": "Groq Mixtral 8x7B (Fast)",
    "groq-gemma-7b": "Groq Gemma 7B (Fast)",
    
    # Perplexity AI models (can search the internet for answers)
    "perplexity-llama-3.1-sonar-large": "Perplexity Sonar Large (Online)",
    "perplexity-llama-3.1-sonar-small": "Perplexity Sonar Small (Online)",
    "perplexity-llama-3.1-70b": "Perplexity Llama 3.1 70B",
    "perplexity-llama-3.1-8b": "Perplexity Llama 3.1 8B",
    
    # Mistral AI models (European company)
    "mistral-large": "Mistral Large (Latest)",
    "mistral-medium": "Mistral Medium",
    "mistral-small": "Mistral Small",
    "codestral": "Codestral (Code Specialist)",
    "mistral-7b": "Mistral 7B (Open)",
    "mixtral-8x7b": "Mixtral 8x7B (Open)",
    "mixtral-8x22b": "Mixtral 8x22B (Open)",
    
    # Microsoft Azure hosted OpenAI models
    "azure-gpt-4o": "Azure GPT-4o",
    "azure-gpt-4-turbo": "Azure GPT-4 Turbo",
    "azure-gpt-35-turbo": "Azure GPT-3.5 Turbo",
    
    # Ollama models (run privately on your own computer)
    "ollama-llama3.1": "Ollama Llama 3.1 (Local)",
    "ollama-llama3": "Ollama Llama 3 (Local)",
    "ollama-llama2": "Ollama Llama 2 (Local)",
    "ollama-codellama": "Ollama CodeLlama (Local)",
    "ollama-mistral": "Ollama Mistral (Local)",
    "ollama-phi3": "Ollama Phi-3 (Local)",
    
    # Cohere AI models (designed for business use)
    "cohere-command-r-plus": "Cohere Command R+ (Enterprise)",
    "cohere-command-r": "Cohere Command R (Enterprise)",
    "cohere-command": "Cohere Command (Enterprise)",
    
    # Together AI models (hosting open-source AI models)
    "together-llama-3.1-405b": "Together AI Llama 3.1 405B",
    "together-llama-3.1-70b": "Together AI Llama 3.1 70B",
    "together-llama-3.1-8b": "Together AI Llama 3.1 8B",
    "together-mixtral-8x7b": "Together AI Mixtral 8x7B",
    
    # Replicate AI models (community-hosted models)
    "replicate-llama-3-70b": "Replicate Llama 3 70B",
    "replicate-llama-3-8b": "Replicate Llama 3 8B",
    "replicate-mistral-7b": "Replicate Mistral 7B",
    
    # DeepSeek AI models (Chinese company with competitive models)
    "deepseek-chat": "DeepSeek Chat",
    "deepseek-coder": "DeepSeek Coder",
    
    # AI21 models (Jurassic language models)
    "ai21-jamba-1.5-large": "AI21 Jamba 1.5 Large",
    "ai21-jamba-1.5-mini": "AI21 Jamba 1.5 Mini",
    
    # Fireworks AI models (optimized for speed)
    "fireworks-llama-3.1-405b": "Fireworks AI Llama 3.1 405B",
    "fireworks-llama-3.1-70b": "Fireworks AI Llama 3.1 70B",
    
    # Cerebras AI models (using special computer chips for extra speed)
    "cerebras-llama-3.1-70b": "Cerebras Llama 3.1 70B (Ultra-fast)",
    "cerebras-llama-3.1-8b": "Cerebras Llama 3.1 8B (Ultra-fast)"
}

def get_available_models():
    """Get a list of all AI models that can be used in the interface"""
    return [{"value": model, "display": MODEL_DISPLAY_NAMES.get(model, model)} 
            for model in MODEL_DISPLAY_NAMES.keys()]

def litellm_api_request(model="gpt-4o",
                       messages=None,
                       temperature=1,
                       top_p=1,
                       presence_penalty=0,
                       frequency_penalty=0,
                       max_tokens=300,
                       logprobs=True):
    
    if messages is None:
        messages = []
    
    # Try backup AI models if the main one doesn't work
    fallback_models = MODEL_FALLBACKS.get(model, [model])
    
    for attempt_model in fallback_models:
        try:
            # Set up the request to the AI with basic settings
            params = {
                "model": attempt_model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens
            }
            
            # Add extra settings for OpenAI models
            if "gpt" in attempt_model or "o1" in attempt_model:
                # OpenAI-specific settings
                params["presence_penalty"] = presence_penalty
                params["frequency_penalty"] = frequency_penalty
                if logprobs and "o1" not in attempt_model:  # o1 models don't support logprobs
                    params["logprobs"] = True
            
            # Send the request to the AI and hide technical warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                warnings.simplefilter("ignore", DeprecationWarning)
                
                # Prepare the AI connection with safe settings
                import litellm
                
                # Store original settings to restore later
                original_drop_params = getattr(litellm, 'drop_params', None)
                litellm.drop_params = True
                
                try:
                    response = completion(**params)
                finally:
                    # Put back the original settings
                    if original_drop_params is not None:
                        litellm.drop_params = original_drop_params
            
            # Count how many words/tokens the AI used
            usage = getattr(response, 'usage', None)
            prompt_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0
            completion_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0
            total_tokens = getattr(usage, 'total_tokens', 0) if usage else 0
            
            # Get probability scores for each word (if available)
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
                "model": attempt_model
            }
            
            # Track if we used a fallback model
            used_fallback = attempt_model != model
            fallback_note = f"\n\n(Generated by {attempt_model} as {model} was unavailable)" if used_fallback else ""
            
            return formatted_response, prompt_tokens, completion_tokens, total_tokens, logprobs_list, used_fallback, fallback_note
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error with model {attempt_model}: {error_msg}")
            
            # Check if this is a specific connection problem
            if "unexpected keyword argument 'proxies'" in error_msg:
                print("Detected proxies parameter issue - trying with simplified client configuration...")
                try:
                    # Try a simpler approach without advanced features
                    simplified_params = {
                        "model": attempt_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                    
                    # Use the simpler approach
                    response = completion(**simplified_params)
                    
                    # Get the response in the same format as above
                    usage = getattr(response, 'usage', None)
                    prompt_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0
                    completion_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0
                    total_tokens = getattr(usage, 'total_tokens', 0) if usage else 0
                    
                    response_content = response.choices[0].message.content
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
                        "model": attempt_model
                    }
                    
                    # Track if we used a fallback model
                    used_fallback = attempt_model != model
                    fallback_note = f"\n\n(Generated by {attempt_model} as {model} was unavailable)" if used_fallback else ""
                    
                    return formatted_response, prompt_tokens, completion_tokens, total_tokens, [], used_fallback, fallback_note
                    
                except Exception as simplified_e:
                    print(f"Simplified approach also failed: {simplified_e}")
            
            if attempt_model == fallback_models[-1]:  # Last backup AI failed
                # Return error message for logging but user-friendly message for display
                error_response = {
                    "choices": [{
                        "message": {
                            "content": "I'm sorry, I'm currently experiencing technical difficulties. Please try again in a moment."
                        }
                    }],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "error_for_logging": f"Error: All fallback models failed. Last error: {error_msg}"
                }
                return error_response, 0, 0, 0, [], False, ""
            continue  # Try next backup AI
    
    # This should never happen, but just in case
    error_response = {
        "choices": [{
            "message": {
                "content": "I'm sorry, I'm currently experiencing technical difficulties. Please try again in a moment."
            }
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "error_for_logging": "Error: No models available"
    }
    return error_response, 0, 0, 0, [], False, ""

class API_Call():
    def __init__(self, agent=None):
        # Set up connections to AI services
        self._setup_litellm()
        
        if agent is None:
            self.agent_data = load_agent("agents/default.json")
        else:
            self.agent_data = load_agent(f"agents/{agent}.json")
    
    def _setup_litellm(self):
        """Set up connections to various AI services using saved passwords"""
        # Get passwords for AI services from environment settings
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
        os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
        os.environ["XAI_API_KEY"] = os.getenv("XAI_API_KEY", "")
        
        # Additional AI service passwords
        os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
        os.environ["PERPLEXITY_API_KEY"] = os.getenv("PERPLEXITY_API_KEY", "")
        os.environ["MISTRAL_API_KEY"] = os.getenv("MISTRAL_API_KEY", "")
        
        # Microsoft Azure setup (needs special handling)
        azure_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        azure_version = os.getenv("AZURE_OPENAI_API_VERSION", "")
        if azure_key and azure_endpoint:
            os.environ["AZURE_API_KEY"] = azure_key
            os.environ["AZURE_API_BASE"] = azure_endpoint
            os.environ["AZURE_API_VERSION"] = azure_version
        
        # Local AI setup (for private AI on your computer)
        ollama_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        os.environ["OLLAMA_API_BASE"] = ollama_base
        
        # Optional AI services (only set up if user has passwords for them)
        optional_providers = {
            "TOGETHER_API_KEY": "TOGETHER_API_KEY",
            "COHERE_API_KEY": "COHERE_API_KEY", 
            "AI21_API_KEY": "AI21_API_KEY",
            "REPLICATE_API_TOKEN": "REPLICATE_API_TOKEN",
            "FIREWORKS_API_KEY": "FIREWORKS_API_KEY",
            "HUGGINGFACE_API_KEY": "HUGGINGFACE_API_KEY",
            "DEEPSEEK_API_KEY": "DEEPSEEK_API_KEY"
        }
        
        for env_key, litellm_key in optional_providers.items():
            value = os.getenv(env_key, "")
            if value:
                os.environ[litellm_key] = value
        
        # Configure AI system settings to avoid errors and warnings
        try:
            # Use the main AI connection system
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
        # Choose which AI to use (if not specified, use the agent's preferred AI)
        if model is None:
            model = self.agent_data.get("model", "gpt-4o")
        
        # Make a copy of the conversation to avoid changing the original
        working_conversation = conversation.copy()
        
        # Add the AI's instructions if they exist
        system_prompt = self.agent_data.get("PrePrompt", "")
        if system_prompt:
            working_conversation.insert(0, {"role": "system", "content": system_prompt})

        # Add the user's new message
        formatted_message = {"role": "user", "content": message}
        working_conversation.append(formatted_message)

        try:
            # Hide technical warnings during AI conversation
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                response, prompt_tokens, completion_tokens, total_tokens, logprobs_list, used_fallback, fallback_note = litellm_api_request(
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
                'choices': [{'message': {'content': "I'm sorry, I'm currently experiencing technical difficulties. Please try again in a moment."}}], 
                'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                'error_for_logging': f"Error: {str(e)}"
            }
            prompt_tokens, completion_tokens, total_tokens, logprobs_list, used_fallback, fallback_note = 0, 0, 0, [], False, ""

        # Handle error responses from the AI
        if "error" in response:
            # Log the technical error but show user-friendly message
            error_message = response["error"]["message"] if "error" in response and "message" in response["error"] else "Unknown error"
            conversation.append({"role": "assistant", "content": "I'm sorry, I'm currently experiencing technical difficulties. Please try again in a moment."})
            # Store original error for logging
            conversation[-1]["error_for_logging"] = error_message
            return conversation, 0, 0, 0, [], False, ""

        # Add the AI's response to the conversation
        assistant_message = response['choices'][0]['message']['content']
        conversation.append({"role": "assistant", "content": assistant_message})
        
        # If there's an error_for_logging in the response, store it for logging purposes
        if "error_for_logging" in response:
            conversation[-1]["error_for_logging"] = response["error_for_logging"]

        # Save conversation to a file for debugging if requested
        if debug:
            with open("logs.txt", "w", encoding="utf-8") as file:
                for i in conversation:
                    file.write(str(i) + "\n")

        # Debug message if probability scores are empty
        if not logprobs_list and debug:
            print("Logprobs are empty. Response:", response)

        return conversation, prompt_tokens, completion_tokens, total_tokens, logprobs_list, used_fallback, fallback_note