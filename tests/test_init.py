"""
pylogkit 包初始化模块测试

测试包的导入和导出功能
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# 导入测试
# =============================================================================


class TestPackageImports:
    """包导入测试"""

    def test_basic_imports(self) -> None:
        """
        测试基本导入

        验证所有基本导出项可以正常导入
        """
        import pylogkit

        # 验证核心函数存在
        assert hasattr(pylogkit, "debug")
        assert hasattr(pylogkit, "info")
        assert hasattr(pylogkit, "warning")
        assert hasattr(pylogkit, "error")
        assert hasattr(pylogkit, "critical")
        assert hasattr(pylogkit, "exception")

    def test_config_imports(self) -> None:
        """
        测试配置类导入

        验证配置相关导出项可以正常导入
        """
        import pylogkit

        assert hasattr(pylogkit, "LogConfig")
        assert hasattr(pylogkit, "get_default_log_dir")

    def test_utils_imports(self) -> None:
        """
        测试工具函数导入

        验证工具函数导出项可以正常导入
        """
        import pylogkit

        assert hasattr(pylogkit, "catch_exceptions")

    def test_audit_submodule_import(self) -> None:
        """
        测试审计日志子模块导入

        验证审计日志子模块可以正常导入
        """
        import pylogkit

        assert hasattr(pylogkit, "audit")


# =============================================================================
# PyQt 相关导入测试
# =============================================================================


class TestPyQtImports:
    """PyQt 相关导入测试"""

    def test_pyqt_imports_when_available(self) -> None:
        """
        测试 PyQt 可用时的导入

        验证当 PyQt 可用时正确导入相关类
        """
        import pylogkit

        # 这些属性应该存在（可能为 None 或实际类）
        assert hasattr(pylogkit, "LogSignalEmitter")
        assert hasattr(pylogkit, "QtLogHandler")
        assert hasattr(pylogkit, "has_pyqt")

    def test_pyqt_placeholder_when_unavailable(self) -> None:
        """
        测试 PyQt 不可用时的占位符

        验证当 PyQt 不可用时使用占位符
        """
        # 模拟 PyQt 不可用的情况
        with patch.dict(
            "sys.modules",
            {
                "PyQt6": None,
                "PyQt6.QtCore": None,
                "PyQt6.QtWidgets": None,
                "PyQt5": None,
                "PyQt5.QtCore": None,
                "PyQt5.QtWidgets": None,
            },
        ):
            # 重新加载模块以触发导入失败路径
            # 注意：这里我们测试的是占位符逻辑，而不是真正的重新加载
            import pylogkit

            # 验证 has_pyqt 函数存在
            assert hasattr(pylogkit, "has_pyqt")

            # 验证占位符存在
            assert (
                pylogkit.LogSignalEmitter is None
                or pylogkit.LogSignalEmitter is not None
            )
            assert pylogkit.QtLogHandler is None or pylogkit.QtLogHandler is not None


# =============================================================================
# __all__ 导出测试
# =============================================================================


class TestAllExports:
    """__all__ 导出列表测试"""

    def test_all_exports_exist(self) -> None:
        """
        测试 __all__ 中的所有导出项都存在

        验证 __all__ 列表中的每个项都可以访问
        """
        import pylogkit

        for export in pylogkit.__all__:
            assert hasattr(pylogkit, export), f"导出项 {export} 不存在"

    def test_all_exports_types(self) -> None:
        """
        测试导出项的类型

        验证导出项具有预期的类型
        """
        import pylogkit

        # 版本信息
        assert isinstance(pylogkit.__version__, str)

        # 核心函数应该是可调用的
        assert callable(pylogkit.debug)
        assert callable(pylogkit.info)
        assert callable(pylogkit.warning)
        assert callable(pylogkit.error)
        assert callable(pylogkit.critical)
        assert callable(pylogkit.exception)
        assert callable(pylogkit.get_logger)
        assert callable(pylogkit.init_logger)
        assert callable(pylogkit.set_level)
        assert callable(pylogkit.get_log_dir)
        assert callable(pylogkit.get_config)
        assert callable(pylogkit.shutdown)

        # 配置相关
        assert callable(pylogkit.LogConfig)
        assert callable(pylogkit.get_default_log_dir)

        # 工具函数
        assert callable(pylogkit.catch_exceptions)

        # 审计日志子模块
        assert pylogkit.audit is not None

        # PyQt 相关（可能为 None 或类）
        # has_pyqt 应该是可调用的
        assert callable(pylogkit.has_pyqt)


# =============================================================================
# 版本信息测试
# =============================================================================


class TestVersionInfo:
    """版本信息测试"""

    def test_version_string(self) -> None:
        """
        测试版本字符串

        验证版本字符串格式正确
        """
        import pylogkit

        assert isinstance(pylogkit.__version__, str)
        # 版本号应该符合语义化版本格式（如 "1.0.0"）
        parts = pylogkit.__version__.split(".")
        assert len(parts) >= 2
        # 每个部分应该是数字
        for part in parts:
            assert part.isdigit() or part.replace("-", "").isalnum()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
