import networkx as nx
import re
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GraphBuilder:
    """Builds a NetworkX graph from parsed Obsidian note data.

    This class takes a list of parsed Obsidian note data (dictionaries)
    and constructs a directed graph where notes are represented as nodes
    and relationships between notes are represented as edges.
    It handles different note types ('node', 'event', 'edge') and their
    respective attributes.
    """

    def build_graph(self, parsed_notes_data: list) -> nx.DiGraph:
        """Orchestrates the construction of a NetworkX graph from parsed Obsidian notes.

        The graph building process occurs in two main phases:
        1. Node Addition and Edge Information Collection: Iterates through all parsed
           notes. 'node' and 'event' type notes are added as nodes to the graph.
           'edge' type notes are collected for processing in the next phase.
        2. Edge Addition: Iterates through the collected 'edge' notes and adds
           corresponding edges to the graph, linking existing nodes.

        Args:
            parsed_notes_data (list): A list of dictionaries, where each dictionary
                                      represents a parsed Obsidian note (ParsedNoteData).

        Returns:
            networkx.DiGraph: The constructed NetworkX directed graph, with nodes
                              representing Obsidian notes and edges representing
                              defined relationships.
        """
        G = nx.DiGraph()
        edge_notes_to_process = []

        # Phase 1: Add Nodes & Collect Edge Info
        for note_data in parsed_notes_data:
            note_type = note_data["yaml_front_matter"].get("type")
            if note_type in ["node", "event"]:
                self._add_node_to_graph(G, note_data)
            elif note_type == "edge":
                edge_notes_to_process.append(note_data)
            else:
                logging.warning(f"未知或缺失的笔记类型 '{note_type}'，跳过笔记: {note_data.get('note_name', '未知名称')}")

        # Phase 2: Add Edges
        for edge_note_data in edge_notes_to_process:
            self._add_edge_to_graph(G, edge_note_data)

        return G

    def _add_node_to_graph(self, graph: nx.DiGraph, note_data: dict):
        """Adds a node to the graph with attributes extracted from parsed note data.

        Node attributes are derived from the YAML front matter and content of the note.
        Supported node types are 'node' and 'event'.

        Args:
            graph (networkx.DiGraph): The NetworkX graph to which the node will be added.
            note_data (dict): A dictionary containing the parsed data for a single
                              Obsidian note (ParsedNoteData).
        """
        note_name = note_data["note_name"]
        yaml_fm = note_data["yaml_front_matter"]

        node_attributes = {
            "type": yaml_fm.get("type"),
            "aliases": yaml_fm.get("aliases", []),
            "describe": yaml_fm.get("describe"),
            "version": yaml_fm.get("version"),
            "over": yaml_fm.get("over"),
            "tags": yaml_fm.get("tags", []),
            "content": note_data["content"],
            "_all_yaml_props": yaml_fm,
            "_internal_links_info": note_data["_internal_links_info"]
        }
        graph.add_node(note_name, **node_attributes)
        logging.info(f"已添加节点: {note_name} (类型: {node_attributes['type']})")

    def _add_edge_to_graph(self, graph: nx.DiGraph, edge_note_data: dict):
        """Adds an edge to the graph with attributes extracted from an 'edge' type note.

        Edges are created based on the 'ends' property in the edge note's YAML front matter,
        linking two existing nodes in the graph. Various attributes from the edge note's
        YAML and content are attached to the edge.

        Args:
            graph (networkx.DiGraph): The NetworkX graph to which the edge will be added.
            edge_note_data (dict): A dictionary containing the parsed data for an
                                   Obsidian note of type 'edge'.
        """
        edge_yaml_fm = edge_note_data["yaml_front_matter"]
        ends = edge_yaml_fm.get("ends")

        if not isinstance(ends, list) or len(ends) != 2:
            logging.warning(f"边笔记 '{edge_note_data.get('note_name', '未知名称')}' 的 'ends' 属性格式不正确或缺失，跳过。")
            return

        source_node_name = self._get_node_name_from_link(ends[0])
        target_node_name = self._get_node_name_from_link(ends[1])

        if not graph.has_node(source_node_name):
            logging.warning(f"边笔记 '{edge_note_data.get('note_name', '未知名称')}' 的源节点 '{source_node_name}' 不存在于图中，跳过。")
            return
        if not graph.has_node(target_node_name):
            logging.warning(f"边笔记 '{edge_note_data.get('note_name', '未知名称')}' 的目标节点 '{target_node_name}' 不存在于图中，跳过。")
            return

        relation_type = edge_yaml_fm.get("describe", "UNKNOWN_RELATION").upper().replace(' ', '_')

        edge_attributes = {
            "relation_type": relation_type,
            "defined_by_note_name": edge_note_data["note_name"],
            "original_content": edge_note_data["content"],
            "_all_yaml_props_from_edge_note": edge_yaml_fm,
            "_internal_links_info": edge_note_data["_internal_links_info"],
            "version": edge_yaml_fm.get("version"),
            "over": edge_yaml_fm.get("over"),
            "tags": edge_yaml_fm.get("tags", [])
        }
        # 将所有其他YAML属性也添加到边属性中
        for key, value in edge_yaml_fm.items():
            if key not in edge_attributes: # 避免覆盖已定义的属性
                edge_attributes[key] = value

        graph.add_edge(source_node_name, target_node_name, **edge_attributes)
        logging.info(f"已添加边: {source_node_name} --[{relation_type}]--> {target_node_name}")

    def _get_node_name_from_link(self, link_str: str) -> str:
        """Helper function to extract the target note name from an Obsidian link string.

        Handles both `[[Note Name]]` and `[[Note Name|Display]]` formats.

        Args:
            link_str (str): The Obsidian link string (e.g., "[[My Note]]" or "[[My Note|Display]]").

        Returns:
            str: The extracted note name (e.g., "My Note"). If the string does not
                 match the link format, the original string is returned.
        """
        match = re.match(r'\[\[([^|\]]+)(?:\|[^\]]+)?\]\]', link_str)
        if match:
            return match.group(1).strip()
        return link_str # 如果不是[[...]]格式，则直接返回原字符串