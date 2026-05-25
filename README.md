# 📈 支付宝基金智能分析系统

基于 LLM 的公募基金智能分析系统，每日自动分析自选基金并推送「决策报告」到企业微信/飞书/Telegram/邮件。

> 灵感来源于 [ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)，将分析对象从股票转换为公募基金。

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| **AI 决策报告** | 综合评级（推荐/观望/谨慎）、业绩分析、风险评估、持仓解读、操作建议 |
| **多维度分析** | 业绩表现、风险指标（夏普/回撤/波动率）、持仓分析、基金经理、费率结构 |
| **智能评分** | 0-100 综合评分，五维度加权算法（业绩35%/风险25%/排名15%/经理15%/费用10%）|
| **多渠道推送** | 企业微信/飞书/Telegram/邮件 |
| **零成本部署** | GitHub Actions 免费定时运行 |
| **数据持久化** | SQLite 存储历史净值和分析报告 |

## 🚀 快速开始

### 方式一：GitHub Actions（推荐）

1. **Fork 本仓库**

2. **配置 Secrets**

   `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

   | Secret 名称 | 说明 | 必填 |
   |------------|------|:----:|
   | `FUND_CODES` | 基金代码，逗号分隔，如 `161725,110011,005827` | ✅ |
   | `LLM_PRIMARY_API_KEY` | 主模型 API Key | ✅ |
   | `WECHAT_WEBHOOK_URL` | 企业微信 Webhook | 至少一个 |
   | `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | |
   | `TELEGRAM_CHAT_ID` | Telegram Chat ID | |
   | `EMAIL_SENDER` | 发件人邮箱 | |
   | `EMAIL_PASSWORD` | 邮箱密码/授权码 | |
   | `EMAIL_RECEIVERS` | 收件人邮箱，逗号分隔 | |

3. **启用 Actions**

   `Actions` 标签 → `I understand my workflows, go ahead and enable them`

4. **手动测试**

   `Actions` → `Daily Fund Analysis` → `Run workflow`

### 方式二：本地运行

```bash
# 克隆项目
git clone <your-repo-url>
cd daily_fund_analysis

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写配置

# 测试系统
python main.py test

# 运行分析
python main.py run --funds 161725,110011,005827

# 仅计算指标（不调用 LLM）
python main.py run --funds 161725 --dry-run

# 查看基金信息
python main.py info 161725

# 查看历史报告
python main.py history 161725
```

## 📊 分析报告示例

```
🎯 2026-05-24 基金分析报告
共分析3只基金 | 🟢推荐:1 🟡观望:1 🔴谨慎:1

📊 分析结果摘要
🟢 招商中证白酒指数(LOF)A(161725): 推荐 | 评分 82 | 业绩优秀，风险可控
🟡 易方达消费行业股票(110022): 观望 | 评分 65 | 表现中等，等待机会
🔴 景顺长城沪深300指数增强(000311): 谨慎 | 评分 45 | 风险较高，谨慎对待
```

## ⚙️ 配置说明

所有配置项以 `DFA_` 为前缀，通过环境变量或 `.env` 文件设置。

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DFA_FUND_CODES` | 基金代码列表，逗号分隔 | - |
| `DFA_LLM_PRIMARY_MODEL` | 主 LLM 模型 | `gpt-4o-mini` |
| `DFA_LLM_PRIMARY_API_KEY` | 主模型 API Key | - |
| `DFA_LLM_FALLBACK_MODEL` | 备选 LLM 模型 | `deepseek-chat` |
| `DFA_RISK_FREE_RATE` | 无风险利率 | `0.025` |
| `DFA_NAV_HISTORY_DAYS` | 净值历史天数 | `365` |
| `DFA_DATABASE_URL` | 数据库路径 | `sqlite:///data/fund_analysis.db` |

## 📐 评分算法

| 维度 | 权重 | 说明 |
|------|------|------|
| 业绩表现 | 35% | 近1月/3月/6月/1年/今年来收益加权 |
| 风险控制 | 25% | 最大回撤、夏普比率、年化波动率 |
| 排名分位 | 15% | 同类基金排名百分位 |
| 基金经理 | 15% | 任职年限、历史业绩 |
| 费用成本 | 10% | 管理费+托管费+销售服务费 |

评级规则：
- 🟢 **推荐**: 评分 ≥ 75
- 🟡 **观望**: 55 ≤ 评分 < 75
- 🔴 **谨慎**: 评分 < 55

## 📁 项目结构

```
daily_fund_analysis/
├── main.py                      # CLI 入口
├── config/
│   ├── settings.py              # 配置管理
│   └── prompts/                 # LLM prompt 模板
├── data_provider/
│   ├── models.py                # 数据模型
│   ├── base.py                  # 数据源抽象基类
│   ├── akshare_fetcher.py       # akshare 数据源
│   └── manager.py               # 数据源管理器
├── analysis_engine/
│   ├── metrics.py               # 指标计算
│   ├── scorer.py                # 评分逻辑
│   └── report_generator.py      # LLM 报告生成
├── notification/
│   ├── base.py                  # 通知基类
│   ├── sender.py                # 通知管理器
│   └── channels/                # 各渠道实现
├── storage/
│   ├── database.py              # 数据库初始化
│   ├── models.py                # ORM 模型
│   └── repository.py            # 数据访问层
└── .github/workflows/           # GitHub Actions
```

## 🔧 技术栈

- **Python 3.10+**
- **akshare** - 基金数据获取（东方财富数据源）
- **LiteLLM** - 统一 LLM 网关（支持 OpenAI/DeepSeek/通义千问等）
- **SQLAlchemy** - 数据持久化
- **Pydantic** - 数据验证
- **Click** - CLI 框架
- **httpx** - 异步 HTTP 客户端

## 📝 注意事项

1. akshare 数据来自东方财富，请求频率不宜过高，系统已内置限速
2. 基金排名数据依赖 akshare 接口，部分基金可能无法获取排名
3. LLM 报告需要配置 API Key，未配置时自动降级为纯数字报告
4. 本系统仅供参考，不构成投资建议

## 📄 License

MIT License
