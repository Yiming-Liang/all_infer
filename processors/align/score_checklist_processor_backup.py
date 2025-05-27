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


def build_prompt(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """根据checklist扩展数据，为每个checklist项创建单独的评估任务"""
    
    # 获取配置
    checklist_field = config['data']['original_field']  # "extra_info.check_list"
    prompt_field = config['data']['prompt_field']
    response_field = config['data']['response_field']
    
    # 获取评估模板
    evaluation_template = config['prompts']['evaluation_template']
    
    expanded_data = []
    total_checklist_items = 0
    skipped_samples = 0
    
    for original_idx, item in enumerate(data):
        # 获取checklist
        checklist = _get_nested_field(item, checklist_field)
        
        if not checklist or not isinstance(checklist, list):
            print(f"警告: 样本 {original_idx} 没有有效的checklist，跳过")
            skipped_samples += 1
            continue
        
        # 获取原始问题和回答
        # 从之前的推理结果中获取问题和回答
        original_question = _get_nested_field(item, "extra_info.question")
        
        # 构建正确的模型回答字段名：从 "qwen25_7B_Instruct_check_response" 变为 "qwen25_7B_Instruct_response"
        # response_field 是类似 "qwen25_7B_Instruct_check_response" 的格式
        # 我们需要获取之前qa步骤的结果，字段名是去掉"_check"的版本
        if "_check_response" in response_field:
            qa_response_field = response_field.replace("_check_response", "_response")
        else:
            qa_response_field = response_field
            
        model_response = item.get(qa_response_field)
        
        if not original_question:
            print(f"警告: 样本 {original_idx} 缺少原始问题")
            skipped_samples += 1
            continue
            
        if not model_response:
            print(f"警告: 样本 {original_idx} 缺少模型回答，字段: {qa_response_field}")
            skipped_samples += 1
            continue
        
        # 为每个checklist项创建单独的评估任务
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
                'checklist_index': checklist_idx,
                'criterion': criterion,
                'total_checklist_items': len(checklist),
                'original_question': original_question,
                'model_response': model_response,
                'qa_response_field': qa_response_field
            }
            
            expanded_data.append(expanded_item)
            total_checklist_items += 1
    
    valid_samples = len(data) - skipped_samples
    avg_checklist_per_sample = total_checklist_items / valid_samples if valid_samples > 0 else 0
    
    print(f"Prompt构建完成:")
    print(f"  输入样本: {len(data)}")
    print(f"  有效样本: {valid_samples}")  
    print(f"  跳过样本: {skipped_samples}")
    print(f"  生成评估任务: {len(expanded_data)}")
    print(f"  平均每样本checklist项: {avg_checklist_per_sample:.1f}")
    
    return expanded_data


def extract_score(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从评估响应中提取分数并聚合回原始样本格式"""
    
    response_field = config['data']['response_field']
    score_pattern = config['prompts']['score_extraction_pattern']
    
    # 步骤1: 从每个response中提取分数
    extraction_stats = {
        'total_evaluations': len(data),
        'successful_extractions': 0,
        'failed_extractions': 0,
        'pattern_matches': 0,
        'fallback_matches': 0
    }
    
    for item in data:
        response_text = item.get(response_field, "")
        extracted_score, method = _extract_single_score_with_method(
            response_text, score_pattern, default_score=0.0
        )
        
        item['_extracted_score'] = extracted_score
        item['_extraction_method'] = method
        
        # 更新统计
        if extracted_score > 0:
            extraction_stats['successful_extractions'] += 1
            if method == 'pattern_match':
                extraction_stats['pattern_matches'] += 1
            elif method == 'number_fallback':
                extraction_stats['fallback_matches'] += 1
        else:
            extraction_stats['failed_extractions'] += 1
    
    # 步骤2: 按原始样本聚合结果
    grouped_results = {}
    for item in data:
        if '_meta' not in item:
            continue
            
        original_idx = item['_meta']['original_sample_index']
        if original_idx not in grouped_results:
            grouped_results[original_idx] = []
        grouped_results[original_idx].append(item)
    
    # 步骤3: 构建最终结果
    aggregated_data = []
    for original_idx in sorted(grouped_results.keys()):
        items = grouped_results[original_idx]
        
        # 取第一个item作为基础
        base_item = items[0].copy()
        
        # 清理临时字段
        for key in ['_meta', '_extracted_score', '_extraction_method']:
            if key in base_item:
                del base_item[key]
        
        # 聚合所有checklist的评估结果
        checklist_scores = []
        score_details = []
        
        for item in items:
            score_info = {
                'criterion': item['_meta']['criterion'],
                'checklist_index': item['_meta']['checklist_index'],
                'score': item['_extracted_score'],
                'extraction_method': item['_extraction_method'],
                'evaluation_response': item.get(response_field, ''),
                # 'evaluation_prompt': item.get(config['data']['prompt_field'], '')
            }
            score_details.append(score_info)
            checklist_scores.append(item['_extracted_score'])
        
        # 计算汇总统计
        total_score = sum(checklist_scores)
        avg_score = total_score / len(checklist_scores) if checklist_scores else 0.0
        pass_count = sum(1 for score in checklist_scores if score >= 0.5)
        pass_rate = pass_count / len(checklist_scores) if checklist_scores else 0.0
        
        # 添加评分结果到原始样本
        base_item['checklist_evaluation'] = {
            'scores': checklist_scores,  # 分数列表 [0.0, 1.0, 0.0, ...]
            'total_items': len(checklist_scores),
            'total_score': total_score,
            'average_score': avg_score,
            'pass_count': pass_count,
            'pass_rate': pass_rate,
            'details': score_details
        }
        
        aggregated_data.append(base_item)
    
    # 打印统计信息
    print(f"分数提取统计:")
    print(f"  总评估数: {extraction_stats['total_evaluations']}")
    print(f"  成功提取: {extraction_stats['successful_extractions']}")
    print(f"  模式匹配: {extraction_stats['pattern_matches']}")
    print(f"  数字回退: {extraction_stats['fallback_matches']}")
    print(f"  提取失败: {extraction_stats['failed_extractions']}")
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
        marked_matches = list(re.finditer(pattern, text))
        if marked_matches:
            # 获取最后一个匹配
            last_match = marked_matches[-1]
            # 确定哪个捕获组匹配了
            for j in range(1, 4):
                if last_match.group(j):
                    score_text = last_match.group(j)
                    method = 'pattern_match'
                    break
    
    # 策略2: 如果没有找到特殊标记，查找独立的0-1数字  
    if not score_text:
        numbers = []
        # 专门寻找0或1（因为评估模板规定只能是0或1）
        matches = re.finditer(r'(?:^|\s|[^\w.-])([01])(?!\d)', text)
        for match in matches:
            numbers.append(match.group(1))
        
        # 使用最后一个找到的数字（通常在结论处）
        if numbers:
            score_text = numbers[-1]
            method = 'number_fallback'
    
    # 策略3: 转换为最终分数
    if score_text:
        try:
            score = float(score_text)
            # 确保分数在0~1范围内
            return max(0.0, min(1.0, score)), method
        except (ValueError, TypeError):
            return default_score, 'default_used'
    else:
        return default_score, 'default_used'
