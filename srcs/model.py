import uuid


class Service:
    def __init__(self, name: str, root_directory: str, main_source: str, framework: str):
        self.id = str(uuid.uuid4())  # 고유 ID 생성
        self.name = name
        self.root_directory = root_directory
        self.main_source = main_source
        self.framework = framework
        self.endpoints = []
        self.database = None
        self.dependencies = DependencyGraph()

    def add_endpoint(self, endpoint: 'Endpoint'):
        """엔드포인트를 추가합니다."""
        self.endpoints.append(endpoint)
        self.dependencies.add_dependency(self.id, endpoint.id)  # ID 기반 의존성 추가

    def remove_endpoint(self, endpoint: 'Endpoint'):
        """엔드포인트를 제거합니다."""
        if endpoint in self.endpoints:
            self.endpoints.remove(endpoint)
            self.dependencies.remove_dependency(self.id, endpoint.id)

    def set_database(self, database: 'Database'):
        """데이터베이스를 설정합니다."""
        self.database = database
        self.dependencies.add_dependency(self.id, database.id)  # ID 기반 의존성 추가

    def remove_database(self):
        """데이터베이스를 제거합니다."""
        if self.database:
            self.dependencies.remove_dependency(self.id, self.database.id)
            self.database = None

    def describe(self):
        """Service의 정보를 출력합니다."""
        return {
            "id": self.id,
            "name": self.name,
            "root_directory": self.root_directory,
            "main_source": self.main_source,
            "framework": self.framework,
            "endpoints": [endpoint.describe() for endpoint in self.endpoints],
            "database": self.database.describe() if self.database else None,
            "dependencies": self.dependencies.describe(),
        }


class DependencyGraph:
    def __init__(self):
        """의존성을 그래프로 관리합니다."""
        self.graph = {}

    def add_dependency(self, from_node: str, to_node: str):
        """의존성을 추가합니다."""
        if from_node not in self.graph:
            self.graph[from_node] = []
        if to_node not in self.graph[from_node]:
            self.graph[from_node].append(to_node)

    def remove_dependency(self, from_node: str, to_node: str):
        """의존성을 제거합니다."""
        if from_node in self.graph and to_node in self.graph[from_node]:
            self.graph[from_node].remove(to_node)
            if not self.graph[from_node]:  # 노드에 더 이상 의존성이 없으면 제거
                del self.graph[from_node]

    def get_dependencies(self, node: str):
        """특정 노드의 의존성을 반환합니다."""
        return self.graph.get(node, [])

    def describe(self):
        """그래프의 전체 구조를 반환합니다."""
        return self.graph

    def to_edge_list(self):
        """그래프를 엣지 리스트로 변환합니다."""
        edges = []
        for from_node, to_nodes in self.graph.items():
            for to_node in to_nodes:
                edges.append((from_node, to_node))
        return edges

    def to_node_list(self):
        """그래프를 노드 리스트로 변환합니다."""
        return list(self.graph.keys())


class Endpoint:
    def __init__(self, path: str, method: str = "GET", file_path: str = None, code: str = None, params: dict = None):
        self.id = str(uuid.uuid4())  # 고유 ID 생성
        self.path = path
        self.method = method
        self.file_path = file_path
        self.params = params if params else {}
        self.cookies = {}  # 쿠키 정보
        self.headers = {}
        self.response_type = None  # 응답 타입
        self.auth_required = False  # 인증 필요 여부
        self.code = None  # 엔드포인트의 코드
        self.description = None  # 엔드포인트의 설명

    def requires_authentication(self, required: bool):
        """인증 필요 여부를 설정합니다."""
        self.auth_required = required

    def describe(self):
        """Endpoint의 정보를 출력합니다."""
        return {
            "id": self.id,
            "path": self.path,
            "method": self.method,
            "file_path": self.file_path,
            "params": self.params,
            "auth_required": self.auth_required,
            "code": self.code,
        }

    def add_param(self, key: str, value: str):
        """파라미터를 추가합니다."""
        self.params[key] = value

    def remove_param(self, key: str):
        """파라미터를 제거합니다."""
        if key in self.params:
            del self.params[key]


class Database:
    def __init__(self, db_type: str = "RDBMS", purpose: str = "User data storage", init_sql: str = "CREATE...",
                 connection_string: str = "localhost:5432"):
        self.id = str(uuid.uuid4())  # 고유 ID 생성
        self.db_type = db_type
        self.purpose = purpose
        self.init_sql = init_sql
        self.connection_string = connection_string
        self.tables = []
        self.dependencies = DependencyGraph()

    def add_table(self, table_name: str):
        """테이블을 추가합니다."""
        self.tables.append(table_name)
        self.dependencies.add_dependency(self.id, table_name)  # ID 기반 의존성 추가

    def remove_table(self, table_name: str):
        """테이블을 제거합니다."""
        if table_name in self.tables:
            self.tables.remove(table_name)
            self.dependencies.remove_dependency(self.id, table_name)

    def describe(self):
        """Database의 정보를 출력합니다."""
        return {
            "id": self.id,
            "db_type": self.db_type,
            "purpose": self.purpose,
            "init_sql": self.init_sql,
            "connection_string": self.connection_string,
            "tables": self.tables,
            "dependencies": self.dependencies.describe(),
        }