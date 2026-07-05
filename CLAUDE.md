# 拼多多莜面鱼/莜面鱼鱼销量监控系统 - 系统架构文档

> 本文档用于帮助理解整个系统，方便后续开发和维护。
> 最后更新：2026-07-06

---

## 1. 项目概述

这是一个针对拼多多（Pinduoduo）APP的安卓自动化销量监控系统，专门监控关键词 **"莜面鱼"**（覆盖"莜面鱼"和"莜面鱼鱼"）相关商品的销量变化。

### 核心功能
- **安卓自动化**：使用 `uiautomator2` 控制拼多多 APP，模拟真人点击、滑动、搜索
- **商品数据采集**：商品标题、价格、累计销量、店铺名称、真实商品链接
- **增量计算**：自动计算今日/昨日/7天/30天销量
- **定时采集**：支持 APScheduler 后台调度 + Windows 任务计划双保险
- **Web 看板**：Flask + Bootstrap 展示看板、商品列表、详情页、日志、设置
- **数据存储**：SQLite（默认）/ MySQL 可选

### 运行环境
- 操作系统：Windows 10
- 安卓设备：MuMu 模拟器（`127.0.0.1:5555`）或 USB 真机
- 拼多多版本：已适配 PDD 8.14
- Python 依赖：见 `requirements.txt`

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Android 设备                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  拼多多 APP  │    │  系统剪贴板  │    │  UI 界面    │      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          │  uiautomator2    │  ADB shell       │  dump_hierarchy
          │  (点击/滑动/输入) │  (dumpsys等)      │  (XML解析)
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      采集引擎 (core/)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   scraper    │  │detail_scraper│  │  link_extractor  │   │
│  │  搜索结果采集 │  │  详情页采集  │  │  真实链接提取    │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                 │                   │             │
│  ┌──────▼─────────────────▼───────────────────▼──────┐      │
│  │                      parser                       │      │
│  │         销量/价格/商品名/店铺名 文本解析          │      │
│  └──────────────────────┬────────────────────────────┘      │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     数据层 (core/db.py)                      │
│  SQLAlchemy ORM  +  SQLite/MySQL                             │
│  - Product (商品主表)                                        │
│  - SalesRecord (每日销量快照)                                │
│  - ScrapeLog (采集日志)                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌─────────────────┐    ┌─────────────────┐
│   Web 看板      │    │   定时调度器    │
│  (web/app.py)   │    │(scheduler/)     │
│  Flask + Jinja2 │    │ APScheduler     │
│  Bootstrap JS   │    │ Windows Task    │
└─────────────────┘    └─────────────────┘
```

---

## 3. 目录结构

```
duoduo1/
├── config.py                 # 全局配置（从 .env 读取）
├── main.py                   # 主入口：Web/单次采集/注册Windows任务
├── run_scrape.py             # 单次采集快捷脚本
├── run_accurate.py           # 精准采集实验脚本（已停用）
├── .env                      # 环境变量配置
├── requirements.txt          # Python 依赖
│
├── core/                     # 核心采集引擎
│   ├── scraper.py            # 主采集流程（搜索→滚动→解析→入库）
│   ├── detail_scraper.py     # 详情页数据采集（店铺名、销量）
│   ├── link_extractor.py     # 真实商品链接提取（分享→复制→ADB读取剪贴板）
│   ├── parser.py             # 文本解析器（销量/价格/商品名清洗）
│   ├── spec_parser.py        # 规格信息提取（已停用）
│   ├── db.py                 # 数据库引擎、ORM、CRUD、查询API
│   └── device_manager.py     # 设备连接/APP生命周期管理（备用）
│
├── models/                   # SQLAlchemy 数据模型
│   ├── product.py            # Product 商品主表
│   ├── sales_record.py       # SalesRecord 销量快照
│   └── scrape_log.py         # ScrapeLog 采集日志
│
├── scheduler/                # 定时任务
│   ├── schedule.py           # APScheduler 调度器、手动触发
│   └── windows_task.py       # Windows 计划任务注册/删除
│
├── web/                      # Flask Web 应用
│   ├── app.py                # 应用工厂
│   ├── routes.py             # 页面路由
│   ├── api.py                # REST API
│   ├── templates/            # Jinja2 模板
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── products.html
│   │   ├── product_detail.html
│   │   ├── logs.html
│   │   └── settings.html
│   └── static/               # CSS/JS
│       ├── css/dashboard.css
│       └── js/dashboard.js, products.js
│
├── utils/                    # 工具模块
│   ├── logger.py             # 日志配置
│   └── helpers.py            # 重试装饰器、文本处理、日期工具
│
├── tests/                    # 测试脚本
│   ├── test_parser.py        # 解析器单元测试
│   ├── test_all.py           # 全功能测试
│   └── test_commercial.py    # 商用级全面测试
│
├── data/                     # SQLite 数据库目录
│   └── scraper.db
│
└── logs/                     # 日志与调试文件
    ├── app.log               # 应用日志
    └── *.txt / *.png         # 调试输出
```

---

## 4. 数据流详解

### 4.1 一次完整采集的流程

```
1. main.py / scheduler → run_scrape()
2. 连接设备 (u2.connect(serial))
3. perform_search()    → 启动APP → 点击搜索 → 输入"莜面鱼" → 回车
4. scrape_all_results() → 滚动搜索结果页
   └─ extract_all_text_with_positions() 获取所有文本+坐标
   └─ parse_product_cards() 按X列匹配解析商品卡片
5. 对每个商品：
   - parse_sales_volume() 解析累计销量
   - 跳过 sales_volume <= 0 的商品
   - upsert_product() 按商品名前80字符匹配去重
   - compute_daily_sales() 计算日增量（含10倍异常检测）
   - save_sales_record() 保存销量快照
6. _extract_real_links() → 对最近3个商品：
   - 点击进入详情页
   - 读取 content-desc 中的完整标题
   - extract_product_link() 提取真实商品链接
7. finish_scrape_log() 更新采集日志
```

### 4.2 关键匹配逻辑：X列匹配

拼多多搜索结果为 **2列网格布局**，屏幕宽度约900px，列分界约450px。

- 左列商品 `x < 450`，只匹配左列的价格/销量
- 右列商品 `x >= 450`，只匹配右列的价格/销量

否则会出现"A商品的名称 + B商品的销量"的关联错误。

### 4.3 销量过滤规则

**保留**（视为单品销量）：
- `已拼X件`
- `本店已拼X件`

**跳过**（视为店铺/全网总销量）：
- `全网总售`、`全网销量`
- `全店总售`、`全店销量`、`店铺总售`

### 4.4 异常检测

`compute_daily_sales()` 中：
- 如果 `delta > last_record.sales_volume * 10`，说明可能出现卡片错配，将该记录视为首次采集（`daily_sales = None`）

---

## 5. 核心模块详解

### 5.1 `core/scraper.py`

主采集模块，包含：

| 函数 | 作用 |
|------|------|
| `human_delay()` / `human_swipe()` / `human_tap()` | 模拟真人操作间隔和滑动 |
| `perform_search()` | 启动APP、输入关键词、执行搜索、验证结果 |
| `extract_all_text_with_positions()` | 从 XML 中提取所有文本及坐标 |
| `_is_product_name()` | 过滤非商品名的文本标签 |
| `parse_product_cards()` | X列匹配解析商品卡片 |
| `scrape_all_results()` | 滚动加载所有搜索结果 |
| `_extract_real_links()` | 点击进入详情页提取真实标题和链接（前3个） |
| `run_scrape()` | 完整采集入口 |

**当前策略**：以搜索结果列表采集为主，**不再逐个点击详情页**（曾因返回后结果移位导致采集错误商品）。仅在最后点击前3个最新商品补充真实标题和链接。

### 5.2 `core/link_extractor.py`

当前真实链接获取方式（已取消粘贴步骤）：

1. 在商品详情页点击右上角分享按钮 (858, 56)
2. 点击"复制链接" (186, 1315)
3. 通过 ADB `dumpsys clipboard` 直接读取剪贴板中的 URL
4. 按返回键关闭分享弹窗
5. 再按返回键回到搜索结果

**实现要点**：
- 新增 `get_clipboard_url(device_serial)`：使用 `adbutils.AdbClient()` 执行 `dumpsys clipboard`，正则匹配 `yangkeduo.com` 商品链接
- 新增 `_get_device_serial(device)`：从 u2 设备对象或 `config.device_serial` 获取序列号
- `extract_product_link()` 不再打开搜索栏、不再长按粘贴、不再读取 EditText

**限制与注意**：
- 依赖 ADB shell 权限读取剪贴板；在部分 Android 15 真机上 `dumpsys clipboard` 可能返回 `<REDACTED>`
- 当前已在 MuMu 模拟器环境验证方向，若 ADB 读取失败会回退到空链接并记录日志
- 如方案 A 在目标设备上不可用，需启用方案 C（Android helper app 接收分享）

**用户原需求**：取消粘贴到搜索框这一步，直接将链接同步到后台。——已实现为 ADB 剪贴板读取方案。

### 5.3 `core/detail_scraper.py`

详情页数据采集工具，目前主要在 `_deep_scrape_specs()` 中用于补充店铺名（最多4个缺店铺名的商品）。

### 5.4 `core/parser.py`

文本解析器：
- `parse_sales_volume()`：将"已拼1.2万件"解析为 12000
- `parse_price()`：解析价格文本
- `normalize_product_name()`：清洗商品名，截断至60字符
- `normalize_shop_name()`：清洗店铺名

### 5.5 `core/db.py`

数据库层：
- `init_db()`：创建所有表
- `upsert_product()`：按商品名前80字符匹配去重
- `compute_daily_sales()`：计算日增量
- `save_sales_record()`：保存销量快照
- `get_dashboard_stats()`：看板统计
- `get_ranking()`：按日增量排序的销量排行（去重每个商品当天最新记录）
- `get_products_list()`：商品列表（含今日/昨日/7天/30天销量，支持排序）
- `get_product_history()` / `get_scrape_logs()`：历史记录和日志

---

## 6. 数据库模型

### `products` 商品主表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| pdd_product_id | String(64), unique | 拼多多内部商品ID（目前未使用） |
| product_name | String(512) | 商品标题 |
| product_link | String(1024) | 商品链接或搜索链接 |
| shop_name | String(256) | 店铺名 |
| keyword | String(128) | 搜索关键词 |
| first_seen | DateTime | 首次发现时间 |
| last_seen | DateTime | 最近出现时间 |
| is_active | Boolean | 是否在售 |

### `sales_records` 销量快照

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| product_id | Integer FK | 关联 products.id |
| scrape_time | DateTime | 精确采集时间 |
| scrape_date | Date | 采集日期 |
| price | Float | 价格 |
| sales_volume | Integer | 累计销量 |
| daily_sales | Integer | 估算日销量（与上条差值） |
| rank_position | Integer | 搜索排名 |
| raw_sales_text | String(64) | 原始销量文本 |

### `scrape_logs` 采集日志

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| started_at | DateTime | 开始时间 |
| finished_at | DateTime | 结束时间 |
| status | String(20) | running/success/failed |
| products_found | Integer | 发现商品数 |
| records_saved | Integer | 保存记录数 |
| error_message | Text | 错误信息 |
| keyword_used | String(128) | 使用关键词 |

---

## 7. Web 界面与 API

### 页面路由 (`web/routes.py`)

| 路由 | 页面 |
|------|------|
| `/` | 看板 Dashboard |
| `/products` | 商品列表 |
| `/products/<id>` | 商品详情 |
| `/logs` | 采集日志 |
| `/settings` | 系统设置 |

### REST API (`web/api.py`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/dashboard/stats` | GET | 看板统计卡片 |
| `/api/dashboard/ranking` | GET | 销量排行 |
| `/api/dashboard/trend` | GET | 销量趋势 |
| `/api/products` | GET | 商品列表（分页/排序/搜索） |
| `/api/products/<id>/info` | GET | 商品基本信息 |
| `/api/products/<id>/history` | GET | 商品历史销量 |
| `/api/logs` | GET | 采集日志分页 |
| `/api/scrape/trigger` | POST | 手动触发采集 |
| `/api/scrape/status` | GET | 最新采集状态 |
| `/api/scheduler/status` | GET | 调度器状态 |
| `/api/settings` | GET/POST | 读取/保存设置 |

### 前端关键文件

- `web/static/js/dashboard.js`：看板统计、排行、趋势图
- `web/static/js/products.js`：商品列表分页/排序、商品详情、历史趋势
- `web/static/css/dashboard.css`：样式

---

## 8. 配置系统

配置从 `.env` 文件读取，由 `config.py` 管理：

| 环境变量 | 说明 | 当前值 |
|----------|------|--------|
| `DEVICE_SERIAL` | 设备序列号 | `127.0.0.1:5555` |
| `SEARCH_KEYWORD` | 搜索关键词 | `莜面鱼` |
| `SCRAPE_CRON` | 采集定时 | `*/10 * * * *`（每10分钟） |
| `MAX_SCROLLS` | 最大滚动次数 | `100` |
| `SCROLL_PAUSE_SECONDS` | 滚动间隔 | `5` |
| `MAX_RESULTS` | 最大商品数 | `200` |
| `WEB_HOST` / `WEB_PORT` | Web服务 | `0.0.0.0:5000` |
| `MYSQL_*` | MySQL配置 | 空=使用SQLite |

设置页面 (`/settings`) 可动态修改配置并写入 `.env`。

---

## 9. 部署与运行方式

### 启动 Web 看板（含定时任务）

```bash
python main.py
```

### 单次采集

```bash
python main.py --run-once
python main.py --run-once --keyword "莜面鱼" --device "127.0.0.1:5555"
```

### 注册 Windows 计划任务

```bash
python main.py --register-task
```

### 纯 Web（无调度器）

```bash
python main.py --no-scheduler
```

### 运行测试

```bash
python tests/test_all.py
python tests/test_commercial.py
python tests/test_parser.py
```

---

## 10. 已知问题与限制

### 10.1 关键待解决问题

1. ~~**真实商品链接提取依赖搜索框粘贴**~~ ✅ 已改为 ADB `dumpsys clipboard` 方案
   - 当前方案：分享 → 复制链接 → ADB 读取剪贴板 → 返回
   - 注意：在部分 Android 15 真机上 `dumpsys clipboard` 可能返回 `<REDACTED>`，若失败需启用 Android helper app 方案（分享到本地应用）

2. **店铺名采集覆盖率低**
   - 当前仅在 `_deep_scrape_specs()` 中补充最多4个缺店铺名的商品
   - 商品列表中大量店铺名显示为 `-`

3. **商品标题仍主要来自搜索列表**
   - 搜索列表标题可能被截断（约30字符）
   - 仅在 `_extract_real_links()` 中对前3个商品从详情页 content-desc 更新标题

4. **链接与商品匹配可能不准确**
   - `_extract_real_links()` 当前按"最近出现"取3个商品，点击可见卡片提取链接后赋值给这3个商品
   - 如果搜索结果顺序与 DB 中的 `last_seen` 顺序不一致，会导致链接错配
   - 长期应改为按商品名/详情页标题精确匹配，或从真实链接中解析 `goods_id` 作为去重主键

### 10.2 稳定性问题

- 详情页返回后搜索结果页可能移位，导致再次点击错误商品
- PDD 反爬机制可能导致搜索被拦截（已加慢速真人模式）
- 坐标硬编码（如分享按钮 858,56）在不同分辨率设备上可能需要调整

### 10.3 数据准确性

- 累计销量为 PDD 展示值，非精确实时值
- 日增量 = 本次累计 - 上次累计，受采集频率和 PDD 数据波动影响
- 不同店铺可能销售同名商品，当前按商品名前80字符去重可能合并不同商品

---

## 11. 后续开发建议

### 高优先级

1. **实现免粘贴的真实链接提取**
   - 调研 Android 15 剪贴板限制的可行绕过方案
   - 优先尝试 `dumpsys clipboard` 和 ADB shell 方案
   - 如不可行，考虑使用无障碍服务

2. **提升店铺名覆盖率**
   - 在搜索结果列表中直接识别店铺名（如卡片底部文本）
   - 或增加详情页补充店铺名的商品数量

3. **完善商品标题**
   - 对所有商品补充详情页真实标题
   - 需要解决"详情页返回后列表移位"问题

### 中优先级

4. **增加 PDD 商品ID（pdd_product_id）的提取**
   - 从真实链接中解析 `goods_id`
   - 改用以 `goods_id` 为主的去重依据

5. **优化反爬策略**
   - 随机化滚动位置、停留时间
   - 增加登录态/设备指纹管理
   - 失败重试和自动恢复

6. **数据质量监控**
   - 检测销量异常波动
   - 自动标记可疑记录

### 低优先级

7. **MySQL 生产部署**
   - 完善 MySQL 配置和连接池

8. **多关键词支持**
   - 支持同时监控多个关键词

9. **数据导出**
   - 增加 Excel/CSV 导出功能

---

## 12. 调试技巧

- 查看日志：`logs/app.log`
- 数据库查看：`data/scraper.db`（可用 SQLite 浏览器）
- 实时检查设备：`adb -s 127.0.0.1:5555 shell dumpsys window displays`
- 获取当前界面 XML：`python -c "import uiautomator2 as u2; d=u2.connect('127.0.0.1:5555'); print(d.dump_hierarchy())"`
- 截图保存：`d.screenshot('logs/debug.png')`

---

## 13. 版本历史

| Commit | 说明 |
|--------|------|
| `66b1966` | refactor: 回归稳定的搜索结果采集方案 |
| `ab30a4b` | feat: 从商品详情页提取真实商品标题(content-desc) |
| `aee9a25` | feat: 商品链接改为真实商品URL(分享→复制链接→粘贴提取) |
| `d88b978` | feat: 商品列表支持点击表头按销量排序 |
| `a0f9603` | feat: 排行榜改为按日增量排序，去重显示每个商品最新记录 |
| `f5becad` | fix: 定时采集不执行 - 设备序列号未传递导致连接失败 |
| `96b6e92` | fix: 添加调度器看门狗，每60秒自动检测并重启已停止的调度器 |
| `de92dce` | feat: 拼多多莜面鱼销量采集监控系统 v1.0 |
