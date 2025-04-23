import networkx as nx
import matplotlib.pyplot as plt
from model import DependencyGraph, Service, Endpoint, Database

# Service 객체 생성
service = Service(name="UserService", root_directory="/app", main_source="app.py", framework="Flask")

# Database 생성 및 설정
db = Database(init_sql="CREATE TABLE users (id INT);")
db.add_table("users")
db.add_table("orders")
service.set_database(db)  # Service에 Database 설정

# Endpoint 생성 및 추가
endpoint_users = Endpoint(path="/users", method="GET", file_path="/app/users.py")
endpoint_orders = Endpoint(path="/orders", method="GET", file_path="/app/orders.py")
endpoint_user_details = Endpoint(path="/users/{id}", method="GET", file_path="/app/users.py")

service.add_endpoint(endpoint_users)  # Service에 Endpoint 추가
service.add_endpoint(endpoint_orders)
service.add_endpoint(endpoint_user_details)

# 엔드포인트 간의 종속성 추가
service.dependencies.add_dependency(endpoint_users.id, endpoint_user_details.id)  # /users -> /users/{id}
service.dependencies.add_dependency(endpoint_orders.id, endpoint_user_details.id)  # /orders -> /users/{id}

# 데이터베이스와 엔드포인트 간의 종속성 추가
service.dependencies.add_dependency(endpoint_users.id, db.id)  # /users -> Database
service.dependencies.add_dependency(endpoint_orders.id, db.id)  # /orders -> Database
service.dependencies.add_dependency(endpoint_user_details.id, db.id)  # /users/{id} -> Database

# 그래프 데이터 가져오기
graph_data = service.dependencies.describe()

# NetworkX 그래프 생성
G = nx.DiGraph()
for from_node, to_nodes in graph_data.items():
    for to_node in to_nodes:
        G.add_edge(from_node, to_node)

# 노드 레이블 설정
node_labels = {}
node_labels[service.id] = f"Service: {service.name}"
node_labels[db.id] = f"Database: {db.db_type}"
for endpoint in service.endpoints:
    node_labels[endpoint.id] = f"Endpoint: {endpoint.path} ({endpoint.method})"

# 그래프 레이아웃 설정 (spring_layout 사용)
pos = nx.spring_layout(G, k=0.5)  # k 값으로 노드 간의 간격 조정

# 그래프 시각화
plt.figure(figsize=(14, 10))  # 그래프 크기 조정
nx.draw(
    G, pos, with_labels=True, labels=node_labels, node_color="lightblue",
    font_weight="bold", node_size=2000, arrowsize=20
)
plt.title("Dependency Graph (Service, Endpoints, and Database)")
plt.show()