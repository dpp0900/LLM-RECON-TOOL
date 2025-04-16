import os
import json
import re
from llm import ask_chatgpt

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
    main_source = parse_result(res)
    
    # 결과가 디렉토리인지 확인
    if os.path.isdir(main_source):
        print(f"경고: 반환된 경로 '{main_source}'는 파일이 아닌 디렉토리입니다.")
        # 해당 디렉토리에서 자바 파일을 찾아봅니다
        java_files = [f for f in list_all_files(main_source) if f.endswith('.java')]
        if java_files:
            print(f"디렉토리에서 파일을 찾습니다. 첫 번째 자바 파일을 사용합니다: {java_files[0]}")
            return java_files[0]
        else:
            print("디렉토리에서 자바 파일을 찾을 수 없습니다.")
            # 상위 디렉토리에서 자바 파일 찾기
            parent_dir = os.path.dirname(main_source)
            parent_files = [f for f in list_all_files(parent_dir) if f.endswith('.java')]
            if parent_files:
                print(f"상위 디렉토리에서 파일을 찾습니다: {parent_files[0]}")
                return parent_files[0]
            else:
                return None
    
    return main_source

def identify_framework(file_path):
    """파일 내용을 읽고 identify_framework 작업을 수행합니다."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if os.path.isdir(file_path):
        raise IsADirectoryError(f"Expected a file, but got a directory: {file_path}")
        
    with open(file_path, "r") as file:
        code = file.read()
    res = ask_chatgpt("identify_framework", code)
    return res

def get_endpoint_patterns(file_path, framework):
    """파일 내용을 읽고 엔드포인트 패턴을 식별합니다."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # 모든 프레임워크에 대해 LLM 사용
    with open(file_path, "r") as file:
        code = file.read()
    prompt = {
        "file_path": file_path,
        "code": code,
        "framework": framework
    }
    
    res = ask_chatgpt("how_to_reconginize_endpoint", str(prompt))
    
    # Try to parse the response
    try:
        parsed = parse_result(res)
        if isinstance(parsed, dict):
            print("Successfully parsed endpoint patterns from LLM response")
            return parsed
        else:
            print(f"Parsed response is not a dictionary: {parsed}")
            
            # Fall back to extracting JSON from the response
            import re
            json_match = re.search(r'\{.*\}', res, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    fixed_json = json.loads(json_str)
                    if "result" in fixed_json and isinstance(fixed_json["result"], dict):
                        print("Extracted valid JSON from response")
                        return fixed_json["result"]
                except Exception as e:
                    print(f"Failed to extract JSON: {e}")
            
            return "Failed to parse response"
    except Exception as e:
        print(f"Error parsing endpoint patterns: {e}")
        print(f"Original response: {res}")
        return "Failed to parse response"

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
    # endpoint_patterns가 딕셔너리가 아닌 경우 처리
    if not isinstance(endpoint_patterns, dict):
        print(f"유효한 엔드포인트 패턴이 아닙니다: {endpoint_patterns}")
        return {}
        
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
            
            # 모든 엔드포인트를 ALL 카테고리에 추가하기 위한 세트
            all_endpoints = set()
            
            # RequestMapping 패턴을 위한 처리
            request_pattern = valid_patterns.get("REQUEST", None)
            if request_pattern:
                try:
                    request_matches = re.finditer(request_pattern, code)
                    
                    for match in request_matches:
                        if match.groups() and len(match.groups()) > 0:
                            endpoint_path = match.group(1)
                        else:
                            endpoint_path = match.group(0)
                        
                        all_endpoints.add(endpoint_path)
                        
                        # ALL 카테고리에 추가
                        if "ALL" not in file_endpoints:
                            file_endpoints["ALL"] = []
                        if endpoint_path not in file_endpoints["ALL"]:
                            file_endpoints["ALL"].append(endpoint_path)
                
                except re.error as e:
                    print(f"RequestMapping 패턴 '{request_pattern}' 검색 중 오류 발생: {e}")
            
            # 각 HTTP 메소드별 엔드포인트 추출
            for method, pattern in valid_patterns.items():
                if method == "REQUEST":  # RequestMapping은 이미 처리했으므로 스킵
                    continue
                
                try:
                    # LLM에서 제공한 패턴 사용
                    matches = re.finditer(pattern, code)
                    
                    for match in matches:
                        # 패턴에서 첫 번째 캡처 그룹을 사용 (일반적으로 경로)
                        # 캡처 그룹이 없는 경우 전체 매치 사용
                        if match.groups() and len(match.groups()) > 0:
                            endpoint_path = match.group(1)
                        else:
                            endpoint_path = match.group(0)
                        
                        # 해당 메소드의 엔드포인트 리스트에 추가
                        if method not in file_endpoints:
                            file_endpoints[method] = []
                        if endpoint_path not in file_endpoints[method]:
                            file_endpoints[method].append(endpoint_path)
                        
                        # ALL 카테고리에도 추가
                        all_endpoints.add(endpoint_path)
                
                except re.error as e:
                    print(f"패턴 '{pattern}' 검색 중 오류 발생: {e}")
            
            # ALL 카테고리에 모든 엔드포인트 추가
            if all_endpoints:
                if "ALL" not in file_endpoints:
                    file_endpoints["ALL"] = []
                for path in all_endpoints:
                    if path not in file_endpoints["ALL"]:
                        file_endpoints["ALL"].append(path)
            
            if file_endpoints:  # 해당 파일에서 엔드포인트가 발견된 경우만 추가
                endpoints_by_file[file_path] = file_endpoints

    return endpoints_by_file

def print_endpoints(endpoints_by_file, root_directory):
    """추출된 엔드포인트를 깔끔한 형식으로 출력합니다."""
    if not endpoints_by_file:
        print("추출된 엔드포인트가 없습니다.")
        return
    
    for file_path, endpoints in endpoints_by_file.items():
        # 루트 디렉토리를 기준으로 순수한 상대 경로 계산
        try:
            # root_directory를 기준으로 상대 경로 계산
            rel_path = os.path.relpath(file_path, root_directory)
            # 경로 구분자를 OS에 맞게 조정
            display_path = rel_path
        except Exception:
            # 상대 경로 계산 실패 시 원본 경로 사용
            display_path = file_path
        
        print(f"파일: {display_path}")
        
        # ALL 카테고리가 있으면 먼저 출력
        if "ALL" in endpoints and endpoints["ALL"]:
            print("  ALL:")
            for path in sorted(endpoints["ALL"]):
                display_path = _clean_endpoint_path(path)
                print(f"    - {display_path}")
        
        # GET, POST 등 HTTP 메소드별 엔드포인트 출력
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            if method in endpoints and endpoints[method]:
                print(f"  {method}:")
                for path in sorted(endpoints[method]):
                    display_path = _clean_endpoint_path(path)
                    print(f"    - {display_path}")
                    
        print()  # 파일 간 구분을 위한 빈 줄

def _clean_endpoint_path(path):
    """엔드포인트 경로를 정리합니다."""
    # 문자열이 아닌 경우 문자열로 변환
    if not isinstance(path, str):
        path = str(path)
    
    # 어노테이션 형식에서 경로 추출 (@RequestMapping({"/path"}) -> /path)
    if '@' in path:
        path_match = re.search(r'"([^"]+)"', path)
        if path_match:
            path = path_match.group(1)
    
    # 경로가 /로 시작하지 않으면 추가
    if not path.startswith('/'):
        path = '/' + path
        
    return path

def main():
    """메인 실행 함수."""
    # 명령줄 인자로 루트 디렉토리를 받을 수 있게 수정
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='웹 서비스 엔드포인트 추출 도구')
    parser.add_argument('--root_dir', '-r', help='분석할 루트 디렉토리 경로', default=None)
    args = parser.parse_args()
    
    # 루트 디렉토리 설정
    if args.root_dir:
        root_directory = args.root_dir
    elif len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        # 첫 번째 인자가 존재하는 경로인 경우 사용
        root_directory = sys.argv[1]
    else:
        root_directory = input("분석할 루트 디렉토리 경로를 입력하세요: ")
    
    # 상대 경로를 절대 경로로 변환
    root_directory = os.path.abspath(root_directory)
    
    # 경로가 존재하는지 확인
    if not os.path.exists(root_directory):
        print(f"오류: 입력한 경로 '{root_directory}'가 존재하지 않습니다.")
        return

    print(f"루트 디렉토리: {root_directory}")

    # Step 1: identify_main_folder
    main_folder = identify_main_folder(root_directory)
    if not check_path_exists(main_folder):
        print(f"경로를 찾을 수 없습니다: {main_folder}")
        return
    print("identify_main_folder 결과:", main_folder)

    # Step 2: identify_main_source
    main_source = identify_main_source(main_folder)
    if not main_source or not check_path_exists(main_source):
        print(f"유효한 파일을 찾을 수 없습니다: {main_source}")
        return
    
    if os.path.isdir(main_source):
        print(f"오류: {main_source}는 파일이 아닌 디렉토리입니다.")
        return
        
    extension = main_source.split(".")[-1]
    extensions = [f".{extension}"]
    print("identify_main_source 결과:", main_source)

    # Step 3: analyze the main source file
    framework_result = identify_framework(main_source)
    print("최종 분석 결과:", framework_result)

    # Step 4: get endpoint patterns
    endpoint_patterns = get_endpoint_patterns(main_source, framework_result)
    print("엔드포인트 패턴:", endpoint_patterns)
    
    # 엔드포인트 패턴이 유효하지 않은 경우 종료
    if isinstance(endpoint_patterns, str) and endpoint_patterns.startswith("Failed"):
        print("유효한 엔드포인트 패턴을 얻지 못했습니다. 프로세스를 종료합니다.")
        return

    # Step 5: extract endpoints
    try:
        endpoints_by_file = extract_endpoints(root_directory, extensions, endpoint_patterns)
        print("\n추출된 엔드포인트:")
        print_endpoints(endpoints_by_file, root_directory)
    except Exception as e:
        print(f"엔드포인트 추출 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()  # 스택 트레이스 출력으로 디버깅 지원

if __name__ == "__main__":
    main()