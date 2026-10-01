"""
Roborock 扫地机器人说明书爬虫模块

职责：
    从 Roborock 产品中心 API 获取扫地机器人产品列表，
    下载每款产品的说明书 PDF，按产品名分文件夹存放到指定目录。

配置：
    所有参数从 config/modules/manual_crawler.yaml 读取，
    通过 config_loader.CONFIG 访问。

路径：
    项目根路径从 project_root.py 获取，禁止硬编码。

模块复用：
    本模块可直接复制到其他项目使用，只需保证 config_loader 存在且 CONFIG 结构一致。
    若要脱离项目独立运行，只需在入口处手动构造 cfg 字典传入 ManualCrawler。
"""

import os
import random
import re
import time
from dataclasses import dataclass
from typing import Optional

import requests

from config_loader import CONFIG
from project_root import PROJECT_ROOT
from utils.logger import get_logger

logger = get_logger("manual_crawler")


# ============================================================
# 数据结构
# ============================================================

@dataclass
class Product:
    id: int
    name: str
    model: str = ""
    code: str = ""


@dataclass
class Manual:
    name: str
    download_url: str
    sort_order: int = 0
    file_size: str = ""


# ============================================================
# 工具函数
# ============================================================

def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:120] if len(cleaned) > 120 else cleaned


# ============================================================
# 爬虫核心
# ============================================================

class ManualCrawler:
    def __init__(self, cfg: Optional[dict] = None):
        self.cfg = cfg or CONFIG["manual_crawler"]

        api_cfg = self.cfg["api"]
        self.api_base_url = api_cfg["base_url"]
        self.category_path = api_cfg["category_path"]
        self.products_path = api_cfg["products_path"]
        self.product_info_path = api_cfg["product_info_path"]

        target_cfg = self.cfg["target"]
        self.vacuum_category_id = target_cfg["vacuum_category_id"]

        request_cfg = self.cfg["request"]
        self.request_timeout = request_cfg["timeout"]
        self.max_retry = request_cfg["max_retry"]
        self.interval_min = request_cfg["interval_min"]
        self.interval_max = request_cfg["interval_max"]

        output_relative_dir = self.cfg["output"]["dir"]
        self.output_dir = str(PROJECT_ROOT / output_relative_dir)

        self.session = requests.Session()
        self.session.headers.update(self._build_headers())

        self._downloaded_count = 0
        self._skipped_count = 0
        self._failed_count = 0

    # ---------- 请求头 ----------

    @staticmethod
    def _build_headers() -> dict:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Origin": "https://cn.roborock.com",
            "Referer": "https://cn.roborock.com/support-info/user-manual",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "content-type": "application/json",
        }

    # ---------- 基础 ----------

    def _throttle(self) -> None:
        time.sleep(random.uniform(self.interval_min, self.interval_max))

    def _build_url(self, path: str) -> str:
        return f"{self.api_base_url}{path}"

    def _get_json(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        url = self._build_url(path)
        for attempt in range(1, self.max_retry + 1):
            try:
                self._throttle()
                response = self.session.get(url, params=params, timeout=self.request_timeout)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                logger.warning(
                    f"请求失败 [{attempt}/{self.max_retry}]: {url} {params or ''} -> {exc}"
                )
                if attempt == self.max_retry:
                    logger.error(f"放弃请求: {url}")
                    return None
        return None

    # ---------- 分类 & 产品 ----------

    def fetch_vacuum_products(self) -> list[Product]:
        logger.info("获取扫地机器人产品列表...")
        response = self._get_json(
            self.products_path,
            params={"category_id": self.vacuum_category_id},
        )
        if not response or response.get("result") != 1:
            logger.error(f"产品列表获取失败: {response}")
            return []

        raw_list = response.get("data", [])
        products = []
        for item in raw_list:
            if item.get("catId") != self.vacuum_category_id:
                continue
            products.append(Product(
                id=item["id"],
                name=item.get("name", f"产品_{item['id']}"),
                model=item.get("model", ""),
                code=item.get("code", ""),
            ))

        logger.info(f"扫地机器人产品共 {len(products)} 款")
        return products

    # ---------- 说明书 ----------

    def fetch_manuals(self, product: Product) -> list[Manual]:
        if not product.model:
            logger.warning(f"[{product.name}] 无 model 字段，跳过")
            return []

        response = self._get_json(
            self.product_info_path,
            params={"modelId": product.model},
        )
        if not response or response.get("result") != 1:
            logger.error(f"[{product.name}] 产品详情获取失败")
            return []

        data = response.get("data") or {}
        manual_list = data.get("manualList") or []
        manuals = []
        for manual_data in manual_list:
            address = manual_data.get("manualAddress") or manual_data.get("address") or ""
            name = manual_data.get("manualName") or manual_data.get("name") or "未命名说明书"
            if not address:
                continue
            manuals.append(Manual(
                name=name,
                download_url=address,
                sort_order=manual_data.get("manualSort", 0) or 0,
                file_size=manual_data.get("manualSize", "") or "",
            ))

        manuals.sort(key=lambda manual: manual.sort_order, reverse=True)
        return manuals

    # ---------- PDF 下载 ----------

    def download_pdf(self, manual: Manual, save_dir: str) -> Optional[str]:
        os.makedirs(save_dir, exist_ok=True)

        filename = sanitize_filename(manual.name)
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        filepath = os.path.join(save_dir, filename)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            logger.debug(f"已存在，跳过: {filepath}")
            self._skipped_count += 1
            return filepath

        for attempt in range(1, self.max_retry + 1):
            try:
                self._throttle()
                response = self.session.get(
                    manual.download_url,
                    timeout=self.request_timeout,
                    stream=True,
                )
                response.raise_for_status()

                with open(filepath, "wb") as file_handle:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file_handle.write(chunk)

                size_kb = os.path.getsize(filepath) / 1024
                logger.info(f"  ✓ {filename}  ({size_kb:.1f} KB)")
                self._downloaded_count += 1
                return filepath

            except requests.RequestException as exc:
                logger.warning(
                    f"下载失败 [{attempt}/{self.max_retry}]: {manual.download_url} -> {exc}"
                )
                if attempt == self.max_retry:
                    logger.error(f"放弃下载: {filename}")
                    self._failed_count += 1
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return None
        return None

    # ---------- 主流程 ----------

    def crawl(self) -> dict[str, list[str]]:
        logger.info("=== Roborock 说明书爬虫启动 ===")

        products = self.fetch_vacuum_products()
        if not products:
            logger.error("未获取到任何产品，终止")
            return {}

        summary: dict[str, list[str]] = {}

        for idx, product in enumerate(products, start=1):
            logger.info(f"[{idx}/{len(products)}] {product.name}  (model={product.model})")

            manuals = self.fetch_manuals(product)
            if not manuals:
                logger.info(f"  无说明书")
                continue

            save_dir = os.path.join(self.output_dir, sanitize_filename(product.name))
            downloaded_paths = []

            for manual in manuals:
                path = self.download_pdf(manual, save_dir)
                if path:
                    downloaded_paths.append(path)

            if downloaded_paths:
                summary[product.name] = downloaded_paths

        logger.info(
            f"=== 完成：下载 {self._downloaded_count} 个，"
            f"跳过 {self._skipped_count} 个，失败 {self._failed_count} 个 ==="
        )
        return summary


# ============================================================
# 入口
# ============================================================

def run(cfg: Optional[dict] = None) -> dict[str, list[str]]:
    crawler = ManualCrawler(cfg=cfg)
    return crawler.crawl()


if __name__ == "__main__":
    logger.info("模块独立自测启动")
    result = run()
    logger.info(f"自测完成，共处理 {len(result)} 款产品")