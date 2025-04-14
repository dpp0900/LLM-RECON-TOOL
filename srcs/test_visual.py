import networkx as nx
import matplotlib.pyplot as plt
from model import DependencyGraph, Endpoint, Database

# 예제 데이터 생성
db = Database(init_sql="CREATE TABLE users (id INT);")
db.add_table("users")
db.add_table("orders")
db.add_dependency("users", "orders")

endpoint = Endpoint(endpoint="GET /users")
endpoint.add_dependency("GET /orders")

# 그래프 데이터 가져오기
db_graph_data = db.to_graph_data()
endpoint_graph_data = endpoint.to_graph_data()

# NetworkX 그래프 생성
G = nx.DiGraph()
G.add_nodes_from(db_graph_data["nodes"])
G.add_edges_from(db_graph_data["edges"])
G.add_nodes_from(endpoint_graph_data["nodes"])
G.add_edges_from(endpoint_graph_data["edges"])

# 그래프 시각화
plt.figure(figsize=(10, 6))
nx.draw(G, with_labels=True, node_color="lightblue", font_weight="bold", node_size=2000, arrowsize=20)
plt.title("Dependency Graph")
plt.show()