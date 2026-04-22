# Capability Map

按任务意图定位掘金 Python SDK 能力（基于镜像文档整理）。

## 1) 策略生命周期与运行框架
- 文档：`快速开始.html`、`策略程序架构.html`、`基本函数.html`、`动态参数.html`
- 关注能力：
- 初始化与启动：`set_token`、`run`
- 定时任务：`schedule`、`timer`
- 动态参数：`add_parameter`、`set_parameter`、`on_parameter`
- 回调体系：`on_tick`、`on_bar`、`on_order_status`、`on_execution_report`、`on_backtest_finished`

## 2) 行情订阅与历史数据
- 文档：`API介绍/数据订阅.html`、`API介绍/数据事件.html`、`API介绍/行情数据查询函数（免费）.html`
- 关注能力：
- 实时订阅：`subscribe`、`unsubscribe`
- 事件驱动：`on_tick`、`on_bar`、`on_l2transaction`、`on_l2order`
- 历史查询：`history`、`history_n`、`get_history_l2ticks`、`get_history_l2bars`、`get_history_l2transactions`

## 3) 交易下单与状态处理
- 文档：`API介绍/交易函数.html`、`API介绍/交易事件.html`、`API介绍/交易查询函数.html`
- 关注能力：
- 下单与撤单：`order_*` 系列
- 订单/成交事件：`on_order_status`、`on_execution_report`
- 账户与持仓查询：`context.account()`、订单成交回查类接口

## 4) 细分交易场景
- 文档：`API介绍/债券交易函数.html`、`API介绍/基金交易函数.html`、`API介绍/新股新债交易函数.html`、`API介绍/两融交易函数.html`、`API介绍/算法交易函数.html`
- 关注能力：
- 债券与可转债交易
- ETF/基金申赎与交易
- 新股新债申购与中签查询：`ipo_*`
- 融资融券相关交易能力
- 算法交易：`algo_order` 及算法参数

## 5) 基础数据与标的筛选（免费）
- 文档：`API介绍/通用数据函数（免费）.html`、`API介绍/股票财务数据及基础数据函数（免费）.html`、`API介绍/期货基础数据函数（免费）.html`、`API介绍/标的池.html`
- 关注能力：
- 交易日历与交易时段查询：`get_trading_dates_by_year`、`get_previous_n_trading_dates`、`get_next_n_trading_dates`、`get_trading_session`
- 股票财务与基础资料
- 期货连续合约、合约基础资料
- 标的池管理：`universe_set`、`universe_get_symbols`、`universe_get_names`、`universe_delete`

## 6) 增值数据（付费）
- 文档：`API介绍/股票增值数据函数（付费）.html`、`API介绍/期货增值数据函数（付费）.html`、`API介绍/基金增值数据函数（付费）.html`、`API介绍/可转债增值数据函数（付费）.html`
- 关注能力：
- 股票、期货、基金、可转债的扩展数据接口
- 典型接口前缀：`fut_get_*`、`fnd_get_*`、`bnd_get_*`

## 7) 协议基础与排错
- 文档：`变量约定.html`、`数据结构.html`、`枚举常量.html`、`错误码.html`、`API介绍/其他函数.html`、`API介绍/其他事件.html`
- 关注能力：
- `symbol`、`exchange`、`mode`、`context` 等核心约定
- 订单/成交/资金/持仓等数据结构字段
- 枚举常量与错误码映射
- 连接与运行诊断事件

## 使用建议
- 先按“任务意图”选能力分区，再查 `references/function-token-index.md` 找具体函数名。
- 在回答用户时，明确区分“免费接口”和“付费增值接口”。
- 在给代码示例前，先确认运行模式（`MODE_LIVE` 或 `MODE_BACKTEST`）与标的市场（`SHSE/SZSE/CFFEX/...`）。
