import os
from openai import OpenAI

LLM_ASK_QUERY_TYPE = {
    "identify_main_folder": '''Your task is to identify and return ONLY ONE path to the folder that most likely contains the main "SOURCE" code of the web service (e.g., *.py, *.java, *.php, etc.). Analyze the provided list of subdirectories and exclude irrelevant folders such as `BOOT-INF/` or other auxiliary directories. Provide your answer in the specified format.''',
    
    "identify_main_source": '''Your task is to identify and return ONLY ONE "SOURCE" FILE path that most likely contains the main source code of the web service (MUST CONTAIN ENDPOINT). Analyze the provided list of files and focus on files with relevant extensions (e.g., *.py, *.java, *.php, etc.). Consider indicators such as entry points, main functions, or framework-specific files. Provide your answer in the specified format.''',
    
    "identify_framework": '''Your task is to identify the framework of the web service based on the provided source code file. Analyze the code carefully to determine the framework (e.g., Django, Flask, Spring, Express). If the framework is not clear, ask for clarification. Provide ONLY the name of the framework in the specified format.''',
    
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
6. Do not include any additional text or explanations outside the specified format.'''
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