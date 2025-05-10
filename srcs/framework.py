import os
import json
import re
import sys
from llm import ask_chatgpt

import model

def list_all_dirs(root_dir):
    """Returns a list of all subdirectories and files."""
    all_items = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for dirname in dirnames:
            all_items.append(os.path.join(dirpath, dirname))
    return all_items

def list_all_files(root_dir):
    """Returns a list of all files in all subdirectories."""
    all_items = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            all_items.append(os.path.join(dirpath, filename))
    return all_items

def parse_result(res):
    """ChatGPT의 응답을 파싱하고 JSON 혹은 마크다운 코드 블록을 처리하고, 필요 시 복구합니다."""
    # 1차: 최상위 JSON 파싱 시도
    try:
        parsed0 = json.loads(res)
    except json.JSONDecodeError:
        # JSON이 아니면 마크다운 코드 블록 내부 JSON 추출 시도
        m0 = re.search(r'```json\s*([\s\S]*?)\s*```', res)
        if m0:
            inner0 = m0.group(1).strip()
            try:
                return json.loads(inner0)
            except json.JSONDecodeError:
                return inner0
        # 그 외 원본 문자열 반환
        return res.strip()

    # 최상위 JSON 파싱 성공
    # 'result' 키가 있으면 그 값을 content로 사용
    if isinstance(parsed0, dict) and "result" in parsed0:
        result0 = parsed0["result"]
        # result0이 문자열인 경우 추가 처리
        if isinstance(result0, str):
            # 마크다운 코드 블록 처리
            m1 = re.search(r'```json\s*([\s\S]*?)\s*```', result0)
            if m1:
                content = m1.group(1).strip()
            else:
                content = result0.strip()
            # 내부 JSON 파싱 시도
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # 복구 로직: 따옴표/공백 정리
                fixed = content.replace("'", '"').replace("\n", " ").replace("\r", " ").strip()
                try:
                    return json.loads(fixed)
                except Exception:
                    return content
        # result0이 dict/list 등 JSON 타입이면 그대로 반환
        return result0
    # result 키 없으면 parsed0 반환
    return parsed0

def check_path_exists(path):
    """Checks whether a file or directory exists."""
    if os.path.exists(path):
        return True
    else:
        return False

def identify_main_folder(root_directory, use_local=False):
    """identify_main_folder 작업을 수행합니다."""
    dirs = list_all_dirs(root_directory)
    res = ask_chatgpt("identify_main_folder", str(dirs), use_local=use_local)
    return parse_result(res)

def identify_main_source(folder_path, temperature=0, use_local=False):
    """identify_main_source 작업을 수행합니다."""
    files = list_all_files(folder_path)
    res = ask_chatgpt("identify_main_source", str(files), temperature=temperature, use_local=use_local)
    return parse_result(res)

def identify_framework(file_path, use_local=False):
    """파일 내용을 읽고 identify_framework 작업을 수행합니다."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, "r") as file:
        code = file.read()
    res = ask_chatgpt("identify_framework", code, use_local=use_local)
    return res

def identify_service_name(folder_path, use_local=False):
    """서비스 이름을 식별합니다."""
    dirs = list_all_dirs(folder_path)
    res = ask_chatgpt("identify_service_name", str(dirs), use_local=use_local)
    return parse_result(res)

def get_endpoint_patterns(file_path, framework, temperature=0, use_local=False):
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
    
    res = ask_chatgpt("how_to_reconginize_endpoint", str(prompt), temperature=temperature, use_local=use_local)
    print("ChatGPT response:", res)
    # 파싱 시도
    patterns = parse_result(res)
    # 결과가 dict이 아니거나 빈 dict인 경우, Spring 기본 패턴 폴백
    # if not isinstance(patterns, dict) or not patterns:
    #     print(f"[Fallback] Applying built-in endpoint patterns for framework '{framework}'")
    #     patterns = {
    #         "ALL": ".*@RequestMapping\\s*({.*?})",
    #         "GET": ".*@GetMapping\\s*({.*?})",
    #         "POST": ".*@PostMapping\\s*({.*?})"
    #     }
    return patterns

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
            print(f"Invalid pattern: {pattern} - error: {e}")
    return valid_patterns

def extract_endpoints(root_directory, extensions, endpoint_patterns):
    """주어진 디렉토리에서 엔드포인트를 추출합니다."""
    valid_patterns = {}
    for method, pattern in endpoint_patterns.items():
        try:
            re.compile(pattern)  # 패턴 컴파일 시도
            valid_patterns[method] = pattern
        except re.error as e:
            print(f"Invalid pattern ({method}): {pattern} - error: {e}")

    if not valid_patterns:
        print("No valid regex patterns found.")
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
                print(f"Found endpoints in file {file_path}: {file_endpoints}")

    return endpoints_by_file

def extract_code_from_endpoint(root_directory, endpoints_by_file):
    """
    주어진 엔드포인트 정보에 기반해 코드를 추출합니다.
    추출할 코드의 범위는 현 엔드포인트 선언부부터 다음 선언부 또는 겹치는 선언부까지입니다.
    또한 ALL 메소드는 무시합니다.
    """
    extracted_code_by_file = {}

    for file_path, endpoints in endpoints_by_file.items():
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
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
                    print(f"Endpoint not found: {endpoint}")
                    continue

                # 다음 엔드포인트의 시작 위치를 전체 엔드포인트에서 탐색
                end_index = len(code_lines)  # 기본적으로 파일 끝까지
                for other_method, other_endpoint_list in endpoints.items():
                    if other_method == "ALL":  # ALL 메소드는 무시
                        continue

                    for other_endpoint in other_endpoint_list:
                        if other_endpoint == endpoint:
                            continue  # 현재 엔드포인트는 건너뜀

                        # 다른 엔드포인트의 시작 위치를 찾음
                        other_start_index = None
                        for line_num, line in enumerate(code_lines):
                            if other_endpoint in line:
                                other_start_index = line_num
                                break

                        # 현재 엔드포인트의 끝 범위를 결정
                        if other_start_index is not None and other_start_index > start_index:
                            end_index = min(end_index, other_start_index)

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
                    print(f"Pattern not found: {endpoint}")
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
    

def add_endpoint_to_service(service, endpoints_by_file, paths_by_file, endpoints_code_by_file):
    """
    Service 객체에 엔드포인트를 추가합니다.
    paths_by_file와 endpoints_code_by_file를 활용하여 엔드포인트 정보를 명확히 추가합니다.
    path는 paths_by_file, code는 endpoints_code_by_file에서 가져옵니다.
    """
    for file_path, endpoints in endpoints_by_file.items():
        for method, paths in endpoints.items():
            if file_path not in paths_by_file or file_path not in endpoints_code_by_file:
                continue

            for path in paths:
                if method not in paths_by_file[file_path]:
                    continue
                
                real_path = paths_by_file[file_path][method][0]  # 첫 번째 경로 사용

                # 엔드포인트 객체 생성
                endpoint = model.Endpoint(path=real_path, method=method, file_path=file_path)
                for code in endpoints_code_by_file[file_path][method]:
                    if code["endpoint"] == path:
                        endpoint.code = code["code"]
                        break
                # Service에 엔드포인트 추가
                service.add_endpoint(endpoint)

def explain_endpoint(endpoint, use_local=False):
    """엔드포인트에 대한 설명을 생성합니다."""
    prompt = {
        "path": endpoint.path,
        "method": endpoint.method,
        "file_path": endpoint.file_path,
        "code": endpoint.code
    }
    res = ask_chatgpt("describe_endpoint", str(prompt), use_local=use_local)
    # 파싱 결과 가져오기
    result = parse_result(res)
    # 'endpoint' 키가 있는 경우 내부 객체 반환
    if isinstance(result, dict) and "endpoint" in result:
        desc = result["endpoint"]
    elif isinstance(result, dict):
        # 이미 사전 형식일 경우 그대로 사용
        desc = result
    else:
        # 문자열 등 다른 형식인 경우 description 필드로 래핑
        print(f"[Warning] explain_endpoint returned non-dict result, wrapping into description: {result}")
        desc = {"description": result}
    return desc

def visualize_dependency_graph(service):
    from pyvis.network import Network
    import os

    # 노드와 엣지 초기화
    id_to_label = {}
    id_to_type = {}
    edges = []

    # 서비스 노드 추가
    id_to_label[service.id] = service.name
    id_to_type[service.id] = "service"

    # 파일 및 엔드포인트 노드 추가
    for endpoint in service.endpoints:
        # 파일 노드 추가 (파일 이름만 사용)
        file_name = os.path.basename(endpoint.file_path)  # 파일 이름 추출
        file_node_id = f"file::{file_name}"
        if file_node_id not in id_to_label:
            id_to_label[file_node_id] = f"📄 {file_name}"
            id_to_type[file_node_id] = "file"

        # 엔드포인트 노드 추가
        id_to_label[endpoint.id] = f"{endpoint.method} {endpoint.path}"
        id_to_type[endpoint.id] = "endpoint"

        # 서비스 → 파일 엣지
        edges.append((service.id, file_node_id))

        # 파일 → 엔드포인트 엣지
        edges.append((file_node_id, endpoint.id))

        # 엔드포인트 간 의존성 엣지
        for dep_id in endpoint.dependencies.describe().get(endpoint.id, []):
            edges.append((endpoint.id, dep_id))

    # 네트워크 생성
    net = Network(height="900px", width="100%", directed=True, notebook=False)

    # 계층적 레이아웃 설정
    net.set_options("""
    {
        "layout": {
            "hierarchical": {
                "enabled": true,
                "direction": "UD",
                "sortMethod": "hubsize"
            }
        },
        "physics": {
            "enabled": false
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 50,
            "navigationButtons": true
        },
        "nodes": {
            "font": {
                "size": 16,
                "color": "#343434"
            },
            "borderWidth": 2,
            "shape": "box"
        },
        "edges": {
            "color": {
                "color": "#cccccc",
                "highlight": "#ff9800"
            },
            "arrows": {
                "to": {
                    "enabled": true,
                    "scaleFactor": 1.2
                }
            },
            "smooth": {
                "enabled": false
            }
        }
    }
    """)

    # 노드 색상 설정
    color_map = {
        "service": "#bbdefb",  # 서비스 노드: 파란색
        "file": "#fff9c4",     # 파일 노드: 노란색
        "endpoint": "#c8e6c9"  # 엔드포인트 노드: 초록색
    }

    # 노드 추가 (툴팁에 줄바꿈 문자 사용)
    for node_id, label in id_to_label.items():
        node_type = id_to_type.get(node_id, "endpoint")
        title = ""
        if node_type == "service":
            title = (
                "Service\n"
                f"Name: {service.name}\n"
                f"Root Directory: {service.root_directory}\n"
                f"Main Source: {service.main_source}\n"
                f"Framework: {service.framework}\n"
                f"Endpoints: {len(service.endpoints)}"
            )
        elif node_type == "file":
            title = f"File: {label}"
        elif node_type == "endpoint":
            endpoint = next((ep for ep in service.endpoints if ep.id == node_id), None)
            if endpoint:
                desc = getattr(endpoint, 'description', '')
                if desc:
                    # \n로 줄바꿈 문자로 치환 (이미 <br>가 포함되어 있다면)
                    desc = desc.replace('<br>', '\n')
                title = (
                    "Endpoint\n"
                    f"Path: {endpoint.path}\n"
                    f"Method: {endpoint.method}\n"
                    f"File: {endpoint.file_path}\n"
                    f"Params: {getattr(endpoint, 'params', 'N/A')}\n"
                    f"Response: {getattr(endpoint, 'response_type', 'N/A')}\n"
                    f"Description: {desc}"
                )
            else:
                title = label

        net.add_node(
            node_id,
            label=label,
            title=title,  # title에 줄바꿈 문자가 포함됨
            color=color_map.get(node_type, "#e0e0e0"),
            shape="ellipse" if node_type == "endpoint" else "box",
            font={"size": 22, "color": "#222222", "face": "Segoe UI"},
            borderWidth=2,
            shadow=False,
        )

    for from_id, to_id in edges:
        net.add_edge(
            from_id, to_id,
            color="#90caf9",
            width=2.5,
            arrows="to",
            smooth=True,
            shadow=False
        )

    net.write_html("dependency_graph.html")
    
    # HTML 파일 post-process: 툴팁 스타일 및 자동 줄바꿈 적용
    html_path = "dependency_graph.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    custom_css = """
    <style>
    .vis-tooltip {
        max-width: 400px !important;
        white-space: pre-line !important;
        word-break: break-all !important;
        overflow-x: auto !important;
        font-size: 14px !important;
        z-index: 9999 !important;
    }
    </style>
    """

    html_content = html_content.replace("</head>", custom_css + "\n</head>")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("dependency_graph.html generated with custom tooltip styling.")

def lookup_endpoint_id_by_path(service, path):
    method = path.split(":")[0]
    path = path.split(":")[1]
    for endpoint in service.endpoints:
        if endpoint.method == method and endpoint.path == path:
            return endpoint.id
    return None
    
def update_endpoint(endpoint, description):
    endpoint.path = description.get("path", endpoint.path)
    endpoint.method = description.get("method", endpoint.method)
    endpoint.cookies = description.get("cookies", endpoint.cookies)
    endpoint.params = description.get("params", endpoint.params)
    endpoint.headers = description.get("headers", endpoint.headers)
    # endpoint.dependencies = description.get("dependencies", endpoint.dependencies)
    endpoint.response_type = description.get("response_type", endpoint.response_type)
    endpoint.description = description.get("description", endpoint.description)

def update_endpoint_dependencies(service, endpoint, dependencies):
    """
    엔드포인트의 의존성을 업데이트합니다.
    """
    for dep in dependencies:
        method, path = dep.split(":")
        dep_id = lookup_endpoint_id_by_path(service, dep)
        if dep_id:
            endpoint.dependencies.add_dependency(endpoint.id, dep_id)
            print(f"[Dependency] {endpoint.method} {endpoint.path} -> {dep}")

def endpoint_patterns_and_extract_endpoints(main_folder, root_directory, main_source, framework_result, extensions, use_local=False):
    """
    엔드포인트 패턴을 인식하고 엔드포인트 및 경로 정보를 추출합니다.

    Parameters:
      main_folder (str): 주요 프로젝트 폴더 경로
      root_directory (str): 분석할 루트 디렉토리
      main_source (str): 주요 소스 파일 경로
      framework_result (str): 식별된 프레임워크 정보
      extensions (list): 처리할 파일 확장자 리스트
      use_local (bool): LMStudio 사용 여부

    Returns:
      tuple: (endpoints_by_file, paths_by_file)
    """
    patterns = get_endpoint_patterns(main_source, framework_result, use_local=use_local)
    for method, pattern in patterns.items():
        print(f"[Pattern] {method}: {pattern}")

    endpoints_by_file = extract_endpoints(root_directory, extensions, patterns)
    paths_by_file = parse_path_from_endpoint(endpoints_by_file)
    print("\n[Endpoints] extraction result:")
    print(json.dumps(paths_by_file, indent=2))

    serialized = json.dumps(paths_by_file)
    if not ('GET' in serialized or 'POST' in serialized):
        print("[Retry] No GET/POST endpoints found, retrying with temperature=1")
        main_source = identify_main_source(main_folder, temperature=1, use_local=use_local)
        framework_result = identify_framework(main_source, use_local=use_local)
        patterns = get_endpoint_patterns(main_source, framework_result, temperature=1, use_local=use_local)
        endpoints_by_file = extract_endpoints(root_directory, extensions, patterns)
        paths_by_file = parse_path_from_endpoint(endpoints_by_file)
        print("\n[Endpoints] result after retry:")
        print(json.dumps(paths_by_file, indent=2))

    return endpoints_by_file, paths_by_file

def main():
    """
    메인 실행 함수

    Steps:
      1. 주요 폴더 및 소스 파일 식별
      2. 프레임워크 및 서비스 분석
      3. 엔드포인트 패턴 추출 및 처리
      4. 각 엔드포인트 설명 생성
    """
    # Check for LOCAL argument to use LMStudio
    use_local = False
    if len(sys.argv) > 1 and sys.argv[1].upper() == "LOCAL":
        use_local = True
        print("[Config] LMStudio LOCAL mode enabled: using qwen3-8b-mlx model")
    
    root_directory = "../target"

    main_folder = identify_main_folder(root_directory, use_local)
    if not check_path_exists(main_folder):
        return
    print(f"[Step1] Main folder: {main_folder}")

    main_source = identify_main_source(main_folder, use_local=use_local)
    if not check_path_exists(main_source):
        return
    extension = main_source.rsplit('.', 1)[-1]
    extensions = [f".{extension}"]
    print(f"[Step2] Main source file: {main_source}")

    framework_result = identify_framework(main_source, use_local)
    print(f"[Step3] Framework: {framework_result}")
    service_name = identify_service_name(main_folder, use_local)
    print(f"[Service] Name: {service_name}")
    service = model.Service(
        name=service_name,
        root_directory=root_directory,
        main_source=main_source,
        framework=framework_result
    )
    
    # Retry loop for endpoint extraction
    retry_count = None
    attempts = 0
    while True:
        endpoints_by_file, paths_by_file = endpoint_patterns_and_extract_endpoints(
            main_folder, root_directory, main_source, framework_result, extensions, use_local
        )
        serialized = json.dumps(paths_by_file)
        # Break if GET or POST endpoints found
        if 'GET' in serialized or 'POST' in serialized:
            break
        attempts += 1
        # Break if reached user-defined retry limit
        if retry_count is not None and attempts >= retry_count:
            print(f"[Main] Retry limit reached ({attempts}/{retry_count}), stopping retries.")
            break
        print(f"[Main] No endpoints found, retrying extraction ({attempts}/{retry_count if retry_count is not None else '∞'})")
    

    paths_by_file = concat_endpoint_results(paths_by_file)
    print("\n[Combined Endpoints]:")
    print(json.dumps(paths_by_file, indent=2))
    endpoints_code_by_file = extract_code_from_endpoint(root_directory, endpoints_by_file)
    print("\n[Endpoint Code]:")
    print(json.dumps(endpoints_code_by_file, indent=2))

    add_endpoint_to_service(service, endpoints_by_file, paths_by_file, endpoints_code_by_file)
    print("\n[Service Endpoints]:")
    print(json.dumps(service.describe(), indent=2))

    for endpoint in service.endpoints:
        desc = explain_endpoint(endpoint, use_local)
        update_endpoint(endpoint, desc)
        print(f"\n[Description] {endpoint.path}")
        print(json.dumps(desc, indent=2))
        update_endpoint_dependencies(service, endpoint, desc.get("dependencies", []))

    # 시각화
    visualize_dependency_graph(service)


if __name__ == "__main__":
    main()