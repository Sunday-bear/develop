"""
项目总调度入口

一键运行完整业务链路：
    1. 爬取 Roborock 扫地机器人说明书 PDF
    2. (后续) PDF 转文本
    3. (后续) RAG 向量化入库
    4. (后续) Streamlit 前端

运行：python main.py
"""

import sys
import time

from config_loader import CONFIG
from utils.logger import get_logger

logger = get_logger("main")


def run_stage_1_crawler() -> None:
    from src.manual_crawler.manual_crawler import run as run_crawler
    logger.info("━━━ Stage 1: 说明书爬取 ━━━")
    run_crawler()


def run_all() -> None:
    logger.info("╔══════════════════════════════════════╗")
    logger.info("║   Roborock RAG 项目 — 完整链路启动   ║")
    logger.info("╚══════════════════════════════════════╝")

    start = time.time()

    run_stage_1_crawler()

    elapsed = time.time() - start
    logger.info(f"全部完成，耗时 {elapsed:.1f} 秒")


if __name__ == "__main__":
    run_all()