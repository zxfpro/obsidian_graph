
# Obsidian Graph SDK - 产品需求文档 (PRD)

## 1. 项目概述

### 1.1 背景与目标

Obsidian 的双链笔记系统功能强大，但其内部可视化和分析能力有限。本项目旨在开发一个 Python SDK，用于将 Obsidian 笔记及其定义的结构化关系（通过 YAML front matter）导出为 NetworkX 图格式。NetworkX 图将作为 Obsidian 知识库的编程友好中间表示，为后续高级图分析、可视化或与其他图工具集成（如 Neo4j、XMind）提供基础。

**核心目标：** 提供一个高效、准确的 Obsidian Vault 到 NetworkX 图的导出工具。

### 1.2 范围

**In Scope (核心功能)：**

- 解析 Obsidian Markdown 文件（YAML front matter, 正文）。
- 基于笔记 `type` (`node`, `event`, `edge`) 构建 NetworkX 图：
    - `type: node` 和 `type: event` 的笔记转化为 NetworkX 节点。
    - `type: edge` 的笔记转化为 NetworkX 边，连接其 `ends` 属性指定的节点。
- 将所有原始笔记的元数据（YAML属性、正文内容）和内部链接信息存储为 NetworkX 节点或边的属性。
- 内部链接 (`[[...]]`) 信息仅作为节点/边属性存储 (`_internal_links_info`)，不直接创建 NetworkX 边，以支持按需构建子图。

**Out of Scope (非核心功能，未来考虑)：**

- 直接导出到 Neo4j、XMind 或其他特定格式（可通过 NetworkX 转换实现）。
- 高级图分析、查询或可视化功能。
- Obsidian Vault 的实时同步或双向写入。

## 2. 核心功能描述

### 2.1 输入与输出

- **输入：** Obsidian Vault 的文件系统路径。
- **输出：** 一个 `networkx.DiGraph` 对象。

### 2.2 笔记类型与图元素映射

|Obsidian 笔记 `type`|NetworkX 图元素|映射详情|
|---|---|---|
|`node`|节点|笔记文件 -> 节点。节点ID为文件名。所有YAML属性和正文为节点属性。|
|`event`|节点|笔记文件 -> 节点。节点ID为文件名。所有YAML属性和正文为节点属性。|
|`edge`|边|笔记文件**不**作为节点。`ends` 属性指定的两个节点之间创建一条边。`edge` 笔记的所有YAML属性和正文为边属性。|

### 2.3 属性保留

- **YAML Front Matter：** 所有的 YAML 属性（包括 `aliases`, `describe`, `type`, `ends`, `version`, `over`, `tags` 及自定义属性）都将被保留。
    - 对于节点，作为节点属性。
    - 对于边（由 `type: edge` 定义），作为边属性。
- **正文内容：** 笔记的正文内容将作为节点或边的 `content` / `original_content` 属性存储。
- **内部链接 (`[[...]]`)：** 所有笔记正文中的内部链接信息（目标笔记名、显示文本）将被提取，并存储在节点或边的 `_internal_links_info` 属性中，作为列表字典的形式。

## 3. 关键业务逻辑

- **双阶段处理：** 先遍历所有文件创建节点并收集 `edge` 笔记信息，再根据收集到的 `edge` 信息创建边，以确保边连接的节点已存在。
- **`edge` 笔记的 `ends` 属性：** 预期为包含两个 Obsidian 链接字符串的列表。SDK 将解析这些链接以确定边的源和目标节点。
- **错误处理：** 对缺失 YAML、格式错误、链接目标不存在等情况进行健壮处理（警告、跳过或默认值）。

## 4. 接口设计 (高层)

graph TD
    subgraph 用户
        A[调用 SDK.export_to_networkx(vault_path)]
    end

    subgraph Obsidian Graph SDK
        B[File Parser]
        C[Graph Builder]
    end

    subgraph 内部数据流
        D[Obsidian Vault (Markdown Files)]
        E[Parsed Note Data (Python Dicts)]
        F[NetworkX DiGraph Object]
    end

    A --> B
    D --> B : 读取文件
    B --> E : 解析文件内容
    E --> C : 传递解析数据
    C --> F : 构建图
    F --> A : 返回图对象

## 5. 验收标准

- **功能：** SDK 成功导出符合上述所有规则的 NetworkX 图。
- **数据完整性：** 原始 Obsidian 笔记的所有关键信息（YAML属性、正文、内部链接）在 NetworkX 图中可追溯。
- **健壮性：** SDK 能处理常见的 Obsidian 笔记格式变体和异常情况。
- **性能：** 在典型规模的 Obsidian Vault (例如，1000个笔记) 上，导出时间可接受。