#!/bin/bash

# 清单检查推理脚本
# 使用说明：bash examples/run_checklist_infer.sh

echo "=========================================="
echo "开始执行清单检查推理任务"
echo "=========================================="

# 设置项目根目录
PROJECT_ROOT=$(dirname $(dirname $(realpath $0)))
echo "项目根目录: $PROJECT_ROOT"

# 进入项目根目录
cd $PROJECT_ROOT

# 检查配置文件是否存在
CONFIG_FILE="configs/experiments/checklist_check.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 配置文件 $CONFIG_FILE 不存在"
    exit 1
fi

# 检查处理器文件是否存在
PROCESSOR_FILE="processors/checklist_processor.py"
if [ ! -f "$PROCESSOR_FILE" ]; then
    echo "错误: 处理器文件 $PROCESSOR_FILE 不存在"
    exit 1
fi

# 创建输出目录
mkdir -p results

echo "配置文件: $CONFIG_FILE"
echo "处理器文件: $PROCESSOR_FILE"
echo "开始推理..."

# 执行推理
python main.py --config $CONFIG_FILE

# 检查执行结果
if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "推理任务执行成功！"
    echo "结果文件保存在 results/ 目录中"
    echo "=========================================="
else
    echo "=========================================="
    echo "推理任务执行失败！"
    echo "请检查配置文件和数据文件"
    echo "=========================================="
    exit 1
fi 