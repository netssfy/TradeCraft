# 需求文档

## 简介

TradeCraft 前端是"韭菜的交易世界"AI 交易观测系统的 Web 界面。它通过调用后端 REST API（FastAPI，默认 :8000），为普通股民提供一个可视化的交易员管理与绩效观测平台。界面采用暗色量化终端风格，数据密度适中，专业感强，类似现代化交易终端。

前端部署在 `packages/web/`，共享类型与组件位于 `packages/shared/`，未来可复用于 `packages/desktop/`（Electron 桌面端）。

---

## 词汇表

- **前端（Frontend）**：运行于浏览器的 Web 应用，位于 `packages/web/`
- **交易员（Trader）**：系统中的 AI 交易主体，具有独立的策略、持仓与成交记录
- **Traits**：交易员的六维性格特征：`risk_appetite`（风险偏好）、`holding_horizon`（持仓周期）、`signal_preference`（信号偏好）、`position_construction`（仓位构建）、`exit_discipline`（退出纪律）、`universe_focus`（标的范围）
- **持仓快照（Portfolio Snapshot）**：某一交易日收盘时交易员的现金余额与各标的持仓状态，包含日期（YYYY-MM-DD）
- **快照历史（Snapshot History）**：按日期排列的持仓快照数组，用于追踪资产净值变化
- **运行模式（Mode）**：portfolio 数据的来源类型，分为 `paper`（模拟盘）和 `backtest`（回测）两种
- **成交记录（Trades）**：交易员在某次运行（paper/backtest）中产生的买卖明细
- **策略文件（Strategy File）**：交易员使用的 Python 策略脚本（`.py`）
- **SSE（Server-Sent Events）**：服务端推送事件，用于创建交易员时的流式输出
- **API 服务（API_Service）**：后端 FastAPI 服务，默认监听 `:8000`
- **后端（Backend）**：FastAPI 后端服务

---

## 需求

### 需求 1：交易员列表页

**用户故事：** 作为普通股民，我希望看到所有 AI 交易员的概览列表，以便快速了解当前系统中有哪些交易员及其基本状态。

#### 验收标准

1. THE 前端 SHALL 在首页展示所有交易员的卡片列表，每张卡片包含交易员 ID、市场、初始资金、激活策略名称。
2. WHEN 用户访问首页，THE 前端 SHALL 调用 `GET /traders` 获取交易员列表并渲染。
3. IF `GET /traders` 返回空列表，THEN THE 前端 SHALL 展示"暂无交易员"的空状态提示，并提供创建入口。
4. IF `GET /traders` 请求失败，THEN THE 前端 SHALL 展示错误提示信息，包含 HTTP 状态码与错误描述。
5. WHEN 用户点击某个交易员卡片，THE 前端 SHALL 导航至该交易员的详情页。

---

### 需求 2：交易员详情页

**用户故事：** 作为普通股民，我希望查看某个 AI 交易员的完整信息，包括其性格特征、持仓状态与成交历史，以便理解该交易员的行为逻辑。

#### 验收标准

1. WHEN 用户进入交易员详情页，THE 前端 SHALL 调用 `GET /traders/{id}` 展示交易员的基础信息与六维 Traits。
2. THE 前端 SHALL 以可读的中文标签展示六维 Traits（风险偏好、持仓周期、信号偏好、仓位构建、退出纪律、标的范围）。
3. WHEN 用户进入交易员详情页，THE 前端 SHALL 默认以 `paper` 模式调用 `GET /traders/{id}/portfolio/{mode}`，展示该模式下的历史持仓快照列表，每条快照包含日期、现金余额与各标的持仓（数量、均价）。
4. WHEN 用户切换运行模式（paper / backtest），THE 前端 SHALL 重新调用 `GET /traders/{id}/portfolio/{mode}` 并刷新持仓快照列表。
5. IF `GET /traders/{id}/portfolio/{mode}` 返回 404，THEN THE 前端 SHALL 展示"该模式暂无持仓数据"的提示。
5. WHEN 用户进入交易员详情页，THE 前端 SHALL 调用 `GET /traders/{id}/trades` 展示成交记录索引，按 paper/backtest 分组列出所有 run_id。
6. WHEN 用户点击某个 run_id，THE 前端 SHALL 调用 `GET /traders/{id}/trades/{mode}/{run_id}` 展示该次运行的成交明细，包含时间、标的、方向、数量、价格、手续费。
7. IF `GET /traders/{id}` 请求失败，THEN THE 前端 SHALL 展示错误提示并提供返回列表的导航。

---

### 需求 9：收益率曲线

**用户故事：** 作为普通股民，我希望查看 AI 交易员的资产净值随时间变化的折线图，以便直观评估其历史表现。

#### 验收标准

1. WHEN 用户进入交易员详情页，THE 前端 SHALL 基于 `GET /traders/{id}/portfolio/{mode}` 返回的历史快照数组，计算并展示资产净值（现金 + 各持仓市值）随日期变化的折线图。
2. THE 前端 SHALL 以交易员初始资金为基准，将折线图纵轴换算为累计收益率（%），计算公式为 `(当日净值 - 初始资金) / 初始资金 × 100%`。
3. WHEN 用户切换运行模式（paper / backtest），THE 前端 SHALL 重新获取对应模式的快照数据并刷新收益率曲线。
4. IF 历史快照数组为空或仅含一条记录，THEN THE 前端 SHALL 展示"数据不足，无法绘制曲线"的提示，不渲染图表。
5. THE 前端 SHALL 在折线图上展示每个数据点的日期与累计收益率，鼠标悬停时以 tooltip 形式呈现。

---

### 需求 3：创建交易员

**用户故事：** 作为普通股民，我希望通过表单创建一个新的 AI 交易员，并实时看到 AI 生成 Traits 的过程，以便了解交易员的性格是如何被赋予的。

#### 验收标准

1. THE 前端 SHALL 提供创建交易员的表单，包含字段：交易员 ID、市场（CN/HK/US）、初始资金、允许标的（多选）、手续费率、订单超时秒数。
2. WHEN 用户提交创建表单，THE 前端 SHALL 对必填字段进行本地校验：ID 不为空、初始资金大于 0、允许标的至少一个。
3. IF 本地校验失败，THEN THE 前端 SHALL 在对应字段下方展示具体的错误提示，且不发起 API 请求。
4. WHEN 本地校验通过，THE 前端 SHALL 调用 `POST /traders`（SSE 流式接口），并实时展示服务端推送的 `log` 事件内容。
5. WHEN SSE 流中收到 `result` 事件，THE 前端 SHALL 展示创建成功提示，并导航至新交易员的详情页。
6. IF SSE 流中收到 `error` 事件，THEN THE 前端 SHALL 展示错误信息并允许用户重新提交。
7. IF `POST /traders` 返回 409，THEN THE 前端 SHALL 提示"交易员 ID 已存在"。
8. WHILE SSE 流式输出进行中，THE 前端 SHALL 禁用提交按钮，防止重复提交。

---

### 需求 4：策略文件管理

**用户故事：** 作为普通股民，我希望为交易员上传和管理策略文件，并能设置激活策略，以便控制交易员使用哪套交易逻辑。

#### 验收标准

1. WHEN 用户进入策略管理面板，THE 前端 SHALL 调用 `GET /traders/{id}/strategy` 展示策略文件列表，标注当前激活策略。
2. THE 前端 SHALL 提供文件上传入口，仅接受 `.py` 文件。
3. IF 用户选择非 `.py` 文件，THEN THE 前端 SHALL 在上传前提示"仅支持 .py 文件"，且不发起上传请求。
4. WHEN 用户上传 `.py` 文件，THE 前端 SHALL 调用 `POST /traders/{id}/strategy`，上传成功后刷新策略文件列表。
5. WHEN 用户点击某个策略文件的"设为激活"按钮，THE 前端 SHALL 调用 `PUT /traders/{id}/strategy/active`，成功后更新列表中的激活状态标记。
6. IF 策略文件列表为空，THEN THE 前端 SHALL 展示"暂无策略文件"的提示，并引导用户上传。

---

### 需求 5：编辑交易员信息

**用户故事：** 作为普通股民，我希望能修改交易员的基础配置和 Traits，以便调整交易员的运行参数。

#### 验收标准

1. THE 前端 SHALL 在交易员详情页提供编辑入口，允许修改：初始资金、允许标的、手续费率、订单超时秒数、六维 Traits。
2. WHEN 用户提交编辑表单，THE 前端 SHALL 调用 `PATCH /traders/{id}`，成功后刷新详情页数据。
3. IF `PATCH /traders/{id}` 请求失败，THEN THE 前端 SHALL 展示错误提示，保留用户已填写的表单内容。

---

### 需求 6：删除交易员

**用户故事：** 作为普通股民，我希望能删除不再需要的交易员，以便保持系统整洁。

#### 验收标准

1. THE 前端 SHALL 在交易员详情页提供删除按钮。
2. WHEN 用户点击删除按钮，THE 前端 SHALL 展示确认对话框，要求用户二次确认。
3. WHEN 用户确认删除，THE 前端 SHALL 调用 `DELETE /traders/{id}`，成功后导航回交易员列表页并刷新列表。
4. IF `DELETE /traders/{id}` 请求失败，THEN THE 前端 SHALL 展示错误提示，不执行页面跳转。

---

### 需求 7：视觉风格与布局

**用户故事：** 作为普通股民，我希望界面具有专业的量化终端风格，以便在视觉上感受到系统的专业性与可信度。

#### 验收标准

1. THE 前端 SHALL 采用暗色主题（深色背景，浅色文字），整体色调参考现代量化交易终端。
2. THE 前端 SHALL 使用等宽字体展示数值型数据（价格、数量、资金）。
3. THE 前端 SHALL 对买入方向（buy）使用绿色标识，对卖出方向（sell）使用红色标识。
4. THE 前端 SHALL 提供响应式布局，在 1280px 及以上宽度下以多列形式展示数据，在 768px 以下宽度下以单列形式展示。
5. THE 前端 SHALL 在所有数据加载过程中展示加载状态指示器（如骨架屏或 spinner）。

---

### 需求 8：API 连接配置

**用户故事：** 作为开发者，我希望能配置后端 API 地址，以便在不同环境（本地开发、生产部署）下灵活切换。

#### 验收标准

1. THE 前端 SHALL 支持通过环境变量（如 `VITE_API_BASE_URL`）配置后端 API 基础地址，默认值为 `http://localhost:8000`。
2. WHEN API 请求发生跨域错误，THE 前端 SHALL 展示明确的跨域错误提示，引导用户检查 API 地址配置。
