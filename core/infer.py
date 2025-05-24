from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
from utils.logger import setup_logging

# 配置日志
setup_logging()

class ModelManager:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.sampling_params = None
        
    def initialize(self):
        """初始化模型和tokenizer"""
        model_config = self.config['model']
        inference_config = self.config['inference']
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_config['path'],
            trust_remote_code=model_config['trust_remote_code'],
            enforce_eager=True
        )
        
        self.model = LLM(
            model=model_config['path'],
            tensor_parallel_size=model_config['tensor_parallel_size'],
            gpu_memory_utilization=model_config['gpu_memory_utilization'],
            trust_remote_code=model_config['trust_remote_code'],
        )
        
        self.sampling_params = SamplingParams(
            max_tokens=inference_config['max_tokens'],
            temperature=inference_config['temperature'],
            top_p=inference_config['top_p']
        )
        
        return self.model, self.tokenizer, self.sampling_params

class InferenceEngine:
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.model, self.tokenizer, self.sampling_params = model_manager.initialize()
        
    def batch_infer(self, batch, prompt_field, response_field):
        """执行批量推理"""
        # 获取原始prompts
        prompts = [item[prompt_field] for item in batch]
        
        # 应用chat template
        processed_prompts = []
        for prompt in prompts:
            messages = [{"role": "user", "content": prompt}]
            chat_text = self.tokenizer.apply_chat_template(
                messages, 
                tokenize=False,
                add_generation_prompt=True
            )
            processed_prompts.append(chat_text)
        
        # 使用处理后的prompts进行生成
        outputs = self.model.generate(processed_prompts, self.sampling_params)
        
        results = []
        for item, output in zip(batch, outputs):
            result = item.copy()
            result[response_field] = output.outputs[0].text.strip()
            results.append(result)
        
        if results:
            print(f"\n{'='*20} Batch Sample 0 {'='*20}")
            # print(f"question: \n{item['extra_info']['question']}")
            print(f"📝 Processed prompt: \n{processed_prompts[0]}")
            print(f"🤖 {response_field}: \n{results[0][response_field]}")
            print(f"{'='*20} end Sample 0 {'='*20}")
        
        return results 