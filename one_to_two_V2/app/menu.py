# -*- coding: utf-8 -*-
import subprocess
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from scheduler import (
    check_task_exists,
    get_task_status,
    install_task,
    uninstall_task,
    format_status_display,
    ensure_logs_dir,
    get_venv_python,
    is_venv_exists as scheduler_venv_exists,
)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def pause():
    input("\n按回车键继续...")

VENV_PATH = os.path.join(PROJECT_ROOT, 'venv')

def get_venv_python():
    if os.name == 'nt':
        return os.path.join(VENV_PATH, 'Scripts', 'python.exe')
    return os.path.join(VENV_PATH, 'bin', 'python')

def is_venv_exists():
    return os.path.exists(get_venv_python())

def is_in_venv():
    return sys.prefix != sys.base_prefix

def check_python_env():
    version = sys.version_info
    if version.major < 3 or (version.minor < 8 if version.major == 3 else False):
        print(f"[错误] Python版本过低: {sys.version}")
        print("请安装 Python 3.8 或更高版本")
        return False
    print(f"[OK] Python版本: {sys.version.split()[0]}")
    return True

def setup_environment():
    clear_screen()
    print("\n========== 环境设置 ==========\n")
    
    print("[步骤 1/3] 检查Python版本...")
    if not check_python_env():
        pause()
        return False
    
    print("\n[步骤 2/3] 创建虚拟环境...")
    if is_venv_exists():
        print(f"[信息] 虚拟环境已存在: {VENV_PATH}")
    else:
        print(f"[信息] 正在创建虚拟环境: {VENV_PATH}")
        try:
            import venv
            venv.create(VENV_PATH, with_pip=True)
            print("[成功] 虚拟环境创建完成!")
        except Exception as e:
            print(f"[错误] 创建虚拟环境失败: {e}")
            pause()
            return False
    
    print("\n[步骤 3/3] 安装依赖...")
    venv_python = get_venv_python()
    requirements_path = os.path.join(PROJECT_ROOT, 'requirements.txt')
    
    if not os.path.exists(requirements_path):
        print(f"[错误] 未找到 requirements.txt: {requirements_path}")
        pause()
        return False
    
    try:
        result = subprocess.run(
            [venv_python, '-m', 'pip', 'install', '-r', requirements_path],
            check=False
        )
        
        if result.returncode == 0:
            print("\n" + "=" * 40)
            print("[成功] 环境设置完成!")
            print("=" * 40)
            if not is_in_venv():
                print("\n[重要] 请关闭当前窗口，重新运行 run.bat")
                print("[重要] 新窗口将自动激活虚拟环境")
            pause()
            return True
        else:
            print("\n[警告] 部分依赖可能安装失败，请检查上方输出")
            pause()
            return False
    except Exception as e:
        print(f"\n[错误] 安装过程出错: {e}")
        pause()
        return False

def run_command(cmd, desc):
    clear_screen()
    print(f"\n[执行] {desc}\n")
    print("-" * 40)
    try:
        subprocess.run(cmd, shell=False, cwd=PROJECT_ROOT)
    except Exception as e:
        print(f"[错误] 执行失败: {e}")
    pause()

def show_scheduler_menu():
    while True:
        clear_screen()
        print("\n========== 计划任务管理 ==========\n")
        
        if scheduler_venv_exists():
            python_path = get_venv_python()
            print(f"  Python路径: {python_path}")
        else:
            print(f"  Python路径: {sys.executable}")
            print("  [提示] 建议先创建虚拟环境 (菜单选项 8)")
        
        print()
        
        status = get_task_status()
        if status.exists:
            print("  任务状态: 已安装")
            if status.enabled:
                print("  运行状态: 已启用")
            else:
                print("  运行状态: 已禁用")
            if status.run_count > 0:
                print(f"  已执行次数: {status.run_count}")
            if status.last_run_time:
                print(f"  上次执行: {status.last_run_time}")
            if status.next_run_time:
                print(f"  下次执行: {status.next_run_time}")
            if status.last_run_result is not None and status.last_run_result != 0:
                print(f"  [警告] 上次执行异常 (代码: {status.last_run_result})")
        else:
            print("  任务状态: 未安装")
        
        print()
        print("  1. 安装计划任务 (工作日16:00同步数据)")
        print("  2. 卸载计划任务")
        print()
        print("  0. 返回上级菜单")
        print()
        
        choice = input("请输入选项: ").strip()
        
        if choice == '0':
            return
        elif choice == '1':
            success, message = install_task()
            print(f"\n{message}")
            pause()
        elif choice == '2':
            success, message = uninstall_task()
            print(f"\n{message}")
            pause()
        else:
            print("\n[错误] 无效选项...")
            pause()

def check_scheduler_status():
    """检查并显示计划任务状态。"""
    if not check_task_exists():
        return
    
    status = get_task_status()
    if status.exists:
        output = format_status_display(status)
        print(output)
        
        warning_parts = []
        if not status.enabled:
            warning_parts.append("计划任务已被禁用，请在计划任务管理中重新启用")
        elif status.last_run_result is not None and status.last_run_result != 0:
            warning_parts.append("计划任务上次执行异常，请检查日志文件")
        
        if warning_parts:
            print("  [警告] " + "；".join(warning_parts))

def show_custom_menu():
    while True:
        clear_screen()
        print("\n========== 自定义模式 ==========\n")
        print("  1. 模型训练 - 指定训练月数")
        print("  2. 模型训练 - 指定日期范围")
        print("  3. 滚动训练 - 敏感性测试")
        print("  4. 情绪分层回测 - 指定日期范围")
        print("  5. 热力图分析 - 指定日期范围")
        print("  6. 热力图分析 - 指定模型文件")
        print("\n  0. 返回上级菜单")
        print()
        
        choice = input("请输入选项: ").strip()
        
        if choice == '0':
            return
        elif choice == '1':
            months = input("请输入训练月数: ").strip()
            if months:
                run_command(
                    [sys.executable, '-m', 'src.pipeline.train_model', '--months', months],
                    f"模型训练 (最近{months}个月)"
                )
        elif choice == '2':
            start_date = input("请输入开始日期 (如20250801): ").strip()
            end_date = input("请输入结束日期 (如20260215): ").strip()
            if start_date and end_date:
                run_command(
                    [sys.executable, '-m', 'src.pipeline.train_model', '--start', start_date, '--end', end_date],
                    f"模型训练 ({start_date} - {end_date})"
                )
        elif choice == '3':
            run_command(
                [sys.executable, '-m', 'src.pipeline.rolling', '--sensitivity'],
                "滚动训练敏感性测试"
            )
        elif choice == '4':
            start_date = input("请输入开始日期 (如20260101): ").strip()
            end_date = input("请输入结束日期 (如20260214): ").strip()
            if start_date and end_date:
                run_command(
                    [sys.executable, '-m', 'src.pipeline.backtest_emotion', '--start', start_date, '--end', end_date],
                    f"情绪分层回测 ({start_date} - {end_date})"
                )
        elif choice == '5':
            start_date = input("请输入开始日期 (如20260101): ").strip()
            end_date = input("请输入结束日期 (如20260214): ").strip()
            if start_date and end_date:
                run_command(
                    [sys.executable, '-m', 'src.pipeline.heatmap', '--start', start_date, '--end', end_date],
                    f"热力图分析 ({start_date} - {end_date})"
                )
        elif choice == '6':
            models_dir = os.path.join(PROJECT_ROOT, 'data', 'models')
            print("\n可用模型文件:")
            if os.path.exists(models_dir):
                for f in os.listdir(models_dir):
                    if f.endswith('.joblib'):
                        print(f"  - {f}")
            print()
            model_path = input("请输入模型文件路径 (如data/models/model_latest.joblib): ").strip()
            if model_path:
                run_command(
                    [sys.executable, '-m', 'src.pipeline.heatmap', '--model', model_path],
                    f"热力图分析 (模型: {model_path})"
                )
        else:
            print("\n[错误] 无效选项...")
            pause()

def show_env_status():
    if is_in_venv():
        print("  [环境] 虚拟环境: 已激活")
    elif is_venv_exists():
        print("  [环境] 虚拟环境: 已创建 (未激活)")
    else:
        print("  [环境] 虚拟环境: 未创建")

def main():
    ensure_logs_dir()
    
    while True:
        clear_screen()
        print()
        print("=" * 42)
        print("        One to Two 工具启动菜单")
        print("=" * 42)
        print()
        show_env_status()
        print()
        print("  1. 模型训练 (默认: 最近6个月)")
        print("  2. 每日日报 (默认模式)")
        print("  3. 滚动训练评估 (默认: 6+1窗口)")
        print("  4. 情绪分层回测 (默认: 最近6个月)")
        print("  5. 热力图分析 (默认: 最近1个月)")
        print("  6. 同步缓存数据")
        print("  7. 自定义模式...")
        print("  8. 环境设置 (初始化)")
        print("  9. 计划任务管理...")
        print()
        print("  0. 退出")
        
        check_scheduler_status()
        
        print()
        
        choice = input("请输入选项: ").strip()
        
        if choice == '0':
            print("\n感谢使用 One to Two 工具!")
            break
        elif choice == '1':
            run_command(
                [sys.executable, '-m', 'src.pipeline.train_model'],
                "模型训练 (默认6个月)"
            )
        elif choice == '2':
            run_command(
                [sys.executable, '-m', 'src.pipeline.daily'],
                "每日日报"
            )
        elif choice == '3':
            run_command(
                [sys.executable, '-m', 'src.pipeline.rolling'],
                "滚动训练评估 (默认6+1窗口)"
            )
        elif choice == '4':
            run_command(
                [sys.executable, '-m', 'src.pipeline.backtest_emotion'],
                "情绪分层回测 (默认6个月)"
            )
        elif choice == '5':
            run_command(
                [sys.executable, '-m', 'src.pipeline.heatmap'],
                "热力图分析 (默认1个月)"
            )
        elif choice == '6':
            run_command(
                [sys.executable, '-m', 'src.data.sync_cache'],
                "同步缓存数据"
            )
        elif choice == '7':
            show_custom_menu()
        elif choice == '8':
            setup_environment()
        elif choice == '9':
            show_scheduler_menu()
        else:
            print("\n[错误] 无效选项，请重新输入...")
            pause()

if __name__ == '__main__':
    main()
