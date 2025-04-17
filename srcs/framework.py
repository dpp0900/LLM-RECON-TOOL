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
    print("ChatGPT 응답:", res)
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
                print(f"파일 {file_path}에서 엔드포인트 발견: {file_endpoints}")

    return endpoints_by_file

def extract_code_from_endpoint(root_directory, endpoints_by_file):
    """
    주어진 엔드포인트 정보에 기반해 코드를 추출합니다.
    추출할 코드의 범위는 현 엔드포인트 선언부부터 다음 엔드포인트 선언부까지입니다.
    또한 ALL 메소드는 무시합니다.
    """
    extracted_code_by_file = {}

    for file_path, endpoints in endpoints_by_file.items():
        if not os.path.exists(file_path):
            print(f"파일을 찾을 수 없습니다: {file_path}")
            continue

        with open(file_path, "r") as file:
            code_lines = file.readlines()

        extracted_code_by_file[file_path] = {}

        for method, endpoint_list in endpoints.items():
            if method == "ALL":  # ALL 메소드는 무시
                continue

            extracted_code_by_file[file_path][method] = []

            # 각 엔드포인트의 선언부와 다음 선언부 사이의 코드 추출
            for i, endpoint in enumerate(endpoint_list):
                # 현재 엔드포인트의 시작 위치
                start_index = None
                for line_num, line in enumerate(code_lines):
                    if endpoint in line:
                        start_index = line_num
                        break

                if start_index is None:
                    print(f"엔드포인트를 찾을 수 없습니다: {endpoint}")
                    continue

                # 다음 엔드포인트의 시작 위치
                if i + 1 < len(endpoint_list):
                    next_endpoint = endpoint_list[i + 1]
                    end_index = None
                    for line_num, line in enumerate(code_lines[start_index + 1:], start=start_index + 1):
                        if next_endpoint in line:
                            end_index = line_num
                            break
                    end_index = end_index if end_index is not None else len(code_lines)
                else:
                    end_index = len(code_lines)  # 마지막 엔드포인트는 파일 끝까지

                # 코드 추출
                extracted_code = "".join(code_lines[start_index:end_index]).strip()
                extracted_code_by_file[file_path][method].append({
                    "endpoint": endpoint,
                    "code": extracted_code
                })

    return extracted_code_by_file

def parse_path_from_endpoint(endpoints_by_file):
    """엔드포인트 선언 코드에서 경로를 추출합니다."""
    RULE = '''(["'])(\/[a-zA-Z0-9_\-\/\.\:\{\}]*)(["'])'''
    paths_by_file = {}
    for file_path, endpoints in endpoints_by_file.items():
        paths_by_file[file_path] = {}
        for method, endpoint_list in endpoints.items():
            paths_by_file[file_path][method] = []
            for endpoint in endpoint_list:
                match = re.search(RULE, endpoint)
                if match:
                    path = match.group(2)
                    paths_by_file[file_path][method].append(path)
                else:
                    print(f"패턴을 찾을 수 없습니다: {endpoint}")
                    paths_by_file[file_path][method].append(endpoint)
    return paths_by_file

    
def concat_endpoint_results(endpoints_by_file):
    """ALL 메소드로 반환된 엔드포인트를 GET, POST 엔드포인트와 합치는 작업을 합니다.
    ALL 엔드포인트는 GET, POST 엔드포인트의 basepath로 사용되며, ALL 엔드포인트는 삭제됩니다.
    Dict의 구조는 {"file_path": {"GET": ["/api/endpoint1", "/api/endpoint2"], "POST": ["/api/endpoint3"]}}"""

    all_endpoints = {}
    for file_path, endpoints in endpoints_by_file.items():
        basepath = None
        if "ALL" in endpoints:
            basepath = endpoints["ALL"][0] if endpoints["ALL"] else None

        for method, paths in endpoints.items():
            if method == "ALL":
                continue

            if paths:
                for path in paths:
                    full_path = f"{basepath}{path}" if basepath else path
                    if file_path not in all_endpoints:
                        all_endpoints[file_path] = {}
                    if method not in all_endpoints[file_path]:
                        all_endpoints[file_path][method] = []
                    all_endpoints[file_path][method].append(full_path)

    return all_endpoints
    

def add_endpoint_to_service(service, all_endpoints):
    """Service 객체에 엔드포인트를 추가합니다."""
    for file_path, endpoints in all_endpoints.items():
        for method, paths in endpoints.items():
            for path in paths:
                endpoint = model.Endpoint(filepath=file_path, method=method, path=path)
                service.add_endpoint(endpoint)
                # print(f"엔드포인트 추가: {endpoint}")
    # print(service.describe())  # Service 객체의 정보를 출력합니다.

def visualize_dependency_graph(service):
    """Service 객체의 의존성 그래프를 시각화합니다."""
    import networkx as nx
    import matplotlib.pyplot as plt

    # 그래프 데이터 가져오기
    graph_data = service.dependencies.describe()

    # NetworkX 그래프 생성
    G = nx.DiGraph()
    for from_node, to_nodes in graph_data.items():
        for to_node in to_nodes:
            G.add_edge(from_node, to_node)

    # 그래프 레이아웃 설정 (spring_layout 사용)
    pos = nx.spring_layout(G, k=0.5)  # k 값으로 노드 간의 간격 조정

    # 그래프 시각화
    plt.figure(figsize=(14, 10))  # 그래프 크기 조정
    nx.draw(G, pos, with_labels=True, node_color="lightblue", font_weight="bold", node_size=2000, arrowsize=20)
    plt.title("Dependency Graph")
    plt.show()

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
    
    Service = model.Service(name=service_name, root_directory=root_directory, main_source=main_source, framework=framework_result)
    
    # Step 4: get endpoint patterns
    endpoint_patterns = get_endpoint_patterns(main_source, framework_result)
    for method, pattern in endpoint_patterns.items():
        print(f"{method} 패턴: {pattern}")

    # # Step 5: extract endpoints
    endpoints_by_file = extract_endpoints(root_directory, extensions, endpoint_patterns)
    paths_by_file = parse_path_from_endpoint(endpoints_by_file)
    print("\n엔드포인트 결과:")
    print(json.dumps(paths_by_file, indent=2))
    all_endpoints = concat_endpoint_results(paths_by_file)
    print("\n최종 엔드포인트 결과:")
    print(json.dumps(all_endpoints, indent=2))
    endpoints_code_by_file = extract_code_from_endpoint(root_directory, endpoints_by_file)
    print("\n엔드포인트 코드 결과:")
    print(json.dumps(endpoints_code_by_file, indent=2))
        
    # Step 6: add endpoints to service
    # add_endpoint_to_service(Service, all_endpoints)
    
    # visualize_dependency_graph(Service)

if __name__ == "__main__":
    main()