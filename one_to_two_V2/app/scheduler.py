# -*- coding: utf-8 -*-
"""Windows计划任务管理模块。

提供计划任务的安装、卸载、状态检查功能。
"""
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
TASK_NAME = "OneToTwo_SyncData"
LOGS_DIR = PROJECT_ROOT / "logs"
VENV_PATH = PROJECT_ROOT / "venv"


def get_venv_python() -> Path:
    """获取虚拟环境中的 Python 路径。"""
    if os.name == 'nt':
        return VENV_PATH / "Scripts" / "python.exe"
    return VENV_PATH / "bin" / "python"


def is_venv_exists() -> bool:
    """检查虚拟环境是否存在。"""
    return get_venv_python().exists()


@dataclass
class TaskStatus:
    """计划任务状态。"""
    exists: bool
    enabled: bool = False
    last_run_time: Optional[str] = None
    last_run_result: Optional[int] = None
    run_count: int = 0
    next_run_time: Optional[str] = None
    error_message: Optional[str] = None


def ensure_logs_dir() -> Path:
    """确保日志目录存在。"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR


def check_task_exists() -> bool:
    """检查计划任务是否存在。"""
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.returncode == 0
    except Exception:
        return False


def get_task_status() -> TaskStatus:
    """获取计划任务状态。"""
    if not check_task_exists():
        return TaskStatus(exists=False)
    
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME, "/V", "/FO", "LIST"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            return TaskStatus(exists=True, enabled=False, error_message="无法获取任务详情")
        
        output = result.stdout
        status = TaskStatus(exists=True)
        
        lines = output.split("\n")
        for line in lines:
            line = line.strip()
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                
                if key in ("状态", "模式"):
                    status.enabled = value == "就绪"
                elif key == "上次运行时间":
                    if value and value != "N/A" and "1999" not in value:
                        status.last_run_time = value
                elif key == "上次结果":
                    try:
                        result_val = int(value) if value and value != "N/A" else None
                        if result_val == 267011:
                            result_val = None
                        status.last_run_result = result_val
                    except ValueError:
                        pass
                elif key == "要运行的任务次数":
                    try:
                        status.run_count = int(value) if value and value != "N/A" else 0
                    except ValueError:
                        status.run_count = 0
                elif key == "下次运行时间":
                    status.next_run_time = value if value and value != "N/A" else None
        
        return status
        
    except Exception as e:
        return TaskStatus(exists=True, enabled=False, error_message=str(e))


def install_task() -> tuple[bool, str]:
    """安装计划任务。
    
    Returns:
        (success, message) 元组
    """
    ensure_logs_dir()
    
    if check_task_exists():
        return False, "计划任务已存在，请先卸载后再安装"
    
    if is_venv_exists():
        python_exe = get_venv_python()
    else:
        python_exe = Path(sys.executable)
    
    script_path = PROJECT_ROOT / "scripts" / "scheduled_sync.py"
    
    if not script_path.exists():
        return False, f"执行脚本不存在: {script_path}"
    
    cmd = [
        "schtasks", "/Create",
        "/TN", TASK_NAME,
        "/TR", f'"{python_exe}" "{script_path}"',
        "/SC", "WEEKLY",
        "/D", "MON,TUE,WED,THU,FRI",
        "/ST", "16:00",
        "/F",
        "/RL", "HIGHEST",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode == 0:
            return True, "计划任务安装成功！将在每个工作日16:00自动执行数据同步"
        else:
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
            return False, f"安装失败: {error_msg}"
            
    except Exception as e:
        return False, f"安装过程出错: {e}"


def uninstall_task() -> tuple[bool, str]:
    """卸载计划任务。
    
    Returns:
        (success, message) 元组
    """
    if not check_task_exists():
        return False, "计划任务未安装"
    
    try:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode == 0:
            return True, "计划任务已卸载"
        else:
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
            return False, f"卸载失败: {error_msg}"
            
    except Exception as e:
        return False, f"卸载过程出错: {e}"


def format_status_display(status: TaskStatus) -> str:
    """格式化状态显示。"""
    if not status.exists:
        return ""
    
    lines = []
    lines.append("\n" + "=" * 42)
    lines.append("        计划任务状态")
    lines.append("=" * 42)
    
    if status.enabled:
        lines.append("  状态: 已启用")
    else:
        lines.append("  状态: 已禁用")
    
    if status.run_count > 0:
        lines.append(f"  已执行次数: {status.run_count}")
    
    if status.last_run_time:
        lines.append(f"  上次执行: {status.last_run_time}")
    
    if status.next_run_time:
        lines.append(f"  下次执行: {status.next_run_time}")
    
    if status.last_run_result is not None and status.last_run_result != 0:
        lines.append(f"  [警告] 上次执行结果异常 (代码: {status.last_run_result})")
    
    if status.error_message:
        lines.append(f"  [错误] {status.error_message}")
    
    return "\n".join(lines)
