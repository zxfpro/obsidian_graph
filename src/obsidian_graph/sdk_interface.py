import os
import networkx as nx
from .obsidian_parser import ObsidianParser
from .graph_builder import GraphBuilder
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ObsidianGraphSDK:
    """The main entry point for the Obsidian Graph SDK.

    This class coordinates the file traversal, parsing, and graph building processes
    to convert an Obsidian vault into a NetworkX graph. It provides a public API
    for external applications to interact with the SDK.
    """

    def export_to_networkx(self, vault_path: str) -> nx.DiGraph:
        """Exports an Obsidian vault into a NetworkX directed graph.

        This is the primary public API method. It traverses the specified Obsidian vault,
        parses each Markdown file, and then builds a comprehensive NetworkX graph
        representing the notes as nodes and their relationships as edges.

        Args:
            vault_path (str): The file system path to the root of the Obsidian vault.

        Returns:
            networkx.DiGraph: A NetworkX directed graph where:
                              - Nodes represent Obsidian notes (type 'node' or 'event').
                                Node attributes include 'type', 'aliases', 'describe',
                                'version', 'over', 'tags', 'content', and raw YAML properties.
                              - Edges represent relationships defined by 'type: edge' notes.
                                Edge attributes include 'relation_type', 'defined_by_note_name',
                                'original_content', and raw YAML properties from the edge note.

        Raises:
            FileNotFoundError: If the provided `vault_path` does not exist or is not a directory.
        """
        if not os.path.isdir(vault_path):
            raise FileNotFoundError(f"Obsidian Vault路径不存在: {vault_path}")

        obsidian_parser = ObsidianParser()
        graph_builder = GraphBuilder()
        all_parsed_notes_data = []

        logging.info(f"开始遍历Obsidian Vault: {vault_path}")
        for root, _, files in os.walk(vault_path):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    logging.info(f"正在解析文件: {file_path}")
                    parsed_data = obsidian_parser.parse_markdown_file(file_path)
                    if parsed_data: # 确保解析成功或至少返回部分数据
                        all_parsed_notes_data.append(parsed_data)
                    else:
                        logging.warning(f"文件 {file_path} 解析失败，跳过。")

        logging.info(f"已解析 {len(all_parsed_notes_data)} 个Markdown文件。")
        logging.info("开始构建图...")
        graph = graph_builder.build_graph(all_parsed_notes_data)
        logging.info("图构建完成。")

        return graph
