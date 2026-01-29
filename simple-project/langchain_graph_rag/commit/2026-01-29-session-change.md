# 2026-01-29 Session Changes

## Summary
本次提交包含了 GraphRAG 设计文档、字典配置优化以及字典服务路径解析改进。

## Changes

### 1. 新增文件
- **chatbi/langchain_chatbi/design_doc/graph_rag.md**
  - 新增 GraphRAG 设计文档
  - 基于 langgraph 的设计方案需求
  - 目标：拆解问题中的实体、指标、维度信息
  - 基于拆解结果决定查询的表、字段和条件

### 2. 配置文件优化
- **chatbi/langchain_chatbi/config/dictionary_config.yaml**
  - 添加详细的中文使用说明
  - 将 product_dict 改为 static 类型作为示例
  - 添加 database 类型的配置示例注释
  - 优化配置注释，使其更易于理解

### 3. 字典服务改进
- **chatbi/langchain_chatbi/dictionary/dictionary_service.py**
  - 改进 YAML 配置文件的路径解析逻辑
  - 支持相对路径和绝对路径
  - 实现多策略路径解析：
    - 策略1：相对于当前工作目录
    - 策略2：相对于模块目录
    - 策略3：相对于包根目录
  - 增强日志输出，便于调试
  - 改进错误处理

## Technical Details

### Path Resolution Strategies
The dictionary service now implements a robust path resolution mechanism:
1. First checks if the path is absolute or exists relative to current working directory
2. Falls back to module-relative path resolution
3. Final fallback to package root resolution

This ensures the configuration can be loaded correctly regardless of how the application is started.

## Files Modified
- `chatbi/langchain_chatbi/config/dictionary_config.yaml` (modified)
- `chatbi/langchain_chatbi/dictionary/dictionary_service.py` (modified)

## Files Added
- `chatbi/langchain_chatbi/design_doc/graph_rag.md` (new)

## Commit Info
- Date: 2026-01-29
- Branch: 3.graph_rag
