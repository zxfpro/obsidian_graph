import os
import re
import yaml
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ObsidianParser:
    """Parses Obsidian Markdown files to extract metadata and content.

    This class is responsible for reading a single Obsidian Markdown file,
    parsing its YAML front matter, extracting the main content, and identifying
    internal links within the note's body.
    """

    def parse_markdown_file(self, file_path: str) -> dict:
        """Parses a single Obsidian Markdown file.

        Reads the specified Markdown file, extracts its YAML front matter,
        the main markdown content, and identifies all internal Obsidian links.

        Args:
            file_path (str): The absolute path to the .md file to be parsed.

        Returns:
            dict: A dictionary representing the parsed content of the Obsidian note.
                  The dictionary contains the following keys:
                  - "file_path" (str): Absolute path to the .md file.
                  - "note_name" (str): File name without extension (e.g., "My Concept").
                  - "yaml_front_matter" (dict): Raw parsed YAML (e.g., {'type': 'node'}).
                  - "content" (str): Full markdown content after YAML (body).
                  - "_internal_links_info" (list[dict]): List of links found in 'content'.
                                                          Each link: {"target_note_name": str, "link_text": str}.
                  If the file cannot be read, a warning is logged, and a dictionary
                  with default/empty values is returned.
        """
        parsed_data = {
            "file_path": file_path,
            "note_name": os.path.splitext(os.path.basename(file_path))[0],
            "yaml_front_matter": {},
            "content": "",
            "_internal_links_info": []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                full_content = f.read()
        except IOError as e:
            logging.warning(f"无法读取文件 {file_path}: {e}")
            return parsed_data # 返回包含错误信息的字典

        yaml_dict, markdown_body_content = self._extract_yaml_front_matter(full_content)
        parsed_data["yaml_front_matter"] = yaml_dict
        parsed_data["content"] = markdown_body_content
        parsed_data["_internal_links_info"] = self._parse_internal_links(markdown_body_content)

        return parsed_data

    def _extract_yaml_front_matter(self, content: str) -> tuple[dict, str]:
        """Extracts and parses the YAML front matter from a Markdown string.

        Identifies the YAML block delimited by '---' at the beginning of the content
        and parses it using PyYAML.

        Args:
            content (str): The full content of the Markdown file.

        Returns:
            tuple[dict, str]: A tuple containing:
                              - dict: The parsed YAML front matter as a dictionary.
                                      Returns an empty dictionary if no YAML is found
                                      or if parsing fails.
                              - str: The remaining Markdown content after the YAML block.
        """
        yaml_front_matter = {}
        markdown_body_content = content

        # 检查是否以YAML front matter开始
        if content.startswith('---'):
            parts = content.split('---', 2) # 最多分割两次
            if len(parts) > 2:
                yaml_block = parts[1]
                markdown_body_content = parts[2].strip() # 移除YAML块后的空白

                try:
                    yaml_front_matter = yaml.safe_load(yaml_block)
                    if not isinstance(yaml_front_matter, dict):
                        logging.warning(f"YAML front matter不是有效的字典，将返回空字典。文件内容开始于: {content[:50]}...")
                        yaml_front_matter = {}
                except yaml.YAMLError as e:
                    logging.warning(f"解析YAML front matter时出错: {e}. 文件内容开始于: {content[:50]}...")
                    yaml_front_matter = {}
            else:
                # 如果只有一个或没有'---'，则没有有效的YAML front matter
                logging.info(f"文件内容以'---'开头，但没有找到第二个'---'来结束YAML front matter。文件内容开始于: {content[:50]}...")
                yaml_front_matter = {}
                markdown_body_content = content # 整个内容都是正文

        return yaml_front_matter, markdown_body_content

    def _parse_internal_links(self, text: str) -> list[dict]:
        """Finds and extracts internal Obsidian links from a given text.

        Matches links in the format `[[target]]` or `[[target|display]]`.

        Args:
            text (str): The Markdown content to search for links.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary represents a link
                        and contains:
                        - "target_note_name" (str): The name of the target note.
                        - "link_text" (str): The display text of the link. If no display
                                             text is provided in the link, `target_note_name`
                                             is used as `link_text`.
        """
        links = []
        # 匹配 [[target]] 或 [[target|display]]
        matches = re.findall(r'\[\[([^|\]]+)(?:\|([^\]]+))?\]\]', text)
        for match in matches:
            target_note_name = match[0].strip()
            display_text = match[1].strip() if match[1] else target_note_name
            links.append({"target_note_name": target_note_name, "link_text": display_text})
        return links
