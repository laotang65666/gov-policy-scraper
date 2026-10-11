# -*- coding: utf-8 -*-
"""
政府政策文件爬取工具 —— 交互式入口
双击 run.bat 运行，按提示输入关键词即可，不需要懂编程。
"""
import os
import re
import sys
import time

from scraper import fetch_all

DEFAULT_KEYWORDS = [
    "互联网+医疗", "人工智能+医疗", "互联网医疗", "互联网诊疗",
    "互联网医院", "远程医疗", "智慧医疗",
]


def ask(prompt, default=""):
    """打印提示并读取一行输入；直接回车返回默认值。"""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        line = input().strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return line if line else default


def banner():
    print()
    print("=" * 52)
    print("        政府政策文件爬取工具")
    print("    （互联网+医疗 / 人工智能+医疗 等政策）")
    print("=" * 52)
    print("  数据来源：中国政府网政策文件库")
    print("  （含国务院文件，以及卫健委、医保局、")
    print("   药监局等所有国务院部门文件）")
    print()


def parse_keywords(text):
    """把用户输入拆成关键词列表（支持空格、逗号、中文逗号分隔）。"""
    parts = re.split(r"[,\s，、]+", text.strip())
    return [p for p in parts if p]


def sanitize_filename(name):
    """去掉文件名里 Windows 不允许的字符。"""
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name)
    return name[:60].strip() or "未命名"


def save_results(items, out_dir):
    """把结果保存为 Excel 元数据表 + 每篇正文一个 md 文件。"""
    os.makedirs(out_dir, exist_ok=True)
    docs_dir = os.path.join(out_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    # ---- 1. 元数据 Excel ----
    xlsx_path = os.path.join(out_dir, "政策文件清单.xlsx")
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "政策文件"
        headers = ["关键词", "标题", "发布机构", "文件类型", "分类", "文号",
                   "发布日期", "来源网站", "原文链接", "摘要"]
        ws.append(headers)
        for it in items:
            ws.append([
                it.get("keyword", ""),
                it.get("title", ""),
                it.get("agencies", ""),
                it.get("document_type", ""),
                it.get("category", ""),
                it.get("pubcode", ""),
                it.get("publish_time", ""),
                it.get("source", ""),
                it.get("url", ""),
                it.get("summary", ""),
            ])
        # 调整列宽，便于阅读
        widths = [12, 50, 18, 12, 14, 22, 14, 12, 45, 40]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[chr(64 + i) if i <= 26 else "A"].width = w
        wb.save(xlsx_path)
        print(f"  [OK] 元数据表格已保存：{xlsx_path}")
    except Exception as e:
        # 退化为 CSV（带 BOM，Excel 打开不乱码）
        csv_path = os.path.join(out_dir, "政策文件清单.csv")
        import csv
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["关键词", "标题", "发布机构", "文件类型", "分类", "文号",
                             "发布日期", "来源网站", "原文链接", "摘要"])
            for it in items:
                writer.writerow([
                    it.get("keyword", ""), it.get("title", ""),
                    it.get("agencies", ""), it.get("document_type", ""),
                    it.get("category", ""), it.get("pubcode", ""),
                    it.get("publish_time", ""), it.get("source", ""),
                    it.get("url", ""), it.get("summary", ""),
                ])
        print(f"  [!] 未安装 openpyxl，已改为保存 CSV：{csv_path}")
        print(f"    （{e}）")

    # ---- 2. 每篇正文 md ----
    fulltext_count = 0
    for idx, it in enumerate(items, 1):
        text = it.get("fulltext") or ""
        if not text.strip():
            continue
        title = sanitize_filename(it.get("title") or "第{}篇".format(idx))
        fname = f"{idx:03d}_{title}.md"
        with open(os.path.join(docs_dir, fname), "w", encoding="utf-8") as f:
            f.write(f"# {it.get('title', '')}\n\n")
            for label, key in [("发布机构", "agencies"), ("文件类型", "document_type"),
                               ("文号", "pubcode"), ("发布日期", "publish_time"),
                               ("来源网站", "source"), ("关键词", "keyword")]:
                val = it.get(key, "")
                if val:
                    f.write(f"- **{label}**：{val}\n")
            f.write(f"- **原文链接**：{it.get('url', '')}\n\n---\n\n")
            f.write(text.strip())
            f.write("\n")
        fulltext_count += 1

    if fulltext_count:
        print(f"  [OK] 已保存 {fulltext_count} 篇正文到：{docs_dir}")
    else:
        print("  [!] 本次未抓取到正文（可能网络问题或未开启全文）")


def main():
    banner()
    print("提示：下面每一步直接按回车即可使用默认值。")
    print()

    default_kw = " ".join(DEFAULT_KEYWORDS)
    kw_text = ask(f"请输入要爬的关键词（多个用空格分开）\n默认：{default_kw}\n> ",
                  default_kw)
    keywords = parse_keywords(kw_text)
    if not keywords:
        print("没有输入任何关键词，程序结束。")
        return
    print(f"本次关键词：{'、'.join(keywords)}")
    print()

    max_text = ask("每个关键词最多抓多少条？（默认 30）\n> ", "30")
    try:
        max_per = int(max_text)
    except ValueError:
        max_per = 30
    print(f"每个关键词最多抓 {max_per} 条")
    print()

    ft_text = ask("是否抓取全文？(y/n，默认 y)\n> ", "y")
    want_fulltext = ft_text.strip().lower() != "n"
    print(f"全文抓取：{'开' if want_fulltext else '关'}")
    print()

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    print("开始抓取，请稍候……")
    print("-" * 52)

    def progress(msg):
        print("  " + msg)

    t0 = time.time()
    try:
        items = fetch_all(
            keywords,
            max_per_keyword=max_per,
            want_fulltext=want_fulltext,
            progress=progress,
        )
    except KeyboardInterrupt:
        print("\n已手动中断。")
        return

    print("-" * 52)
    if not items:
        print("没有抓到任何结果。请检查网络或换个关键词试试。")
        return

    print(f"\n共抓到 {len(items)} 条记录，正在保存……")
    save_results(items, out_dir)

    cost = time.time() - t0
    print()
    print("=" * 52)
    print(f"全部完成！共 {len(items)} 条，用时 {cost:.0f} 秒。")
    print(f"结果保存在：{out_dir}")
    print("  - 政策文件清单.xlsx  （所有文件的元数据表格）")
    print("  - docs/               （每篇正文一个 md 文件）")
    print("=" * 52)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已退出。")
    input("\n按回车键关闭窗口……")
