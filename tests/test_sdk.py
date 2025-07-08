import pytest
import os
import shutil
import networkx as nx
from obsidian_graph.obsidian_parser import ObsidianParser
from obsidian_graph.graph_builder import GraphBuilder
from obsidian_graph.sdk_interface import ObsidianGraphSDK

# 定义一个fixture来创建和清理测试用的虚拟Vault
@pytest.fixture
def test_vault(tmp_path):
    """创建一个临时Obsidian Vault用于测试，并在测试结束后清理"""
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()

    # Node Note 1: Concept A
    (vault_path / "Concept A.md").write_text("""---
type: node
aliases: [CA, Concept_A]
describe: This is Concept A
version: "1.0"
tags: [concept, test]
---
This is the content of Concept A. It links to [[Concept B]] and [[Event X]].
""")

    # Node Note 2: Concept B
    (vault_path / "Concept B.md").write_text("""---
type: node
describe: This is Concept B
version: "1.0"
tags: [concept]
---
This is the content of Concept B.
""")

    # Event Note: Event X
    (vault_path / "Event X.md").write_text("""---
type: event
describe: An important event
version: "2023-01-01"
---
Details about Event X.
""")

    # Edge Note 1: Relation AB
    (vault_path / "Relation AB.md").write_text("""---
type: edge
ends: ["[[Concept A]]", "[[Concept B]]"]
describe: relates to
version: "1.0"
over: "time"
---
This note describes the relation between Concept A and Concept B.
""")

    # Edge Note 2: Relation AX (to an event)
    (vault_path / "Relation AX.md").write_text("""---
type: edge
ends: ["[[Concept A]]", "[[Event X]]"]
describe: happened at
---
Concept A happened at Event X.
""")

    # Edge Note 3: Relation AC (target C does not exist)
    (vault_path / "Relation AC.md").write_text("""---
type: edge
ends: ["[[Concept A]]", "[[Concept C]]"]
describe: depends on
---
This note describes a dependency that Concept C does not exist.
""")

    # Note without YAML
    (vault_path / "Plain Note.md").write_text("""
This is a plain markdown note without any YAML front matter.
It links to [[Concept A]].
""")

    # Note with invalid YAML
    (vault_path / "Invalid YAML Note.md").write_text("""---
type: node
invalid: [
  item1
  item2
---
This note has invalid YAML.
""")

    yield vault_path
    # 清理由tmp_path创建的临时目录，pytest会自动处理

# --- ObsidianParser Tests ---

def test_parser_valid_node_note(test_vault):
    parser = ObsidianParser()
    file_path = test_vault / "Concept A.md"
    parsed_data = parser.parse_markdown_file(str(file_path))

    assert parsed_data["note_name"] == "Concept A"
    assert parsed_data["file_path"] == str(file_path)
    assert parsed_data["yaml_front_matter"]["type"] == "node"
    assert "This is the content of Concept A." in parsed_data["content"]
    assert len(parsed_data["_internal_links_info"]) == 2
    assert {"target_note_name": "Concept B", "link_text": "Concept B"} in parsed_data["_internal_links_info"]
    assert {"target_note_name": "Event X", "link_text": "Event X"} in parsed_data["_internal_links_info"]

def test_parser_plain_note(test_vault):
    parser = ObsidianParser()
    file_path = test_vault / "Plain Note.md"
    parsed_data = parser.parse_markdown_file(str(file_path))

    assert parsed_data["note_name"] == "Plain Note"
    assert parsed_data["yaml_front_matter"] == {}
    assert "This is a plain markdown note" in parsed_data["content"]
    assert len(parsed_data["_internal_links_info"]) == 1
    assert parsed_data["_internal_links_info"][0] == {"target_note_name": "Concept A", "link_text": "Concept A"}

def test_parser_non_existent_file():
    parser = ObsidianParser()
    file_path = "non_existent_file.md"
    parsed_data = parser.parse_markdown_file(file_path)
    assert parsed_data["file_path"] == file_path
    assert parsed_data["yaml_front_matter"] == {}
    assert parsed_data["content"] == ""
    assert parsed_data["_internal_links_info"] == []

def test_parser_invalid_yaml(test_vault):
    parser = ObsidianParser()
    file_path = test_vault / "Invalid YAML Note.md"
    parsed_data = parser.parse_markdown_file(str(file_path))
    assert parsed_data["note_name"] == "Invalid YAML Note"
    assert parsed_data["yaml_front_matter"] == {} # 预期是空字典，因为YAML解析失败
    assert "This note has invalid YAML." in parsed_data["content"]

# --- GraphBuilder Tests ---

def test_graph_builder_basic_graph(test_vault):
    parser = ObsidianParser()
    sdk = ObsidianGraphSDK() # 使用SDK的解析逻辑来获取所有parsed_data
    all_parsed_data = []
    for root, _, files in os.walk(test_vault):
        for file in files:
            if file.endswith(".md"):
                parsed_data = parser.parse_markdown_file(os.path.join(root, file))
                if parsed_data:
                    all_parsed_data.append(parsed_data)

    builder = GraphBuilder()
    graph = builder.build_graph(all_parsed_data)

    assert graph.number_of_nodes() == 3 # Concept A, Concept B, Event X
    assert graph.number_of_edges() == 2 # Relation AB, Relation AX

    # 检查节点属性
    assert "Concept A" in graph.nodes
    assert graph.nodes["Concept A"]["type"] == "node"
    assert "CA" in graph.nodes["Concept A"]["aliases"]

    assert "Concept B" in graph.nodes
    assert graph.nodes["Concept B"]["type"] == "node"

    assert "Event X" in graph.nodes
    assert graph.nodes["Event X"]["type"] == "event"

    # 检查边属性
    assert graph.has_edge("Concept A", "Concept B")
    edge_data_ab = graph.get_edge_data("Concept A", "Concept B")
    assert edge_data_ab["relation_type"] == "RELATES_TO"
    assert edge_data_ab["defined_by_note_name"] == "Relation AB"

    assert graph.has_edge("Concept A", "Event X")
    edge_data_ax = graph.get_edge_data("Concept A", "Event X")
    assert edge_data_ax["relation_type"] == "HAPPENED_AT"
    assert edge_data_ax["defined_by_note_name"] == "Relation AX"

def test_graph_builder_missing_target_node(test_vault, caplog):
    parser = ObsidianParser()
    file_path = test_vault / "Relation AC.md"
    parsed_data = parser.parse_markdown_file(str(file_path))

    builder = GraphBuilder()
    # 模拟只有Relation AC这一个笔记被解析的情况
    graph = builder.build_graph([parsed_data])

    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0
    assert "不存在于图中，跳过。" in caplog.text
    assert "Concept A" in caplog.text or "Concept C" in caplog.text

def test_graph_builder_invalid_edge_ends_format(test_vault, caplog):
    parser = ObsidianParser()
    # 创建一个带有无效ends格式的虚拟笔记
    invalid_edge_path = test_vault / "Invalid Edge.md"
    invalid_edge_path.write_text("""---
type: edge
ends: "[[Concept A]]" # 应该是列表
describe: invalid
---
""")
    parsed_data = parser.parse_markdown_file(str(invalid_edge_path))

    builder = GraphBuilder()
    graph = builder.build_graph([parsed_data])

    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0
    assert "的 'ends' 属性格式不正确或缺失，跳过。" in caplog.text

# --- ObsidianGraphSDK Tests ---

def test_sdk_export_to_networkx_success(test_vault):
    sdk = ObsidianGraphSDK()
    graph = sdk.export_to_networkx(str(test_vault))

    assert graph.number_of_nodes() == 3 # Concept A, Concept B, Event X
    assert graph.number_of_edges() == 2 # Relation AB, Relation AX

    assert "Concept A" in graph.nodes
    assert "Concept B" in graph.nodes
    assert "Event X" in graph.nodes

    assert graph.has_edge("Concept A", "Concept B")
    assert graph.has_edge("Concept A", "Event X")

def test_sdk_export_to_networkx_non_existent_vault():
    sdk = ObsidianGraphSDK()
    with pytest.raises(FileNotFoundError, match="Obsidian Vault路径不存在"):
        sdk.export_to_networkx("./non_existent_vault_path")
