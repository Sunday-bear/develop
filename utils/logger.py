"""
日志工具模块

封装 logging：控制台 + 文件双输出，文件按天轮转。
日志路径统一从 project_root.LOGS_DIR 拼接，禁止硬编码。
"""

import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from project_root import LOGS_DIR


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    detailed_fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple_fmt = logging.Formatter("%(levelname)s: %(message)s")

    os.makedirs(str(LOGS_DIR), exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{name}_{today}.log"

    file_handler = TimedRotatingFileHandler(
        str(log_file), when="midnight", backupCount=30, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_fmt)
    file_handler.suffix = "%Y-%m-%d.log"

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.propagate = False

    return logger


if __name__ == "__main__":
    demo_logger = get_logger("demo")
    demo_logger.debug("这是一条 DEBUG 日志（仅文件可见）")
    demo_logger.info("这是一条 INFO 日志")
    demo_logger.warning("这是一条 WARNING 日志")
    demo_logger.error("这是一条 ERROR 日志")
    demo_logger.critical("这是一条 CRITICAL 日志")