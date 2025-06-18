import os
import requests
import json
from anthropic import Anthropic

client = Anthropic()

def load_agent(filepath):
    with open(filepath, 'r') as file:
        return json.load(file)
    
def anthropic_api_request(model=None,
                       messages=None,
                       system=None,
                       temperature=1,
                       top_p=1,
                       max_tokens=300):
    
    # Use the Anthropic client instead of raw API calls
    completion = client.messages.create(
        model=model,
        system=system,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens
    )
    
    # Extract token usage
    input_tokens = completion.usage.input_tokens
    output_tokens = completion.usage.output_tokens
    
    return completion, input_tokens, output_tokens


class API_Call_anthropic():
    
    def __init__(self, agent=None):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if agent is None:
            self.agent_data = load_agent("agents/default_anthropic.json")
        else:
            self.agent_data = load_agent(f"agents/{agent}.json")
        
    def update_agent(self, filename):
        self.agent_data = load_agent(filename)
   
    def thinkAbout(self, message, conversation, model=None):
        if not conversation:
            conversation = []  # I have to initialise this first message to stop logprobs retrieval from sending an error.
        if model is None:
           model = self.agent_data.get("model", "claude-3-5-sonnet-20241022")
        pre_prompt = self.agent_data.get("PrePrompt", "")
        conversation.append({"role": "assistant", "content": response.content[0].text})

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        logprobs_list = []

        try:
            response, input_tokens, output_tokens = anthropic_api_request(
                model=model,
                system=pre_prompt,
                messages=conversation,
                temperature=self.agent_data.get("temperature", 1),
                top_p=self.agent_data.get("top_p", 1),
                max_tokens=300
            )
            
            conversation.append({"role": "assistant", "content": response['content'][0]['text']})
            prompt_tokens = input_tokens
            completion_tokens = output_tokens
            total_tokens = prompt_tokens + completion_tokens

        except Exception as e:
            print(f"Anthropic API error: {str(e)}")
            conversation.append({"role": "assistant", "content": f"Error: Unable to retrieve information. {str(e)}"})

        return conversation, prompt_tokens, completion_tokens, total_tokens, logprobs_list
    