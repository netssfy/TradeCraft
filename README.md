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
│   ├── app/
│   │   ├── api/                  # REST / WebSocket 接口
│   │   ├── core/                 # 配置、依赖注入、通用基础设施
│   │   ├── engine/               # 核心交易引擎（只保留一份）
│   │   │   ├── core.py           # 策略执行主流程
│   │   │   ├── context.py        # 运行上下文
│   │   │   ├── orders.py         # 订单模型
│   │   │   ├── portfolio.py      # 仓位 / 资金状态
│   │   │   ├── risk.py           # 风控逻辑
│   │   │   └── events.py         # 行情 / 订单 / 成交事件
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
├── data/                         # 本地数据目录（gitignore）
│   ├── market/
│   ├── cache/
│   ├── logs/
│   ├── runs/
│   └── strategies/
│
├── package.json
└── README.md
```
