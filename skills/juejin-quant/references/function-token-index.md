# Function Token Index

????? 29 ????????/????????????????

## API介绍/两融交易函数.html
account_id, order_type, SHSE, position_src, order_duration, order_qualifier, account_name, OrderType_Limit, OrderDuration_Unknown, OrderQualifier_Unknown, strategy_id, cl_ord_id, created_at, order_business, order_id, ex_ord_id, algo_order_id, position_effect, position_side, order_src

## API介绍/交易事件.html
cl_ord_id, filled_volume, exec_id, strategy_id, on_order_status, on_execution_report, on_account_status, account_id, position_effect, account_name, SHSE, order_type, created_at, order_id, order_business, ord_rej_reason, ord_rej_reason_detail, order_list, exec_rpt_list, position_side

## API介绍/交易函数.html
order_type, position_effect, SHSE, position_side, order_duration, order_qualifier, account_id, cl_ord_id, stop_price, created_at, strategy_id, account_name, order_id, ord_rej_reason, ord_rej_reason_detail, order_style, target_volume, target_value, target_percent, filled_volume

## API介绍/交易查询函数.html
account_id, account_name, last_inout, created_at, updated_at, market_value, order_frozen, change_reason, change_event_id, last_price, last_volume, vwap_diluted, available_now, volume_today, order_frozen_today, available_today, has_dividend, fpnl_diluted, channel_id, vwap_open

## API介绍/债券交易函数.html
account_id, bond_reverse_repurchase_agreement, bond_convertible_call, bond_convertible_put, bond_convertible_put_cancel, order_type, OrderQualifier_Unknown, OrderType_Limit, order_duration, order_qualifier

## API介绍/其他事件.html
on_backtest_finished, on_error, on_market_data_connected, on_trade_data_connected, on_market_data_disconnected, on_trade_data_disconnected, account_id, pnl_ratio, pnl_ratio_annual, sharp_ratio, max_drawdown, risk_ratio, open_count, close_count, lose_count, calmar_ratio, win_count, win_ratio, created_at, updated_at

## API介绍/其他函数.html
max_wait_time, set_option, backtest_thread_num, set_token, get_strerror, get_version, error_code, ctp_md_info, SHSE, history_data, history, start_time, end_time, __future__, print_function, absolute_import, SZSE, CFFEX, IC2406, SHFE

## API介绍/动态参数.html
k_value, add_parameter, set_parameter, on_parameter, k_xl, d_value

## API介绍/可转债增值数据函数（付费）.html
end_date, start_date, pub_date, SZSE, SHSE, trade_date, bnd_get_conversion_price, bnd_get_call_info, bnd_get_put_info, bnd_get_amount_change, bnd_get_analysis, get_open_call_auction, cash_date, interest_included, open_volume, effective_date, execution_date, conversion_price, conversion_rate, conversion_volume

## API介绍/基本函数.html
timer_stop, timer_id, time_rule, timer_func, schedule_func, date_rule, start_delay, SHSE, strategy_id, backtest_start_time, backtest_end_time, backtest_adjust, counter_1, counter_2, algo_1, algo_2, backtest_initial_cash, backtest_transaction_ratio, backtest_commission_ratio, backtest_slippage_ratio

## API介绍/基金交易函数.html
account_id, ETF, fund_etf_buy, fund_etf_redemption, fund_subscribing, fund_buy, fund_redemption

## API介绍/基金增值数据函数（付费）.html
SHSE, end_date, SZSE, start_date, ETF, LOF, trade_date, pub_date, portfolio_type, FOF, base_date, sec_id, fnd_get_etf_constituents, fnd_get_portfolio, fnd_get_net_value, fnd_get_adj_factor, fnd_get_dividend, fnd_get_split, fnd_get_share, get_open_call_auction

## API介绍/数据事件.html
subscribe, on_tick, on_bar, on_l2transaction, on_l2order, SHSE, created_at, SZSE, backtest_start_time, backtest_end_time, MODE_BACKTEST, On_bar, cum_volume, cum_amount, cum_position, last_amount, last_volume, trade_type, receive_local_time, __future__

## API介绍/数据订阅.html
SHSE, subscribe, unsubscribe, unsubscribe_previous, on_tick, on_bar, wait_group, wait_group_timeout, bid_v

## API介绍/新股新债交易函数.html
account_id, start_time, end_time, ipo_buy, ipo_get_quota, ipo_get_instruments, ipo_get_match_number, ipo_get_lot_info, sec_type, order_at, min_vol, max_vol, order_id, match_number, match_at, lot_at, lot_volume, give_up_volume, pay_volume, pay_amount

## API介绍/期货基础数据函数（免费）.html
SHFE, CFFEX, trade_date, start_date, end_date, fut_get_continuous_contracts, IM22, IM00, IM01, IM02, IM03, IM99, sec_id, IF2206, IF22, IC22, RB00, RB01, RB04

## API介绍/期货增值数据函数（付费）.html
SHFE, product_code, trade_date, CFFEX, fut_get_contract_info, fut_get_transaction_rankings, fut_get_warehouse_receipt, product_name, exchange_name, start_date, end_date, product_codes, ranking_change, underlying_symbol, SHSE, trade_unit, price_unit, price_tick, delivery_month, trade_time

## API介绍/标的池.html
SZSE, universe_name, SHSE, universe_set, universe_get_symbols, universe_get_names, universe_delete, universe_symbols

## API介绍/算法交易函数.html
algo_param, algo_name, cl_ord_id, account_id, order_type, position_effect, ATS, SMART, algo_order, SHSE, algo_status, POV, start_time, end_time_referred, end_time, end_time_valid, stop_sell_when_dl, cancel_when_pl, min_trade_amount, strategy_id

## API介绍/股票增值数据函数（付费）.html
SHSE, SZSE, trade_date, sec_name, end_date, start_date, participant_name, share_holding, shares_rate, change_type, buy_amount, sell_amount, sales_dept, pub_date, SZHK, sec_id, cum_volume, cum_amount, change_type_name, prc_change_rate

## API介绍/股票财务数据及基础数据函数（免费）.html
data_type, SHSE, end_date, rpt_type, SZSE, start_date, trade_date, pub_date, rpt_date, eps_dil, eps_basic, TTM, inc_oper, EBITDA, start_dat, cash_pay_fee, net_prof, eps_dil2, pe_ttm, pe_lyr

## API介绍/行情数据查询函数（免费）.html
SHSE, bid_p, bid_v, ask_p, ask_v, end_time, created_at, start_time, skip_suspended, fill_missing, ADJUST_NONE, adjust_end_time, SZSE, ADJUST_PREV, last_tick, current_price, backtest_intraday, subscribe, history, history_n

## API介绍/通用数据函数（免费）.html
SHSE, SZSE, ETF, sec_type1, trade_date, CFFEX, sec_type2, SHFE, sec_id, DCE, CZCE, start_date, end_date, INE, GFEX, delisted_date, conversion_start_date, sec_name, sec_abbr, price_tick

## 变量约定.html
SHSE, SHFE, bid_p, bid_v, ask_p, ask_v, created_at, subscribe, account_id, SZSE, updated_at, account_name, order_frozen, market_value, last_inout, change_reason, change_event_id, k_value, CFFEX, DCE

## 快速开始.html
SHSE, strategy_id, subscribe, MODE_BACKTEST, on_bar, ADJUST_PREV, __future__, print_function, absolute_import, backtest_start_time, backtest_end_time, k_value, __name__, __main__, token_id, backtest_adjust, backtest_initial_cash, backtest_commission_ratio, backtest_slippage_ratio, d_value

## 数据结构.html
created_at, account_id, account_name, updated_at, filled_volume, filled_vwap, volume_today, pnl_ratio, bid_p, bid_v, ask_p, ask_v, queue_volumes, order_type, strategy_id, cl_ord_id, order_id, position_effect, order_business, ord_rej_reason

## 枚举常量.html
OrderType_Limit, OrderType_Market, OrderType_Market_FOK, OrderType_Limit_FAK, OrderType_Limit_FOK, OrderType_Market_B5TC, OrderType_Market_FAK, OrderType_Market_BOC, OrderType_Market_BOP, OrderType_Market_B5TL, OrderStatus_New, OrderStatus_PartiallyFilled, OrderStatus_Filled, OrderStatus_Canceled, OrderStatus_Rejected, OrderStatus_PendingNew, OrderStatus_Expired, OrderStatus_PendingTrigger, OrderStatus_Triggered, OrderSide_Buy

## 策略程序架构.html
subscribe, on_tick, on_bar, on_execution_report, on_order_status, on_account_status, on_parameter, on_backtest_finished, set_token, strategy_id

## 错误码.html
ACCOUNT_ID
