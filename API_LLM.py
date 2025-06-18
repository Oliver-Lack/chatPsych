import os
import json
import warnings
import litellm
from litellm import completion
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Suppress Pydantic serialization warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

def load_agent(filepath):
    with open(filepath, 'r') as file:
        return json.load(file)

# Model fallbacks incase a model isn't working. Never changes provider, only the model. 
MODEL_FALLBACKS = {
    # OpenAI models
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
    
    # Anthropic models
    "claude-3-5-sonnet": ["claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "claude-3-5-sonnet-20241022": ["claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "claude-3-sonnet": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "claude-3-sonnet-20240229": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "claude-3-haiku": ["claude-3-haiku-20240307"],
    "claude-3-haiku-20240307": ["claude-3-haiku-20240307"],
    "claude-opus-4-20250514": ["claude-opus-4-20250514", "claude-sonnet-4-20250514", "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022"],
    "claude-sonnet-4-20250514": ["claude-sonnet-4-20250514", "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022"],
    "claude-3-7-sonnet-20250219": ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229"],
    
    # Google models
    "gemini-2-0-flash": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
    "gemini-2-0-pro-exp-02-05": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
    "gemini-1.5-pro": ["gemini-1.5-pro", "gemini-1.5-flash"],
    "gemini-1.5-flash": ["gemini-1.5-flash"],
    "gemini-pro": ["gemini-1.5-pro", "gemini-1.5-flash"],
    
    # XAI models
    "grok-2-latest": ["grok-2-1212", "grok-2"],
    "grok-2": ["grok-2", "grok-beta"],
    "grok-beta": ["grok-beta"],
    
    # Groq models (ultra-fast inference)
    "groq-llama-3.1-405b": ["llama-3.1-405b-reasoning", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
    "groq-llama-3.1-70b": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
    "groq-llama-3.1-8b": ["llama-3.1-8b-instant"],
    "groq-mixtral-8x7b": ["mixtral-8x7b-32768"],
    "groq-gemma-7b": ["gemma-7b-it"],
    
    # Perplexity models (search-augmented)
    "perplexity-llama-3.1-sonar-large": ["llama-3.1-sonar-large-128k-online", "llama-3.1-sonar-small-128k-online"],
    "perplexity-llama-3.1-sonar-small": ["llama-3.1-sonar-small-128k-online"],
    "perplexity-llama-3.1-70b": ["llama-3.1-70b-instruct", "llama-3.1-8b-instruct"],
    "perplexity-llama-3.1-8b": ["llama-3.1-8b-instruct"],
    
    # Mistral models (European AI)
    "mistral-large": ["mistral-large-latest", "mistral-medium", "mistral-small"],
    "mistral-medium": ["mistral-medium", "mistral-small"],
    "mistral-small": ["mistral-small"],
    "codestral": ["codestral-latest"],
    "mistral-7b": ["open-mistral-7b"],
    "mixtral-8x7b": ["open-mixtral-8x7b"],
    "mixtral-8x22b": ["open-mixtral-8x22b"],
    
    # Azure OpenAI models
    "azure-gpt-4o": ["azure/gpt-4o", "azure/gpt-4-turbo", "azure/gpt-35-turbo"],
    "azure-gpt-4-turbo": ["azure/gpt-4-turbo", "azure/gpt-35-turbo"],
    "azure-gpt-35-turbo": ["azure/gpt-35-turbo"],
    
    # Ollama models (local)
    "ollama-llama3.1": ["ollama/llama3.1", "ollama/llama3", "ollama/llama2"],
    "ollama-llama3": ["ollama/llama3", "ollama/llama2"],
    "ollama-llama2": ["ollama/llama2"],
    "ollama-codellama": ["ollama/codellama"],
    "ollama-mistral": ["ollama/mistral"],
    "ollama-phi3": ["ollama/phi3"],
    
    # Cohere models (enterprise-focused)
    "cohere-command-r-plus": ["command-r-plus", "command-r", "command"],
    "cohere-command-r": ["command-r", "command"],
    "cohere-command": ["command"],
    
    # Together AI models (open source hosting)
    "together-llama-3.1-405b": ["together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"],
    "together-llama-3.1-70b": ["together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"],
    "together-llama-3.1-8b": ["together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"],
    "together-mixtral-8x7b": ["together_ai/mistralai/Mixtral-8x7B-Instruct-v0.1"],
    
    # Replicate models (community hosting)
    "replicate-llama-3-70b": ["replicate/meta/meta-llama-3-70b-instruct", "replicate/meta/meta-llama-3-8b-instruct"],
    "replicate-llama-3-8b": ["replicate/meta/meta-llama-3-8b-instruct"],
    "replicate-mistral-7b": ["replicate/mistralai/mistral-7b-instruct-v0.1"],
    
    # DeepSeek models (competitive Chinese models)
    "deepseek-chat": ["deepseek-chat", "deepseek-coder"],
    "deepseek-coder": ["deepseek-coder"],
    
    # AI21 models (Jurassic)
    "ai21-jamba-1.5-large": ["ai21/jamba-1.5-large", "ai21/jamba-1.5-mini"],
    "ai21-jamba-1.5-mini": ["ai21/jamba-1.5-mini"],
    
    # Fireworks AI models (fast inference)
    "fireworks-llama-3.1-405b": ["fireworks_ai/accounts/fireworks/models/llama-v3p1-405b-instruct", "fireworks_ai/accounts/fireworks/models/llama-v3p1-70b-instruct"],
    "fireworks-llama-3.1-70b": ["fireworks_ai/accounts/fireworks/models/llama-v3p1-70b-instruct"],
    
    # Cerebras models (ultra-fast chips)
    "cerebras-llama-3.1-70b": ["cerebras/llama3.1-70b", "cerebras/llama3.1-8b"],
    "cerebras-llama-3.1-8b": ["cerebras/llama3.1-8b"]
}

# User-friendly model names mapping
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
    
    # Google
    "gemini-2-0-flash": "Gemini 2.0 Flash",
    "gemini-2-0-pro-exp-02-05": "Gemini 2.0 Pro",
    "gemini-1.5-pro": "Gemini 1.5 Pro",
    "gemini-1.5-flash": "Gemini 1.5 Flash",
    "gemini-pro": "Gemini Pro",
    
    # XAI
    "grok-2-latest": "Grok 2 (Latest)",
    "grok-2": "Grok 2",
    "grok-beta": "Grok Beta",
    
    # Groq (Ultra-fast inference)
    "groq-llama-3.1-405b": "Groq Llama 3.1 405B (Ultra-fast)",
    "groq-llama-3.1-70b": "Groq Llama 3.1 70B (Fast)",
    "groq-llama-3.1-8b": "Groq Llama 3.1 8B (Instant)",
    "groq-mixtral-8x7b": "Groq Mixtral 8x7B (Fast)",
    "groq-gemma-7b": "Groq Gemma 7B (Fast)",
    
    # Perplexity (Search-augmented)
    "perplexity-llama-3.1-sonar-large": "Perplexity Sonar Large (Online)",
    "perplexity-llama-3.1-sonar-small": "Perplexity Sonar Small (Online)",
    "perplexity-llama-3.1-70b": "Perplexity Llama 3.1 70B",
    "perplexity-llama-3.1-8b": "Perplexity Llama 3.1 8B",
    
    # Mistral (European AI)
    "mistral-large": "Mistral Large (Latest)",
    "mistral-medium": "Mistral Medium",
    "mistral-small": "Mistral Small",
    "codestral": "Codestral (Code Specialist)",
    "mistral-7b": "Mistral 7B (Open)",
    "mixtral-8x7b": "Mixtral 8x7B (Open)",
    "mixtral-8x22b": "Mixtral 8x22B (Open)",
    
    # Azure OpenAI
    "azure-gpt-4o": "Azure GPT-4o",
    "azure-gpt-4-turbo": "Azure GPT-4 Turbo",
    "azure-gpt-35-turbo": "Azure GPT-3.5 Turbo",
    
    # Ollama (Local models)
    "ollama-llama3.1": "Ollama Llama 3.1 (Local)",
    "ollama-llama3": "Ollama Llama 3 (Local)",
    "ollama-llama2": "Ollama Llama 2 (Local)",
    "ollama-codellama": "Ollama CodeLlama (Local)",
    "ollama-mistral": "Ollama Mistral (Local)",
    "ollama-phi3": "Ollama Phi-3 (Local)",
    
    # Cohere (Enterprise-focused)
    "cohere-command-r-plus": "Cohere Command R+ (Enterprise)",
    "cohere-command-r": "Cohere Command R (Enterprise)",
    "cohere-command": "Cohere Command (Enterprise)",
    
    # Together AI (Open source hosting)
    "together-llama-3.1-405b": "Together AI Llama 3.1 405B",
    "together-llama-3.1-70b": "Together AI Llama 3.1 70B",
    "together-llama-3.1-8b": "Together AI Llama 3.1 8B",
    "together-mixtral-8x7b": "Together AI Mixtral 8x7B",
    
    # Replicate (Community hosting)
    "replicate-llama-3-70b": "Replicate Llama 3 70B",
    "replicate-llama-3-8b": "Replicate Llama 3 8B",
    "replicate-mistral-7b": "Replicate Mistral 7B",
    
    # DeepSeek (Competitive models)
    "deepseek-chat": "DeepSeek Chat",
    "deepseek-coder": "DeepSeek Coder",
    
    # AI21 (Jurassic models)
    "ai21-jamba-1.5-large": "AI21 Jamba 1.5 Large",
    "ai21-jamba-1.5-mini": "AI21 Jamba 1.5 Mini",
    
    # Fireworks AI (Fast inference)
    "fireworks-llama-3.1-405b": "Fireworks AI Llama 3.1 405B",
    "fireworks-llama-3.1-70b": "Fireworks AI Llama 3.1 70B",
    
    # Cerebras (Ultra-fast chips)
    "cerebras-llama-3.1-70b": "Cerebras Llama 3.1 70B (Ultra-fast)",
    "cerebras-llama-3.1-8b": "Cerebras Llama 3.1 8B (Ultra-fast)"
}

def get_available_models():
    """Return list of available models with display names"""
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
    
    # Get fallback models for the requested model
    fallback_models = MODEL_FALLBACKS.get(model, [model])
    
    for attempt_model in fallback_models:
        try:
            # Prepare parameters for liteLLM
            params = {
                "model": attempt_model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens
            }
            
            # Add parameters that are supported by the model
            if "gpt" in attempt_model or "o1" in attempt_model:
                # OpenAI-specific parameters
                params["presence_penalty"] = presence_penalty
                params["frequency_penalty"] = frequency_penalty
                if logprobs and "o1" not in attempt_model:  # o1 models don't support logprobs
                    params["logprobs"] = True
            
            # Make the API call with warning suppression
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                response = completion(**params)
            
            # Extract token usage safely
            usage = getattr(response, 'usage', None)
            prompt_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0
            completion_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0
            total_tokens = getattr(usage, 'total_tokens', 0) if usage else 0
            
            # Extract logprobs if available - more robust handling
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
                # If we can't extract logprobs, just use empty list
                logprobs_list = []
            
            # Extract response content safely
            try:
                response_content = response.choices[0].message.content
            except (AttributeError, IndexError):
                response_content = "Error: Could not extract response content"
            
            # Format response to match expected structure
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
            
            # Add fallback notice if we used a different model
            if attempt_model != model:
                formatted_response["choices"][0]["message"]["content"] += f"\n\n(Generated by {attempt_model} as {model} was unavailable)"
            
            return formatted_response, prompt_tokens, completion_tokens, total_tokens, logprobs_list
            
        except Exception as e:
            print(f"Error with model {attempt_model}: {str(e)}")
            if attempt_model == fallback_models[-1]:  # Last fallback failed
                # Return error response
                error_response = {
                    "choices": [{
                        "message": {
                            "content": f"Error: All fallback models failed. Last error: {str(e)}"
                        }
                    }],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                }
                return error_response, 0, 0, 0, []
            continue  # Try next fallback model
    
    # This should never be reached, but just in case
    error_response = {
        "choices": [{
            "message": {
                "content": "Error: No models available"
            }
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }
    return error_response, 0, 0, 0, []

class API_Call():
    def __init__(self, agent=None):
        # Set up liteLLM with environment variables
        self._setup_litellm()
        
        if agent is None:
            self.agent_data = load_agent("agents/default.json")
        else:
            self.agent_data = load_agent(f"agents/{agent}.json")
    
    def _setup_litellm(self):
        """Setup liteLLM with API keys from environment"""
        # Set API keys for liteLLM
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
        os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")
        os.environ["XAI_API_KEY"] = os.getenv("XAI_API_KEY", "")
        
        # New expanded providers
        os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
        os.environ["PERPLEXITY_API_KEY"] = os.getenv("PERPLEXITY_API_KEY", "")
        os.environ["MISTRAL_API_KEY"] = os.getenv("MISTRAL_API_KEY", "")
        
        # Azure OpenAI (requires special handling)
        azure_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        azure_version = os.getenv("AZURE_OPENAI_API_VERSION", "")
        if azure_key and azure_endpoint:
            os.environ["AZURE_API_KEY"] = azure_key
            os.environ["AZURE_API_BASE"] = azure_endpoint
            os.environ["AZURE_API_VERSION"] = azure_version
        
        # Ollama (local setup)
        ollama_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        os.environ["OLLAMA_API_BASE"] = ollama_base
        
        # Optional providers (if user wants to add them later)
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
        
        # Configure liteLLM settings to suppress warnings and handle errors gracefully
        litellm.drop_params = True  # Drop unsupported parameters instead of erroring
        litellm.set_verbose = False  # Set to True for debugging
        
        # Suppress specific warnings from liteLLM and dependencies
        warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.main")
        warnings.filterwarnings("ignore", category=UserWarning, module="litellm")
        
    def update_agent(self, filename):
        self.agent_data = load_agent(filename)
   
    def thinkAbout(self, message, conversation, model=None, debug=False):
        # Use provided model or fall back to agent's model or default
        if model is None:
            model = self.agent_data.get("model", "gpt-4o")
        
        # Create a copy of conversation to avoid modifying the original
        working_conversation = conversation.copy()
        
        # Add system prompt if it exists
        system_prompt = self.agent_data.get("PrePrompt", "")
        if system_prompt:
            working_conversation.insert(0, {"role": "system", "content": system_prompt})

        # Add user message
        formatted_message = {"role": "user", "content": message}
        working_conversation.append(formatted_message)

        try:
            # Suppress warnings during API call
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                response, prompt_tokens, completion_tokens, total_tokens, logprobs_list = litellm_api_request(
                    model=model,
                    messages=working_conversation,
                    temperature=self.agent_data.get("temperature", 1),
                    frequency_penalty=self.agent_data.get("frequency_penalty", 0),
                    presence_penalty=self.agent_data.get("presence_penalty", 0),
                    top_p=self.agent_data.get("top_p", 1),
                    max_tokens=self.agent_data.get("max_completion_tokens", 300)
                )
        except Exception as e:
            # Fallback error handling
            print(f"Unexpected error in thinkAbout: {str(e)}")
            response = {
                'choices': [{'message': {'content': f"Error: {str(e)}"}}], 
                'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            }
            prompt_tokens, completion_tokens, total_tokens, logprobs_list = 0, 0, 0, []

        # Handle error responses
        if "error" in response:
            conversation.append({"role": "assistant", "content": response["error"]["message"]})
            return conversation, 0, 0, 0, []

        # Add assistant response to conversation
        assistant_message = response['choices'][0]['message']['content']
        conversation.append({"role": "assistant", "content": assistant_message})

        # Debug logging
        if debug:
            with open("logs.txt", "w", encoding="utf-8") as file:
                for i in conversation:
                    file.write(str(i) + "\n")

        # Debug empty logprobs
        if not logprobs_list and debug:
            print("Logprobs are empty. Response:", response)

        return conversation, prompt_tokens, completion_tokens, total_tokens, logprobs_list