"""
PDF 说明书 → 纯文本转换模块

职责：
    遍历 data/ 下所有产品说明书 PDF，提取文本并清洗，
    按原目录结构输出到 output/pdf_text/，供后续 RAG 切片使用。

依赖：
    pdfplumber —— 主解析引擎，处理带文本层的 PDF。
    无文本层的扫描版 PDF 会记录日志并跳过，后续可扩展 OCR。

配置：
    所有参数从 config/modules/pdf_to_text.yaml 读取，
    通过 config_loader.CONFIG 访问。

路径：
    项目根路径从 project_root.py 获取，禁止硬编码。

模块复用：
    本模块可直接复制到其他项目使用，只需保证 config_loader 存在且 CONFIG 结构一致。
    若要脱离项目独立运行，只需在入口处手动构造 cfg 字典传入 PdfConverter。
"""

import os
import re
from typing import Optional

import pdfplumber

from config_loader import CONFIG
from project_root import PROJECT_ROOT
from utils.logger import get_logger

logger = get_logger("pdf_to_text")


class PdfConverter:
    def __init__(self, cfg: Optional[dict] = None):
        self.cfg = cfg or CONFIG["pdf_to_text"]

        input_cfg = self.cfg["input"]
        input_relative_dir = input_cfg["dir"]
        self.input_dir = PROJECT_ROOT / input_relative_dir
        self.input_glob = input_cfg["glob"]

        output_cfg = self.cfg["output"]
        output_relative_dir = output_cfg["dir"]
        self.output_dir = PROJECT_ROOT / output_relative_dir

        clean_cfg = self.cfg.get("clean", {})
        self.remove_page_numbers = clean_cfg.get("remove_page_numbers", True)
        self.remove_headers_footers = clean_cfg.get("remove_headers_footers", True)
        self.max_blank_lines = clean_cfg.get("max_consecutive_blank_lines", 2)
        self.strip_symbols = clean_cfg.get("strip_symbols", True)

        self._converted_count = 0
        self._skipped_count = 0
        self._failed_count = 0

    # ---------- 核心提取 ----------

    def _extract_text(self, pdf_path: str) -> Optional[str]:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_text = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    if text.strip():
                        pages_text.append(text)
                if not pages_text:
                    return None
                return "\n".join(pages_text)
        except Exception as exc:
            logger.error(f"PDF 解析失败: {pdf_path} -> {exc}")
            return None

    # ---------- 文本清洗 ----------

    def _clean_text(self, text: str) -> str:
        cleaned = text

        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)

        if self.remove_page_numbers:
            cleaned = re.sub(r"^\s*\d+\s*$", "", cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r"^-\s*\d+\s*-$", "", cleaned, flags=re.MULTILINE)

        if self.remove_headers_footers:
            lines = cleaned.split("\n")
            if len(lines) > 10:
                cleaned = "\n".join(lines)

        if self.strip_symbols:
            cleaned = re.sub(r"[ \t]+", " ", cleaned)
            cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)

        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        return cleaned.strip()

    # ---------- 单文件转换 ----------

    def convert_one(self, pdf_path: str) -> Optional[str]:
        rel_path = os.path.relpath(pdf_path, self.input_dir)
        txt_rel_path = os.path.splitext(rel_path)[0] + ".txt"
        txt_path = self.output_dir / txt_rel_path

        if txt_path.exists() and txt_path.stat().st_size > 100:
            logger.debug(f"已存在，跳过: {txt_rel_path}")
            self._skipped_count += 1
            return str(txt_path)

        raw_text = self._extract_text(pdf_path)
        if raw_text is None:
            logger.warning(f"无文本层，跳过: {rel_path}")
            self._skipped_count += 1
            return None

        cleaned = self._clean_text(raw_text)
        if not cleaned:
            logger.warning(f"清洗后为空，跳过: {rel_path}")
            self._skipped_count += 1
            return None

        os.makedirs(txt_path.parent, exist_ok=True)
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(cleaned)
            size_kb = txt_path.stat().st_size / 1024
            logger.info(f"  ✓ {txt_rel_path}  ({size_kb:.1f} KB)")
            self._converted_count += 1
            return str(txt_path)
        except Exception as exc:
            logger.error(f"写入失败: {txt_rel_path} -> {exc}")
            self._failed_count += 1
            return None

    # ---------- 批量转换 ----------

    def convert_all(self) -> dict:
        logger.info("=== PDF 转文本模块启动 ===")

        if not self.input_dir.exists():
            logger.error(f"输入目录不存在: {self.input_dir}")
            return {}

        pdf_files = sorted(self.input_dir.glob(self.input_glob))
        pdf_files = [p for p in pdf_files if p.suffix.lower() == ".pdf"]

        if not pdf_files:
            logger.warning(f"未找到任何 PDF 文件于 {self.input_dir}")
            return {}

        logger.info(f"共发现 {len(pdf_files)} 个 PDF 文件")

        os.makedirs(self.output_dir, exist_ok=True)

        summary: dict[str, list[str]] = {}
        last_product = ""

        for idx, pdf_path in enumerate(pdf_files, start=1):
            rel_path = os.path.relpath(pdf_path, self.input_dir)
            product_name = rel_path.split(os.sep)[0] if os.sep in rel_path else "根目录"

            if product_name != last_product:
                logger.info(f"[{idx}/{len(pdf_files)}] {product_name}")
                last_product = product_name

            txt_path = self.convert_one(str(pdf_path))
            if txt_path:
                summary.setdefault(product_name, []).append(txt_path)

        logger.info(
            f"=== 完成：转换 {self._converted_count} 个，"
            f"跳过 {self._skipped_count} 个，失败 {self._failed_count} 个 ==="
        )
        return summary


# ============================================================
# 入口
# ============================================================

def run(cfg: Optional[dict] = None) -> dict:
    converter = PdfConverter(cfg=cfg)
    return converter.convert_all()


if __name__ == "__main__":
    logger.info("模块独立自测启动")
    result = run()
    logger.info(f"自测完成，共处理 {len(result)} 款产品目录")