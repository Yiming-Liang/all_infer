import logging
import re
import sys
import warnings
from pathlib import Path
from datetime import datetime

# 过滤掉vllm版本相关的警告
warnings.filterwarnings("ignore", message="Failed to read commit hash")

class VllmProcessFilter(logging.Filter):
    """过滤vLLM进程相关的日志信息"""
    def filter(self, record):
        if re.search(r'\(VllmWorkerProcess pid=\d+\)', record.getMessage()):
            return False
        if 'VllmWorkerProcess' in record.getMessage():
            return False
        return True

def setup_logging(log_file=None):
    """
    简单的日志配置
    
    Args:
        log_file: 可选的日志文件路径
    """
    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        stream=sys.stdout
    )
    
    # 添加vLLM过滤器
    logger = logging.getLogger()
    vllm_filter = VllmProcessFilter()
    for handler in logger.handlers:
        handler.addFilter(vllm_filter)
    
    # 过滤vllm的日志
    vllm_logger = logging.getLogger('vllm')
    vllm_logger.addFilter(vllm_filter)
    
    # 如果需要日志文件
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        file_handler.addFilter(vllm_filter)
        logger.addHandler(file_handler)
    
    return logger

def get_log_file(experiment_name):
    """生成日志文件路径"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if experiment_name:
        log_filename = f"{experiment_name}_{timestamp}.log"
    else:
        log_filename = f"inference_{timestamp}.log"
    return f"logs/{log_filename}" 