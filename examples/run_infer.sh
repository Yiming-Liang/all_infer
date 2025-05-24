#!/bin/bash

# 通用推理脚本
# 使用说明：bash examples/run_infer.sh <config_file>
# 示例：bash examples/run_infer.sh configs/experiments/checklist_check.yaml

# 检查参数
if [ $# -eq 0 ]; then
    echo "使用方法: bash examples/run_infer.sh <config_file>"
    echo "示例: bash examples/run_infer.sh configs/experiments/checklist_check.yaml"
    exit 1
fi

CONFIG_FILE=$1

echo "=========================================="
echo "开始执行推理任务"
echo "配置文件: $CONFIG_FILE"
echo "=========================================="

# 设置项目根目录
PROJECT_ROOT=$(dirname $(dirname $(realpath $0)))
echo "项目根目录: $PROJECT_ROOT"

# 进入项目根目录
cd $PROJECT_ROOT

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 配置文件 $CONFIG_FILE 不存在"
    exit 1
fi

# 创建输出目录
mkdir -p results

echo "开始推理..."

# 记录开始时间
start_time=$(date +%s)

# 执行推理
python main.py --config $CONFIG_FILE

# 检查执行结果
if [ $? -eq 0 ]; then
    # 计算执行时间
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    hours=$((duration / 3600))
    minutes=$(((duration % 3600) / 60))
    seconds=$((duration % 60))
    
    echo "=========================================="
    echo "推理任务执行成功！"
    printf "执行时间: %02d:%02d:%02d\n" $hours $minutes $seconds
    echo "结果文件保存在 results/ 目录中"
    echo "=========================================="
else
    echo "=========================================="
    echo "推理任务执行失败！"
    echo "请检查配置文件和数据文件"
    echo "=========================================="
    exit 1
fi 