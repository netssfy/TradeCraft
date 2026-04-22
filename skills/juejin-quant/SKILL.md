---
name: juejin-quant
description: 掘金量化 Python SDK 能力导航与任务映射技能。Use when tasks involve identifying whether Juejin Python SDK supports a requirement, selecting the correct API category (行情订阅、历史数据、交易下单、交易查询、算法交易、标的池、免费/付费数据接口), clarifying callback/data-structure/enum usage, or drafting SDK-aligned strategy code skeletons.
---

# Juejin Quant

将“策略需求”快速映射到掘金 Python SDK 的正确能力域与接口族，并避免把不支持能力误判为可用。

## Quick Workflow

1. 判断任务类型：
- 将请求归类为：行情、交易、查询、算法交易、标的池、基础/财务数据、增值数据、框架与回调、排错。

2. 读取能力地图：
- 优先读取 [references/capability-map.md](references/capability-map.md) 定位能力分区。

3. 检索函数候选：
- 按分区到 [references/function-token-index.md](references/function-token-index.md) 查函数关键词。
- 若用户只问“能不能做”，给出“支持/不支持/需要付费”三态结论。

4. 生成回答或代码骨架：
- 先声明运行模式：`MODE_LIVE` 或 `MODE_BACKTEST`。
- 再给最小可运行结构：`init` + 相关回调（如 `on_tick` / `on_bar` / 交易事件回调）。
- 需要交易时，补充账户、订单状态、成交回报与查询链路。

5. 标注边界与依赖：
- 明确免费接口与付费增值接口边界。
- 明确是否依赖账号权限、交易通道、市场/品种支持范围。

## Capability Routing Rules

- 需要实时行情推送或 K 线驱动：走“数据订阅 + 数据事件”。
- 需要历史行情/历史逐笔：走“行情数据查询函数（免费）”。
- 需要下单、撤单、成交跟踪：走“交易函数 + 交易事件 + 交易查询函数”。
- 需要 ETF/基金/债券/两融/新股新债：走对应专类交易函数页面。
- 需要智能执行与参数化算法单：走“算法交易函数”。
- 需要股票财务、期货基础、交易日历、交易时段：走“免费基础数据函数”分组。
- 需要更深层行业或扩展数据：走“增值数据函数（付费）”，并先提示付费前置条件。

## Output Requirements

- 用“任务 -> API 分组 -> 代表函数 -> 注意事项”的格式输出。
- 不编造不存在的函数名；函数名优先来自 `references/function-token-index.md`。
- 对不确定项明确说“需以当前账户权限和 SDK 版本验证”。

## References

- 全量来源清单： [references/source-index.md](references/source-index.md)
- 能力分区地图： [references/capability-map.md](references/capability-map.md)
- 函数关键词索引： [references/function-token-index.md](references/function-token-index.md)
