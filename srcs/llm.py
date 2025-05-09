import os
import requests
import json
from openai import OpenAI

LLM_ASK_QUERY_TYPE = {
    "identify_main_folder": '''Your task is to identify and return ONLY ONE path to the folder that most likely contains the main "SOURCE" code of the web service (e.g., *.py, *.java, *.php, etc.). Analyze the provided list of subdirectories and exclude irrelevant folders such as `BOOT-INF/` or other auxiliary directories. Provide your answer in the specified format.''',
    
    "identify_main_source": '''Your task is to identify and return ONLY ONE "SOURCE" FILE path that most likely contains the main source code of the web service (MUST CONTAIN ENDPOINT). Analyze the provided list of files and focus on files with relevant extensions (e.g., *.py, *.java, *.php, etc.). Consider indicators such as entry points, main functions, or framework-specific files. Provide your answer in the specified format.''',
    
    "identify_framework": '''Your task is to identify the framework of the web service based on the provided source code file. Analyze the code carefully to determine the framework (e.g., Django, Flask, Spring, Express). If the framework is not clear, ask for clarification. Provide ONLY the name of the framework in the specified format.''',
    
    "identify_service_name": '''Your task is to identify the name of the web service based on the provided list of dir and files. Analyze the data carefully to determine the service name. If the service name is not clear, ask for clarification. Provide ONLY the name of the service in the specified format.''',
    
    "how_to_reconginize_endpoint": '''Your task is to generate a JSON object where each key is an HTTP method (e.g., GET, POST, PUT, DELETE, etc.), and the value is a valid and precise regular expression pattern that can be used to identify endpoints for that method in the provided source code. Follow these rules:
1. Ensure all patterns are syntactically correct and can be compiled without errors.
2. Patterns should be work for frameworks and code that user prompt provide.
3. Avoid overly specific patterns that depend on a single framework or language. Your return will be used to identify endpoints in various web service implementations.
4. Include patterns that match common endpoint definitions, such as:
   - Annotations (e.g., @GetMapping, @RequestMapping, @Route, @app.route)
5. Provide the patterns in the following JSON format:
{
    "ALL": "regex_for_generic_request_mapping"
    "GET": "regex_for_get",
    "POST": "regex_for_post"
}
6. The "ALL" key should include patterns for annotations or functions that do not specify a specific HTTP method (e.g., @RequestMapping without a method).
7. Result of regex should be line of code containing endpoint. (e.g.,`@GetMapping("/api/users"), @app.route("/api/users")`)
8. **The regex should be most simple and easy to make it work.**
9. Do not include any additional text or explanations outside the specified format.'''
,
    "describe_endpoint": '''Your task is to analyze the provided source code and extract detailed information about a SINGLE endpoint defined in it. Extract the following information for the most relevant endpoint:

1. **Path**: The URL path of the endpoint (e.g., `/api/users`).
2. **Method**: The HTTP method used (e.g., GET, POST, PUT, DELETE).
3. **Cookies**: Any cookies used in the endpoint (e.g., `session_id`).
4. **Parameters**: A list of parameters used in the endpoint (e.g., `user_id`, `page`).
5. **HTTP Headers**: Any HTTP headers used in the endpoint (e.g., `Authorization`, `Content-Type`).
6. **Dependencies**: Any endpoint refer, href, dependency, or related endpoints with "method" (e.g., `GET:/api/users/{id}`).
7. **Response Type**: The type of response returned by the endpoint (e.g., JSON, XML, HTML).
8. **Description**: A human-readable description of the endpoint's purpose. Longer descriptions are preferred.

**Rules**:
- Extract information for ONLY ONE endpoint, even if multiple endpoints are present in the source code.
- Select the most relevant endpoint based on its complexity, importance, or centrality in the source code.
- If any field is not applicable or cannot be determined, use an empty array (`[]`) or `null` as the value.
- The response must strictly follow the JSON format below.
- Do not include any additional text, explanations, or comments outside the JSON structure.
- Ensure the JSON is syntactically correct and can be parsed without errors.

**Response Format**:
{
    "result": {
        "endpoint": {
            "path": "/api/users",
            "method": "GET",
            "cookies": ["session_id"],
            "params": ["user_id", "page"],
            "headers": ["Authorization", "Content-Type"],
            "dependencies": ["GET:/api/users/{id}"],
            "response_type": "JSON",
            "description": "Get user information"
        }
    }
}

**IMPORTANT**:
- The top-level key must always be `"result"`.
- The `"result"` key must contain a single `"endpoint"` object as shown in the format above.
- Do not include any additional text, explanations, or comments outside the JSON structure.
- If no endpoints are found, return: `{"result": {"endpoint": null}}`.
'''
}

SYSTEM_PROMPT_HEADER = '''You are a highly capable AI assistant specializing in information security and software analysis. Your primary task is to assist in the reconnaissance and analysis of authorized web services. You will follow the user's instructions step by step and provide precise, actionable, and concise responses.
You must respond deterministically. For the same input, your response must always be exactly the same. Do not change the format, structure, or wording of your response across different runs. Consistency is required. Assume that this task may be executed repeatedly with the same input. Avoid introducing any randomness, variation, or rephrasing in your response. Return the same result if the input is the same.
'''
SYSTEM_PROMPT_FOOTER = '''Your response must strictly follow this format: {"result":"your_answer"}. Do not include any additional text or explanations outside this format.'''

# LMStudio API settings
#LMSTUDIO_API_URL = "http://localhost:1234/v1/chat/completions"
LMSTUDIO_API_URL = "http://localhost:1234/v1/chat/completions"  # Local API URL
LMSTUDIO_MODEL = "gemma-3-12b-it-qat"  # Default model name (changed to qwen3-8b-mlx for LOCAL)

def get_openai_api_key():
    """Reads the OpenAI API key from a file or environment variable."""
    if os.path.exists("openai_key"):
        with open("openai_key", "r") as key_file:
            return key_file.read().strip()
    return os.environ.get("OPENAI_API_KEY")

def create_openai_client():
    """Creates and returns an OpenAI client."""
    api_key = get_openai_api_key()
    if not api_key:
        raise ValueError("OpenAI API key not found. Ensure 'openai_key' file or environment variable is set.")
    return OpenAI(api_key=api_key)

def ask_lmstudio(ask_type: str, prompt: str, temperature: float=0):
    """Send a request to LMStudio local API and get the response."""
    system_prompt_body = LLM_ASK_QUERY_TYPE.get(ask_type, "send me 'Unknown'")
    system_content = SYSTEM_PROMPT_HEADER + system_prompt_body + SYSTEM_PROMPT_FOOTER
    
    payload = {
        "model": LMSTUDIO_MODEL,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(LMSTUDIO_API_URL, json=payload)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        response_json = response.json()
        if 'choices' not in response_json or not response_json['choices']:
            print(f"[Error] Invalid response format from LMStudio: {response_json}")
            return json.dumps({"result": "Error: Invalid response format from LMStudio"})
            
        content = response_json['choices'][0]['message']['content'].strip()
        
        # Ensure response is a valid JSON string with "result" key
        try:
            # First try to parse it as JSON
            parsed = json.loads(content)
            # If it parses but doesn't have "result" key, wrap it
            if "result" not in parsed:
                return json.dumps({"result": parsed})
            return content
        except json.JSONDecodeError:
            # If not valid JSON, wrap the raw text in a result object
            return json.dumps({"result": content})
            
    except requests.exceptions.RequestException as e:
        print(f"[Error] LMStudio API request failed: {str(e)}")
        return json.dumps({"result": f"Error: LMStudio API request failed - {str(e)}"})
    except Exception as e:
        print(f"[Error] Unexpected error in LMStudio API call: {str(e)}")
        return json.dumps({"result": f"Error: Unexpected error - {str(e)}"})

def ask_chatgpt(ask_type: str, prompt: str, model: str="gpt-4o-mini-2024-07-18", max_tokens: int=2000, temperature: float=0, use_local: bool=False):
    """
    Send a request to either OpenAI API or LMStudio local API based on the use_local parameter.
    
    Args:
        ask_type: Type of query to send
        prompt: The user prompt
        model: Model name (for OpenAI)
        max_tokens: Maximum tokens in response
        temperature: Temperature setting for generation
        use_local: If True, use LMStudio instead of OpenAI
    
    Returns:
        The response content
    """
    if use_local:
        return ask_lmstudio(ask_type, prompt, temperature)
    
    # Default OpenAI behavior
    system_prompt_body = LLM_ASK_QUERY_TYPE.get(ask_type, "send me 'Unknown'")
    openai_client = create_openai_client()
    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_HEADER + system_prompt_body + SYSTEM_PROMPT_FOOTER},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        # max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()