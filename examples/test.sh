#!/bin/bash

# 简单问答推理脚本
# 使用模板配置进行基础的问答推理

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📁 项目根目录: $PROJECT_ROOT"

# 切换到项目根目录
cd "$PROJECT_ROOT" || exit 1

# 配置文件路径
CONFIG_FILE="configs/experiments/test.yaml"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 错误: 配置文件 $CONFIG_FILE 不存在"
    exit 1
fi

# 检查处理器文件是否存在
PROCESSOR_FILE="processors/test_processor.py"
if [ ! -f "$PROCESSOR_FILE" ]; then
    echo "❌ 错误: 处理器文件 $PROCESSOR_FILE 不存在"
    exit 1
fi

# 检查示例数据文件是否存在
DATA_FILE="datas/questions.json"
if [ ! -f "$DATA_FILE" ]; then
    echo "❌ 错误: 数据文件 $DATA_FILE 不存在"
    exit 1
fi

echo "✅ 配置文件: $CONFIG_FILE"
echo "✅ 处理器文件: $PROCESSOR_FILE"
echo "✅ 数据文件: $DATA_FILE"

# 创建必要的目录
mkdir -p results
mkdir -p logs

echo ""
echo "🔧 开始执行推理..."
echo "配置: 简单问答推理"
echo "数据: $(jq length $DATA_FILE 2>/dev/null || echo "未知") 个问题"

# 记录开始时间
start_time=$(date +%s)

# 执行推理
python main.py --config "$CONFIG_FILE"

# 检查执行结果
if [ $? -eq 0 ]; then
    # 记录结束时间并计算耗时
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    echo "✅ 推理任务执行成功!"
    echo "⏱️  执行耗时: ${duration}秒"
    
    # 检查输出文件
    OUTPUT_FILE="results/answers.json"
    if [ -f "$OUTPUT_FILE" ]; then
        result_count=$(jq length "$OUTPUT_FILE" 2>/dev/null || echo "未知")
        echo "📄 输出文件: $OUTPUT_FILE"
        echo "📊 输出结果: $result_count 条"
        
        # 显示第一个结果样例
        echo "📝 结果样例:"
        jq '.[0] | {id, question, answer: (.answer // .response), cleaned_answer, answer_length}' "$OUTPUT_FILE" 2>/dev/null || echo "无法解析结果文件"
    else
        echo "⚠️  警告: 未找到输出文件 $OUTPUT_FILE"
    fi
else
    echo ""
    echo "❌ 推理任务执行失败!"
    echo "请检查日志信息排查问题。"
    exit 1
fi