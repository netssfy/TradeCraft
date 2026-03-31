# TradeCraft

AI编写，AI驱动，AI自己研究策略

## 界面预览

> 本节截图来自本地开发环境 `http://localhost:5173`（2026-03-31）。

### 功能截图（桌面端）

#### 交易员列表
![Trader List](docs/images/ui-trader-list.png)

#### 创建交易员
![Create Trader](docs/images/ui-trader-create.png)

#### 交易员详情
![Trader Detail](docs/images/ui-trader-detail.png)

#### 策略源码页
![Strategy Code](docs/images/ui-strategy-code.png)

#### 市场数据页
![Market Data](docs/images/ui-market-data.png)

### 演示动图

![TradeCraft Overview GIF](docs/images/ui-overview.gif)


## 目录结构

```text
TradeCraft/
├─ backend/
│  ├─ app/
│  │  ├─ adapters/
│  │  ├─ api/
│  │  ├─ backtest/
│  │  ├─ core/
│  │  ├─ data/
│  │  ├─ engine/
│  │  ├─ models/
│  │  ├─ runtimes/
│  │  └─ trading/
│  └─ tests/
├─ packages/
│  ├─ shared/
│  │  └─ src/
│  │     ├─ types/
│  │     └─ utils/
│  └─ web/
│     ├─ dist/
│     └─ src/
│        ├─ components/
│        ├─ hooks/
│        ├─ pages/
│        ├─ services/
│        └─ styles/
├─ skills/
│  └─ retail-quant-trainer/
│     ├─ agents/
│     └─ references/
└─ .kiro/
```

## 运行时数据目录（重要）

> 以下目录通常在运行后生成，默认位于项目根目录 `data/` 下。

```text
data/
├─ market/
│  └─ {market}/{symbol}/{interval}/{period}.parquet
└─ traders/
   └─ {trader_id}/
      ├─ trader.json
      ├─ strategy/
      │  └─ *.py
      ├─ trades/
      │  ├─ paper/{run_id}/trades.json
      │  └─ backtest/{run_id}/
      │     ├─ trades.json
      │     └─ report.json
      └─ portfolio/
         ├─ paper.json
         └─ {backtest_run_id}.json
```

## 系统功能总览

### 交易员管理

- 创建交易员：支持填写市场（CN/HK/US）、初始资金、可交易标的、手续费率、订单超时。
- 创建过程支持 SSE 流式反馈：前端可实时查看训练/生成日志与错误信息。
- 自动生成六维交易特质：风险偏好、持有周期、信号偏好、仓位构建、止盈止损纪律、标的偏好。
- 查询交易员列表与详情：查看基础参数、特质、策略、组合表现。
- 编辑交易员：支持更新资金、标的池、手续费、超时参数和特质字段。
- 删除交易员：删除交易员及其目录数据。

### 策略管理与研究

- 策略文件管理：列出策略文件并设置 active strategy。
- 策略源码查看：支持从交易员详情页新窗口打开策略源码页面。
- 策略研究（Create/Update）：通过 Codex 流式执行研究，支持新建策略或基于指定策略更新。
- 策略研究日志可视化：前端按 info/warning/error/result 分类展示流式消息。

### 回测与组合分析

- 一键运行回测：支持配置起止日期与回测策略文件。
- 支持未设置 active strategy 的回测执行（可显式指定策略文件）。
- 回测 Run 管理：列出 run_id、按 run_id 查看交易与组合快照。
- 回测报告：提供年化收益、最大回撤、夏普、胜率、盈亏比、最终净值等指标。
- 回测筛选：按策略文件筛选回测 run。
- 删除回测 run：删除 run 对应交易记录、报告和组合快照文件。
- 交易记录分页展示：按模式（paper/backtest）与 run 维度查看。

### 市场数据浏览

- 市场数据可用性总览：统计市场数、标的数、周期数、组合数、文件总数。
- 本地 parquet 结构扫描：按 `{market}/{symbol}/{interval}/{period}` 聚合展示。
- 文件级明细浏览：分页读取 parquet 行数据并展示字段列。
- 支持从总览直接跳转到指定 period 的文件详情页。

### 运行时数据与持久化

- 交易员数据目录化：每个交易员独立存放配置、策略、交易记录、组合快照。
- 回测记录按 run_id 结构化存储：`trades/backtest/{run_id}/trades.json` 与 `report.json`。
- 组合快照支持 paper 与 backtest 分离，backtest 支持按 run_id 单文件存储。
- 兼容历史数据布局：读取和删除逻辑包含旧格式回退处理。

### 前端体验与可用性

- 中英文界面切换（zh/en），并持久化语言偏好。
- 明暗主题切换（dark/light），并持久化主题偏好。
- 统一错误提示、加载态、空态展示。
- 交易员列表支持按 paper 收益排序并展示近期回测组合收益摘要。

### 后端与开放接口

- FastAPI 服务，自动提供 OpenAPI 文档：`/docs` 与 `/redoc`。
- 交易员 API：创建、查询、更新、删除、策略管理、组合查询、交易查询、回测执行与删除。
- 市场数据 API：可用性查询与文件明细分页查询。
- 跨域支持：默认允许本地前端开发地址访问（5173）。
