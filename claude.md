# Claude Code 使用指南项目

## 项目概述
这是一个关于 Claude Code CLI 工具的使用指南文档项目，旨在帮助用户学习和掌握 Claude Code 的各种功能和最佳实践。

## 目标受众
- Claude Code 的新手用户
- 希望深入了解 Claude Code 高级功能的开发者
- 需要定制 Claude Code 行为的高级用户

## 项目结构

```
claude_guide/
├── README.md                    # 项目说明
├── claude.md                    # 本文件 - 项目上下文
├── claude使用指南.md            # 主要使用指南
├── quick_key/                   # 快捷键和命令相关
│   ├── 1.claudecode指令.md
│   └── 2.hook自定义.md
├── skills使用说明/              # Skills 功能说明
│   └── 1skills使用说明.md
├── claude项目初始化/            # 项目初始化相关
│   └── 1.claude初始化.md
├── plan/                        # 规划材料
├── simple-project/              # 简单项目示例
└── .claude/                     # Claude Code 配置目录
    ├── settings.json            # 全局设置
    ├── settings.local.json      # 本地设置
    └── skills/                  # 自定义技能
        └── git-commit/
            ├── skill.json
            └── skill.md
```

## 文档语言
- 使用中文编写
- 技术术语保留英文原文

## 内容组织原则
1. 每个主题一个独立文件，便于查找
2. 按功能模块划分目录
3. 提供实用示例和命令输出
4. 包含配置文件示例

## 开发规范
- Git 提交信息使用中文，简洁明了
- 文档使用 Markdown 格式
- 文件命名使用中文，便于理解

## Claude Code 配置
- 项目已配置 git push 权限
- 包含自定义 git-commit skill
