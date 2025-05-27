# QA推理处理器
# 专门处理checklist评分任务的推理流程

from typing import List, Dict, Any
import re


def _get_nested_field(item: Dict[str, Any], field_path: str) -> Any:
    """
    获取嵌套字段的值
    支持类似 "extra_info.question" 的路径
    """
    if not field_path:
        return None
        
    fields = field_path.split('.')
    value = item
    
    for field in fields:
        if isinstance(value, dict) and field in value:
            value = value[field]
        else:
            return None
    
    return value


def _find_response_fields(item: Dict[str, Any], base_response_field: str) -> Dict[int, str]:
    """
    自动发现所有 {model_name}_response_{i} 字段
    
    Args:
        item: 数据项
        base_response_field: 基础response字段名，如 "qwen25_7B_Instruct_check_response"
    
    Returns:
        Dict[int, str]: {index: field_name} 映射
    """
    # 从base_response_field提取模型名
    # 例如："qwen25_7B_Instruct_check_response" -> "qwen25_7B_Instruct"
    if "_check_response" in base_response_field:
        model_name = base_response_field.replace("_check_response", "")
    else:
        model_name = base_response_field.replace("_response", "")
    
    # 构建匹配模式：{model_name}_response_{digits}
    pattern = f"{re.escape(model_name)}_response_(\\d+)"
    
    response_fields = {}
    for key in item.keys():
        match = re.match(pattern, key)
        if match:
            index = int(match.group(1))
            response_fields[index] = key
    
    return response_fields


def build_prompt(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """根据checklist扩展数据，为每个response和每个checklist项创建单独的评估任务"""
    
    # 获取配置
    checklist_field = config['data']['original_field']  # "extra_info.check_list"
    prompt_field = config['data']['prompt_field']
    response_field = config['data']['response_field']
    
    # 获取评估模板
    evaluation_template = config['prompts']['evaluation_template']
    
    expanded_data = []
    total_evaluation_tasks = 0
    skipped_samples = 0
    
    for original_idx, item in enumerate(data):
        # 获取checklist
        checklist = _get_nested_field(item, checklist_field)
        
        if not checklist or not isinstance(checklist, list):
            print(f"警告: 样本 {original_idx} 没有有效的checklist，跳过")
            skipped_samples += 1
            continue
        
        # 获取原始问题
        original_question = _get_nested_field(item, "extra_info.question")
        if not original_question:
            print(f"警告: 样本 {original_idx} 缺少原始问题")
            skipped_samples += 1
            continue
        
        # 自动发现所有response字段
        response_fields = _find_response_fields(item, response_field)
        
        if not response_fields:
            print(f"警告: 样本 {original_idx} 没有找到任何response字段")
            skipped_samples += 1
            continue
        
        print(f"样本 {original_idx}: 找到 {len(response_fields)} 个responses, {len(checklist)} 个checklist项")
        
        # 为每个response和每个checklist项创建评估任务
        for response_idx in sorted(response_fields.keys()):
            response_field_name = response_fields[response_idx]
            model_response = item.get(response_field_name)
            
            if not model_response:
                print(f"警告: 样本 {original_idx} response {response_idx} 为空，跳过")
                continue
            
            # 为当前response的每个checklist项创建评估任务
            for checklist_idx, criterion in enumerate(checklist):
                expanded_item = item.copy()  # 复制原始数据
                
                # 构建评估prompt
                prompt = evaluation_template.format(
                    criterion=criterion,
                    prompt=original_question,
                    response=model_response
                )
                
                expanded_item[prompt_field] = prompt
                
                # 添加跟踪信息，用于后续聚合
                expanded_item['_meta'] = {
                    'original_sample_index': original_idx,
                    'response_index': response_idx,
                    'response_field': response_field_name,
                    'checklist_index': checklist_idx,
                    'criterion': criterion,
                    'total_checklist_items': len(checklist),
                    'original_question': original_question,
                    'model_response': model_response
                }
                
                expanded_data.append(expanded_item)
                total_evaluation_tasks += 1
    
    valid_samples = len(data) - skipped_samples
    avg_tasks_per_sample = total_evaluation_tasks / valid_samples if valid_samples > 0 else 0
    
    print(f"Prompt构建完成:")
    print(f"  输入样本: {len(data)}")
    print(f"  有效样本: {valid_samples}")  
    print(f"  跳过样本: {skipped_samples}")
    print(f"  生成评估任务: {len(expanded_data)}")
    print(f"  平均每样本评估任务: {avg_tasks_per_sample:.1f}")
    
    return expanded_data


def extract_score(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从评估响应中提取分数并聚合回原始样本格式"""
    
    # 步骤1: 提取每个评估任务的分数
    data_with_scores = extract_individual_scores(data, config)
    
    # 步骤2: 聚合结果
    aggregated_data = aggregate_evaluation_results(data_with_scores, config)
    
    return aggregated_data


def extract_individual_scores(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从每个评估任务的推理结果中提取分数"""
    
    base_response_field = config['data']['response_field']  # 基础字段名
    score_pattern = config['prompts']['score_extraction_pattern']
    
    # 自动找到实际的推理结果字段
    # 因为runner中使用了rollout机制，实际字段名可能是 base_response_field_0
    actual_response_field = None
    if data:
        # 尝试原始字段名
        if base_response_field in data[0]:
            actual_response_field = base_response_field
        # 尝试加 _0 的字段名
        elif f"{base_response_field}_0" in data[0]:
            actual_response_field = f"{base_response_field}_0"
        else:
            # 搜索所有包含 check_response 的字段
            for key in data[0].keys():
                if 'check_response' in key and key.endswith('_0'):
                    actual_response_field = key
                    break
    
    if not actual_response_field:
        print(f"错误：找不到推理结果字段！期望: {base_response_field}")
        return data
    
    extraction_stats = {
        'total_evaluations': len(data),
        'successful_extractions': 0,
        'failed_extractions': 0,
        'pattern_matches': 0,
        'fallback_matches': 0,
        'empty_responses': 0
    }
    
    for i, item in enumerate(data):
        # 从实际字段中获取评分文本
        response_text = item.get(actual_response_field, "")
        
        if not response_text:
            extraction_stats['empty_responses'] += 1
        
        extracted_score, method = _extract_single_score_with_method(
            response_text, score_pattern, default_score=0.0
        )
        
        item['_extracted_score'] = extracted_score
        item['_extraction_method'] = method
        
        # 更新统计
        if method != 'default_used':
            extraction_stats['successful_extractions'] += 1
            if method == 'pattern_match':
                extraction_stats['pattern_matches'] += 1
            elif method == 'number_fallback':
                extraction_stats['fallback_matches'] += 1
        else:
            extraction_stats['failed_extractions'] += 1
    
    # 打印提取统计
    print(f"分数提取统计:")
    print(f"  总评估数: {extraction_stats['total_evaluations']}")
    print(f"  空响应数: {extraction_stats['empty_responses']}")
    print(f"  成功提取: {extraction_stats['successful_extractions']}")
    print(f"  模式匹配: {extraction_stats['pattern_matches']}")
    print(f"  数字回退: {extraction_stats['fallback_matches']}")
    print(f"  提取失败: {extraction_stats['failed_extractions']}")
    
    return data


def aggregate_evaluation_results(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """将提取的分数聚合成最终的评估结果"""
    
    # 按(原始样本, response)分组结果
    grouped_results = {}
    for item in data:
        if '_meta' not in item:
            continue
            
        original_idx = item['_meta']['original_sample_index']
        response_idx = item['_meta']['response_index']
        group_key = (original_idx, response_idx)
        
        if group_key not in grouped_results:
            grouped_results[group_key] = []
        grouped_results[group_key].append(item)
    
    # 按原始样本重新组织
    sample_results = {}
    for (original_idx, response_idx), items in grouped_results.items():
        if original_idx not in sample_results:
            sample_results[original_idx] = {}
        sample_results[original_idx][response_idx] = items
    
    # 构建最终结果
    aggregated_data = []
    for original_idx in sorted(sample_results.keys()):
        response_groups = sample_results[original_idx]
        
        # 取任意一个item作为基础
        first_response_idx = min(response_groups.keys())
        base_item = response_groups[first_response_idx][0].copy()
        
        # 清理临时字段
        for key in ['_meta', '_extracted_score', '_extraction_method']:
            if key in base_item:
                del base_item[key]
        
        # 为每个response生成评估结果
        for response_idx in sorted(response_groups.keys()):
            items = response_groups[response_idx]
            
            # 聚合当前response的所有checklist评估结果
            checklist_scores = []
            score_details = []
            
            for item in items:
                score_info = {
                    'criterion': item['_meta']['criterion'],
                    'checklist_index': item['_meta']['checklist_index'],
                    'score': item['_extracted_score'],
                    'extraction_method': item['_extraction_method'],
                    'evaluation_response': item.get(config['data']['response_field'], ''),
                }
                score_details.append(score_info)
                checklist_scores.append(item['_extracted_score'])
            
            # 计算汇总统计
            total_score = sum(checklist_scores)
            avg_score = total_score / len(checklist_scores) if checklist_scores else 0.0
            pass_count = sum(1 for score in checklist_scores if score >= 0.5)
            pass_rate = pass_count / len(checklist_scores) if checklist_scores else 0.0
            
            # 添加评分结果到原始样本
            evaluation_field = f'checklist_evaluation_{response_idx}'
            base_item[evaluation_field] = {
                'response_field': items[0]['_meta']['response_field'],
                'scores': checklist_scores,
                'total_items': len(checklist_scores),
                'total_score': total_score,
                'average_score': avg_score,
                'pass_count': pass_count,
                'pass_rate': pass_rate,
                'details': score_details
            }
        
        aggregated_data.append(base_item)
    
    print(f"聚合完成: {len(aggregated_data)} 个原始样本")
    return aggregated_data


def _extract_single_score_with_method(text: str, pattern: str, default_score: float = 0.0) -> tuple[float, str]:
    """
    从单个文本中提取分数，返回分数和提取方法
    """
    score_text = None
    method = 'default_used'
    
    # 策略1: 查找特殊标记内的数字 [SCORE=1], boxed{0}, Score: 1
    if pattern:
        try:
            import re
            marked_matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            if marked_matches:
                # 获取最后一个匹配
                last_match = marked_matches[-1]
                
                # 确定哪个捕获组匹配了
                for j in range(1, 4):
                    try:
                        if last_match.group(j):
                            score_text = last_match.group(j)
                            method = 'pattern_match'
                            break
                    except IndexError:
                        continue
        except re.error:
            pass
    
    # 策略2: 如果没有找到特殊标记，查找独立的0-1数字  
    if not score_text:
        numbers = []
        # 专门寻找0或1（因为评估模板规定只能是0或1）
        matches = re.finditer(r'(?:^|\s|[^\w.-])([01])(?!\d)', text)
        for match in matches:
            numbers.append(match.group(1))
        
        # 使用第一个找到的数字（通常在开头处）
        if numbers:
            score_text = numbers[0]
            method = 'number_fallback'
    
    # 策略3: 转换为最终分数
    if score_text:
        try:
            score = float(score_text)
            # 确保分数在0~1范围内
            final_score = max(0.0, min(1.0, score))
            return final_score, method
        except (ValueError, TypeError):
            return default_score, 'default_used'
    else:
        return default_score, 'default_used'


def average_max_score(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    计算所有样本的最大average_score的平均值
    
    对每个样本，从checklist_evaluation_0, checklist_evaluation_1, checklist_evaluation_2等字段中
    提取average_score，取最大值作为该样本的最终评分，然后计算所有样本的平均值
    """
    
    if not data:
        print("警告: 没有数据用于计算average_max_score")
        return data
    
    sample_max_scores = []
    
    for idx, item in enumerate(data):
        # 查找所有checklist_evaluation_*字段并提取average_score
        average_scores = []
        for key in item.keys():
            if key.startswith('checklist_evaluation_') and isinstance(item[key], dict):
                if 'average_score' in item[key]:
                    average_scores.append(item[key]['average_score'])
        
        if average_scores:
            # 取最大的average_score作为该样本的最终评分
            max_score = max(average_scores)
            sample_max_scores.append(max_score)
        else:
            print(f"警告: 样本 {idx} 没有找到有效的average_score")
    
    # 计算并打印结果
    if sample_max_scores:
        overall_average = sum(sample_max_scores) / len(sample_max_scores)
        print(f"\n=== Average Max Score 统计 ===")
        print(f"有效样本数: {len(sample_max_scores)}")
        print(f"所有样本最大average_score的平均值: {overall_average:.4f}")
    else:
        print("错误: 没有找到任何有效的样本评分")
    
    return data
