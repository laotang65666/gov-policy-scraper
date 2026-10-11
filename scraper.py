# -*- coding: utf-8 -*-
"""
政府政策文件爬虫核心模块
数据来源：中国政府网政策文件库（www.gov.cn），涵盖国务院文件及卫健委、医保局、
药监局等所有国务院部门文件。给同学写的小工具，配合「爬取.py」使用。
"""
import base64
import re
import time
import urllib.parse

import curl_cffi.requests as cr
from lxml import html as lxml_html

# ---------------------------------------------------------------------------
# 全局配置
# ---------------------------------------------------------------------------
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0.0.0 Safari/537.36")

# 中国政府网搜索接口配置信息
GOV_PUBKEY_B64 = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCSMhMJQ+XLI7oW0k9Bwufur4Ag40tcsrzT7"
    "WZf6Ao0O/hyY1gZtCSYFxkxIZUXjW46j27XSW8IDX1rTJoHaMxHCWsOpTi2W5stybGYZytsY"
    "5on8gd8AIaS1d52h9eaS2TFydtJJtE50xHmT0WmoyoinWCuVCOkdCLhh9b9jSdeSQIDAQAB"
)
GOV_AUTH_PLAINTEXT = "a46884b2013e4d189f2a8e2d49a23525"
GOV_SEARCH_URL = ("https://sousuoht.www.gov.cn/athena/forward/"
                  "2B22E8E39E850E17F95A016A74FCB6B673336FA8B6FEC0E2955907EF9AEE06BE")
GOV_CODE = "17da70961a7"

# 每次请求之间的等待秒数（礼貌抓取，避免给服务器压力）
REQUEST_DELAY = 0.6

_session = None


def _get_session():
    global _session
    if _session is None:
        # curl_cffi 能伪装浏览器 TLS 指纹，绕过 gov.cn 对普通请求的指纹拦截
        _session = cr.Session(impersonate="chrome", timeout=30)
    return _session


# ---------------------------------------------------------------------------
# 中国政府网搜索（需要 RSA 签名认证）
# ---------------------------------------------------------------------------
def _make_gov_headers():
    """生成 gov.cn 搜索接口需要的认证请求头（athenaAppKey 用 RSA 加密）。"""
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5

    key = RSA.import_key(base64.b64decode(GOV_PUBKEY_B64))
    cipher = PKCS1_v1_5.new(key)
    encrypted = cipher.encrypt(GOV_AUTH_PLAINTEXT.encode("utf-8"))
    return {
        "User-Agent": USER_AGENT,
        "Referer": "https://sousuo.www.gov.cn/",
        "Origin": "https://sousuo.www.gov.cn",
        "Content-Type": "application/json;charset=utf-8",
        "athenaAppKey": urllib.parse.quote(base64.b64encode(encrypted)),
        "athenaAppName": urllib.parse.quote("国网搜索"),
    }


def search_gov(keyword, page_no=1, page_size=10):
    """
    在中国政府网搜索一个关键词，返回 (结果列表, 总条数, 总页数)。
    每条结果是原始 dict，字段含 title / url / agencies / documentType / time 等。
    """
    body = {
        "code": GOV_CODE,
        "historySearchWords": [],
        "dataTypeId": "107",  # 107 = 全部（之后按 URL 过滤出政策文件）
        "orderBy": "time",
        "searchBy": "title",
        "appendixType": "",
        "granularity": "ALL",
        "trackTotalHits": True,
        "beginDateTime": "",
        "endDateTime": "",
        "isSearchForced": 0,
        "filters": [],
        "pageNo": page_no,
        "pageSize": page_size,
        "customFilter": {"operator": "and", "properties": []},
        "searchWord": keyword,
    }
    resp = _get_session().post(
        GOV_SEARCH_URL, json=body, headers=_make_gov_headers()
    )
    data = resp.json()
    result = data.get("result") or {}
    # resultCode 在响应顶层；成功时 code 是数字，失败时是字符串（如 "athena_01509"）
    code = (data.get("resultCode") or {}).get("code")
    if isinstance(code, str):
        raise RuntimeError("gov.cn 搜索失败：" + str(data.get("resultCode")))

    inner = (result.get("data") or {}).get("middle") or {}
    items = inner.get("list") or []
    pager = (result.get("data") or {}).get("pager") or {}
    total = pager.get("total", len(items))
    page_count = pager.get("pageCount", 1)
    return items, total, page_count


def _to_str(value):
    """把任意类型的字段安全转成去空白的字符串。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        return ", ".join(_to_str(v) for v in value)
    return str(value)


def is_policy_url(url):
    """判断一个 gov.cn 链接是否属于政策文件（国务院文件/部门文件/公报）。"""
    if not url:
        return False
    return ("/zhengce/" in url) or ("/gongbao/" in url)


def parse_gov_item(item):
    """把 gov.cn 的一条搜索结果转成统一的元数据 dict。"""
    title = item.get("title_no_tag") or item.get("title") or ""
    title = re.sub(r"</?em>", "", str(title))
    title = re.sub(r"\s+", " ", title).strip()

    document_type = _to_str(item.get("documentType"))
    # 有些条目 documentType 是未解析的数字 ID，用 label（如"国务院部门文件"）代替
    if document_type.isdigit():
        document_type = _to_str(item.get("label")) or document_type

    agencies = _to_str(item.get("agencies"))
    # 纯数字说明机构名未解析（多为新闻/解读条目），清空避免显示无意义编号
    if agencies.isdigit():
        agencies = ""

    return {
        "title": title,
        "url": _to_str(item.get("url")),
        "agencies": agencies,
        "document_type": document_type,
        "category": _to_str(item.get("label")),
        "pubcode": _to_str(item.get("pubcode")),
        "publish_time": _to_str(item.get("time")),
        "summary": _to_str(item.get("summary")),
        "source": "中国政府网",
    }


def fetch_gov_fulltext(url):
    """抓取 gov.cn 政策文件详情页正文。"""
    resp = _get_session().get(url, headers={"User-Agent": USER_AGENT})
    doc = lxml_html.fromstring(resp.content)
    node = doc.xpath("//div[@id='UCAP-CONTENT']")
    if node:
        text = node[0].xpath("string()").strip()
        return re.sub(r"[ \t]+", " ", text)
    return ""


# ---------------------------------------------------------------------------
# 通用抓取流程
# ---------------------------------------------------------------------------
def fetch_all(keywords, max_per_keyword=30, want_fulltext=True, progress=None):
    """
    按多个关键词抓取政策文件。
    keywords: 关键词列表
    max_per_keyword: 每个关键词最多抓多少条
    want_fulltext: 是否抓全文
    progress: 回调函数 progress(msg)，用于打印进度
    返回统一元数据列表（含 fulltext 字段）。
    """
    all_items = []

    for kw in keywords:
        if progress:
            progress(f"正在搜索关键词「{kw}」…")
        try:
            page_no = 1
            collected = 0
            while collected < max_per_keyword:
                items, total, page_count = search_gov(kw, page_no=page_no, page_size=10)
                if not items:
                    break
                for it in items:
                    if collected >= max_per_keyword:
                        break
                    meta = parse_gov_item(it)
                    # 只保留政策文件（国务院文件/部门文件/公报），过滤掉新闻等
                    if not is_policy_url(meta["url"]):
                        continue
                    meta["keyword"] = kw
                    if want_fulltext and meta["url"]:
                        time.sleep(REQUEST_DELAY)
                        try:
                            meta["fulltext"] = fetch_gov_fulltext(meta["url"])
                        except Exception:
                            meta["fulltext"] = ""
                    all_items.append(meta)
                    collected += 1
                if page_no >= page_count:
                    break
                page_no += 1
                time.sleep(REQUEST_DELAY)
            if progress:
                progress(f"「{kw}」完成，累计 {len(all_items)} 条")
        except Exception as e:
            if progress:
                progress(f"「{kw}」出错：{e}")

    # 去重（按 URL）
    deduped = []
    seen = set()
    for it in all_items:
        if it["url"] and it["url"] in seen:
            continue
        seen.add(it["url"])
        deduped.append(it)
    return deduped
