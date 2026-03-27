# TradeCraft
“韭菜的交易世界”是一个面向普通股民的AI交易观测系统。它通过构建和运行多个AI“交易员”，模拟不同交易逻辑，在真实市场环境中持续观测、记录与评估其表现，并为用户提供可跟随、可理解的投资参考。

我是什么：

* 面向资金体量有限的普通股民的交易参考系统
* 以AI交易员为核心的策略模拟与观察平台
* 强调可理解、可跟随的简单交易逻辑（非黑箱）
* 聚焦少数常见交易标的（如A股/美股股票）
* 提供持续跟踪、复盘与结果展示的决策辅助工具

我不是什么：

* 不是高频量化或超低延迟交易系统
* 不是覆盖全资产、多市场的复杂组合投资平台
* 不是做空、杠杆或衍生品驱动的高风险系统
* 不是追求极致收益、忽视风险的投机工具
* 不是替代用户决策的全自动“稳赚不赔”交易机器人

## 项目结构

```
├── packages/
│   ├── web/                      # Web 前端
│   │   └── src/
│   │
│   ├── desktop/                  # Electron 桌面端
│   │   └── src/
│   │       ├── main/             # Electron main process
│   │       └── renderer/         # 可复用前端页面
│   │
│   └── shared/                   # 前端共享类型、工具、组件
│       └── src/
│
├── backend/
│   ├── run.py                     # 启动交易引擎（从 data/traders 加载 Trader）
│   ├── server.py                  # 启动 FastAPI 服务（默认 :8000）
│   ├── config.yaml                # 全局运行配置（不再内嵌 traders）
│   ├── app/
│   │   ├── api/                   # REST API
│   │   │   ├── __init__.py        # FastAPI app 实例
│   │   │   └── traders.py         # Trader 资源接口
│   │   ├── core/                 # 配置、依赖注入、通用基础设施
│   │   ├── engine/               # 核心交易引擎（只保留一份）
│   │   │   ├── core.py           # 策略执行主流程
│   │   │   ├── context.py        # 运行上下文
│   │   │   ├── orders.py         # 订单模型
│   │   │   ├── portfolio.py      # 仓位 / 资金状态
│   │   │   ├── risk.py           # 风控逻辑
│   │   │   ├── events.py         # 行情 / 订单 / 成交事件
│   │   │   ├── trader.py         # Trader 实体（支持从目录加载/保存）
│   │   │   └── trader_store.py   # Trader 持久化存储
│   │   │
│   │   ├── runtimes/             # 运行时，只负责驱动 engine
│   │   │   ├── backtest.py       # 回测运行时
│   │   │   ├── live.py           # 实盘运行时
│   │   │   └── paper.py          # 模拟盘 / 纸交易
│   │   │
│   │   ├── adapters/             # 外部系统适配
│   │   │   ├── data_feed.py      # 行情数据源
│   │   │   └── simulator.py      # 模拟撮合
│   │   │
│   │   ├── trading/              # 策略与交易相关业务
│   │   │   ├── strategy.py       # 策略基类
│   │   │   └── strategy_loader.py
│   │   │
│   │   ├── backtest/             # 回测专用能力
│   │   │   ├── metrics.py        # 绩效指标
│   │   │   └── report.py         # 回测报告
│   │   │
│   │   ├── data/                 # 数据访问层
│   │   │   ├── market.py         # 行情数据读写
│   │   │   └── repository.py     # 统一数据仓库
│   │   │
│   │   └── models/               # DTO / 领域模型
│   │
│   ├── strategies/               # 用户自定义策略目录
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.txt
│
├── data/                         # 本地数据目录（gitignore，运行时生成）
│   ├── market/
│   ├── traders/
│   │   └── {trader_id}/
│   │       ├── trader.json
│   │       ├── strategy/
│   │       ├── trades/
│   │       │   ├── paper/
│   │       │   └── backtest/
│   │       └── portfolio/
│   │           ├── paper.json      # 模拟盘每日收盘快照数组
│   │           └── backtest.json   # 回测每日收盘快照数组
│   ├── logs/
│   └── runs/
│
├── package.json
└── README.md
```

## 启动方式

### 1) 启动交易引擎

```bash
cd backend
python run.py
```

- 入口：`backend/run.py`
- 加载方式：`Engine.from_traders_dir(config_path="config.yaml", traders_dir="data/traders")`
- 说明：`config.yaml` 仅保留全局运行项（如 `mode/bar_interval/data_sources`），Trader 配置来自 `data/traders/*/trader.json`

### 2) 启动 REST API

```bash
cd backend
python server.py
```

- 入口：`backend/server.py`
- 文档地址：
  - Swagger UI: `http://127.0.0.1:8000/docs`
  - ReDoc: `http://127.0.0.1:8000/redoc`

## Trader REST API（新增）

基础前缀：`/traders`

- `POST /traders`：创建 Trader（含基础信息与 traits）
- `GET /traders`：获取 Trader 列表
- `GET /traders/{trader_id}`：获取 Trader 详情
- `PATCH /traders/{trader_id}`：更新 Trader 基础信息
- `DELETE /traders/{trader_id}`：删除 Trader
- `GET /traders/{trader_id}/strategy`：获取策略文件列表
- `POST /traders/{trader_id}/strategy`：上传策略文件（`.py`）
- `PUT /traders/{trader_id}/strategy/active?filename=...`：设置激活策略
- `GET /traders/{trader_id}/portfolio/{mode}`：获取持仓历史快照（`mode` 为 `paper` 或 `backtest`），返回每日收盘时的 cash 和 positions 数组，可用于绘制收益率曲线或复盘
- `GET /traders/{trader_id}/trades`：获取成交记录索引（paper/backtest）
- `GET /traders/{trader_id}/trades/{mode}/{run_id}`：获取单次运行成交明细

## 依赖变更（后端）

后端新增 API 相关依赖：

- `fastapi>=0.110`
- `uvicorn[standard]>=0.29`
- `python-multipart>=0.0.9`
