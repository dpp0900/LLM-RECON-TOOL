import os
from openai import OpenAI

LLM_ASK_QUERY_TYPE = {
    "identify_main_folder": '''Your task is to identify and return ONLY ONE path to the folder that most likely contains the main "SOURCE" code of the web service (e.g., *.py, *.java, *.php, etc.). Analyze the provided list of subdirectories and exclude irrelevant folders such as `BOOT-INF/` or other auxiliary directories. Provide your answer in the specified format.''',
    
    "identify_main_source": '''Your task is to identify and return ONLY ONE "SOURCE" FILE path that most likely contains the main source code of the web service (MUST CONTAIN ENDPOINT). Analyze the provided list of files and focus on files with relevant extensions (e.g., *.py, *.java, *.php, etc.). Consider indicators such as entry points, main functions, or framework-specific files. Provide your answer in the specified format.''',
    
    "identify_framework": '''Your task is to identify the framework of the web service based on the provided source code file. Analyze the code carefully to determine the framework (e.g., Django, Flask, Spring, Express). If the framework is not clear, ask for clarification. Provide ONLY the name of the framework in the specified format.''',
    
    "identify_service_name": '''Your task is to identify the name of the web service based on the provided list of dir and files. Analyze the data carefully to determine the service name. If the service name is not clear, ask for clarification. Provide ONLY the name of the service in the specified format.''',
    
    "how_to_reconginize_endpoint": '''Your task is to generate a JSON object mapping HTTP methods to regular expression patterns that extract endpoint paths from source code. Follow these instructions:

1. Produce a JSON object with exactly these keys: "ALL", "GET", "POST"
2. Each value must be a syntactically correct regex pattern that, when applied to source code, returns only the endpoint path (e.g., "/api"). Use capturing groups or optional markers as needed.
3. The regex patterns should be generic enough to detect endpoint definitions in multiple languages and frameworks (e.g., via annotations like @GetMapping, @RequestMapping, @app.route; function calls like app.get(), router.post(); or route definitions like path('url/', ...)).
4. The "ALL" key should include patterns for annotations or functions that do not specify a specific HTTP method (e.g., @RequestMapping without a method).
5. Regex should return only the endpoint path, not the entire line or function signature.
6. Regex should return single endpoint paths, not lists or arrays.
7. Do not include any additional text—return only the JSON object.

Example expected format:
{
    "ALL": "regex_for_generic_request_mapping",
    "GET": "regex_for_get",
    "POST": "regex_for_post",
}'''
,
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
    if not api_key:
        raise ValueError("OpenAI API key not found. Ensure 'openai_key' file or environment variable is set.")
    return OpenAI(api_key=api_key)

def ask_chatgpt(ask_type: str, prompt: str, model: str="gpt-4o-mini", temp: float=0.05, max_tokens: int=2000):
    system_prompt_body = LLM_ASK_QUERY_TYPE.get(ask_type, "send me 'Unknown'")
    openai_client = create_openai_client()
    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_HEADER + system_prompt_body + SYSTEM_PROMPT_FOOTER},
            {"role": "user", "content": prompt}
        ],
        temperature=temp,
        # max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()