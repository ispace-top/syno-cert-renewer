#!/usr/bin/env python3
"""
证书续签循环执行程序
该程序替代原来的cron定时任务，在一个循环中定期执行证书检查和更新任务，
避免因cron执行导致的容器重启问题。
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime, timedelta
import json

# 添加项目src目录到Python路径
sys.path.append('/app/src')

from config_manager import ConfigManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

# 状态文件路径
STATE_FILE_PATH = '/app/.scheduler_state'

def load_scheduler_state():
    """加载调度器状态"""
    if os.path.exists(STATE_FILE_PATH):
        try:
            with open(STATE_FILE_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"无法加载调度器状态: {e}")
    return {}

def save_scheduler_state(state):
    """保存调度器状态"""
    try:
        with open(STATE_FILE_PATH, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logger.warning(f"无法保存调度器状态: {e}")

def run_certificate_check():
    """运行证书检查和更新任务"""
    logger.info("开始执行证书检查与更新任务...")
    
    try:
        # 执行主程序
        result = subprocess.run([
            'python', '/app/src/main.py'
        ], capture_output=True, text=True, timeout=300)  # 5分钟超时
        
        if result.returncode == 0:
            logger.info("证书检查与更新任务执行成功")
            logger.debug(f"输出: {result.stdout}")
        else:
            logger.error(f"证书检查与更新任务执行失败，返回码: {result.returncode}")
            logger.error(f"错误输出: {result.stderr}")
            
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.error("证书检查与更新任务执行超时")
        return False
    except Exception as e:
        logger.error(f"执行证书检查与更新任务时发生异常: {e}")
        return False

def calculate_next_run_time():
    """计算下次运行时间"""
    config_manager = ConfigManager()
    interval_days = config_manager.cert_check_interval_days
    
    # 默认按配置间隔计算下次运行时间
    next_run = datetime.now() + timedelta(days=interval_days)
    
    # 检查状态文件中是否有更精确的下次运行时间
    state = load_scheduler_state()
    if 'next_run_time' in state:
        try:
            scheduled_next_run = datetime.fromisoformat(state['next_run_time'])
            # 取两个时间中较早的一个
            next_run = min(next_run, scheduled_next_run)
        except Exception as e:
            logger.warning(f"无法解析状态文件中的下次运行时间: {e}")
    
    return next_run

def main():
    """主循环函数"""
    logger.info("=== 证书续签服务启动 ===")
    
    # 立即执行一次任务
    logger.info("首次启动，立即执行证书检查任务")
    run_certificate_check()
    
    while True:
        try:
            # 计算下次运行时间
            next_run_time = calculate_next_run_time()
            
            # 计算睡眠时间
            sleep_seconds = (next_run_time - datetime.now()).total_seconds()
            
            if sleep_seconds > 0:
                logger.info(f"下次运行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} "
                           f"(约 {sleep_seconds/3600:.1f} 小后)")
                
                # 分段睡眠，每分钟检查一次是否需要提前执行
                while sleep_seconds > 0:
                    # 每次最多睡眠60秒
                    sleep_chunk = min(sleep_seconds, 60)
                    time.sleep(sleep_chunk)
                    sleep_seconds -= sleep_chunk
                    
                    # 重新检查下次运行时间，以防有变化
                    new_next_run_time = calculate_next_run_time()
                    if new_next_run_time < next_run_time:
                        logger.info("检测到新的下次运行时间，更新计划")
                        next_run_time = new_next_run_time
                        break
                
                # 执行任务
                run_certificate_check()
            else:
                # 如果计算出的时间已经过去，立即执行
                logger.warning("计划的执行时间已过，立即执行任务")
                run_certificate_check()
                # 等待一段时间再继续循环
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在退出...")
            break
        except Exception as e:
            logger.error(f"主循环中发生异常: {e}")
            # 发生异常时等待一段时间再继续
            time.sleep(60)

if __name__ == "__main__":
    main()