import os
from openai import OpenAI

LLM_ASK_QUERY_TYPE = {
    "identify_main_folder": '''Your task is to identify and return ONLY ONE path to the folder that most likely contains the main "SOURCE" code of the web service (e.g., *.py, *.java, *.php, etc.). Analyze the provided list of subdirectories and exclude irrelevant folders such as `BOOT-INF/` or other auxiliary directories. Provide your answer in the specified format.''',
    
    "identify_main_source": '''Your task is to identify and return ONLY ONE "SOURCE" FILE path that most likely contains the main source code of the web service (MUST CONTAIN ENDPOINT). Analyze the provided list of files and focus on files with relevant extensions (e.g., *.py, *.java, *.php, etc.). Consider indicators such as entry points, main functions, or framework-specific files. Provide your answer in the specified format.''',
    
    "identify_framework": '''Your task is to identify the framework of the web service based on the provided source code file. Analyze the code carefully to determine the framework (e.g., Django, Flask, Spring, Express, Laravel, Ruby on Rails). Look for framework-specific imports, annotations, or patterns. If the framework is not clear, ask for clarification. Provide ONLY the name of the framework in the specified format.''',
    
    "how_to_reconginize_endpoint": '''Your task is to generate a JSON object where each key is an HTTP method (e.g., GET, POST, PUT, DELETE, etc.), and the value is a valid and precise regular expression pattern that can be used to identify endpoints for that method in the provided source code. Follow these rules:
1. Ensure all patterns are syntactically correct and can be compiled without errors.
2. Patterns should be general enough to work across multiple programming languages and frameworks (e.g., Java, Python, JavaScript, PHP).
3. Avoid overly specific patterns that depend on a single framework or language. Your return will be used to identify endpoints in various web service implementations.
4. Include patterns that match common endpoint definitions, such as:
   - Annotations (e.g., @GetMapping, @RequestMapping, @Route, @app.route)
   - Function calls (e.g., app.get(), router.post())
   - Path definitions (e.g., path('url/', view_function))
5. Provide the patterns in the following JSON format:
{
    //if method like @RequestMapping in spring, add your self
    "GET": "regex_for_get",
    "POST": "regex_for_post",
    "PUT": "regex_for_put",
    "DELETE": "regex_for_delete",
    "PATCH": "regex_for_patch"
}
6. Do not include any additional text or explanations outside this specified format.''',

    "extract_parameters": '''Your task is to analyze the provided endpoint code and extract all parameters (path parameters, query parameters, request body fields, etc.). Return the information in the following JSON format:
{
    "endpoint": "/path/to/endpoint",
    "method": "HTTP_METHOD",
    "parameters": [
        {
            "name": "param_name",
            "type": "param_type",
            "required": true/false,
            "location": "path/query/body/header",
            "description": "Brief description if available"
        }
    ]
}
Do not include any additional text or explanations outside this specified format.''',

    "security_analysis": '''Your task is to analyze the provided endpoint code and identify potential security vulnerabilities or weaknesses. Focus on common web security issues such as:
1. Injection vulnerabilities (SQL, NoSQL, OS command, etc.)
2. Authentication/Authorization issues
3. Sensitive data exposure
4. CSRF/XSS vulnerabilities
5. Input validation issues
6. Business logic flaws

Return your analysis in the following JSON format:
{
    "endpoint": "/path/to/endpoint",
    "method": "HTTP_METHOD",
    "vulnerabilities": [
        {
            "type": "vulnerability_type",
            "severity": "high/medium/low",
            "description": "Description of the vulnerability",
            "recommendation": "How to fix the issue"
        }
    ]
}
Do not include any additional text or explanations outside this specified format.''',
}

SYSTEM_PROMPT_HEADER = '''You are a highly capable AI assistant specializing in information security and software analysis. Your primary task is to assist in the reconnaissance and analysis of authorized web services. You will follow the user's instructions step by step and provide precise, actionable, and concise responses.'''
SYSTEM_PROMPT_FOOTER = '''Your response must strictly follow this format: {"result":"your_answer"}. Do not include any additional text or explanations outside this format.'''

def get_openai_api_key():
    """Reads the OpenAI API key from a file or environment variable."""
    if os.path.exists("openai_key"):
        with open("openai_key", "r") as key_file:
            return key_file.read().strip()
    return os.environ.get("OPENAI_API_KEY")

def create_openai_client():
    """Creates and returns an OpenAI client."""
    api_key = get_openai_api_key()
    if api_key:
        return OpenAI(api_key=api_key)
    else:
        # OpenAI API 키가 없는 경우 LMStudio로 대체
        # localhost:1234를 베이스 주소로 지정
        return OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

def get_claude_api_key():
    """Reads the Anthropic Claude API key from a file or environment variable."""
    if os.path.exists("claude_key"):
        with open("claude_key", "r") as key_file:
            return key_file.read().strip()
    return os.environ.get("ANTHROPIC_API_KEY")

def create_llm_client(provider="openai"):
    """Creates and returns an LLM client based on the specified provider."""
    if provider == "openai":
        return create_openai_client()
    elif provider == "claude":
        # Implementation for Claude would go here
        # This is a placeholder for future implementation
        api_key = get_claude_api_key()
        if not api_key:
            print("Claude API key not found. Falling back to OpenAI.")
            return create_openai_client()
        # Would need to implement Claude client here
        return None
    elif provider == "local":
        # Local LLM via Ollama or similar
        return OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

def ask_llm(ask_type: str, prompt: str, provider="openai", model: str=None, temp: float=0.05, max_tokens: int=2000):
    """Queries an LLM with the given prompt and returns the response."""
    system_prompt_body = LLM_ASK_QUERY_TYPE.get(ask_type, "send me 'Unknown'")
    
    # Set default model based on provider
    if model is None:
        if provider == "openai":
            model = "gpt-4o-mini"
        elif provider == "claude":
            model = "claude-3-haiku-20240307"
        elif provider == "local":
            model = "llama3:latest"  # or other local model
    
    # Use appropriate client based on provider
    if provider == "openai" or provider == "local":
        client = create_llm_client(provider)
        
        # Check if using local LLM
        if provider == "local" and not get_openai_api_key():
            provider = "local"
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_HEADER + system_prompt_body + SYSTEM_PROMPT_FOOTER},
                {"role": "user", "content": prompt}
            ],
            temperature=temp,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    
    elif provider == "claude":
        # Placeholder for Claude implementation
        # Would need to implement Claude API call here
        print("Claude API not yet implemented. Falling back to OpenAI.")
        return ask_llm(ask_type, prompt, "openai", model, temp, max_tokens)
    
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

# Legacy function for backward compatibility
def ask_chatgpt(ask_type: str, prompt: str, model: str="gpt-4o-mini", temp: float=0.05, max_tokens: int=2000):
    """Legacy function that forwards to ask_llm for backward compatibility."""
    return ask_llm(ask_type, prompt, "openai", model, temp, max_tokens)