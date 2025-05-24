# 简单推理处理器模板
# 最基础的问答推理处理逻辑

def validate_data(data, config):
    """数据验证函数"""
    print("执行数据验证...")
    valid_data = []
    
    original_field = config['data']['original_field']
    
    for item in data:
        # 检查是否包含问题字段
        if original_field in item and item[original_field]:
            valid_data.append(item)
        else:
            print(f"警告: 数据项缺少问题字段 '{original_field}': {item}")
    
    print(f"数据验证完成: {len(valid_data)}/{len(data)} 条数据有效")
    return valid_data

def build_prompt(data, config):
    """构建prompt函数"""
    print("构建prompt...")
    
    original_field = config['data']['original_field']
    prompt_field = config['data']['prompt_field']
    
    # 从配置文件读取prompt模板
    prompt_template = config['prompts']['simple_qa']
    
    for item in data:
        # 使用模板构建prompt
        item[prompt_field] = prompt_template.format(**{original_field: item[original_field]})
    
    print("Prompt构建完成")
    return data

def extract_answer(data, config):
    """提取答案函数"""
    print("提取推理结果...")
    
    response_field = config['data']['response_field']
    
    for item in data:
        if response_field in item:
            # 简单清理答案（去除前后空白）
            item['cleaned_answer'] = item[response_field].strip()
            
            # 记录答案长度等基本信息
            item['answer_length'] = len(item['cleaned_answer'])
            item['has_answer'] = len(item['cleaned_answer']) > 0
    
    # 简单统计
    total_count = len(data)
    answered_count = sum(1 for item in data if item.get('has_answer', False))
    
    print(f"结果提取完成: {answered_count}/{total_count} 条有效回答")
    return data 