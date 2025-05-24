# 通用推理框架 (Universal Inference Framework)

一个简单易用的通用推理框架，支持用户通过配置文件和自定义处理器快速进行各种推理实验。

## 📁 项目结构

```
all_infer/
├── core/                          # 核心功能模块（用户无需修改）
│   ├── __init__.py
│   ├── infer.py                   # 推理核心逻辑（模型管理、推理引擎）
│   └── runner.py                  # 运行器（流程控制、数据加载）
├── configs/experiments/           # 实验配置目录
│   └── checklist_check.yaml       # 示例配置文件
├── processors/                    # 用户自定义处理逻辑
│   ├── __init__.py
│   └── checklist_processor.py     # 示例处理器
├── examples/                      # 示例脚本目录
│   ├── run_infer.sh              # 通用推理脚本
│   ├── run_checklist_infer.sh    # 清单检查专用脚本
│   └── README.md                 # 脚本使用说明
├── datas/                         # 示例数据目录
│   └── sample_data.json          # 示例数据文件
├── utils/                         # 工具函数
│   ├── __init__.py
│   └── logger.py                 # 简化的日志工具
├── logs/                          # 日志文件目录（自动创建）
├── results/                       # 推理结果目录（自动创建）
├── main.py                        # 主入口文件
├── requirements.txt               # 项目依赖
└── README.md                      # 项目说明文档
```

## 🔧 模块说明

### 核心模块 (core/)

#### `infer.py`
- **ModelManager**: 负责模型加载和管理
- **InferenceEngine**: 执行推理的核心引擎

#### `runner.py`
- **Runner**: 整个推理流程的控制器
  - 配置文件加载（支持YAML/JSON）
  - 动态处理器加载
  - 数据读取/保存（支持JSON/JSONL）
  - 流程编排（预处理 → prompt构建 → 推理 → 后处理）
  - **函数列表执行**: 支持按顺序执行多个处理函数

### 工具模块 (utils/)

#### `logger.py`
- 简化的日志配置，支持控制台和文件输出
- 自动过滤vLLM冗余日志

### 用户自定义模块 (processors/)

用户可以在这个目录下创建自己的处理器文件，实现多个具体的处理函数：

- **预处理函数**: 多个预处理步骤函数（如数据验证、清洗等）
- **prompt构建函数**: 从配置文件读取prompt模板，进行数据填充
- **后处理函数**: 多个后处理步骤函数（如结果提取、统计分析等）

#### 函数签名规范
```python
def function_name(data, config):
    """
    处理函数模板
    
    Args:
        data: 输入数据（列表格式）
        config: 配置字典（包含prompt模板等所有配置信息）
    
    Returns:
        处理后的数据（列表格式）
    """
    # 可以从config['prompts']中读取prompt模板
    # prompt_template = config['prompts']['your_prompt_name']
    return data
```

## ✨ 框架特点

### 1. 简单易用
- 用户只需创建**两个文件**：处理器文件 + 配置文件
- **Prompt模板配置化**: 所有prompt都在YAML中配置，无需修改代码
- 核心推理逻辑已封装，无需重复编写
- 支持多种数据格式（JSON/JSONL）
- 支持多种配置格式（YAML/JSON）

### 2. 灵活配置
- 所有参数通过YAML文件配置（包括prompt模板）
- 支持不同模型和推理参数
- 动态加载用户自定义处理器
- **支持函数列表**: 预处理和后处理可配置多个函数，按顺序执行

### 3. 模块化设计
- 核心功能与用户代码分离
- 处理器可独立开发和测试
- **配置驱动**: prompt模板、数据路径等都通过配置文件管理
- 易于维护和扩展
- **细粒度控制**: 可以将复杂的处理逻辑拆分为多个小函数

### 4. 高性能推理
- 基于vLLM实现高效推理
- 支持批量处理
- 支持多GPU并行

## 🚀 使用方式

### 方法1：使用推理脚本（推荐）

```bash
# 使用通用推理脚本
bash examples/run_infer.sh configs/experiments/checklist_check.yaml

# 或者使用专用脚本
bash examples/run_checklist_infer.sh
```

### 方法2：手动步骤

#### 步骤1：创建处理器文件

在`processors/`目录下创建你的处理器文件，例如`my_processor.py`：

```python
# 预处理函数列表
def validate_input(data, config):
    """验证输入数据"""
    # 验证逻辑
    return data

def normalize_data(data, config):
    """数据标准化"""
    # 标准化逻辑
    return data

# prompt构建函数
def build_prompt(data, config):
    """构建prompt - 从配置文件读取模板"""
    prompt_field = config['data']['prompt_field']
    
    # 从配置文件读取prompt模板
    prompt_template = config['prompts']['my_task']
    
    for item in data:
        # 使用模板填充数据
        item[prompt_field] = prompt_template.format(**item)
    return data

# 后处理函数列表
def extract_answers(data, config):
    """提取答案"""
    # 答案提取逻辑
    return data

def calculate_metrics(data, config):
    """计算指标"""
    # 指标计算逻辑
    return data
```

#### 步骤2：创建配置文件

在`configs/experiments/`目录下创建配置文件，例如`my_experiment.yaml`：

```yaml
# 实验基本信息
name: "my_experiment"
description: "实验描述"

# 模型配置
model:
  name: "qwen25"
  path: "/path/to/your/model"
  tensor_parallel_size: 8
  gpu_memory_utilization: 0.9
  trust_remote_code: true

# 推理参数
inference:
  max_tokens: 5120
  batch_size: 32
  temperature: 0.1
  top_p: 0.9

# 数据处理
data:
  input_file: "datas/your_data.json"
  output_file: "results/output.json"
  original_field: "原始数据字段"
  prompt_field: "prompt字段"
  response_field: "response字段"

# Prompt模板配置
prompts:
  my_task: |
    请基于以下信息进行分析：
    
    输入数据：{input_data}
    
    任务要求：
    1. 分析数据特点
    2. 给出结论
    3. 提供建议
    
    请按照以下格式回答：
    [分析结果]：你的分析
    [结论]：你的结论
    [建议]：你的建议

# 处理器配置（支持函数列表）
processor:
  module: "processors.my_processor"
  pre_process: ["validate_input", "normalize_data"]  # 多个预处理函数
  build_prompt: "build_prompt"                       # 单个prompt构建函数
  post_process: ["extract_answers", "calculate_metrics"]  # 多个后处理函数
```

#### 步骤3：运行推理

```bash
python main.py --config configs/experiments/my_experiment.yaml
```

## 📝 示例文件说明

### `processors/checklist_processor.py`
示例处理器，演示如何：
- **预处理函数列表**:
  - `validate_data`: 验证数据完整性和格式
  - `clean_data`: 清洗数据，去除重复和空内容
- **prompt构建函数**:
  - `build_prompt`: 从配置文件读取prompt模板，构建结构化的证明步骤检查prompt
- **后处理函数列表**:
  - `extract_results`: 从响应中提取结构化结果
  - `save_statistics`: 生成和保存统计信息

### `configs/experiments/checklist_check.yaml`
示例配置文件，展示：
- 完整的配置项结构
- 模型和推理参数设置
- 数据路径和字段配置
- **Prompt模板配置**: 在`prompts`部分定义所有prompt模板
- **函数列表配置**: 预处理和后处理的多函数配置

### `datas/sample_data.json`
示例数据文件，包含：
- 3个数学证明题样本
- 标准的数据格式
- 清单检查所需的字段结构

## 🏃‍♂️ 快速开始

1. **克隆项目**
```bash
git clone <repository>
cd all_infer
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **运行示例**
```bash
# 运行复杂示例（清单检查）
bash examples/run_checklist_infer.sh

# 运行简单示例（问答推理）
bash examples/run_simple_qa.sh
```

4. **创建自己的实验**

### 方法1：使用简单模板（推荐新手）

```bash
# 复制简单模板
cp configs/experiments/template.yaml configs/experiments/my_simple_exp.yaml
cp processors/template_processor.py processors/my_simple_processor.py

# 修改配置文件中的prompt和数据路径
vim configs/experiments/my_simple_exp.yaml

# 运行简单实验
bash examples/run_infer.sh configs/experiments/my_simple_exp.yaml
```

**简单模板特点**：
- 只需要3个函数：`validate_data`, `build_prompt`, `extract_answer`
- 直接对问题进行推理，无复杂处理逻辑
- 适合基础的问答、文本生成等任务

### 方法2：使用复杂模板（适合高级用户）

```bash
# 复制复杂示例
cp processors/checklist_processor.py processors/my_processor.py
cp configs/experiments/checklist_check.yaml configs/experiments/my_exp.yaml

# 修改处理逻辑和配置（支持多函数列表）
vim processors/my_processor.py    # 修改处理逻辑
vim configs/experiments/my_exp.yaml  # 修改配置和prompt模板

# 将数据文件放入datas目录
cp your_data.json datas/

# 运行自定义实验
bash examples/run_infer.sh configs/experiments/my_exp.yaml
```

**复杂模板特点**：
- 支持多个预处理和后处理函数
- 适合需要复杂数据处理的任务
- 支持结构化结果提取和统计分析

## 📋 配置文件参数说明

### 基本配置参数

| 参数类别 | 参数名 | 说明 | 示例值 |
|---------|--------|------|--------|
| model | path | 模型路径 | `/path/to/model` |
| model | tensor_parallel_size | 并行GPU数量 | `8` |
| model | gpu_memory_utilization | GPU内存利用率 | `0.9` |
| inference | max_tokens | 最大生成token数 | `5120` |
| inference | batch_size | 批处理大小 | `32` |
| inference | temperature | 采样温度 | `0.1` |
| data | input_file | 输入文件路径 | `datas/input.json` |
| data | output_file | 输出文件路径 | `results/output.json` |
| processor | module | 处理器模块路径 | `processors.my_processor` |
| processor | pre_process | 预处理函数列表 | `["func1", "func2"]` |
| processor | build_prompt | prompt构建函数 | `"build_prompt"` |
| processor | post_process | 后处理函数列表 | `["func3", "func4"]` |

### Prompt配置说明

在配置文件的`prompts`部分可以定义多个prompt模板：

```yaml
prompts:
  task1: |
    这是任务1的prompt模板
    数据：{data_field}
    
  task2: |
    这是任务2的prompt模板
    输入：{input_field}
    要求：{requirement_field}
```

**Prompt模板特点**：
- 使用Python的`str.format()`语法
- 支持多行文本（使用`|`符号）
- 可以引用数据中的任何字段
- 处理器函数通过`config['prompts']['template_name']`访问

## 🔄 函数列表执行流程

框架按以下顺序执行处理函数：

1. **预处理阶段**: 按配置列表顺序执行预处理函数
2. **prompt构建阶段**: 从配置文件读取prompt模板，执行prompt构建函数
3. **推理阶段**: 框架自动执行批量推理
4. **后处理阶段**: 按配置列表顺序执行后处理函数

## 🔍 注意事项

1. **数据格式**: 支持JSON和JSONL格式，框架会自动识别
2. **配置格式**: 支持YAML和JSON格式的配置文件
3. **Prompt配置**: 所有prompt模板都在配置文件的`prompts`部分定义
4. **处理器命名**: 处理器模块名要与文件名保持一致
5. **函数命名**: 函数名必须与配置文件中的名称完全一致
6. **函数签名**: 所有处理函数必须接受(data, config)两个参数
7. **数据传递**: 函数列表中的每个函数输出会作为下一个函数的输入
8. **Prompt变量**: prompt模板中的变量名要与数据字段名匹配

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个框架！

## 📄 许可证

[MIT License](LICENSE)