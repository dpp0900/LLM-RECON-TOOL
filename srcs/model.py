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
    def __init__(self, endpoint: str, method: str = "GET", path: str = "/", params: dict = None):
        self.endpoint = endpoint
        self.method = method
        self.path = path
        self.params = params if params else {}
        self.auth_required = False  # 인증 필요 여부
        self.dependency_graph = DependencyGraph()  # 의존성 그래프

    def add_dependency(self, to_node: str):
        """의존성을 추가합니다."""
        self.dependency_graph.add_dependency(self.endpoint, to_node)

    def remove_dependency(self, to_node: str):
        """의존성을 제거합니다."""
        self.dependency_graph.remove_dependency(self.endpoint, to_node)

    def requires_authentication(self, required: bool):
        """인증 필요 여부를 설정합니다."""
        self.auth_required = required

    def describe(self):
        """Endpoint의 정보를 출력합니다."""
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "path": self.path,
            "params": self.params,
            "auth_required": self.auth_required,
            "dependencies": self.dependency_graph.get_dependencies(self.endpoint),
        }

    def to_graph_data(self):
        """시각화를 위한 그래프 데이터를 반환합니다."""
        return {
            "nodes": [self.endpoint],
            "edges": self.dependency_graph.to_edge_list(),
        }


class Database:
    def __init__(self, db_type: str = "RDBMS", purpose: str = "User data storage", init_sql: str = "CREATE...",
                 connection_string: str = "localhost:5432"):
        self.db_type = db_type
        self.purpose = purpose
        self.init_sql = init_sql
        self.connection_string = connection_string
        self.tables = []
        self.dependencies = DependencyGraph()

    def add_table(self, table_name: str):
        """테이블을 추가합니다."""
        self.tables.append(table_name)
        self.dependencies.add_dependency(self.purpose, table_name)

    def remove_table(self, table_name: str):
        """테이블을 제거합니다."""
        if table_name in self.tables:
            self.tables.remove(table_name)
            self.dependencies.remove_dependency(self.purpose, table_name)

    def add_dependency(self, from_node: str, to_node: str):
        """의존성을 추가합니다."""
        self.dependencies.add_dependency(from_node, to_node)

    def remove_dependency(self, from_node: str, to_node: str):
        """의존성을 제거합니다."""
        self.dependencies.remove_dependency(from_node, to_node)

    def describe(self):
        """Database의 정보를 출력합니다."""
        return {
            "db_type": self.db_type,
            "purpose": self.purpose,
            "init_sql": self.init_sql,
            "connection_string": self.connection_string,
            "tables": self.tables,
            "dependencies": self.dependencies.describe(),
        }

    def to_graph_data(self):
        """시각화를 위한 그래프 데이터를 반환합니다."""
        return {
            "nodes": [self.purpose] + self.tables,
            "edges": self.dependencies.to_edge_list(),
        }