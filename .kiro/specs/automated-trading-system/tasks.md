# 实现计划：TradeCraft 自动化交易系统

## 概览

按照"基础设施 → 数据模型 → 数据层 → 核心引擎 → 策略层 → 主引擎 → 指标报告 → 测试"的顺序逐步实现。每个任务在前一任务的基础上构建，最终通过集成测试将所有组件串联。

## 任务

- [x] 1. 项目基础设施与配置
  - 在 `backend/pyproject.toml` 中声明项目元数据和依赖（pandas、pyarrow、pyyaml、hypothesis、pytest、akshare、yfinance、baostock）
  - 在 `backend/requirements.txt` 中生成对应的依赖列表
  - 在 `backend/app/` 各子目录下创建 `__init__.py`，确保包结构可导入
  - 在 `backend/tests/` 下创建 `__init__.py` 和 `conftest.py`（含公共 fixture 占位）
  - 创建 `backend/app/core/config.py`：定义 `Config` 数据类及 YAML 加载函数，支持环境变量覆盖，缺少必填字段时抛出 `ConfigError`
  - 创建 `backend/app/core/logging.py`：封装结构化日志初始化，支持 DEBUG/INFO/WARNING/ERROR 级别和文件输出
  - _需求：13.1, 13.2, 13.3, 13.4, 13.5, 12.2_

- [ ] 2. 基础数据模型
  - [x] 2.1 实现枚举与核心数据类
    - 在 `backend/app/data/market.py` 中实现：`Market`（CN/HK/US）、`BarInterval`（M1/M5/M15/M30/H1/D1）、`MarketInfo`、`MARKET_INFO` 字典
    - 在 `backend/app/engine/models.py` 中实现：`Bar`、`Direction`、`OrderType`、`OrderStatus`、`Order`、`Fill`、`Trade`、`Position` 数据类
    - 所有数据类使用 `@dataclass`，`Order.id` 默认生成 UUID
    - _需求：5.1, 5.2, 6.7, 8.1, 8.2_

  - [ ]* 2.2 为 Bar 数据类编写属性测试
    - **属性 12：Simulator 撮合规则（前置验证 Bar 字段约束）**
    - **验证需求：9.3**

- [ ] 3. MarketRepository（本地数据存储）
  - [x] 3.1 实现 `MarketRepository` 类
    - 在 `backend/app/data/repository.py` 中实现 `MarketRepository`
    - `write()` 方法：按 `data/market/{Market}/{Symbol}/{interval}/YYYY-MM.parquet` 路径分片存储，幂等写入（按时间戳去重），返回实际新增条数
    - `read()` 方法：按 Symbol、Market、interval、时间范围查询，结果按时间戳升序排列
    - `get_latest_timestamp()` 方法：返回本地最新数据时间戳，无数据时返回 `None`
    - _需求：6.4, 6.5, 6.8, 5.5, 12.3_

  - [ ]* 3.2 编写属性测试：幂等写入
    - **属性 10：幂等写入**
    - **验证需求：6.8**

  - [ ]* 3.3 编写属性测试：Market 数据隔离存储
    - **属性 11：Market 数据隔离存储**
    - **验证需求：5.5**

- [ ] 4. DataFeed 抽象基类与三个子类
  - [x] 4.1 实现 `DataFeed` 抽象基类
    - 在 `backend/app/adapters/data_feed.py` 中定义 `DataFeed` ABC，声明 `supported_markets`、`max_lookback_days` 类变量和 `fetch()` 抽象方法
    - 失败时抛出包含数据源名称和原因的异常（`DataFeedError`）
    - _需求：6.1, 6.2, 6.3, 6.6_

  - [x] 4.2 实现 `AkshareDataFeed`
    - 继承 `DataFeed`，`supported_markets = [Market.CN]`，实现 `fetch()` 调用 akshare API
    - 按设计文档配置 `max_lookback_days`
    - _需求：5.6, 6.1, 6.2_

  - [x] 4.3 实现 `YfinanceDataFeed`
    - 继承 `DataFeed`，`supported_markets = [Market.HK, Market.US]`，实现 `fetch()` 调用 yfinance API
    - 按设计文档配置 `max_lookback_days`
    - _需求：5.6, 6.1, 6.2_

  - [x] 4.4 实现 `BaostockDataFeed`
    - 继承 `DataFeed`，`supported_markets = [Market.CN]`，实现 `fetch()` 调用 baostock API
    - 按设计文档配置 `max_lookback_days`
    - _需求：5.6, 6.1, 6.2_

  - [ ]* 4.5 编写 DataFeed 单元测试（mock 网络请求）
    - 使用 `unittest.mock` 模拟三个子类的 `fetch()` 返回值，验证接口契约
    - 验证 `fetch()` 失败时抛出 `DataFeedError`
    - _需求：6.6_

- [x] 5. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有问题请向用户提问。

- [ ] 6. Portfolio 与 OrderManager
  - [x] 6.1 实现 `Portfolio`
    - 在 `backend/app/engine/portfolio.py` 中实现 `Portfolio` 类
    - `update_on_fill(fill)` 方法：买入时增加持仓并扣减现金（含手续费），卖出时减少持仓并增加现金（扣手续费），持仓归零时移除 `Position`
    - `net_value(prices)` 方法：现金 + 所有持仓数量 × 对应价格
    - `can_sell(symbol, quantity)` 方法：检查持仓是否充足
    - `trade_history` 属性：记录每笔成交的完整 `Trade` 对象
    - _需求：7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 6.2 编写属性测试：Portfolio 净值计算
    - **属性 14：Portfolio 净值计算**
    - **验证需求：7.3**

  - [ ]* 6.3 编写属性测试：成交后 Portfolio 状态更新
    - **属性 15：成交后 Portfolio 状态更新**
    - **验证需求：7.1, 7.2**

  - [ ]* 6.4 编写属性测试：卖出超量被拒绝
    - **属性 16：卖出超量被拒绝**
    - **验证需求：7.5**

  - [ ]* 6.5 编写属性测试：成交历史完整性
    - **属性 17：成交历史完整性**
    - **验证需求：7.6**

  - [x] 6.6 实现 `EventBus`
    - 在 `backend/app/engine/events.py` 中实现 `EventType` 枚举和 `EventBus` 类（`subscribe`/`publish`）
    - _需求：8.3_

  - [x] 6.7 实现 `OrderManager`
    - 在 `backend/app/engine/orders.py` 中实现 `OrderManager` 类
    - `submit(order)` 方法：校验 `allowed_symbols`，分配 UUID，状态设为 `SUBMITTED`，拒绝时记录原因
    - `cancel(order_id)` 方法：手动撤销未完全成交的订单
    - `process_fill(fill)` 方法：更新订单状态，通过 `EventBus` 发布状态变更事件
    - `cancel_expired(current_time)` 方法：撤销所有超时未成交的订单
    - `get_open_orders()` 方法：返回所有未完成订单
    - _需求：2.2, 2.3, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 6.8 编写属性测试：订单 ID 唯一性
    - **属性 18：订单 ID 唯一性**
    - **验证需求：8.1**

  - [ ]* 6.9 编写属性测试：订单状态合法流转
    - **属性 19：订单状态合法流转**
    - **验证需求：8.2**

  - [ ]* 6.10 编写属性测试：allowed_symbols 权限校验
    - **属性 4：allowed_symbols 权限校验**
    - **验证需求：2.2, 2.3**

- [ ] 7. Simulator（撮合引擎）
  - [x] 7.1 实现 `Simulator`
    - 在 `backend/app/adapters/simulator.py` 中实现 `Simulator` 类
    - `match(order, bar)` 方法：市价单以 `bar.close` 成交；限价买单 `bar.high >= limit_price` 时以 `limit_price` 成交；限价卖单 `bar.low <= limit_price` 时以 `limit_price` 成交；不满足条件返回 `None`
    - 手续费 = 成交金额 × `commission_rate`
    - _需求：9.3, 9.4_

  - [ ]* 7.2 编写属性测试：Simulator 撮合规则
    - **属性 12：Simulator 撮合规则**
    - **验证需求：9.3**

  - [ ]* 7.3 编写属性测试：手续费计算正确性
    - **属性 13：手续费计算正确性**
    - **验证需求：9.4**

- [ ] 8. Strategy 基类、Context 与 StrategyLoader
  - [x] 8.1 实现 `Strategy` 抽象基类
    - 在 `backend/app/trading/strategy.py` 中实现 `Strategy` ABC，定义 `initialize(context)` 和 `on_bar(context, bar)` 抽象方法
    - _需求：3.1, 3.5_

  - [x] 8.2 实现 `Context`
    - 在 `backend/app/engine/context.py` 中实现 `Context` 类
    - `portfolio` 属性：只读访问当前 Trader 的 Portfolio
    - `order(symbol, qty, order_type, limit_price)` 方法：转发给 `OrderManager.submit()`
    - `history(symbol, interval, n)` 方法：查询历史 Bar，只返回严格早于 `current_time` 的数据（防止前视偏差）
    - _需求：3.2, 3.3, 3.4, 9.6_

  - [ ]* 8.3 编写属性测试：历史 Bar 查询无前视偏差
    - **属性 8：历史 Bar 查询无前视偏差**
    - **验证需求：9.6**

  - [x] 8.4 实现 `StrategyLoader`
    - 在 `backend/app/trading/strategy_loader.py` 中实现 `StrategyLoader` 类
    - `load(file_path, params)` 方法：动态导入 Python 文件，实例化 `Strategy` 子类；文件不存在或语法错误时返回 `success=False` 的 `LoadResult`，不抛出未处理异常
    - `scan(directory)` 方法：扫描目录，返回所有 `.py` 策略文件路径
    - _需求：4.1, 4.2, 4.3, 4.4_

  - [ ]* 8.5 编写属性测试：策略文件加载失败返回失败结果
    - **属性 9：策略文件加载失败返回失败结果**
    - **验证需求：4.2**

- [ ] 9. Trader
  - [x] 9.1 实现 `Trader`
    - 在 `backend/app/engine/trader.py` 中实现 `Trader` 类（组合 Strategy、OrderManager、Portfolio）
    - `initialize(context)` 方法：调用 `strategy.initialize(context)`
    - `on_bar(bar)` 方法：构造 `Context`，调用 `strategy.on_bar(context, bar)`，再调用 `order_manager.cancel_expired(bar.timestamp)`，最后对所有挂单调用 `simulator.match(order, bar)` 并处理成交
    - _需求：2.1, 2.2, 2.6_

  - [ ]* 9.2 编写属性测试：Trader 隔离性
    - **属性 3：Trader 隔离性**
    - **验证需求：2.4**

  - [ ]* 9.3 编写属性测试：初始资金注入
    - **属性 6：初始资金注入**
    - **验证需求：2.6**

- [x] 10. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有问题请向用户提问。

- [ ] 11. Engine（主循环、数据预热、BACKTEST/PAPER 模式）
  - [x] 11.1 实现 `Engine._warmup()`
    - 在 `backend/app/engine/core.py` 中实现 `Engine` 类的 `_warmup()` 方法
    - 汇总所有 Trader 的 Symbol 列表，对每个 Symbol × 6 种 BarInterval 循环
    - 从 `MarketRepository.get_latest_timestamp()` 读取本地最新时间戳，计算缺口
    - 缺口超过 `max_lookback_days` 时截断并记录 WARNING；首次运行时按 `max_lookback_days` 尽量拉取
    - 调用对应 `DataFeed.fetch()` 拉取数据并写入 `MarketRepository`
    - 预热完成后记录每个 Symbol 各 BarInterval 的实际起止时间
    - _需求：6.1.1, 6.1.2, 6.1.3, 6.1.4, 6.1.5, 6.1.6_

  - [x] 11.2 实现 `Engine._tick()` 与 `Engine._run_loop()`
    - `_tick(bar_time)` 方法：按 Market 分发 Bar 给对应 Trader → 依次调用 `trader.on_bar()` → PAPER 模式下落盘新 Bar 数据
    - `_run_loop()` 方法：BACKTEST 模式从 Repository 按时间顺序逐 Bar 读取推进；PAPER 模式等待真实 1 分钟后拉取最新数据
    - 某个 Trader 的 Strategy 抛出异常时记录 ERROR 日志并跳过该 Trader，不影响其他 Trader
    - _需求：1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 2.5, 2.7, 9.1, 10.1, 10.2, 10.3, 10.4_

  - [x] 11.3 实现 `Engine.start()` 与 `Engine.stop()`
    - `start()` 方法：执行预热 → 调用所有 `strategy.initialize()` → 启动主循环
    - `stop()` 方法：设置停止标志，等待当前 Bar 完成后退出
    - PAPER 模式停止时持久化所有 Trader 的 Portfolio 状态到 `data/cache/portfolio_{trader_id}.json`
    - 未捕获的 Engine 级异常时记录 ERROR 日志并安全停止，持久化已成交记录
    - _需求：1.6, 1.7, 1.8, 10.5, 12.1_

  - [x] 11.4 实现配置加载与 Engine 工厂函数
    - 在 `backend/app/core/config.py` 中完善 `Config` 加载逻辑：支持 YAML 格式，环境变量覆盖，缺少必填字段时报告所有缺失字段并拒绝启动
    - 实现 `Engine.from_config(config_path)` 工厂方法，根据配置实例化所有组件
    - _需求：13.1, 13.2, 13.3, 13.4, 13.5_

  - [ ]* 11.5 编写属性测试：主循环步长一致性
    - **属性 1：主循环步长一致性**
    - **验证需求：1.1**

  - [ ]* 11.6 编写属性测试：多 Trader 均被驱动
    - **属性 2：多 Trader 均被驱动**
    - **验证需求：1.5, 2.4**

  - [ ]* 11.7 编写属性测试：Market 数据路由
    - **属性 5：Market 数据路由**
    - **验证需求：2.5**

  - [ ]* 11.8 编写属性测试：单个 Trader 异常不影响其他 Trader
    - **属性 7：单个 Trader 异常不影响其他 Trader**
    - **验证需求：2.7**

  - [ ]* 11.9 编写属性测试：回测 Bar 时间戳单调递增
    - **属性 20：回测 Bar 时间戳单调递增**
    - **验证需求：9.1**

  - [ ]* 11.10 编写属性测试：配置加载正确性
    - **属性 24：配置加载正确性**
    - **验证需求：13.1**

  - [ ]* 11.11 编写属性测试：缺少必填字段时拒绝启动
    - **属性 25：缺少必填字段时拒绝启动**
    - **验证需求：13.3**

  - [ ]* 11.12 编写属性测试：多配置优先级合并
    - **属性 26：多配置优先级合并**
    - **验证需求：13.5**

- [ ] 12. Metrics 与 Report
  - [x] 12.1 实现 `Metrics`
    - 在 `backend/app/backtest/metrics.py` 中实现 `Metrics` 类
    - `annualized_return(nav_series, trading_days=252)` 方法
    - `max_drawdown(nav_series)` 方法（返回负值）
    - `sharpe_ratio(nav_series, risk_free_rate=0.02, trading_days=252)` 方法，交易次数为零时返回 `0.0`
    - `win_rate(trades)` 方法，无交易时返回 `0.0`
    - `profit_loss_ratio(trades)` 方法，无交易时返回 `0.0`
    - _需求：11.1, 11.2, 11.5_

  - [ ]* 12.2 编写属性测试：Metrics 计算正确性（含零交易边界情况）
    - **属性 21：Metrics 计算正确性（含零交易边界情况）**
    - **验证需求：11.1, 11.2, 11.5**

  - [x] 12.3 实现 `Report`
    - 在 `backend/app/backtest/report.py` 中实现 `Report` 数据类
    - `to_json()` 方法：序列化为 JSON 字符串（处理 datetime 和 Enum 的序列化）
    - `from_json(json_str)` 类方法：从 JSON 字符串反序列化
    - `Engine._generate_reports()` 方法：回测结束时为每个 Trader 生成 Report，写入 `data/runs/{run_id}/{trader_id}_report.json`
    - _需求：11.3, 11.4, 11.6, 9.5, 12.1_

  - [ ]* 12.4 编写属性测试：Report JSON 序列化往返
    - **属性 22：Report JSON 序列化往返**
    - **验证需求：11.4**

  - [ ]* 12.5 编写属性测试：Report 包含完整成交记录
    - **属性 23：Report 包含完整成交记录**
    - **验证需求：11.6**

- [x] 13. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有问题请向用户提问。

- [ ] 14. 集成测试（端到端回测流程）
  - [x] 14.1 编写端到端回测集成测试
    - 在 `backend/tests/test_integration.py` 中编写集成测试
    - 使用 mock DataFeed 注入预设历史 Bar 数据，运行完整 BACKTEST 流程
    - 验证：Engine 正确推进所有 Bar → 策略收到正确数据 → 订单被撮合 → Portfolio 状态正确 → Report 生成并包含完整成交记录
    - _需求：1.1, 1.5, 9.1, 9.2, 9.5, 9.6, 11.6_

  - [x] 14.2 编写多 Trader 隔离集成测试
    - 验证两个 Trader 在同一 Engine 中运行时，各自的 Portfolio 和 OrderManager 完全独立
    - 验证 Market 数据路由：CN Trader 只收到 CN 的 Bar，US Trader 只收到 US 的 Bar
    - _需求：2.4, 2.5_

  - [x] 14.3 编写错误恢复集成测试
    - 验证某个 Trader 的 Strategy 抛出异常时，其他 Trader 继续正常运行
    - 验证持久化写入失败时 Engine 继续运行主循环
    - _需求：1.7, 2.7, 12.4_

- [x] 15. 最终检查点 — 确保所有测试通过
  - 确保所有测试通过，如有问题请向用户提问。

## 备注

- 标有 `*` 的子任务为可选属性测试，可在 MVP 阶段跳过
- 每个任务引用了对应的需求编号，便于追溯
- 属性测试使用 Hypothesis 库，每个测试最少运行 100 次迭代（`@settings(max_examples=100)`）
- 每个属性测试必须通过注释引用设计文档中对应的属性编号，格式：`# Feature: automated-trading-system, Property N: <属性描述>`
- 所有代码位于 `backend/app/` 下，测试位于 `backend/tests/` 下
- 数据存储路径遵循设计文档中的目录结构：`data/market/{Market}/{Symbol}/{interval}/`
