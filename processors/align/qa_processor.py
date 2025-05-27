# QA推理处理器
# 专门处理问答任务的推理流程

from typing import List, Dict, Any

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
    构建prompt函数
    根据配置文件的prompt模板构建推理输入
    """
    print("构建prompt...")
    
    original_field = config['data']['original_field']
    prompt_field = config['data']['prompt_field']
    
    # 从配置文件读取prompt模板
    prompt_template = config['prompts']['checklist_check']
    
    for item in data:
        try:
            # 获取问题内容
            question = _get_nested_field(item, original_field)
            
            if not question:
                print(f"警告: 无法获取问题内容，字段: {original_field}")
                item[prompt_field] = ""
                continue
            
            # 使用模板构建prompt
            prompt = prompt_template.format(question=question)
            item[prompt_field] = prompt
            
        except Exception as e:
            print(f"错误: 构建prompt时出错: {e}")
            # 如果构建失败，设置为空prompt
            item[prompt_field] = ""
    
    print("Prompt构建完成")
    return data 