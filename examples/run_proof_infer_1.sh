#!/bin/bash

# 设置项目根目录
PROJECT_ROOT=$(dirname $(dirname $(realpath $0)))
echo "项目根目录: $PROJECT_ROOT"
# 进入项目根目录
cd $PROJECT_ROOT

# 创建输出目录
mkdir -p results

#### 1. 运行前需修改main函数的config文件地址 （默认是configs/align/simple_qa.yaml） ####
# 简单的QA推理
# python main.py --config-path configs/proof --config-name simple_qa \
#     inference.rollout_num=1 \
#     data.output_file=results/proof/proving_train_qa_rollout1.json \
#     data.num_samples=32
###################### end 1 ###############################


#### 2. 运行前需修改main函数的config文件地址 （默认是configs/align/score_checklist.yaml） ####
python main.py --config-path configs/proof --config-name score_checklist \
    data.input_file=results/proof/proving_train_qa_rollout1.json \
    data.output_file=results/proof/proving_train_qa_rollout1_checklist_score.json \
    processor.post_process=[extract_score,average_max_score]
###################### end 2 ###############################



