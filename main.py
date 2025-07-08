import os
import shutil
from src.obsidian_graph.sdk_interface import ObsidianGraphSDK
import networkx as nx

def create_test_vault(vault_path):
    """创建虚拟的Obsidian Vault用于测试"""
    if os.path.exists(vault_path):
        shutil.rmtree(vault_path)
    os.makedirs(vault_path)

    # Node Note 1
    with open(os.path.join(vault_path, "Concept A.md"), "w", encoding="utf-8") as f:
        f.write("""---
type: node
aliases: [CA]
describe: This is Concept A
version: "1.0"
tags: [concept, test]
---
This is the content of Concept A. It links to [[Concept B]].
""")

    # Node Note 2
    with open(os.path.join(vault_path, "Concept B.md"), "w", encoding="utf-8") as f:
        f.write("""---
type: node
describe: This is Concept B
version: "1.0"
tags: [concept]
---
This is the content of Concept B.
""")

    # Event Note
    with open(os.path.join(vault_path, "Event X.md"), "w", encoding="utf-8") as f:
        f.write("""---
type: event
describe: An important event
version: "2023-01-01"
---
Details about Event X.
""")

    # Edge Note
    with open(os.path.join(vault_path, "Relation AB.md"), "w", encoding="utf-8") as f:
        f.write("""---
type: edge
ends: ["[[Concept A]]", "[[Concept B]]"]
describe: relates to
version: "1.0"
over: "time"
---
This note describes the relation between Concept A and Concept B.
""")

    # Edge Note with missing target
    with open(os.path.join(vault_path, "Relation AC.md"), "w", encoding="utf-8") as f:
        f.write("""---
type: edge
ends: ["[[Concept A]]", "[[Concept C]]"]
describe: depends on
---
This note describes a dependency that Concept C does not exist.
""")

    print(f"虚拟Vault已创建在: {vault_path}")

def main():
    print("Hello from obsidian-graph!")

    test_vault_path = "./test_vault"
    create_test_vault(test_vault_path)

    sdk = ObsidianGraphSDK()
    try:
        graph = sdk.export_to_networkx(test_vault_path)

        print("\n--- Graph Details ---")
        print(f"节点数量: {graph.number_of_nodes()}")
        print(f"边数量: {graph.number_of_edges()}")

        print("\n节点:")
        for node, data in graph.nodes(data=True):
            print(f"  - {node} (类型: {data.get('type')}, 别名: {data.get('aliases')})")

        print("\n边:")
        for u, v, data in graph.edges(data=True):
            print(f"  - {u} --[{data.get('relation_type')}]--> {v} (定义于: {data.get('defined_by_note_name')})")

    except FileNotFoundError as e:
        print(f"错误: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")
    finally:
        # 清理虚拟Vault
        if os.path.exists(test_vault_path):
            shutil.rmtree(test_vault_path)
            print(f"\n虚拟Vault已清理: {test_vault_path}")

if __name__ == "__main__":
    main()
