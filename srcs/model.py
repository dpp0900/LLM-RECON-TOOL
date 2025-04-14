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