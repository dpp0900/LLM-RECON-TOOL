import os
import json
import re
from llm import ask_chatgpt

import model

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

def check_path_exists(path):
    """파일 또는 폴더가 존재하는지 확인합니다."""
    if os.path.exists(path):
        return True
    else:
        return False

def identify_main_folder(root_directory):
    """identify_main_folder 작업을 수행합니다."""
    dirs = list_all_dirs(root_directory)
    res = ask_chatgpt("identify_main_folder", str(dirs))
    return parse_result(res)

def identify_main_source(folder_path):
    """identify_main_source 작업을 수행합니다."""
    files = list_all_files(folder_path)
    res = ask_chatgpt("identify_main_source", str(files))
    return parse_result(res)

def identify_framework(file_path):
    """파일 내용을 읽고 identify_framework 작업을 수행합니다."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, "r") as file:
        code = file.read()
    res = ask_chatgpt("identify_framework", code)
    return res

def identify_service_name(folder_path):
    """서비스 이름을 식별합니다."""
    dirs = list_all_dirs(folder_path)
    res = ask_chatgpt("identify_service_name", str(dirs))
    return parse_result(res)

def get_endpoint_patterns(file_path, framework):
    """파일 내용을 읽고 엔드포인트 패턴을 식별합니다."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, "r") as file:
        code = file.read()
    prompt = {
        "file_path": file_path,
        "code": code,
        "framework": framework
    }
    
    res = ask_chatgpt("how_to_reconginize_endpoint", str(prompt))
    return parse_result(res)

def get_all_extension_files(root_directory, extensions):
    """특정 확장자를 가진 모든 파일을 찾습니다."""
    all_files = []
    for dirpath, dirnames, filenames in os.walk(root_directory):
        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                all_files.append(os.path.join(dirpath, filename))
    return all_files

def validate_regex_patterns(regex_patterns):
    """정규 표현식 패턴의 유효성을 검사합니다."""
    valid_patterns = []
    for pattern in regex_patterns:
        try:
            re.compile(pattern)  # 패턴 컴파일 시도
            valid_patterns.append(pattern)
        except re.error as e:
            print(f"유효하지 않은 패턴: {pattern} - 오류: {e}")
    return valid_patterns

def extract_endpoints(root_directory, extensions, endpoint_patterns):
    """주어진 디렉토리에서 엔드포인트를 추출합니다."""
    valid_patterns = {}
    for method, pattern in endpoint_patterns.items():
        try:
            re.compile(pattern)  # 패턴 컴파일 시도
            valid_patterns[method] = pattern
        except re.error as e:
            print(f"유효하지 않은 패턴 ({method}): {pattern} - 오류: {e}")

    if not valid_patterns:
        print("유효한 정규 표현식 패턴이 없습니다.")
        return {}

    all_files = get_all_extension_files(root_directory, extensions)
    endpoints_by_file = {}

    for file_path in all_files:
        with open(file_path, "r") as file:
            code = file.read()
            file_endpoints = {}
            for method, pattern in valid_patterns.items():
                # 매칭된 경로만 추출
                matches = re.findall(pattern, code)
                if matches:
                    if method not in file_endpoints:
                        file_endpoints[method] = []
                    file_endpoints[method].extend(matches)
            if file_endpoints:  # 해당 파일에서 엔드포인트가 발견된 경우만 추가
                endpoints_by_file[file_path] = file_endpoints

    return endpoints_by_file
    

def main():
    """메인 실행 함수."""
    root_directory = "../target/Piggy-bank/sources/com/teamsa/"  # 분석할 루트 디렉토리

    # Step 1: identify_main_folder
    main_folder = identify_main_folder(root_directory)
    if not check_path_exists(main_folder):
        return
    print("identify_main_folder 결과:", main_folder)

    # Step 2: identify_main_source
    main_source = identify_main_source(main_folder)
    if not check_path_exists(main_source):
        return
    extension = main_source.split(".")[-1]
    extensions = [f".{extension}"]
    print("identify_main_source 결과:", main_source)

    # Step 3: analyze the main source file
    framework_result = identify_framework(main_source)
    print("최종 분석 결과:", framework_result)
    
    service_name = identify_service_name(main_folder)
    print("서비스 이름:", service_name)
    
    Service = model.Service(name="UserService", root_directory=root_directory, main_source=main_source, framework=framework_result)

    # Step 4: get endpoint patterns
    endpoint_patterns = get_endpoint_patterns(main_source, framework_result)
    print("엔드포인트 패턴:", endpoint_patterns)

    # Step 5: extract endpoints
    endpoints_by_file = extract_endpoints(root_directory, extensions, endpoint_patterns)
    input()
    print("\n추출된 엔드포인트:")
    for file_path, endpoints in endpoints_by_file.items():
        print(f"파일: {file_path}")
        for method, paths in endpoints.items():
            print(f"  {method}:")
            for path in paths:
                print(f"    - {path}")

if __name__ == "__main__":
    main()