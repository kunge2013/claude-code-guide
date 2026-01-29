# 2026-01-29 Entity Extraction Session Changes

## Summary
添加了实体提取模块，用于从自然语言查询中识别和提取业务实体。

## New Module: entity_extraction

这是一个独立的 Python 项目，专注于实体提取功能。

### 目录结构
```
entity_extraction/
├── .claude/           # Claude Code 配置
├── config/            # 配置文件
├── logs/              # 日志目录
├── scripts/           # 脚本文件
├── src/               # 源代码
├── tests/             # 测试文件
├── .env.example       # 环境变量示例
├── .gitignore         # Git 忽略规则
├── README.md          # 项目文档
└── requirements.txt   # Python 依赖
```

### 主要功能
- 从自然语言查询中提取业务实体
- 支持配置化的实体识别规则
- 提供 API 接口用于集成

## Files Added
- `entity_extraction/` 整个目录 (新模块)

## Technical Details

### 项目特点
1. **独立模块**: 可独立运行的 Python 服务
2. **配置驱动**: 通过配置文件定义实体识别规则
3. **可扩展**: 易于添加新的实体类型和识别规则

### 依赖
- Python 3.x
- 详见 requirements.txt

## Commit Info
- Date: 2026-01-29
- Branch: 3.graph_rag
