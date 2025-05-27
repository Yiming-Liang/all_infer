# 通用推理框架 (Universal Inference Framework)

一个简单易用的通用推理框架，支持用户通过配置文件和自定义处理器快速进行各种推理实验。

## 🌟 核心特性

### 解耦式处理架构
框架采用完全解耦的设计，将推理逻辑和数据预处理，构建prompt逻辑以及后处理逻辑分开。：

1. **预处理阶段**：数据验证、清洗、格式转换等预备工作，对应yaml文件processor.pre_process函数列表设置
2. **Prompt构建阶段**：根据配置模板构建推理输入，支持数据扩展和任务分解，对应processor.build_prompt函数
3. **推理阶段**：框架自动执行批量推理（支持多轮rollout），对应data.rollout_num=n，多轮推理结果自动保存为 `{response_field}_0`, `{response_field}_1`, ..., `{response_field}_{n-1}` 格式
4. **后处理阶段**：结果提取、聚合、统计分析等后续处理,对应processor.post_process函数列表设置

每个阶段都可以配置多个处理函数，按顺序执行，实现细粒度的流程控制。

### 测试与采样控制
- **`data.num_samples`**：控制测试推理的样本数量，便于快速验证和调试
- **完整数据处理**：设置为 `null` 时处理全部数据

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
- **InferenceEngine**: 执行推理的核心引擎，支持批量推理和多轮rollout

#### `runner.py`
- **Runner**: 整个推理流程的控制器
  - 配置文件加载（支持YAML/JSON）
  - 动态处理器加载
  - 数据读取/保存（支持JSON/JSONL）
  - 流程编排（预处理 → prompt构建 → 推理 → 后处理）
  - **多轮推理执行**: 支持 `rollout_num=n` 配置，自动管理多轮推理结果
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
- **多轮推理配置**: 通过 `inference.rollout_num` 控制推理轮数

### 3. 模块化设计
- 核心功能与用户代码分离
- 处理器可独立开发和测试
- **配置驱动**: prompt模板、数据路径等都通过配置文件管理
- 易于维护和扩展
- **细粒度控制**: 可以将复杂的处理逻辑拆分为多个小函数
- **解耦式架构**: 预处理、prompt构建、后处理完全独立

### 4. 高性能推理
- 基于vLLM实现高效推理
- 支持批量处理
- 支持多GPU并行
- **多轮推理优化**: 自动管理多轮推理的内存和计算资源

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
  rollout_num: 3                          # 多轮推理：生成3个不同的响应

# 数据处理
data:
  input_file: "datas/your_data.json"
  output_file: "results/output.json"
  original_field: "原始数据字段"
  prompt_field: "prompt字段"
  response_field: "response字段"
  num_samples: 32                         # 测试时只处理32个样本

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
  post_process: ["extract_answers", "aggregate_rollouts", "calculate_metrics"]  # 多个后处理函数
```

**多轮推理说明**：
- 设置 `rollout_num: 3` 会对每个输入生成3个不同的响应
- 结果会保存为 `response字段_0`, `response字段_1`, `response字段_2`
- 后处理函数 `aggregate_rollouts` 可以聚合多轮结果，选择最佳答案或计算一致性

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
- **多轮推理配置**: `inference.rollout_num` 设置推理轮数

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

# 运行多轮推理示例
bash examples/run_infer.sh configs/experiments/my_experiment.yaml
```

4. **创建自己的实验**

### 方法1：使用简单模板（推荐新手）

```bash
# 复制简单模板
cp configs/experiments/template.yaml configs/experiments/my_simple_exp.yaml
cp processors/template_processor.py processors/my_simple_processor.py

# 修改配置文件中的prompt和数据路径
vim configs/experiments/my_simple_exp.yaml

# 设置测试模式（处理少量数据）
# 在配置文件中设置: data.num_samples: 10

# 运行简单实验
bash examples/run_infer.sh configs/experiments/my_simple_exp.yaml
```

**简单模板特点**：
- 只需要3个函数：`validate_data`, `build_prompt`, `extract_answer`
- 直接对问题进行推理，无复杂处理逻辑
- 适合基础的问答、文本生成等任务
- 支持多轮推理：设置 `rollout_num > 1` 生成多个候选答案

### 方法2：使用复杂模板（适合高级用户）

```bash
# 复制复杂示例
cp processors/checklist_processor.py processors/my_processor.py
cp configs/experiments/checklist_check.yaml configs/experiments/my_exp.yaml

# 修改处理逻辑和配置（支持多函数列表）
vim processors/my_processor.py    # 修改处理逻辑
vim configs/experiments/my_exp.yaml  # 修改配置和prompt模板

# 设置多轮推理和测试模式
# 在配置文件中设置:
# inference.rollout_num: 5    # 生成5个不同的响应
# data.num_samples: 20        # 只处理20个样本进行测试

# 将数据文件放入datas目录
cp your_data.json datas/

# 运行自定义实验
bash examples/run_infer.sh configs/experiments/my_exp.yaml
```

**复杂模板特点**：
- 支持多个预处理和后处理函数
- 适合需要复杂数据处理的任务
- 支持结构化结果提取和统计分析
- **多轮推理聚合**：可以将多轮推理结果进行聚合分析
- **数据扩展**：一个样本可以扩展为多个评估任务

### 多轮推理最佳实践

1. **测试阶段**：
   ```yaml
   inference:
     rollout_num: 3              # 少量轮次测试
   data:
     num_samples: 10             # 少量样本测试
   ```

2. **正式运行**：
   ```yaml
   inference:
     rollout_num: 8              # 更多轮次获得多样性
   data:
     num_samples: null           # 处理全部数据
   ```

3. **后处理聚合**：
   ```python
   def aggregate_rollouts(data, config):
       """聚合多轮推理结果"""
       for item in data:
           # 收集所有rollout结果
           responses = []
           for i in range(config['inference']['rollout_num']):
               field_name = f"{config['data']['response_field']}_{i}"
               if field_name in item:
                   responses.append(item[field_name])
           
           # 进行聚合处理（选择最佳、计算一致性等）
           item['aggregated_result'] = process_multiple_responses(responses)
       return data
   ```

## 🔄 解耦式处理流程详解

### 预处理阶段 (Pre-processing)
**功能**：对原始数据进行预备处理，为后续推理做准备

**典型处理函数**：
- `validate_data`: 验证数据完整性和格式
- `clean_data`: 清洗数据，去除重复和空内容
- `normalize_data`: 数据标准化和格式转换
- `filter_samples`: 根据条件过滤样本

**参数配置**：
```yaml
processor:
  pre_process: ["validate_data", "clean_data", "normalize_data"]  # 按顺序执行
```

**数据流**：原始数据 → 预处理函数列表 → 清洗后的数据

### Prompt构建阶段 (Prompt Building)
**功能**：根据配置模板构建推理输入，支持数据扩展和任务分解

**核心特性**：
- **模板驱动**：从 `config['prompts']` 读取prompt模板
- **数据扩展**：一个样本可以扩展为多个推理任务（如checklist评分）
- **字段映射**：灵活的输入输出字段配置
- **嵌套字段支持**：支持 `extra_info.question` 等嵌套字段访问

**典型处理函数**：
- `build_prompt`: 基础prompt构建
- `build_evaluation_prompt`: 评估任务prompt构建
- `expand_checklist_tasks`: 将checklist扩展为多个评估任务

**参数配置**：
```yaml
data:
  original_field: "extra_info.question"    # 原始数据字段
  prompt_field: "prompt"                   # 构建的prompt字段
  response_field: "response"               # 推理结果字段

prompts:
  task_template: |                         # Prompt模板
    请分析以下问题：{question}
    要求：{requirements}

processor:
  build_prompt: "build_prompt"             # 单个构建函数
```

**数据流**：清洗后的数据 → prompt构建函数 → 带prompt的推理任务

### 推理阶段 (Inference)
**功能**：框架自动执行的批量推理，支持多轮rollout

**核心参数**：
```yaml
inference:
  rollout_num: 8                          # 多轮推理次数
  batch_size: 32                          # 批处理大小
  max_tokens: 5120                        # 最大生成token数
  temperature: 0.1                        # 采样温度
  top_p: 0.9                             # 核采样参数

data:
  num_samples: 32                         # 测试样本数（null为全部）
```

**多轮推理机制**：
- 对每个输入执行 `rollout_num` 次推理
- 结果保存为 `{response_field}_0`, `{response_field}_1`, ..., `{response_field}_{n-1}`
- 自动管理内存和计算资源

### 后处理阶段 (Post-processing)
**功能**：对推理结果进行提取、聚合、分析等后续处理

**典型处理函数**：
- `extract_results`: 从响应中提取结构化结果
- `aggregate_scores`: 聚合多轮推理的评分结果
- `compute_statistics`: 计算统计指标
- `save_analysis`: 保存分析报告

**多轮推理处理**：
- **自动字段发现**：自动识别 `{response_field}_{i}` 格式的多轮结果
- **结果聚合**：将多轮结果聚合为最终评估
- **统计分析**：计算平均值、最大值、一致性等指标

**参数配置**：
```yaml
processor:
  post_process: ["extract_results", "aggregate_scores", "compute_statistics"]
```

**数据流**：推理结果 → 后处理函数列表 → 最终分析结果

## 📋 配置文件参数详解

### 推理配置参数

| 参数类别 | 参数名 | 说明 | 示例值 | 备注 |
|---------|--------|------|--------|------|
| **多轮推理** | rollout_num | 推理轮数 | `8` | 默认为1，支持多轮推理 |
| **批处理** | batch_size | 批处理大小 | `32` | 影响推理速度和内存使用 |
| **生成控制** | max_tokens | 最大生成token数 | `5120` | 控制输出长度 |
| **采样参数** | temperature | 采样温度 | `0.1` | 控制输出随机性 |
| **采样参数** | top_p | 核采样参数 | `0.9` | 控制输出多样性 |

### 数据配置参数

| 参数类别 | 参数名 | 说明 | 示例值 | 备注 |
|---------|--------|------|--------|------|
| **测试控制** | num_samples | 测试样本数 | `32` | null为全部数据 |
| **文件路径** | input_file | 输入文件路径 | `datas/input.json` | 支持JSON/JSONL |
| **文件路径** | output_file | 输出文件路径 | `results/output.json` | 自动创建目录 |
| **字段映射** | original_field | 原始数据字段 | `extra_info.question` | 支持嵌套字段 |
| **字段映射** | prompt_field | prompt字段 | `prompt` | 构建的推理输入 |
| **字段映射** | response_field | 响应字段 | `response` | 推理结果基础字段名 |

### 处理器配置参数

| 参数类别 | 参数名 | 说明 | 示例值 | 备注 |
|---------|--------|------|--------|------|
| **模块加载** | module | 处理器模块路径 | `processors.my_processor` | Python模块路径 |
| **预处理** | pre_process | 预处理函数列表 | `["validate", "clean"]` | 按顺序执行 |
| **Prompt构建** | build_prompt | prompt构建函数 | `"build_prompt"` | 单个函数名 |
| **后处理** | post_process | 后处理函数列表 | `["extract", "analyze"]` | 按顺序执行 |

### 多轮推理结果字段命名

当设置 `rollout_num=n` 时，推理结果会保存为：
- `{response_field}_0`: 第1轮推理结果
- `{response_field}_1`: 第2轮推理结果
- ...
- `{response_field}_{n-1}`: 第n轮推理结果

例如，配置 `response_field: "qwen_response"` 和 `rollout_num: 3` 时，会生成：
- `qwen_response_0`
- `qwen_response_1` 
- `qwen_response_2`

## 🔍 注意事项

1. **数据格式**: 支持JSON和JSONL格式，框架会自动识别
2. **配置格式**: 支持YAML和JSON格式的配置文件
3. **Prompt配置**: 所有prompt模板都在配置文件的`prompts`部分定义
4. **处理器命名**: 处理器模块名要与文件名保持一致
5. **函数命名**: 函数名必须与配置文件中的名称完全一致
6. **函数签名**: 所有处理函数必须接受(data, config)两个参数
7. **数据传递**: 函数列表中的每个函数输出会作为下一个函数的输入
8. **Prompt变量**: prompt模板中的变量名要与数据字段名匹配
9. **多轮推理**: 后处理函数需要能够处理多个 `{response_field}_{i}` 字段
10. **测试配置**: 使用 `data.num_samples` 进行小规模测试，验证流程正确性

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个框架！

## 📄 许可证

[MIT License](LICENSE)