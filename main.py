import hydra
from omegaconf import DictConfig, OmegaConf
from core.runner import Runner

# @hydra.main(version_base=None, config_path="configs/align", config_name="simple_qa")
# @hydra.main(version_base=None, config_path="configs/align", config_name="score_checklist")
# @hydra.main(version_base=None, config_path="configs/align", config_name="score_effectlist")
@hydra.main(version_base=None, config_path="configs/align", config_name="simple_qa")
def main(cfg: DictConfig) -> None:
    """主函数，使用hydra自动加载和解析配置"""
    
    # Hydra自动解析所有变量引用
    print("配置文件内容:")
    print(OmegaConf.to_yaml(cfg, resolve=True))
    
    # 转换为普通字典传给Runner
    config_dict = OmegaConf.to_container(cfg, resolve=True)
    
    # 创建Runner并执行推理
    runner = Runner(config_dict)
    runner.run()

if __name__ == "__main__":
    main()