# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-02-23

### Added
- 初始版本发布
- 基于 loguru 的核心日志功能
- 统一的日志接口：debug, info, warning, error, critical, exception
- 跨平台默认日志目录支持（Windows、macOS、Linux）
- 自动日志轮转、压缩和清理
- 彩色控制台输出
- 完整的类型注解支持
- 审计日志子模块（JSON 结构化日志）
- PyQt 集成支持（可选依赖）
- 异常捕获装饰器
- 环境变量配置支持
- 完整的测试覆盖

### Features
- **Core Logging**: 基于 loguru 的高性能日志系统
- **Audit Logging**: 独立的 JSON 格式审计日志
- **Qt Integration**: PyQt5/PyQt6 信号集成支持
- **Exception Handling**: 便捷的异常捕获装饰器
- **Configuration**: 灵活的配置系统，支持环境变量
- **Cross-platform**: 自动适配各平台的日志存储路径

[Unreleased]: https://github.com/yourusername/pylogkit/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/pylogkit/releases/tag/v1.0.0
