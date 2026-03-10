# -*- coding: utf-8 -*-
"""计划任务执行脚本。

供Windows计划任务调用，执行数据同步并输出日志。
"""
import sys
import os
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"


def setup_logging():
    """设置日志输出到文件。"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    today = datetime.now().strftime("%Y%m%d")
    log_file = LOGS_DIR / f"sync_{today}.log"
    
    class Logger:
        def __init__(self, log_path):
            self.log_path = log_path
            self.terminal = sys.stdout
            self.log_file = open(log_path, 'a', encoding='utf-8')
        
        def write(self, message):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if message.strip():
                self.terminal.write(message)
                self.log_file.write(f"[{timestamp}] {message}")
                self.log_file.flush()
        
        def flush(self):
            self.terminal.flush()
            self.log_file.flush()
        
        def isatty(self):
            return False
        
        def close(self):
            self.log_file.close()
    
    return Logger(log_file)


def main():
    """主入口。"""
    logger = setup_logging()
    sys.stdout = logger
    sys.stderr = logger
    
    print("=" * 50)
    print("计划任务: 数据同步开始")
    print("=" * 50)
    
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        
        from src.data.sync_cache import run_sync, SyncConfig
        from pathlib import Path
        
        config = SyncConfig(
            cache_root=Path("data/cache"),
            zt_trade_days=14,
            index_months=2,
            index_symbol="000300",
        )
        
        result = run_sync(config)
        
        print()
        print("=" * 50)
        if result.success:
            print("数据同步完成")
            print(f"  ZT同步: {result.zt_synced} 天")
            print(f"  指数同步: {'成功' if result.index_synced else '跳过'}")
        else:
            print("数据同步存在问题:")
            if result.zt_failed > 0:
                print(f"  ZT失败: {result.zt_failed} 天")
            if result.index_error:
                print(f"  指数错误: {result.index_error}")
        print("=" * 50)
        
    except Exception as e:
        print(f"[错误] 执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.close()


if __name__ == '__main__':
    main()
