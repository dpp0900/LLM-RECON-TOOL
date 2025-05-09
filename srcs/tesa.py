import os
import json
import re
import sys
from llm import ask_chatgpt

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from collections import defaultdict
from matplotlib.colors import to_rgba
import model

def list_all_dirs(root_dir):
    """모든 하위 디렉토리와 파일 목록을 반환합니다."""
    all_items = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for dirname in dirnames:
            all_items.append(os.path.join(dirpath, dirname))
    return all_items

def list_all_files(root_dir):
    """모든 하위 디렉토리의 모든 파일 목록을 반환합니다."""
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
    """파일이나 디렉토리가 존재하는지 확인합니다."""
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
    if not isinstance(patterns, dict) or not patterns:
        print(f"[Fallback] Applying built-in endpoint patterns for framework '{framework}'")
        patterns = {
            "ALL": ".*@RequestMapping\\s*({.*?})",
            "GET": ".*@GetMapping\\s*({.*?})",
            "POST": ".*@PostMapping\\s*({.*?})"
        }
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
    RULE = r'''(["'])(/[a-zA-Z0-9_\-/\.:\{\}]*)(["'])'''
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
    """서비스 및 엔드포인트 종속성의 향상된 시각화로 레이아웃과 가독성이 개선됩니다. 경로 생략 없음."""
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.lines import Line2D
    
    # 그래프 생성
    G = nx.DiGraph()
    
    # 노드와 엣지를 적절한 레이블로 추출
    service_node = service.name
    endpoint_nodes = {}
    edges = []
    
    # 서비스 노드 추가
    G.add_node(service_node, type='service')
    
    # 메소드 접두사를 사용하여 겹치는 레이블을 피하면서 엔드포인트 노드 추가
    for endpoint in service.endpoints:
        # 전체 경로를 그대로 사용 (생략 없음)
        node_label = f"{endpoint.method} {endpoint.path}"
        endpoint_nodes[endpoint.id] = node_label
        G.add_node(node_label, type=endpoint.method.lower())
        
        # 서비스에서 엔드포인트로 엣지 추가
        edges.append((service_node, node_label))
        
    # 엔드포인트 의존성 추가
    for endpoint in service.endpoints:
        from_node = endpoint_nodes[endpoint.id]
        for from_id, to_ids in endpoint.dependencies.describe().items():
            for to_id in to_ids:
                # 대상 엔드포인트 찾기
                to_endpoint = next((ep for ep in service.endpoints if ep.id == to_id), None)
                if to_endpoint:
                    to_node = endpoint_nodes[to_endpoint.id]
                    edges.append((from_node, to_node))
    
    # 모든 엣지를 그래프에 추가
    G.add_edges_from(edges)
    
    # 더 많은 공간으로 레이아웃 구성
    # 원형 레이아웃 시도
    try:
        pos = nx.circular_layout(G, scale=6)  # 더 큰 scale 값으로 노드 간 간격 확대
    except:
        # 더 나은 매개변수로 스프링 레이아웃으로 폴백
        pos = nx.spring_layout(G, k=2.0, iterations=150, scale=6)
    
    # 더 큰 그림으로 플롯 설정
    plt.figure(figsize=(20, 18))
    
    # 유형에 따른 노드 색상 매핑
    color_map = {
        'service': 'lightblue',
        'get': 'lightgreen',
        'post': 'salmon',
        'put': 'orange',
        'delete': 'pink'
    }
    
    # 유형에 따라 다른 색상으로 노드 그리기
    for node_type in set(nx.get_node_attributes(G, 'type').values()):
        node_list = [node for node, data in G.nodes(data=True) if data.get('type') == node_type]
        nx.draw_networkx_nodes(
            G, pos, 
            nodelist=node_list,
            node_color=color_map.get(node_type, 'lightgray'),
            node_size=3000,
            alpha=0.8
        )
    
    # 화살표로 엣지 그리기
    nx.draw_networkx_edges(
        G, pos,
        arrowstyle='-|>',
        arrowsize=20,
        width=1.5,
        edge_color='gray',
        alpha=0.6
    )
    
    # 더 나은 글꼴 설정과 배경으로 레이블 그리기
    # 가독성을 높이기 위한 레이블의 흰색 배경
    for node, (x, y) in pos.items():
        # 서비스 노드에는 더 큰 글꼴 사용
        fontsize = 12 if node == service_node else 9
        plt.text(
            x, y, 
            node,
            ha='center', 
            va='center',
            size=fontsize,
            wrap=True,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8)
        )
    
    # 범례 생성
    legend_elements = [
        mpatches.Patch(color=color_map.get('service'), label='Service'),
        mpatches.Patch(color=color_map.get('get'), label='GET Endpoint'),
        mpatches.Patch(color=color_map.get('post'), label='POST Endpoint'),
        mpatches.Patch(color=color_map.get('put'), label='PUT Endpoint'),
        mpatches.Patch(color=color_map.get('delete'), label='DELETE Endpoint'),
        Line2D([0], [0], color='gray', lw=2, label='Dependency')
    ]
    plt.legend(handles=legend_elements, loc='best')
    
    # 제목 추가 및 축 제거
    plt.title(f"{service.name} API Dependency Graph", fontsize=16)
    plt.axis('off')
    
    # 플롯 경계를 자동 조정
    plt.tight_layout()
    
    # 표시 전 저장 (선택적)
    plt.savefig(f"{service.name}_api_graph.png", dpi=300, bbox_inches='tight')
    
    plt.show()

def visualize_dependency_graph_hierarchical(service):
    """API 구조를 명확하게 보여주는 대안적 계층 시각화. 경로 생략 없음."""
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    
    # 그래프 생성
    G = nx.DiGraph()
    
    # 노드 및 엣지 추출
    service_node = service.name
    endpoint_nodes = {}
    
    # 더 나은 구성을 위해 첫 번째 경로 세그먼트별로 엔드포인트 그룹화
    endpoint_groups = {}
    
    # 서비스 노드 추가
    G.add_node(service_node, type='service')
    
    # 엔드포인트 그룹 생성
    for endpoint in service.endpoints:
        # 경로의 첫 번째 세그먼트 가져오기 (예: /api/user/profile -> /api)
        if endpoint.path.startswith('/'):
            parts = endpoint.path.split('/')
            if len(parts) > 1:
                first_segment = f"/{parts[1]}"
            else:
                first_segment = "/"
        else:
            first_segment = "/"
            
        if first_segment not in endpoint_groups:
            endpoint_groups[first_segment] = []
            
        # 전체 경로 사용 (생략 없음)
        node_label = f"{endpoint.method} {endpoint.path}"
        endpoint_groups[first_segment].append((endpoint.id, node_label, endpoint.method))
        endpoint_nodes[endpoint.id] = node_label
    
    # 모든 노드를 그래프에 추가
    for group, endpoints in endpoint_groups.items():
        # 그룹 노드 추가
        group_node = f"Group: {group}"
        G.add_node(group_node, type='group')
        G.add_edge(service_node, group_node)
        
        # 이 그룹의 엔드포인트 추가
        for ep_id, node_label, method in endpoints:
            G.add_node(node_label, type=method.lower())
            G.add_edge(group_node, node_label)
    
    # 엔드포인트 의존성 추가
    for endpoint in service.endpoints:
        if endpoint.id in endpoint_nodes:
            from_node = endpoint_nodes[endpoint.id]
            for from_id, to_ids in endpoint.dependencies.describe().items():
                for to_id in to_ids:
                    if to_id in endpoint_nodes:
                        G.add_edge(from_node, endpoint_nodes[to_id])
    
    # 계층적 레이아웃 사용
    pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
    
    # 플롯 설정
    plt.figure(figsize=(20, 18))
    
    # 유형에 따라 노드 색상 지정
    color_map = {
        'service': 'lightblue',
        'group': 'lightyellow',
        'get': 'lightgreen',
        'post': 'salmon',
        'put': 'orange',
        'delete': 'pink'
    }
    
    # 다양한 노드 유형 그리기
    for node_type in set(nx.get_node_attributes(G, 'type').values()):
        node_list = [node for node, data in G.nodes(data=True) if data.get('type') == node_type]
        nx.draw_networkx_nodes(
            G, pos, 
            nodelist=node_list,
            node_color=color_map.get(node_type, 'lightgray'),
            node_size=2000 if node_type == 'service' or node_type == 'group' else 1800,
            alpha=0.8
        )
    
    # 엣지 그리기
    nx.draw_networkx_edges(
        G, pos,
        arrowstyle='->',
        arrowsize=15,
        edge_color='gray',
        alpha=0.6
    )
    
    # 가독성을 높이기 위해 레이블에 흰색 배경 추가
    for node, (x, y) in pos.items():
        fontsize = 12 if 'Group' in str(node) or node == service_node else 9
        plt.text(
            x, y, 
            node,
            ha='center', 
            va='center',
            size=fontsize,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8)
        )
    
    # 범례 생성
    legend_elements = [
        mpatches.Patch(color=color_map.get('service'), label='Service'),
        mpatches.Patch(color=color_map.get('group'), label='API Group'),
        mpatches.Patch(color=color_map.get('get'), label='GET Endpoint'),
        mpatches.Patch(color=color_map.get('post'), label='POST Endpoint'),
        mpatches.Patch(color=color_map.get('put'), label='PUT Endpoint'),
        mpatches.Patch(color=color_map.get('delete'), label='DELETE Endpoint')
    ]
    plt.legend(handles=legend_elements, loc='best')
    
    # 제목 추가 및 축 제거
    plt.title(f"{service.name} API Hierarchy", fontsize=16)
    plt.axis('off')
    
    # 플롯 조정
    plt.tight_layout()
    
    # 표시 전 저장 (선택적)
    plt.savefig(f"{service.name}_api_hierarchy.png", dpi=300, bbox_inches='tight')
    
    plt.show()

def visualize_endpoints_force_directed(service):
    """API 엔드포인트에 최적화된 힘 기반 그래프 시각화. 경로 생략 없음."""
    import networkx as nx
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch
    import matplotlib.patheffects as pe
    
    # 그래프 생성
    G = nx.DiGraph()
    
    # 엔드포인트 ID에서 노드 이름으로의 매핑
    endpoint_map = {}
    
    # 중앙 노드로 서비스 추가
    G.add_node(service.name, type='service')
    
    # 엔드포인트 추가
    for endpoint in service.endpoints:
        # 더 읽기 쉬운 레이블 생성
        if endpoint.method == "GET":
            shape = "◆"  # GET을 위한 다이아몬드
        elif endpoint.method == "POST":
            shape = "■"  # POST를 위한 사각형
        elif endpoint.method == "PUT":
            shape = "▲"  # PUT을 위한 삼각형
        elif endpoint.method == "DELETE":
            shape = "●"  # DELETE를 위한 원
        else:
            shape = "★"  # 다른 메소드를 위한 별
            
        # 전체 경로를 사용한 노드 레이블 생성 (생략 없음)
        node_name = f"{shape} {endpoint.path}"
        G.add_node(node_name, type=endpoint.method.lower())
        endpoint_map[endpoint.id] = node_name
        
        # 서비스에서 엔드포인트로 연결
        G.add_edge(service.name, node_name)
    
    # 엔드포인트 간 의존성 추가
    for endpoint in service.endpoints:
        if endpoint.id in endpoint_map:
            for from_id, to_ids in endpoint.dependencies.describe().items():
                if from_id in endpoint_map:
                    from_node = endpoint_map[from_id]
                    for to_id in to_ids:
                        if to_id in endpoint_map:
                            to_node = endpoint_map[to_id]
                            G.add_edge(from_node, to_node)
    
    # 더 나은 간격을 위해 반발력과 반복 횟수 증가
    pos = nx.spring_layout(G, k=2.5, iterations=250, seed=42)
    
    # 더 큰 크기로 그림 설정
    plt.figure(figsize=(22, 20))
    
    # 서로 다른 노드 유형에 대한 색상 정의
    colors = {
        'service': '#6BAED6',  # 파랑
        'get': '#74C476',      # 녹색
        'post': '#FD8D3C',     # 주황색
        'put': '#9E9AC8',      # 보라색
        'delete': '#FB6A4A'    # 빨강
    }
    
    # 유형에 따라 다른 스타일로 노드 그리기
    for node_type in set(nx.get_node_attributes(G, 'type').values()):
        node_list = [node for node, data in G.nodes(data=True) if data.get('type') == node_type]
        
        # 서비스 노드는 더 큰 크기로 설정
        size = 1200 if node_type == 'service' else 800
        
        nx.draw_networkx_nodes(
            G, pos,
            nodelist=node_list,
            node_color=colors.get(node_type, '#CCCCCC'),
            node_size=size,
            alpha=0.9
        )
    
    # 멋진 화살표로 곡선 엣지 그리기
    curved_edges = []
    for edge in G.edges():
        # 곡선 화살표 생성
        arrow = FancyArrowPatch(
            posA=pos[edge[0]],
            posB=pos[edge[1]],
            arrowstyle='-|>',
            connectionstyle='arc3,rad=0.2',
            mutation_scale=15,
            linewidth=1.5,
            alpha=0.6,
            color='#888888'
        )
        curved_edges.append(arrow)
    
    # 모든 화살표를 플롯에 추가
    for arrow in curved_edges:
        plt.gca().add_patch(arrow)
    
    # 가시성이 향상된 레이블 추가
    for node, (x, y) in pos.items():
        # 서비스 노드에 더 큰 폰트 사용
        fontsize = 14 if node == service.name else 10
        
        # 가독성을 높이기 위해 흰색 윤곽선이 있는 레이블 추가
        text = plt.text(
            x, y, 
            node,
            fontsize=fontsize,
            ha='center',
            va='center',
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="gray", alpha=0.9),
            path_effects=[pe.withStroke(linewidth=3, foreground='white')]
        )
    
    # 범례 추가
    legend_elements = []
    for method, color in colors.items():
        if method == 'service':
            label = 'Service'
        else:
            label = f"{method.upper()} Endpoint"
        legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color,
                                           markersize=10, label=label))
    plt.legend(handles=legend_elements, loc='lower right')
    
    # 제목 설정 및 축 끄기
    plt.title(f"{service.name} API Endpoints", fontsize=16)
    plt.axis('off')
    
    # 레이아웃 조정
    plt.tight_layout()
    
    # 표시 전 이미지 저장
    plt.savefig(f"{service.name}_api_network.png", dpi=300, bbox_inches='tight')
    
    plt.show()

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

def visualize_endpoint_tree(service):
    """서비스 API를 명확한 트리 구조로 시각화합니다. 위에서 아래로 내려가는 구조."""
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.colors import to_rgba
    
    # 그래프 생성
    G = nx.DiGraph()
    
    # 서비스를 루트 노드로 추가
    G.add_node(service.name, type='service')
    
    # API 경로 기반으로 그룹화
    path_groups = {}
    
    # 엔드포인트 ID와 레이블 매핑
    endpoint_nodes = {}
    
    # 엔드포인트를 경로 패턴별로 그룹화
    for endpoint in service.endpoints:
        path_parts = endpoint.path.split('/')
        if len(path_parts) > 1:
            # 첫 번째와 두 번째 세그먼트로 그룹 만들기
            if len(path_parts) > 2:
                group_path = f"/{path_parts[1]}"
            else:
                group_path = "/"
        else:
            group_path = "/"
            
        if group_path not in path_groups:
            path_groups[group_path] = []
            
        node_label = f"{endpoint.method} {endpoint.path}"
        path_groups[group_path].append((endpoint.id, node_label, endpoint.method))
        endpoint_nodes[endpoint.id] = node_label
    
    # 그룹 레벨 추가
    for group_path, endpoints in path_groups.items():
        group_name = f"그룹: {group_path}"
        G.add_node(group_name, type='group')
        G.add_edge(service.name, group_name)
        
        # 각 그룹 내에서 메서드별로 하위 그룹 만들기
        method_groups = {}
        for ep_id, node_label, method in endpoints:
            if method not in method_groups:
                method_groups[method] = []
            method_groups[method].append((ep_id, node_label))
        
        # 메서드 그룹 추가 
        for method, method_endpoints in method_groups.items():
            method_group_name = f"{method} 엔드포인트"
            G.add_node(method_group_name, type=method.lower(), parent=group_name)
            G.add_edge(group_name, method_group_name)
            
            # 엔드포인트 추가
            for ep_id, node_label in method_endpoints:
                G.add_node(node_label, type=method.lower(), parent=method_group_name)
                G.add_edge(method_group_name, node_label)
    
    # 의존성 추가
    for endpoint in service.endpoints:
        if endpoint.id in endpoint_nodes:
            for from_id, to_ids in endpoint.dependencies.describe().items():
                for to_id in to_ids:
                    if from_id in endpoint_nodes and to_id in endpoint_nodes:
                        G.add_edge(endpoint_nodes[from_id], endpoint_nodes[to_id], type='dependency')
    
    # 트리 레이아웃 사용 (위에서 아래로)
    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog='dot', args='-Grankdir=TB')
    except:
        # 대체 레이아웃
        pos = nx.drawing.nx_pydot.graphviz_layout(G, prog='dot')
    
    if not pos:  # 레이아웃을 얻지 못한 경우 기본 레이아웃 사용
        pos = nx.spring_layout(G, k=0.5, iterations=50, scale=10)
    
    # 그림 크기 설정
    plt.figure(figsize=(24, 20))
    
    # 노드 색상 설정
    color_map = {
        'service': '#AEDFF7',  # 연한 파랑
        'group': '#F7E6AD',    # 연한 노랑
        'get': '#C2E6C2',      # 연한 녹색
        'post': '#F5C4C4',     # 연한 빨강
        'put': '#F7D5AD',      # 연한 주황
        'delete': '#E6C2E6',   # 연한 보라
    }
    
    # 노드 그리기
    for node_type in set(nx.get_node_attributes(G, 'type').values()):
        node_list = [node for node, data in G.nodes(data=True) if data.get('type') == node_type]
        
        # 노드 크기 설정
        if node_type == 'service':
            node_size = 5000
        elif node_type == 'group':
            node_size = 3000
        else:
            node_size = 2000
            
        nx.draw_networkx_nodes(
            G, pos,
            nodelist=node_list,
            node_color=color_map.get(node_type, 'lightgray'),
            node_size=node_size,
            alpha=0.8
        )
    
    # 일반 엣지 그리기 (계층 구조)
    normal_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('type') != 'dependency']
    nx.draw_networkx_edges(
        G, pos,
        edgelist=normal_edges,
        arrows=True,
        arrowstyle='-|>',
        arrowsize=15,
        width=1.5,
        alpha=0.7
    )
    
    # 의존성 엣지 그리기 (다른 스타일)
    dependency_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('type') == 'dependency']
    if dependency_edges:
        nx.draw_networkx_edges(
            G, pos,
            edgelist=dependency_edges,
            arrows=True,
            arrowstyle='->',
            arrowsize=10,
            width=1.0,
            alpha=0.5,
            edge_color='red',
            style='dashed'
        )
    
    # 레이블 추가 (흰색 배경)
    for node, (x, y) in pos.items():
        # 노드 유형에 따른 글꼴 크기 및 배경 설정
        if node == service.name:
            fontsize = 14
            bbox_props = dict(boxstyle="round,pad=0.5", fc="lightblue", ec="gray", alpha=0.8)
        elif len(node.split()) == 1:  # 그룹 노드
            fontsize = 12
            bbox_props = dict(boxstyle="round,pad=0.4", fc="lightyellow", ec="gray", alpha=0.8)
        else:  # 엔드포인트 노드
            fontsize = 10
            if "GET" in node:
                bg_color = "lightgreen"
            elif "POST" in node:
                bg_color = "salmon"
            elif "PUT" in node:
                bg_color = "orange"
            elif "DELETE" in node:
                bg_color = "pink"
            else:
                bg_color = "white"
            bbox_props = dict(boxstyle="round,pad=0.3", fc=bg_color, ec="gray", alpha=0.8)
            
        plt.text(
            x, y, 
            node,
            ha='center',
            va='center',
            size=fontsize,
            wrap=True,
            bbox=bbox_props
        )
    
    # 범례 추가
    legend_elements = [
        mpatches.Patch(color=color_map.get('service'), label='서비스'),
        mpatches.Patch(color=color_map.get('group'), label='API 그룹'),
        mpatches.Patch(color=color_map.get('get'), label='GET 엔드포인트'),
        mpatches.Patch(color=color_map.get('post'), label='POST 엔드포인트'),
        mpatches.Patch(color=color_map.get('put'), label='PUT 엔드포인트'),
        mpatches.Patch(color=color_map.get('delete'), label='DELETE 엔드포인트'),
        plt.Line2D([0], [0], color='gray', lw=2, label='계층 구조'),
        plt.Line2D([0], [0], color='red', lw=2, linestyle='dashed', label='API 의존성')
    ]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=12)
    
    # 제목 추가
    plt.title(f"{service.name} API 트리 구조", fontsize=18)
    plt.axis('off')  # 축 제거
    
    # 여백 조정
    plt.tight_layout()
    
    # 이미지 저장
    plt.savefig(f"{service.name}_api_tree.png", dpi=300, bbox_inches='tight')
    
    # 그래프 표시
    plt.show()

def visualize_api_tree_grouped(service):
    """API를 그룹화하여 깔끔한 트리 구조로 시각화합니다."""
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    from collections import defaultdict
    
    # 그래프 생성
    G = nx.DiGraph()
    
    # 루트 노드 (서비스) 추가
    G.add_node(service.name, type='service', level=0)
    
    # 엔드포인트 그룹화 
    path_mapping = defaultdict(list)
    for endpoint in service.endpoints:
        # 경로를 세그먼트로 분리
        parts = endpoint.path.split('/')
        parts = [p for p in parts if p]  # 빈 문자열 제거
        
        # 그룹 결정 (첫 번째 또는 두 번째 경로 세그먼트)
        if len(parts) > 0:
            group = f"/{parts[0]}"
            if group not in path_mapping:
                G.add_node(group, type='group', level=1)
                G.add_edge(service.name, group)
            
            # 엔드포인트 노드 추가
            node_name = f"{endpoint.method} {endpoint.path}"
            G.add_node(node_name, type=endpoint.method.lower(), level=2)
            G.add_edge(group, node_name)
            path_mapping[endpoint.id] = node_name
        else:
            # 루트 경로인 경우
            root_group = "/root"
            if root_group not in path_mapping:
                G.add_node(root_group, type='group', level=1)
                G.add_edge(service.name, root_group)
            
            node_name = f"{endpoint.method} {endpoint.path}"
            G.add_node(node_name, type=endpoint.method.lower(), level=2)
            G.add_edge(root_group, node_name)
            path_mapping[endpoint.id] = node_name
    
    # 의존성 관계 추가
    for endpoint in service.endpoints:
        if endpoint.id in path_mapping:
            for from_id, to_ids in endpoint.dependencies.describe().items():
                if from_id in path_mapping:
                    from_node = path_mapping[from_id]
                    for to_id in to_ids:
                        if to_id in path_mapping:
                            to_node = path_mapping[to_id]
                            G.add_edge(from_node, to_node, type='dependency')
    
    # 계층적 트리 레이아웃 생성
    try:
        # Graphviz 사용 시도
        pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
    except:
        try:
            # PyDot 사용 시도
            pos = nx.drawing.nx_pydot.graphviz_layout(G, prog='dot')
        except:
            # 실패 시 기본 레이아웃 사용
            pos = {}
            y_levels = {0: 0, 1: -5, 2: -10}  # 레벨별 y 좌표
            
            # 레벨별 노드 수 계산
            nodes_per_level = {}
            for node, data in G.nodes(data=True):
                level = data.get('level', 0)
                if level not in nodes_per_level:
                    nodes_per_level[level] = 0
                nodes_per_level[level] += 1
            
            # 각 레벨의 너비 계산
            level_widths = {level: count * 2 for level, count in nodes_per_level.items()}
            
            # 노드 위치 할당
            level_counts = {0: 0, 1: 0, 2: 0}
            for node, data in G.nodes(data=True):
                level = data.get('level', 0)
                count = level_counts[level]
                
                # x 좌표: 레벨 내에서 균등 분포
                width = level_widths.get(level, 10)
                x = (count - (nodes_per_level[level] - 1) / 2) * (width / max(nodes_per_level[level], 1))
                
                # y 좌표: 레벨에 따라 고정
                y = y_levels[level]
                
                pos[node] = np.array([x, y])
                level_counts[level] += 1
    
    # 그림 생성
    plt.figure(figsize=(20, 16))
    
    # 노드 색상 매핑
    color_map = {
        'service': 'lightblue',
        'group': 'lightyellow',
        'get': 'lightgreen',
        'post': 'salmon',
        'put': 'orange',
        'delete': 'pink'
    }
    
    # 노드 그리기
    for node_type in set(nx.get_node_attributes(G, 'type').values()):
        node_list = [node for node, data in G.nodes(data=True) if data.get('type') == node_type]
        
        # 노드 크기 설정
        if node_type == 'service':
            node_size = 4000
        elif node_type == 'group':
            node_size = 2500
        else:
            node_size = 2000
            
        nx.draw_networkx_nodes(
            G, pos,
            nodelist=node_list,
            node_color=color_map.get(node_type, 'lightgray'),
            node_size=node_size,
            alpha=0.8
        )
    
    # 일반 엣지 그리기 (계층 구조)
    normal_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('type') != 'dependency']
    nx.draw_networkx_edges(
        G, pos,
        edgelist=normal_edges,
        arrows=True,
        arrowstyle='-|>',
        arrowsize=15,
        width=1.5,
        alpha=0.7
    )
    
    # 의존성 엣지 그리기 (다른 스타일)
    dependency_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('type') == 'dependency']
    if dependency_edges:
        nx.draw_networkx_edges(
            G, pos,
            edgelist=dependency_edges,
            arrows=True,
            arrowstyle='->',
            arrowsize=10,
            width=1.0,
            alpha=0.5,
            edge_color='red',
            style='dashed'
        )
    
    # 레이블 추가 (흰색 배경)
    for node, (x, y) in pos.items():
        # 노드 유형에 따른 글꼴 크기 및 배경 설정
        if node == service.name:
            fontsize = 14
            bbox_props = dict(boxstyle="round,pad=0.5", fc="lightblue", ec="gray", alpha=0.8)
        elif len(node.split()) == 1:  # 그룹 노드
            fontsize = 12
            bbox_props = dict(boxstyle="round,pad=0.4", fc="lightyellow", ec="gray", alpha=0.8)
        else:  # 엔드포인트 노드
            fontsize = 10
            if "GET" in node:
                bg_color = "lightgreen"
            elif "POST" in node:
                bg_color = "salmon"
            elif "PUT" in node:
                bg_color = "orange"
            elif "DELETE" in node:
                bg_color = "pink"
            else:
                bg_color = "white"
            bbox_props = dict(boxstyle="round,pad=0.3", fc=bg_color, ec="gray", alpha=0.8)
            
        plt.text(
            x, y, 
            node,
            ha='center',
            va='center',
            size=fontsize,
            wrap=True,
            bbox=bbox_props
        )
    
    # 범례 추가
    legend_elements = [
        mpatches.Patch(color=color_map.get('service'), label='서비스'),
        mpatches.Patch(color=color_map.get('group'), label='API 그룹'),
        mpatches.Patch(color=color_map.get('get'), label='GET 엔드포인트'),
        mpatches.Patch(color=color_map.get('post'), label='POST 엔드포인트'),
        mpatches.Patch(color=color_map.get('put'), label='PUT 엔드포인트'),
        mpatches.Patch(color=color_map.get('delete'), label='DELETE 엔드포인트'),
        plt.Line2D([0], [0], color='gray', lw=2, label='계층 구조'),
        plt.Line2D([0], [0], color='red', lw=2, linestyle='dashed', label='API 의존성')
    ]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=12)
    
    # 제목 추가
    plt.title(f"{service.name} API 그룹화된 트리 구조", fontsize=18)
    plt.axis('off')  # 축 제거
    
    # 여백 조정
    plt.tight_layout()
    
    # 이미지 저장
    plt.savefig(f"{service.name}_api_grouped_tree.png", dpi=300, bbox_inches='tight')
    
    # 그래프 표시
    plt.show()

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
    
    root_directory = "../target/Piggy-bank/sources/com/teamsa/"

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
    
    # 시각화 - 다음 중 하나를 선택하세요
    visualize_endpoint_tree(service)  # 트리 구조 시각화
    # visualize_api_tree_grouped(service)  # 그룹화된 트리 구조 시각화
    # visualize_dependency_graph(service)  # 향상된 원형 레이아웃
    # visualize_dependency_graph_hierarchical(service)  # 계층적 레이아웃
    # visualize_endpoints_force_directed(service)  # 힘 기반 레이아웃
    

if __name__ == "__main__":
    main()