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


def build_prompt(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    为每个样本构建effectlist评估prompt
    一个样本对应一个prompt（不像checklist那样扩展）
    """
    print("开始构建effectlist评估prompt...")
    
    # 获取配置
    effectlist_field = config['data']['original_field']  # "extra_info.effect_list"
    prompt_field = config['data']['prompt_field']
    response_field = config['data']['response_field']
    
    # 获取评估模板
    evaluation_template = config['prompts']['evaluation_template']
    
    processed_data = []
    skipped_samples = 0
    
    for idx, item in enumerate(data):
        # 获取effectlist
        effectlist = _get_nested_field(item, effectlist_field)
        
        if not effectlist or not isinstance(effectlist, list):
            print(f"警告: 样本 {idx} 没有有效的effectlist，跳过")
            skipped_samples += 1
            continue
        
        # 获取原始问题和回答
        original_question = _get_nested_field(item, "extra_info.question")
        
        # 构建正确的模型回答字段名
        if "_effect_response" in response_field:
            qa_response_field = response_field.replace("_effect_response", "_response")
        else:
            qa_response_field = response_field
            
        model_response = item.get(qa_response_field)
        
        if not original_question:
            print(f"警告: 样本 {idx} 缺少原始问题")
            skipped_samples += 1
            continue
            
        if not model_response:
            print(f"警告: 样本 {idx} 缺少模型回答，字段: {qa_response_field}")
            skipped_samples += 1
            continue
        
        # 格式化effectlist为numbered criteria list
        criteria_list = _format_effectlist_to_criteria(effectlist)
        
        # 构建评估prompt
        prompt = evaluation_template.format(
            criteria_list=criteria_list,
            prompt=original_question,
            response=model_response
        )
        
        # 复制item并添加prompt
        processed_item = item.copy()
        processed_item[prompt_field] = prompt
        
        # 添加元信息用于后续处理
        processed_item['_effectlist_meta'] = {
            'original_index': idx,
            'effectlist_count': len(effectlist),
            'criteria_list': criteria_list,
            'original_question': original_question,
            'model_response': model_response,
            'qa_response_field': qa_response_field
        }
        
        processed_data.append(processed_item)
    
    valid_samples = len(data) - skipped_samples
    
    print(f"Effectlist prompt构建完成:")
    print(f"  输入样本: {len(data)}")
    print(f"  有效样本: {valid_samples}")
    print(f"  跳过样本: {skipped_samples}")
    print(f"  生成评估任务: {len(processed_data)}")
    
    return processed_data


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
    从effectlist评估响应中提取分数
    """
    print("开始提取effectlist分数...")
    
    response_field = config['data']['response_field']
    score_pattern = config['prompts']['effect_score_extraction_pattern']
    
    # 分数提取统计
    extraction_stats = {
        'total_evaluations': len(data),
        'successful_extractions': 0,
        'failed_extractions': 0,
        'pattern_matches': 0,
        'fallback_matches': 0,
        'score_distribution': {}
    }
    
    for item in data:
        response_text = item.get(response_field, "")
        extracted_score, method = _extract_effect_score_with_method(
            response_text, score_pattern, default_score=0.0
        )
        
        # 添加effectlist评估结果
        item['effectlist_evaluation'] = {
            'raw_score': extracted_score * 10,  # 原始0-10分数
            'normalized_score': extracted_score,  # 归一化0-1分数  
            'extraction_method': method,
            'criteria_count': item.get('_effectlist_meta', {}).get('effectlist_count', 0),
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
        
        # 分数分布统计
        score_key = f"{extracted_score:.1f}"
        extraction_stats['score_distribution'][score_key] = extraction_stats['score_distribution'].get(score_key, 0) + 1
        
        # 清理临时元信息
        if '_effectlist_meta' in item:
            del item['_effectlist_meta']
    
    # 打印统计信息
    print(f"Effectlist分数提取统计:")
    print(f"  总评估数: {extraction_stats['total_evaluations']}")
    print(f"  成功提取: {extraction_stats['successful_extractions']}")
    print(f"  模式匹配: {extraction_stats['pattern_matches']}")
    print(f"  数字回退: {extraction_stats['fallback_matches']}")
    print(f"  提取失败: {extraction_stats['failed_extractions']}")
    
    return data


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


def compute_weighted_score(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    计算加权最终分数
    final_score = checklist_score * effectlist_score
    """
    print("开始计算加权分数...")
    
    computed_scores = 0
    
    for item in data:
        # 获取checklist评估结果
        checklist_eval = item.get('checklist_evaluation', {})
        checklist_scores = checklist_eval.get('scores', [])
        
        # 获取effectlist评估结果
        effectlist_eval = item.get('effectlist_evaluation', {})
        effectlist_score = effectlist_eval.get('normalized_score', 0.0)
        
        # 计算checklist_score: 全为1才为1，否则为0
        if checklist_scores and all(score == 1.0 for score in checklist_scores):
            checklist_score = 1.0
        else:
            checklist_score = 0.0
        
        # 计算最终分数
        final_score = checklist_score * effectlist_score
        
        # 添加分数计算结果
        item['final_evaluation'] = {
            'checklist_score': checklist_score,
            'effectlist_score': effectlist_score,
            'final_score': final_score,
            'checklist_all_passed': checklist_score == 1.0,
            'checklist_pass_count': checklist_eval.get('pass_count', 0),
            'checklist_total_items': checklist_eval.get('total_items', 0),
            'effectlist_criteria_count': effectlist_eval.get('criteria_count', 0)
        }
        
        computed_scores += 1
    
    print(f"加权分数计算完成: {computed_scores} 个样本")
    
    return data


def compute_all_final_avg_score(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    计算所有样本的final_score平均分，并打印全局统计信息
    """
    print("开始计算全局平均分...")
    
    final_scores = []
    checklist_scores = []
    effectlist_scores = []
    checklist_pass_counts = []
    
    # 收集所有分数
    for item in data:
        final_eval = item.get('final_evaluation', {})
        
        final_score = final_eval.get('final_score', 0.0)
        checklist_score = final_eval.get('checklist_score', 0.0)
        effectlist_score = final_eval.get('effectlist_score', 0.0)
        checklist_all_passed = final_eval.get('checklist_all_passed', False)
        
        final_scores.append(final_score)
        checklist_scores.append(checklist_score)
        effectlist_scores.append(effectlist_score)
        checklist_pass_counts.append(1 if checklist_all_passed else 0)
    
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
        
        # 打印详细统计信息
        print("="*60)
        print("全局评分统计结果")
        print("="*60)
        print(f"总样本数: {total_samples}")
        print(f"平均final_score: {avg_final_score:.4f}")
        print(f"平均checklist_score: {avg_checklist_score:.4f}")
        print(f"平均effectlist_score: {avg_effectlist_score:.4f}")
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
        
        print("="*60)
    else:
        print("警告: 没有有效样本进行统计")
    
    return data
