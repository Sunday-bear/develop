"""
项目路径统一管理

以自身文件位置为基准，自动计算项目根目录绝对路径。
项目内所有模块的 config / data / logs / output 路径，
统一从此文件拼接生成，禁止各模块硬编码路径。
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

CONFIG_DIR = PROJECT_ROOT / "config"
MODULES_DIR = CONFIG_DIR / "modules"

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"


def get_path(*relative_parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*relative_parts)


if __name__ == "__main__":
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"CONFIG_DIR:   {CONFIG_DIR}")
    print(f"DATA_DIR:     {DATA_DIR}")
    print(f"OUTPUT_DIR:   {OUTPUT_DIR}")
    print(f"LOGS_DIR:     {LOGS_DIR}")
    print(f"config_loader: {PROJECT_ROOT / 'config_loader.py'}")