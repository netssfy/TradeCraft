# 需求文档

## 简介

TradeCraft（韭菜的交易世界）是一个面向对象设计的自动化量化交易系统，支持回测（Backtest）和模拟盘（Paper）两种运行模式。系统以统一的事件驱动引擎为核心，通过 Trader 抽象封装策略、订单和持仓，提供完整的市场数据接入、绩效分析和报告功能。系统通过桌面端和 Web 端提供用户界面。

---

## 术语表

- **Engine（交易引擎）**：负责驱动主循环、协调所有 Trader 执行交易逻辑的核心类，支持 Backtest 和 Paper 两种运行模式
- **Engine_Mode（引擎模式）**：Engine 的运行模式枚举，取值为 `BACKTEST` 或 `PAPER`
- **Trader（交易员）**：代表一个独立交易主体的类，持有 Strategy、Order_Manager、Portfolio、所属 Market 和可交易 Symbol 列表作为属性
- **Strategy（策略）**：用户编写的交易逻辑基类，实现买卖信号生成；每个 Trader 持有一个 Strategy 实例
- **Strategy_Loader（策略加载器）**：负责动态加载和实例化用户策略文件的类
- **Portfolio（投资组合）**：跟踪持仓、现金余额和盈亏的类；每个 Trader 持有一个 Portfolio 实例
- **Order_Manager（订单管理器）**：负责订单生命周期管理的类；每个 Trader 持有一个 Order_Manager 实例
- **Order（订单）**：表示一笔买卖委托的类，包含订单 ID、标的、方向、数量、类型和状态
- **Data_Feed（数据源基类）**：提供统一行情数据接口的抽象基类，三个数据源各自实现子类
- **AkshareDataFeed**：基于 akshare 库实现的 Data_Feed 子类，支持 CN 市场
- **YfinanceDataFeed**：基于 yfinance 库实现的 Data_Feed 子类，支持 HK 和 US 市场
- **BaostockDataFeed**：基于 baostock 库实现的 Data_Feed 子类，支持 CN 市场
- **Simulator（模拟器）**：在 Backtest 和 Paper 模式下模拟订单撮合的类
- **Context（策略上下文）**：策略执行时可访问的数据和操作接口，由 Engine 在每个 Bar 构造并传入策略
- **Bar（K 线）**：一个时间步长内的 OHLCV 行情数据单元
- **Market_Data（市场数据）**：包含标的代码、所属 Market、时间戳、开盘价、最高价、最低价、收盘价和成交量的数据类
- **Position（持仓）**：某一标的的当前持有数量和成本信息的类
- **Metrics（绩效指标）**：衡量策略表现的量化指标类，如夏普比率、最大回撤等
- **Report（回测报告）**：汇总回测结果和绩效指标的输出类
- **Market_Repository（市场数据仓库）**：负责市场数据本地缓存和查询的类
- **Bar_Interval（K 线周期）**：K 线的时间粒度枚举，取值为 `1m`、`5m`、`15m`、`30m`、`60m`、`1d`
- **Market（市场）**：对应现实世界中的交易市场，如 A 股（CN）、港股（HK）、美股（US）；一个 Market 可能涵盖多个交易所，每个 Market 有独立的交易时段、时区和标的命名规范
- **Symbol（标的代码）**：在特定 Market 内唯一标识一只可交易证券的代码字符串

---

## 需求

### 需求 1：交易引擎核心与运行模式

**用户故事：** 作为量化交易者，我希望系统有一个统一的事件驱动引擎，以便策略能够在回测和模拟盘两种模式下以一致的方式运行。

#### 验收标准

1. THE Engine SHALL 以 1 分钟为步长推进主循环，在每个步长内依次完成"数据推送 → 策略执行 → 订单处理"
2. THE Engine SHALL 支持 `BACKTEST` 和 `PAPER` 两种 Engine_Mode，通过构造参数指定
3. WHILE Engine_Mode 为 `BACKTEST` 时，THE Engine SHALL 直接跳转到下一根 Bar，不等待真实时间流逝
4. WHILE Engine_Mode 为 `PAPER` 时，THE Engine SHALL 等待真实的 1 分钟过去后再推进到下一根 Bar
5. THE Engine SHALL 管理一个或多个 Trader 实例，在每个 Bar 依次驱动所有 Trader 执行策略
6. WHEN Engine 启动时，THE Engine SHALL 完成所有 Trader 及依赖组件的初始化后再开始主循环
7. IF Engine 在事件处理过程中发生未捕获异常，THEN THE Engine SHALL 记录错误日志并安全停止，不丢失已成交的交易记录
8. THE Engine SHALL 支持优雅停止，在收到停止信号后完成当前 Bar 的处理周期再退出

---

### 需求 2：Trader（交易员）

**用户故事：** 作为量化交易者，我希望系统以 Trader 为独立交易主体，并能够限定其所属市场和可交易标的，以便多个策略可以在同一引擎中相互隔离地运行。

#### 验收标准

1. THE Trader SHALL 持有以下属性：Strategy、Order_Manager、Portfolio、所属 Market（单个）、可交易 Symbol 列表（`allowed_symbols`）
2. THE Trader 的 `allowed_symbols` SHALL 支持设为 `None`，表示该 Market 内所有 Symbol 均可交易；若指定列表，则 Trader 只能对列表内的 Symbol 下单
3. IF 策略通过 Context 对不在 `allowed_symbols` 内的 Symbol 下单，THEN THE Order_Manager SHALL 拒绝该订单并记录原因
4. THE Engine SHALL 支持同时管理多个 Trader 实例，各 Trader 的 Portfolio 和 Order_Manager 相互独立
5. WHEN Engine 推进一个 Bar 时，THE Engine SHALL 仅将属于该 Trader 所属 Market 的 Bar 数据推送给对应 Trader
6. THE Trader SHALL 支持配置初始资金，该资金在 Trader 初始化时注入其 Portfolio
7. IF 某个 Trader 的 Strategy 抛出异常，THEN THE Engine SHALL 记录异常信息并跳过该 Trader 当前 Bar，不影响其他 Trader 的执行

---

### 需求 3：策略开发接口

**用户故事：** 作为策略开发者，我希望有一个清晰的策略基类和上下文接口，以便我能够专注于编写交易逻辑而无需关心底层实现。

#### 验收标准

1. THE Strategy SHALL 提供 `initialize(context)` 和 `on_bar(context, bar)` 两个生命周期方法供子类实现
2. WHEN 策略调用 `context.order(symbol, quantity)` 时，THE Context SHALL 将订单请求转发给所属 Trader 的 Order_Manager 处理
3. THE Context SHALL 向策略暴露所属 Trader 的 Portfolio 状态，包括持仓列表、现金余额和总资产净值
4. THE Context SHALL 向策略暴露历史 Bar 数据查询接口，支持按标的和回溯根数查询
5. THE Strategy SHALL 支持自定义参数，参数在 `initialize` 阶段通过 Context 注入

---

### 需求 4：策略加载器

**用户故事：** 作为用户，我希望能够动态加载外部 Python 策略文件，以便在不重启系统的情况下切换或更新策略。

#### 验收标准

1. WHEN 用户指定策略文件路径时，THE Strategy_Loader SHALL 动态导入该 Python 文件并实例化 Strategy 子类
2. IF 策略文件不存在或存在语法错误，THEN THE Strategy_Loader SHALL 返回包含错误描述的失败结果，不抛出未处理异常
3. THE Strategy_Loader SHALL 支持从指定目录扫描并列出所有可用策略文件
4. WHEN 策略文件被重新加载时，THE Strategy_Loader SHALL 使用新版本策略替换旧版本，不影响其他正在运行的 Trader 实例

---

### 需求 5：市场（Market）

**用户故事：** 作为量化交易者，我希望系统能够区分不同的交易市场，以便正确处理各市场的交易时段、时区和标的命名规范。

#### 验收标准

1. THE Market SHALL 以枚举或类的形式定义，初始支持 A 股（CN）、港股（HK）、美股（US）三个市场
2. THE Market SHALL 定义各自的交易时区（CN: Asia/Shanghai，HK: Asia/Hong_Kong，US: America/New_York）
3. THE Market SHALL 定义各自的交易时段，Engine 在 Paper 模式下 SHALL 仅在对应 Market 的交易时段内推进主循环
4. THE Market_Data 和 Order SHALL 均携带 Market 字段，以明确所属市场
5. THE Market_Repository SHALL 按 Market 隔离缓存数据，不同 Market 的同名 Symbol 不会互相覆盖
6. THE Data_Feed 子类 SHALL 各自声明其支持的 Market 列表（AkshareDataFeed 和 BaostockDataFeed 支持 CN，YfinanceDataFeed 支持 HK 和 US）

---

### 需求 6：市场数据管理

**用户故事：** 作为量化交易者，我希望系统能够通过统一接口从多个数据源获取历史和实时市场数据，以便策略能够基于准确的行情数据做出决策。

#### 验收标准

1. THE Data_Feed SHALL 以抽象基类形式定义统一的行情数据接口，AkshareDataFeed、YfinanceDataFeed 和 BaostockDataFeed 各自继承并实现该接口
2. THE Data_Feed SHALL 支持 `1m`、`5m`、`15m`、`30m`、`60m`、`1d` 六种 Bar_Interval 的 K 线数据拉取
3. THE Data_Feed 子类 SHALL 各自声明其每种 Bar_Interval 所能提供的最大历史回溯天数（`max_lookback_days`），Engine 在补数据时以此为上限
4. WHEN 请求历史 K 线数据时，THE Market_Repository SHALL 优先从本地缓存读取，缓存未命中时调用 Data_Feed 从远程拉取并存储
5. THE Market_Repository SHALL 支持按 Symbol、Market、时间范围和 Bar_Interval 查询 Market_Data 列表
6. IF 远程数据源请求失败，THEN THE Data_Feed SHALL 抛出包含数据源名称和失败原因的异常，不返回空数据集作为正常结果
7. THE Market_Data SHALL 包含 Symbol、Market、时间戳、开盘价、最高价、最低价、收盘价和成交量字段
8. FOR ALL 存储的 Market_Data，THE Market_Repository SHALL 保证同一 Symbol 同一 Market 同一时间戳同一 Bar_Interval 的数据唯一性（幂等写入）

---

### 需求 6.1：启动时数据预热

**用户故事：** 作为量化交易者，我希望 Engine 启动时自动将所有 Trader 所需 Symbol 的本地数据补齐到最新，以便回测和模拟盘都能基于完整数据运行。

#### 验收标准

1. WHEN Engine 启动时，THE Engine SHALL 汇总所有 Trader 的 Symbol 列表，对每个 Symbol 的 `1m`、`5m`、`15m`、`30m`、`60m`、`1d` 六种 Bar_Interval 执行数据预热
2. THE Engine SHALL 从 Market_Repository 读取每个 Symbol 每种 Bar_Interval 本地已有数据的最新时间戳，计算与目标时间（回测结束时间或当前时间）之间的缺口
3. IF 缺口大于零，THEN THE Engine SHALL 调用对应 Data_Feed 拉取缺口范围内的数据并写入 Market_Repository
4. IF 缺口超过 Data_Feed 的 `max_lookback_days`，THEN THE Engine SHALL 仅拉取 `max_lookback_days` 范围内的数据，并记录警告日志说明数据不完整
5. IF 本地无任何历史数据（首次运行），THEN THE Engine SHALL 按 Data_Feed 的 `max_lookback_days` 尽可能拉取最长历史
6. WHEN 数据预热完成后，THE Engine SHALL 记录每个 Symbol 各 Bar_Interval 的实际数据起止时间，再启动主循环

---

### 需求 7：投资组合管理

**用户故事：** 作为交易者，我希望系统实时跟踪每个 Trader 的持仓和资金状况，以便随时了解当前的投资组合状态。

#### 验收标准

1. THE Portfolio SHALL 跟踪每个 Symbol 的 Position，包含持仓数量、平均成本和未实现盈亏
2. WHEN 成交事件发生时，THE Portfolio SHALL 更新对应 Symbol 的 Position 和现金余额
3. THE Portfolio SHALL 计算总资产净值（现金余额加上所有持仓的当前市值）
4. WHEN 持仓数量归零时，THE Portfolio SHALL 从持仓列表中移除该 Symbol 的 Position 记录
5. IF 卖出数量超过当前持仓数量，THEN THE Portfolio SHALL 拒绝该操作并返回错误信息
6. THE Portfolio SHALL 记录每笔成交的完整历史，包括时间、Symbol、方向、数量、价格和手续费

---

### 需求 8：订单管理

**用户故事：** 作为交易者，我希望系统能够管理订单的完整生命周期，以便追踪每笔订单从提交到成交的全过程。

#### 验收标准

1. THE Order_Manager SHALL 为每笔 Order 分配唯一订单 ID
2. THE Order_Manager SHALL 跟踪 Order 状态，状态流转为：待提交 → 已提交 → 部分成交 → 全部成交 / 已撤销
3. WHEN Order 状态发生变化时，THE Order_Manager SHALL 发布订单状态变更事件
4. THE Order_Manager SHALL 支持市价单和限价单两种 Order 类型
5. IF 订单在可配置的超时时间内未成交，THEN THE Order_Manager SHALL 自动撤销该 Order
6. THE Order_Manager SHALL 支持手动撤销未完全成交的 Order

---

### 需求 9：回测模式

**用户故事：** 作为策略开发者，我希望能够用历史数据对策略进行回测，以便在真实交易前评估策略的历史表现。

#### 验收标准

1. WHILE Engine_Mode 为 `BACKTEST` 时，THE Engine SHALL 按时间顺序从 Market_Repository 逐 Bar 读取历史 Market_Data 并推送给所有 Trader
2. THE Engine SHALL 支持配置回测的起止日期、Bar_Interval、初始资金和 Symbol 列表
3. THE Simulator SHALL 以当前 Bar 收盘价模拟市价单成交；对于限价单，WHEN 当前 1m Bar 的最高价 >= 限价买单挂单价，或最低价 <= 限价卖单挂单价时，THE Simulator SHALL 以挂单价格认定为成交，不考虑流动性不足的情况
4. THE Simulator SHALL 根据可配置的手续费率计算每笔成交的交易费用
5. WHEN 回测完成时，THE Engine SHALL 为每个 Trader 生成包含绩效指标的 Report
6. THE Engine SHALL 保证回测过程中策略无法通过 Context 访问当前 Bar 之后的数据（无前视偏差）

---

### 需求 10：模拟盘模式

**用户故事：** 作为交易者，我希望能够用真实行情数据进行模拟交易，以便在不承担真实风险的情况下验证策略的实盘表现。

#### 验收标准

1. WHILE Engine_Mode 为 `PAPER` 时，THE Engine SHALL 汇总所有 Trader 的 Symbol 列表，每隔真实 1 分钟通过 Data_Feed 拉取这些 Symbol 的最新 `1m`、`5m`、`15m`、`30m`、`60m` 数据并推送给对应 Trader
2. THE Engine SHALL 在 Paper 模式下使用 Simulator 处理所有 Order 撮合，不向任何真实券商发送订单
3. WHEN 每个 Bar 周期内所有 Trader 的策略执行完毕后，THE Engine SHALL 将本次拉取的新 Bar 数据合并写入 Market_Repository（落盘）
4. WHILE Engine_Mode 为 `PAPER` 时，THE Portfolio SHALL 在每个 Bar 结束后实时更新持仓市值和总资产净值
5. WHEN Paper 模式的 Engine 停止时，THE Engine SHALL 持久化所有 Trader 的 Portfolio 状态，支持下次启动时恢复

---

### 需求 11：绩效指标与报告

**用户故事：** 作为策略开发者，我希望回测结束后能够获得详细的绩效报告，以便客观评估策略的风险收益特征。

#### 验收标准

1. THE Metrics SHALL 计算年化收益率、最大回撤、夏普比率、胜率和盈亏比
2. THE Metrics SHALL 基于每日净值序列计算所有时间序列类指标
3. THE Report SHALL 包含策略参数、回测区间、初始资金、最终净值和所有 Metrics 计算结果
4. THE Report SHALL 支持导出为 JSON 格式
5. WHEN 回测区间内交易次数为零时，THE Metrics SHALL 返回各指标的零值或空值，不抛出除零异常
6. FOR ALL 回测报告，THE Report SHALL 包含完整的逐笔成交记录，支持事后审计

---

### 需求 12：数据持久化与日志

**用户故事：** 作为系统运维者，我希望系统的关键操作和数据都有完整的持久化记录，以便在系统故障后能够恢复状态和审计操作历史。

#### 验收标准

1. THE Engine SHALL 将所有 Trader 的成交记录持久化存储，存储格式支持按运行 ID 和 Trader ID 查询
2. THE Engine SHALL 记录结构化运行日志，日志级别支持 DEBUG、INFO、WARNING、ERROR
3. THE Market_Repository SHALL 将下载的历史数据缓存到本地文件系统，路径结构为 `data/market/{Market}/{Symbol}/{Bar_Interval}/`
4. IF 持久化写入失败，THEN THE Engine SHALL 记录错误日志并继续运行，不因存储故障中断主循环

---

### 需求 13：配置管理

**用户故事：** 作为用户，我希望能够通过配置文件灵活调整系统参数，以便在不修改代码的情况下定制系统行为。

#### 验收标准

1. THE Engine SHALL 从配置文件加载运行模式、Trader 列表（含各 Trader 的所属 Market、allowed_symbols、初始资金和策略路径）、Bar_Interval 及数据源类型
2. THE Engine SHALL 支持通过环境变量覆盖配置文件中的任意参数
3. IF 配置文件缺少必填字段，THEN THE Engine SHALL 在启动时报告缺失字段并拒绝启动
4. THE Engine SHALL 支持 YAML 格式的配置文件
5. WHERE 提供了多个配置文件时，THE Engine SHALL 按照"环境变量 > 用户配置 > 默认配置"的优先级合并配置
