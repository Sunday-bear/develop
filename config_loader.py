"""
配置统一加载入口

自动读取 config/ 下全部 yaml + config/modules/ 下全部 yaml，
合并为单一全局 CONFIG 字典；同时通过 load_dotenv 加载 .env。

安全约定：
    .env 环境变量仅通过 load_dotenv 注入 os.environ，
    不存入 CONFIG，业务模块按需用 os.getenv("KEY") 显式读取。
    禁止序列化完整 CONFIG 用于日志打印，防止密钥泄露。

所有业务模块统一从此文件读取配置，禁止模块单独读取 yaml。
"""

from dotenv import load_dotenv
import yaml

from project_root import PROJECT_ROOT, CONFIG_DIR, MODULES_DIR


def _load_yaml_files(directory) -> dict:
    merged = {}
    if not directory.exists():
        return merged
    for yaml_path in sorted(directory.glob("*.yaml")):
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        merged[yaml_path.stem] = data
    return merged


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config() -> dict:
    load_dotenv(PROJECT_ROOT / ".env")

    config: dict = {}

    app_yaml = CONFIG_DIR / "app.yaml"
    if app_yaml.exists():
        with open(app_yaml, "r", encoding="utf-8") as f:
            app_data = yaml.safe_load(f) or {}
        config = app_data

    modules_data = _load_yaml_files(MODULES_DIR)
    for module_name, module_cfg in modules_data.items():
        if module_name not in config:
            config[module_name] = {}
        _deep_merge(config[module_name], module_cfg)

    return config


CONFIG = load_config()


if __name__ == "__main__":
    print("=== 配置加载测试 ===")
    print(f"项目名称: {CONFIG.get('project', {}).get('name', 'N/A')}")
    print(f"日志目录: {CONFIG.get('logs', {}).get('dir', 'N/A')}")
    print(f"数据目录: {CONFIG.get('data_dir', 'N/A')}")
    print(f"输出目录: {CONFIG.get('output_dir', 'N/A')}")

    crawler_cfg = CONFIG.get("manual_crawler", {})
    if crawler_cfg:
        api = crawler_cfg.get("api", {})
        print(f"爬虫API基址: {api.get('base_url', 'N/A')}")
        print(f"目标分类ID: {crawler_cfg.get('target', {}).get('vacuum_category_id', 'N/A')}")
    print("=== 配置加载成功（敏感字段已隐藏） ===")