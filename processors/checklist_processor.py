# 预处理函数列表

def validate_data(data, config):
    """数据验证函数"""
    print("执行数据验证...")
    valid_data = []
    for item in data:
        # 检查必要字段是否存在
        if 'extra_info' in item and 'check_list' in item['extra_info']:
            if isinstance(item['extra_info']['check_list'], list) and len(item['extra_info']['check_list']) > 0:
                valid_data.append(item)
            else:
                print(f"警告: 数据项 {item.get('id', '未知')} 的check_list为空或格式错误")
        else:
            print(f"警告: 数据项 {item.get('id', '未知')} 缺少必要字段")
    
    print(f"数据验证完成: {len(valid_data)}/{len(data)} 条数据有效")
    return valid_data

def clean_data(data, config):
    """数据清洗函数"""
    print("执行数据清洗...")
    for item in data:
        # 清理check_list中的空字符串和重复项
        if 'extra_info' in item and 'check_list' in item['extra_info']:
            check_list = item['extra_info']['check_list']
            # 去除空字符串和只包含空白字符的项
            cleaned_list = [step.strip() for step in check_list if step.strip()]
            # 去除重复项，但保持顺序
            seen = set()
            unique_list = []
            for step in cleaned_list:
                if step not in seen:
                    seen.add(step)
                    unique_list.append(step)
            
            item['extra_info']['check_list'] = unique_list
    
    print("数据清洗完成")
    return data

# Prompt构建函数

def build_prompt(data, config):
    """构建prompt函数"""
    print("构建prompt...")
    original_field = config['data']['original_field']
    prompt_field = config['data']['prompt_field']
    
    # 从配置文件中读取prompt模板
    prompt_template = config['prompts']['checklist_check']
    
    for item in data:
        # 为每一步添加序号
        numbered_steps = []
        for i, step in enumerate(item['extra_info'][original_field], 0):
            numbered_steps.append(f"{i}. {step}")
        
        # 将带序号的步骤组合成字符串
        formatted_steps = '\n'.join(numbered_steps)
        
        # 构建最终的prompt
        item[prompt_field] = prompt_template.format(check_list=formatted_steps)
    
    print("Prompt构建完成")
    return data

# 后处理函数列表

def extract_results(data, config):
    """提取结果函数"""
    print("提取推理结果...")
    response_field = config['data']['response_field']
    
    for item in data:
        if response_field in item:
            response = item[response_field]
            
            # 提取评价结果
            evaluation_result = "未知"
            if "[评价结果：是]" in response:
                evaluation_result = "是"
            elif "[评价结果：否]" in response:
                evaluation_result = "否"
            
            # 提取问题步骤编号
            problem_steps = []
            import re
            step_pattern = r'不严格证明步骤：\[([0-9,\s]+)\]'
            match = re.search(step_pattern, response)
            if match:
                steps_str = match.group(1)
                problem_steps = [int(x.strip()) for x in steps_str.split(',') if x.strip().isdigit()]
            
            # 添加结构化结果
            item['structured_result'] = {
                'evaluation': evaluation_result,
                'problem_steps': problem_steps,
                'has_problems': evaluation_result == "是"
            }
    
    print("结果提取完成")
    return data

def save_statistics(data, config):
    """保存统计信息函数"""
    print("生成统计信息...")
    
    # 统计结果
    total_count = len(data)
    problem_count = sum(1 for item in data if item.get('structured_result', {}).get('has_problems', False))
    success_rate = (total_count - problem_count) / total_count * 100 if total_count > 0 else 0
    
    # 统计每种问题的出现次数
    all_problem_steps = []
    for item in data:
        if 'structured_result' in item:
            all_problem_steps.extend(item['structured_result'].get('problem_steps', []))
    
    from collections import Counter
    step_counter = Counter(all_problem_steps)
    
    # 保存统计信息
    statistics = {
        'total_samples': total_count,
        'samples_with_problems': problem_count,
        'samples_without_problems': total_count - problem_count,
        'success_rate': round(success_rate, 2),
        'most_common_problem_steps': step_counter.most_common(5) if step_counter else []
    }
    
    # 添加统计信息到每个数据项
    for item in data:
        item['experiment_statistics'] = statistics
    
    print(f"统计信息生成完成: 总样本数={total_count}, 有问题样本数={problem_count}, 成功率={success_rate:.1f}%")
    return data 