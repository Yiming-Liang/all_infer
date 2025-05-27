import importlib
import json
from pprint import pprint
import logging
from pathlib import Path
from .infer import ModelManager, InferenceEngine
from utils.logger import setup_logging, get_log_file

class Runner:
    def __init__(self, config):
        """
        初始化Runner
        config: 配置字典（已经由hydra解析好的）
        """
        self.config = config
        # pprint(self.config, indent=2, width=250, depth=None)
        self.processor = self._load_processor()
        self.model_manager = ModelManager(self.config)
        self.inference_engine = InferenceEngine(self.model_manager)
        
        # 设置日志
        experiment_name = self.config.get('name', 'unknown_experiment')
        log_file = get_log_file(experiment_name)
        self.logger = setup_logging(log_file)
        self.logger.info(f"推理日志已配置，日志文件: {log_file}")

    def _load_processor(self):
        """动态加载用户自定义的处理器模块"""
        module_path = self.config['processor']['module']
        return importlib.import_module(module_path)
    
    def _execute_function_list(self, data, function_names, step_name):
        """按顺序执行函数列表"""
        # 如果是字符串，转换为单元素列表
        if isinstance(function_names, str):
            function_names = [function_names]
        
        # 按顺序执行每个函数
        for i, func_name in enumerate(function_names):
            if hasattr(self.processor, func_name):
                func = getattr(self.processor, func_name)
                self.logger.info(f"{step_name} - 执行函数 {i+1}/{len(function_names)}: {func_name}")
                data = func(data, self.config)
                self.logger.info(f"{step_name} - 函数 {func_name} 执行完成")
            else:
                self.logger.warning(f"{step_name} - 函数 {func_name} 不存在，跳过")
        
        return data
    
    def run(self):
        """执行完整的推理流程"""
        self.logger.info("="*50)
        self.logger.info(f"开始执行推理任务: {self.config.get('name', 'Unknown')}")
        self.logger.info(f"描述: {self.config.get('description', 'No description')}")
        self.logger.info("="*50)
        
        # 1. 加载数据
        self.logger.info("步骤1: 加载数据")
        input_file = self.config['data']['input_file']
        with open(input_file, 'r', encoding='utf-8') as f:
            if input_file.endswith('.json'):
                data = json.load(f)
            elif input_file.endswith('.jsonl'):
                data = [json.loads(line) for line in f]
            else:
                raise ValueError(f"Unsupported file format: {input_file}")
        
        if self.config['data'].get('num_samples', None) is not None:
            data = data[:self.config['data'].get('num_samples')]
        
        self.logger.info(f"成功加载 {len(data)} 条样本")
        
        # 2. 预处理
        pre_process_funcs = self.config['processor'].get('pre_process')
        if pre_process_funcs:
            self.logger.info("步骤2: 执行预处理")
            data = self._execute_function_list(data, pre_process_funcs, "预处理")
            self.logger.info("预处理完成")
        
        # 3. 构建prompt
        build_prompt_func = self.config['processor'].get('build_prompt')
        if build_prompt_func:
            self.logger.info("步骤3: 构建prompt")
            data = self._execute_function_list(data, build_prompt_func, "Prompt构建")
            self.logger.info("Prompt构建完成")
        
        # 4. 执行推理
        self.logger.info("步骤4: 执行推理")
        batch_size = self.config['inference']['batch_size']
        prompt_field = self.config['data']['prompt_field']
        response_field = self.config['data']['response_field']
        rollout_num = self.config['inference'].get('rollout_num', 1)  # 默认1次，向后兼容
        
        self.logger.info(f"推理配置: batch_size={batch_size}, prompt_field={prompt_field}, response_field={response_field}, rollout_num={rollout_num}")
        
        # 初始化结果，复制原始数据作为基础
        all_results = [item.copy() for item in data]
        
        # 执行多次rollout推理
        for rollout_idx in range(rollout_num):
            current_response_field = f"{response_field}_{rollout_idx}"
            self.logger.info(f"开始第 {rollout_idx+1}/{rollout_num} 次推理，结果将保存到字段: {current_response_field}")
            
            # 分批推理当前rollout
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                batch_results = self.inference_engine.batch_infer(
                    batch, 
                    prompt_field=prompt_field,
                    response_field=current_response_field
                )
                
                # 将当前rollout的结果合并到总结果中
                for j, result in enumerate(batch_results):
                    result_idx = i + j
                    if result_idx < len(all_results):
                        # 只添加新的response字段，保留其他字段
                        all_results[result_idx][current_response_field] = result[current_response_field]
                
                processed_count = i + len(batch)
                self.logger.info(f"第 {rollout_idx+1} 次推理已处理 {processed_count}/{len(data)} 条样本")
            
            self.logger.info(f"第 {rollout_idx+1}/{rollout_num} 次推理完成")
        
        self.logger.info(f"所有 {rollout_num} 次推理完成")
        
        # 5. 后处理
        post_process_funcs = self.config['processor'].get('post_process')
        if post_process_funcs:
            self.logger.info("步骤5: 执行后处理")
            all_results = self._execute_function_list(all_results, post_process_funcs, "后处理")
            self.logger.info("后处理完成")
        
        # 6. 保存结果
        self.logger.info("步骤6: 保存结果")
        output_file = self.config['data']['output_file']
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            if output_file.endswith('.json'):
                json.dump(all_results, f, ensure_ascii=False, indent=2)
            elif output_file.endswith('.jsonl'):
                for item in all_results:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            else:
                raise ValueError(f"Unsupported file format: {output_file}")
        
        self.logger.info(f"结果已保存到: {output_file}")
        
        return all_results 