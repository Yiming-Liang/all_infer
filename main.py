import argparse
from core.runner import Runner

def parse_arguments():
    parser = argparse.ArgumentParser(description='通用推理框架')
    parser.add_argument('--config', type=str, required=True, help='配置文件路径')
    return parser.parse_args()

def main():
    args = parse_arguments()
    runner = Runner(args.config)
    runner.run()

if __name__ == "__main__":
    main()