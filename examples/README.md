# 推理脚本使用说明

## 📁 文件说明

- `run_infer.sh`: 通用推理脚本，可用于任何配置文件
- `run_checklist_infer.sh`: 清单检查专用脚本（复杂示例）
- `run_simple_qa.sh`: 简单问答推理脚本（简单示例）

## 🚀 使用方法

### 1. 运行示例实验

```bash
# 方法1: 使用通用脚本
bash examples/run_infer.sh configs/experiments/checklist_check.yaml

# 方法2: 使用复杂示例脚本（清单检查）
bash examples/run_checklist_infer.sh

# 方法3: 使用简单示例脚本（问答推理）
bash examples/run_simple_qa.sh
```

### 2. 创建自定义实验

#### 简单实验（推荐新手）

```bash
# 复制简单模板
cp configs/experiments/template.yaml configs/experiments/my_simple_exp.yaml
cp processors/template_processor.py processors/my_simple_processor.py

# 修改配置文件
vim configs/experiments/my_simple_exp.yaml
```

修改要点：
```yaml
# 修改基本信息
name: "my_simple_experiment"
description: "我的简单实验"

# 修改数据路径
data:
  input_file: "datas/my_questions.json"
  output_file: "results/my_answers.json"

# 修改简单的prompt
prompts:
  simple_qa: |
    请回答以下问题：
    
    问题：{question}
    
    回答：
```

```bash
# 运行简单实验
bash examples/run_infer.sh configs/experiments/my_simple_exp.yaml
```

#### 复杂实验（高级用户）

```bash
# 复制复杂模板
cp processors/checklist_processor.py processors/my_processor.py
cp configs/experiments/checklist_check.yaml configs/experiments/my_exp.yaml

# 修改处理逻辑和配置
vim processors/my_processor.py
vim configs/experiments/my_exp.yaml

# 运行复杂实验
bash examples/run_infer.sh configs/experiments/my_exp.yaml
```

## 📋 脚本参数说明

### `run_infer.sh`

```bash
Usage: bash examples/run_infer.sh <config_file>

Arguments:
  config_file: 配置文件路径 (必需)

Example:
  bash examples/run_infer.sh configs/experiments/my_exp.yaml
```

### `run_checklist_infer.sh`

```bash
Usage: bash examples/run_checklist_infer.sh

# 该脚本使用固定配置文件: configs/experiments/checklist_check.yaml
```

## ✨ 关键特性

### 1. Prompt模板配置化

**旧方式（硬编码）**：
```python
# 不推荐：prompt写在代码里
def build_prompt(data, config):
    for item in data:
        item['prompt'] = f"请分析：{item['text']}"
```

**新方式（配置化）**：
```yaml
# 推荐：prompt写在配置文件里
prompts:
  analysis_task: |
    请分析以下内容：
    
    内容：{text}
    维度：{dimensions}
    
    分析结果：
    [结论]：你的结论
    [建议]：你的建议
```

```python
# 推荐：从配置读取prompt
def build_prompt(data, config):
    prompt_template = config['prompts']['analysis_task']
    for item in data:
        item['prompt'] = prompt_template.format(**item)
```

### 2. 多Prompt支持

你可以在一个配置文件中定义多个prompt模板：

```yaml
prompts:
  task1: "第一个任务的prompt: {data}"
  task2: "第二个任务的prompt: {content}"
  task3: |
    第三个任务的复杂prompt:
    输入：{input}
    要求：
    1. 分析
    2. 总结
```

然后在处理器中根据条件选择：

```python
def build_prompt(data, config):
    for item in data:
        if item['type'] == 'analysis':
            template = config['prompts']['task1']
        elif item['type'] == 'summary':
            template = config['prompts']['task2']
        else:
            template = config['prompts']['task3']
        
        item['prompt'] = template.format(**item)
```

### 3. 便捷的实验管理

- **配置驱动**: 修改prompt无需改代码，只需改YAML
- **版本控制**: 不同的配置文件对应不同的实验版本
- **快速迭代**: 复制模板文件即可快速创建新实验

## 🔧 常见使用场景

### 场景1：prompt迭代优化

```bash
# 创建多个配置文件测试不同prompt
cp configs/experiments/template.yaml configs/experiments/prompt_v1.yaml
cp configs/experiments/template.yaml configs/experiments/prompt_v2.yaml
cp configs/experiments/template.yaml configs/experiments/prompt_v3.yaml

# 分别修改各自的prompt模板，然后对比效果
bash examples/run_infer.sh configs/experiments/prompt_v1.yaml
bash examples/run_infer.sh configs/experiments/prompt_v2.yaml
bash examples/run_infer.sh configs/experiments/prompt_v3.yaml
```

### 场景2：多任务实验

```yaml
# 在一个配置文件中定义多个任务的prompt
prompts:
  classification: "分类任务prompt: {text}"
  generation: "生成任务prompt: {context}"
  evaluation: "评估任务prompt: {content}"
```

### 场景3：A/B测试

```bash
# 创建两个只有prompt不同的配置文件
cp configs/experiments/template.yaml configs/experiments/version_a.yaml
cp configs/experiments/template.yaml configs/experiments/version_b.yaml

# 运行对比实验
bash examples/run_infer.sh configs/experiments/version_a.yaml
bash examples/run_infer.sh configs/experiments/version_b.yaml
```

## 📝 最佳实践

1. **模板复用**: 使用模板文件作为起点，避免从零开始
2. **命名规范**: 配置文件和处理器使用有意义的命名
3. **版本管理**: 为不同版本的prompt创建不同的配置文件
4. **文档记录**: 在配置文件中使用注释记录实验目的和变更
5. **测试验证**: 修改prompt后使用小样本测试验证效果

## 📊 示例数据

项目的 `datas/` 目录包含示例数据文件：

- `sample_data.json`: 包含3个数学证明题的清单检查样本

## 📝 脚本功能

### `run_infer.sh` 功能特点：
- ✅ 参数验证：检查配置文件是否存在
- ✅ 路径自动检测：自动获取项目根目录
- ✅ 目录创建：自动创建输出目录
- ✅ 执行时间统计：显示推理耗时
- ✅ 错误处理：执行失败时给出错误提示

### `run_checklist_infer.sh` 功能特点：
- ✅ 预设配置：专门针对清单检查任务
- ✅ 文件验证：检查配置文件和处理器文件是否存在
- ✅ 友好输出：详细的执行状态提示

## 💡 使用提示

1. **确保在项目根目录执行脚本**：脚本会自动处理路径问题
2. **修改配置文件**：根据需要修改 `configs/experiments/` 中的配置文件
3. **准备数据文件**：将您的数据文件放在 `datas/` 目录中
4. **查看结果**：推理结果会保存在 `results/` 目录中

## 🔧 自定义脚本

您可以参考现有脚本创建自己的推理脚本：

```bash
# 复制模板
cp examples/run_infer.sh examples/my_task.sh

# 修改脚本中的配置文件路径和任务名称
vim examples/my_task.sh

# 添加执行权限
chmod +x examples/my_task.sh

# 运行自定义脚本
bash examples/my_task.sh
``` 