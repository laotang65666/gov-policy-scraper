# 政府政策文件爬取工具 (gov-policy-scraper)

一个面向**非技术人员**的中国政府网政策文件爬取工具：双击运行、按提示输入关键词，
即可自动搜索并下载国务院文件及各部门文件（含卫健委、医保局、药监局等），并抓取全文。

## 功能

- 按关键词搜索国务院政策文件库（国务院文件 + 国务院部门文件）
- 自动过滤新闻等非政策内容，只保留真正的政策文件
- 抓取每篇文件的全文正文
- 输出 Excel 元数据表 + 每篇全文 Markdown

## 快速开始

1. 安装 [Python](https://www.python.org/downloads/)（3.8+，安装时勾选 **Add Python to PATH**）
2. 双击 `install.bat` 安装依赖（只需一次）
3. 双击 `run.bat`，按提示输入关键词（直接回车使用默认关键词）

## 输出

运行后在本目录 `data/` 下生成：

- `政策文件清单.xlsx` —— 元数据表（关键词、标题、发布机构、文件类型、分类、文号、日期、链接、摘要）
- `docs/` —— 每篇文件的全文 Markdown

## 项目结构

```
gov-policy-scraper/
├── main.py          # 交互式入口
├── scraper.py       # 核心爬虫逻辑
├── run.bat          # 双击运行入口
├── install.bat      # 首次安装依赖
├── requirements.txt # 依赖清单
└── README.md
```

## 技术原理

### 1. TLS 指纹拦截与绕过

中国政府网的服务器会识别非浏览器客户端的 TLS 指纹，普通的 `requests` / `urllib`
请求会在 SSL 握手阶段被直接断开（报 `UNEXPECTED_EOF_WHILE_READING`）。

本工具使用 [`curl_cffi`](https://github.com/lexiforest/curl_cffi) 的
`impersonate="chrome"` 能力模拟 Chrome 浏览器的 TLS 指纹，从而正常访问。

### 2. 搜索接口的 RSA 签名认证

gov.cn 的前端搜索并非简单的 GET 请求，而是经由 **athena 网关**转发：

```
POST https://sousuoht.www.gov.cn/athena/forward/2B22E8E39E850E17F95A016A74FCB6B673336FA8B6FEC0E2955907EF9AEE06BE
```

该接口要求两个认证请求头：

- `athenaAppName` —— 固定值 `国网搜索`
- `athenaAppKey` —— 对一段固定明文做 **RSA PKCS#1 v1.5 加密**后 Base64/URL 编码的结果

RSA 公钥与加密明文从前端 `search.js` 中提取，硬编码在 `scraper.py` 顶部常量里，
用 `pycryptodome` 在本地复刻签名流程，无需执行任何 JS。

### 3. 搜索结果与全文提取

- 搜索使用 `dataTypeId=107`（全部），再按 URL 含 `/zhengce/` 或 `/gongbao/` 过滤出
  政策文件，自动排除新闻（`/lianbo/`、`/xinwen/` 等路径）。
- 全文通过详情页的 `#UCAP-CONTENT` 元素提取。

### 4. 为什么不需要单独爬卫健委 / 医保局官网

中国政府网**政策文件库本身已收录卫健委、医保局、药监局等所有国务院部门的规范性文件**。
而卫健委官网有瑞数(JS)反爬、医保局官网列表是动态 dataproxy 加载，
因此直接以 gov.cn 政策文件库为唯一数据源即可完整覆盖，无需逐个部门逆向。

## 依赖

| 包 | 用途 |
|----|------|
| `curl_cffi` | TLS 指纹模拟 |
| `lxml` | HTML 解析 |
| `pycryptodome` | RSA 签名 |
| `openpyxl` | Excel 输出 |

## 免责声明

本项目仅用于学习与合法获取公开政策文件。请遵守目标网站的 robots 协议与服务条款，
控制抓取频率，勿用于任何非法用途。

## License

[MIT](./LICENSE)
