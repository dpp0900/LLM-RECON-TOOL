import os
from llm import ask_chatgpt
import json

def list_all_dirs(root_dir):
    """하위 모든 디렉토리와 파일을 리스트로 반환합니다."""
    all_items = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for dirname in dirnames:
            all_items.append(os.path.join(dirpath, dirname))
    return all_items

def list_all_files(root_dir):
    """하위 모든 파일을 리스트로 반환합니다."""
    all_items = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            all_items.append(os.path.join(dirpath, filename))
    return all_items

def parse_result(res):
    """ChatGPT의 응답을 파싱합니다."""
    try:
        parsed = json.loads(res)
        return parsed.get("result", "No result found")
    except json.JSONDecodeError:
        return "Failed to parse response"
    

if __name__ == "__main__":
    root_directory = "../target/Piggy-bank/sources"  # 현재 디렉토리
    items = list_all_dirs(root_directory)
    print("모든 디렉토리와 파일:")
    for item in items:
        print(item)
    
    res = ask_chatgpt("identify_main_source", str(items))
    print("ChatGPT 응답:")
    print(res)
    parsed_result = parse_result(res)
    print("파싱된 결과:")
    print(parsed_result)
    #check path exist
    
    if os.path.exists(parsed_result):
        print(f"폴더 {parsed_result} 존재")
    else:
        print(f"폴더 {parsed_result} 존재하지 않음")
        
    items = list_all_files(parsed_result)
    print(items)
    res = ask_chatgpt("identify_main_source", str(items))
    print("ChatGPT 응답:")
    print(res)
    
    main_source = parse_result(res)
    print("파싱된 결과:")
    print(main_source)
    code = open(main_source, "r").read()
    print(code)
    res = ask_chatgpt("identify_framework", code)
    print("ChatGPT 응답:")
    print(res)