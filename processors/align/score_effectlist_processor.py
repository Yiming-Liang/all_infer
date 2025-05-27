# Effectlist评分处理器
# 专门处理effectlist评分任务的推理流程

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
        base_response_field: 基础response字段名，如 "qwen25_7B_Instruct_effect_response"
    
    Returns:
        Dict[int, str]: {index: field_name} 映射
    """
    # 从base_response_field提取模型名
    # 例如："qwen25_7B_Instruct_effect_response" -> "qwen25_7B_Instruct"
    if "_effect_response" in base_response_field:
        model_name = base_response_field.replace("_effect_response", "")
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
    """
    为每个样本的每个response构建effectlist评估prompt
    一个样本的每个response对应一个prompt
    """
    print("开始构建effectlist评估prompt...")
    
    # 获取配置
    effectlist_field = config['data']['original_field']  # "extra_info.effect_list"
    prompt_field = config['data']['prompt_field']
    response_field = config['data']['response_field']
    
    # 获取评估模板
    evaluation_template = config['prompts']['evaluation_template']
    
    expanded_data = []
    total_evaluation_tasks = 0
    skipped_samples = 0
    
    for original_idx, item in enumerate(data):
        # 获取effectlist
        effectlist = _get_nested_field(item, effectlist_field)
        
        if not effectlist or not isinstance(effectlist, list):
            print(f"警告: 样本 {original_idx} 没有有效的effectlist，跳过")
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
        
        print(f"样本 {original_idx}: 找到 {len(response_fields)} 个responses, effectlist包含 {len(effectlist)} 个criteria")
        
        # 格式化effectlist为numbered criteria list
        criteria_list = _format_effectlist_to_criteria(effectlist)
        
        # 为每个response创建评估任务
        for response_idx in sorted(response_fields.keys()):
            response_field_name = response_fields[response_idx]
            model_response = item.get(response_field_name)
            
            if not model_response:
                print(f"警告: 样本 {original_idx} response {response_idx} 为空，跳过")
                continue
            
            # 复制原始数据
            expanded_item = item.copy()
            
            # 构建评估prompt
            prompt = evaluation_template.format(
                criteria_list=criteria_list,
                prompt=original_question,
                response=model_response
            )
            
            expanded_item[prompt_field] = prompt
            
            # 添加元信息用于后续聚合
            expanded_item['_effectlist_meta'] = {
                'original_sample_index': original_idx,
                'response_index': response_idx,
                'response_field': response_field_name,
                'effectlist_count': len(effectlist),
                'criteria_list': criteria_list,
                'original_question': original_question,
                'model_response': model_response
            }
            
            expanded_data.append(expanded_item)
            total_evaluation_tasks += 1
    
    valid_samples = len(data) - skipped_samples
    avg_tasks_per_sample = total_evaluation_tasks / valid_samples if valid_samples > 0 else 0
    
    print(f"Effectlist prompt构建完成:")
    print(f"  输入样本: {len(data)}")
    print(f"  有效样本: {valid_samples}")
    print(f"  跳过样本: {skipped_samples}")
    print(f"  生成评估任务: {len(expanded_data)}")
    print(f"  平均每样本评估任务: {avg_tasks_per_sample:.1f}")
    
    return expanded_data


def _format_effectlist_to_criteria(effectlist: List[str]) -> str:
    """
    将effectlist格式化为numbered criteria list
    例如: ['effect1', 'effect2'] -> "1. effect1\n2. effect2"
    """
    formatted_items = []
    for i, effect in enumerate(effectlist, 1):
        formatted_items.append(f"{i}. {effect}")
    
    return "\n".join(formatted_items)


def extract_score(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从effectlist评估响应中提取分数并聚合回原始样本格式
    """
    print("开始提取effectlist分数...")
    
    # 步骤1: 提取每个评估任务的分数
    data_with_scores = extract_individual_scores(data, config)
    
    # 步骤2: 聚合结果
    aggregated_data = aggregate_evaluation_results(data_with_scores, config)
    
    return aggregated_data


def extract_individual_scores(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从每个评估任务的推理结果中提取分数"""
    
    base_response_field = config['data']['response_field']  # 基础字段名
    score_pattern = config['prompts']['effect_score_extraction_pattern']
    
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
            # 搜索所有包含 effect_response 的字段
            for key in data[0].keys():
                if 'effect_response' in key and key.endswith('_0'):
                    actual_response_field = key
                    break
    
    if not actual_response_field:
        print(f"错误：找不到推理结果字段！期望: {base_response_field}")
        return data
    
    print(f"使用推理结果字段: {actual_response_field}")
    
    # 分数提取统计
    extraction_stats = {
        'total_evaluations': len(data),
        'successful_extractions': 0,
        'failed_extractions': 0,
        'pattern_matches': 0,
        'fallback_matches': 0,
        'empty_responses': 0
    }
    
    for item in data:
        response_text = item.get(actual_response_field, "")
        
        if not response_text:
            extraction_stats['empty_responses'] += 1
            extracted_score, method = 0.0, 'empty_response'
        else:
            extracted_score, method = _extract_effect_score_with_method(
                response_text, score_pattern, default_score=0.0
            )
        
        # 添加单个评估任务的结果
        item['_individual_score'] = {
            'raw_score': extracted_score * 10,  # 原始0-10分数
            'normalized_score': extracted_score,  # 归一化0-1分数  
            'extraction_method': method,
            'evaluation_response': response_text
        }
        
        # 更新统计
        if extracted_score > 0:
            extraction_stats['successful_extractions'] += 1
            if method == 'pattern_match':
                extraction_stats['pattern_matches'] += 1
            elif method == 'number_fallback':
                extraction_stats['fallback_matches'] += 1
        else:
            extraction_stats['failed_extractions'] += 1
    
    # 打印统计信息
    print(f"Effectlist分数提取统计:")
    print(f"  总评估数: {extraction_stats['total_evaluations']}")
    print(f"  成功提取: {extraction_stats['successful_extractions']}")
    print(f"  模式匹配: {extraction_stats['pattern_matches']}")
    print(f"  数字回退: {extraction_stats['fallback_matches']}")
    print(f"  空响应: {extraction_stats['empty_responses']}")
    print(f"  提取失败: {extraction_stats['failed_extractions']}")
    
    return data


def aggregate_evaluation_results(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """将多个response的评估结果聚合回原始样本格式"""
    
    print("开始聚合effectlist评估结果...")
    
    # 按原始样本索引分组
    sample_groups = {}
    for item in data:
        meta = item.get('_effectlist_meta', {})
        original_idx = meta.get('original_sample_index')
        
        if original_idx is not None:
            if original_idx not in sample_groups:
                sample_groups[original_idx] = []
            sample_groups[original_idx].append(item)
    
    # 重建原始样本格式
    aggregated_data = []
    
    for original_idx in sorted(sample_groups.keys()):
        group_items = sample_groups[original_idx]
        
        # 使用第一个item作为基础（去除扩展的字段）
        base_item = group_items[0].copy()
        
        # 清理扩展字段
        fields_to_remove = ['_effectlist_meta', '_individual_score']
        for field in fields_to_remove:
            if field in base_item:
                del base_item[field]
        
        # 聚合所有response的评估结果
        effectlist_evaluations = {}
        
        for item in group_items:
            meta = item.get('_effectlist_meta', {})
            individual_score = item.get('_individual_score', {})
            
            response_idx = meta.get('response_index')
            response_field = meta.get('response_field')
            
            if response_idx is not None:
                effectlist_evaluations[f"response_{response_idx}"] = {
                    'response_field': response_field,
                    'raw_score': individual_score.get('raw_score', 0.0),
                    'normalized_score': individual_score.get('normalized_score', 0.0),
                    'extraction_method': individual_score.get('extraction_method', 'default_used'),
                    'criteria_count': meta.get('effectlist_count', 0),
                    'evaluation_response': individual_score.get('evaluation_response', '')
                }
        
        # 计算统计信息
        scores = [eval_result['normalized_score'] for eval_result in effectlist_evaluations.values()]
        
        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
        else:
            avg_score = max_score = min_score = 0.0
        
        # 添加聚合的effectlist评估结果
        base_item['effectlist_evaluations'] = effectlist_evaluations
        base_item['effectlist_summary'] = {
            'total_responses': len(effectlist_evaluations),
            'avg_score': avg_score,
            'max_score': max_score,
            'min_score': min_score,
            'criteria_count': group_items[0].get('_effectlist_meta', {}).get('effectlist_count', 0)
        }
        
        aggregated_data.append(base_item)
    
    print(f"Effectlist结果聚合完成:")
    print(f"  聚合样本数: {len(aggregated_data)}")
    print(f"  原始评估任务数: {len(data)}")
    
    return aggregated_data


def _extract_effect_score_with_method(text: str, pattern: str, default_score: float = 0.0) -> tuple[float, str]:
    """
    从单个文本中提取effectlist分数（0-10范围），返回归一化分数(0-1)和提取方法
    """
    score_text = None
    method = 'default_used'
    
    # 策略1: 查找特殊标记内的数字 [SCORE=5], boxed{7}, Score: 3
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
    
    # 策略2: 如果没有找到特殊标记，查找独立的0-10数字
    if not score_text:
        numbers = []
        # 匹配0-10之间的数字（包括小数）
        matches = re.finditer(r'(?:^|\s|[^\w.-])(-?\d+(?:\.\d+)?|\d+\.\d+)(?!\d)', text)
        for match in matches:
            try:
                num = float(match.group(1))
                if 0 <= num <= 10:  # 只接受0-10之间的数字
                    numbers.append(match.group(1))
            except ValueError:
                continue
        
        # 使用第一个找到的数字
        if numbers:
            score_text = numbers[0]
            method = 'number_fallback'
    
    # 策略3: 转换为最终分数
    if score_text:
        try:
            score = float(score_text)
            # 确保分数在0~10范围内，然后归一化到0~1
            clamped_score = max(0.0, min(10.0, score))
            normalized_score = clamped_score / 10.0
            return normalized_score, method
        except (ValueError, TypeError):
            return default_score, 'default_used'
    else:
        return default_score, 'default_used'


def _find_checklist_evaluation_fields(item: Dict[str, Any]) -> Dict[int, str]:
    """
    自动发现所有 checklist_evaluation_{i} 字段
    
    Returns:
        Dict[int, str]: {index: field_name} 映射
    """
    pattern = r"checklist_evaluation_(\d+)"
    
    checklist_fields = {}
    for key in item.keys():
        match = re.match(pattern, key)
        if match:
            index = int(match.group(1))
            checklist_fields[index] = key
    
    return checklist_fields


def _compute_max_checklist_score(item: Dict[str, Any]) -> float:
    """计算所有response中checklist_score的最大值"""
    # 自动发现所有checklist_evaluation_{i}字段
    checklist_fields = _find_checklist_evaluation_fields(item)
    
    if not checklist_fields:
        # 兼容旧格式
        checklist_eval = item.get('checklist_evaluation', {})
        if checklist_eval:
            scores = checklist_eval.get('scores', [])
            return 1.0 if (scores and all(score == 1.0 for score in scores)) else 0.0
        return 0.0
    
    # 计算每个response的checklist_score
    checklist_scores = []
    for idx in sorted(checklist_fields.keys()):
        field_name = checklist_fields[idx]
        checklist_eval = item.get(field_name, {})
        scores = checklist_eval.get('scores', [])
        
        # 判断该response是否全部通过
        if scores and all(score == 1.0 for score in scores):
            checklist_scores.append(1.0)
        else:
            checklist_scores.append(0.0)
    
    # 返回最大值
    return max(checklist_scores) if checklist_scores else 0.0


def _compute_max_effectlist_score(item: Dict[str, Any]) -> float:
    """计算所有response中effectlist_score的最大值"""
    # 方案1：使用summary中的max_score（推荐）
    effectlist_summary = item.get('effectlist_summary', {})
    if 'max_score' in effectlist_summary:
        return effectlist_summary['max_score']
    
    # 方案2：从evaluations重新计算（备用）
    effectlist_evaluations = item.get('effectlist_evaluations', {})
    if effectlist_evaluations:
        all_scores = [eval_result.get('normalized_score', 0.0) 
                     for eval_result in effectlist_evaluations.values()]
        return max(all_scores) if all_scores else 0.0
    
    # 方案3：兼容旧格式（向后兼容）
    effectlist_eval = item.get('effectlist_evaluation', {})
    if effectlist_eval:
        return effectlist_eval.get('normalized_score', 0.0)
    
    return 0.0


def compute_weighted_score(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    计算加权最终分数
    final_score = max(checklist_scores) * max(effectlist_scores)
    支持多rollout的情况，同时兼容单rollout
    """
    print("开始计算加权分数...")
    
    computed_scores = 0
    
    for item in data:
        # 1. 计算checklist_score（取所有response中的最大值）
        checklist_score = _compute_max_checklist_score(item)
        
        # 2. 计算effectlist_score（取所有response中的最大值）
        effectlist_score = _compute_max_effectlist_score(item)
        
        # 3. 计算最终分数
        final_score = checklist_score * effectlist_score
        
        # 4. 收集统计信息
        checklist_fields = _find_checklist_evaluation_fields(item)
        effectlist_summary = item.get('effectlist_summary', {})
        
        # 计算checklist统计信息
        total_checklist_items = 0
        total_pass_count = 0
        if checklist_fields:
            for field_name in checklist_fields.values():
                checklist_eval = item.get(field_name, {})
                total_checklist_items = max(total_checklist_items, checklist_eval.get('total_items', 0))
                total_pass_count += checklist_eval.get('pass_count', 0)
        else:
            # 兼容旧格式
            checklist_eval = item.get('checklist_evaluation', {})
            total_checklist_items = checklist_eval.get('total_items', 0)
            total_pass_count = checklist_eval.get('pass_count', 0)
        
        # 5. 添加分数计算结果
        item['final_evaluation'] = {
            'checklist_score': checklist_score,
            'effectlist_score': effectlist_score,
            'final_score': final_score,
            'checklist_all_passed': checklist_score == 1.0,
            'checklist_pass_count': total_pass_count,
            'checklist_total_items': total_checklist_items,
            'effectlist_criteria_count': effectlist_summary.get('criteria_count', 0),
            'effectlist_responses_count': effectlist_summary.get('total_responses', len(checklist_fields) if checklist_fields else 1),
            'total_rollouts': len(checklist_fields) if checklist_fields else 1
        }
        
        computed_scores += 1
    
    print(f"加权分数计算完成: {computed_scores} 个样本")
    print(f"  使用最大值策略: checklist_score和effectlist_score都取所有response中的最大值")
    
    return data


def compute_all_final_avg_score(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    计算所有样本的final_score平均分，并打印全局统计信息
    支持多rollout的统计
    """
    print("开始计算全局平均分...")
    
    final_scores = []
    checklist_scores = []
    effectlist_scores = []
    checklist_pass_counts = []
    total_rollouts_list = []
    
    # 收集所有分数
    for item in data:
        final_eval = item.get('final_evaluation', {})
        
        final_score = final_eval.get('final_score', 0.0)
        checklist_score = final_eval.get('checklist_score', 0.0)
        effectlist_score = final_eval.get('effectlist_score', 0.0)
        checklist_all_passed = final_eval.get('checklist_all_passed', False)
        total_rollouts = final_eval.get('total_rollouts', 1)
        
        final_scores.append(final_score)
        checklist_scores.append(checklist_score)
        effectlist_scores.append(effectlist_score)
        checklist_pass_counts.append(1 if checklist_all_passed else 0)
        total_rollouts_list.append(total_rollouts)
    
    # 计算统计信息
    total_samples = len(data)
    
    if total_samples > 0:
        avg_final_score = sum(final_scores) / total_samples
        avg_checklist_score = sum(checklist_scores) / total_samples
        avg_effectlist_score = sum(effectlist_scores) / total_samples
        checklist_pass_rate = sum(checklist_pass_counts) / total_samples
        
        # 计算分数分布
        final_score_distribution = {}
        for score in final_scores:
            score_key = f"{score:.1f}"
            final_score_distribution[score_key] = final_score_distribution.get(score_key, 0) + 1
        
        # 计算多rollout统计
        total_responses = sum(item.get('final_evaluation', {}).get('effectlist_responses_count', 0) for item in data)
        avg_responses_per_sample = total_responses / total_samples if total_samples > 0 else 0
        total_rollouts_all = sum(total_rollouts_list)
        avg_rollouts_per_sample = total_rollouts_all / total_samples if total_samples > 0 else 0
        max_rollouts = max(total_rollouts_list) if total_rollouts_list else 0
        min_rollouts = min(total_rollouts_list) if total_rollouts_list else 0
        
        # 打印详细统计信息
        print("="*60)
        print("全局评分统计结果")
        print("="*60)
        print(f"总样本数: {total_samples}")
        print(f"总response数: {total_responses}")
        print(f"总rollout数: {total_rollouts_all}")
        print(f"平均每样本response数: {avg_responses_per_sample:.1f}")
        print(f"平均每样本rollout数: {avg_rollouts_per_sample:.1f}")
        print(f"rollout数范围: {min_rollouts} - {max_rollouts}")
        print(f"平均final_score: {avg_final_score:.4f}")
        print(f"平均checklist_score: {avg_checklist_score:.4f} (最大值策略)")
        print(f"平均effectlist_score: {avg_effectlist_score:.4f} (最大值策略)")
        print(f"checklist通过率: {checklist_pass_rate:.2%}")
        print(f"checklist通过数量: {sum(checklist_pass_counts)}/{total_samples}")
        
        print(f"\n分数范围:")
        print(f"  final_score: {min(final_scores):.3f} - {max(final_scores):.3f}")
        print(f"  checklist_score: {min(checklist_scores):.3f} - {max(checklist_scores):.3f}")
        print(f"  effectlist_score: {min(effectlist_scores):.3f} - {max(effectlist_scores):.3f}")
        
        print(f"\nfinal_score分布:")
        for score_key in sorted(final_score_distribution.keys(), key=lambda x: float(x)):
            count = final_score_distribution[score_key]
            percentage = count / total_samples * 100
            print(f"  {score_key}: {count} 样本 ({percentage:.1f}%)")
        
        print("\n评分策略说明:")
        print("  - checklist_score: 取所有rollout中的最大值 (任一rollout全部通过即为1.0)")
        print("  - effectlist_score: 取所有rollout中的最大值")
        print("  - final_score = checklist_score * effectlist_score")
        
        print("="*60)
    else:
        print("警告: 没有有效样本进行统计")
    
    return data
