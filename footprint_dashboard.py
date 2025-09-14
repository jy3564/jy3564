# -*- coding: utf-8 -*-
"""
金融微观结构分析仪表盘：足迹图 (Footprint Chart)

核心功能:
- 实时连接Polygon.io获取加密货币的Trades和Quotes数据。
- 使用严谨的“攻击方判断”逻辑（BBO比较 + Tick Test）确定每笔交易的主动方。
- 按指定时间窗口聚合Tick数据，生成包含OHLC、成交量、Delta、POC和成交量失衡的K线。
- 通过Dash和Plotly在Web仪表盘上动态可视化足迹图及相关指标。
- 采用多进程架构，确保数据接收、处理和Web服务互不阻塞。
"""

import os
import time
import copy
from datetime import datetime, timezone
from multiprocessing import Process, Manager, Lock
from collections import deque, defaultdict

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

from polygon import WebSocketClient
from polygon.websocket.models import WebSocketMessage, CryptoTrade, CryptoQuote

# ==============================================================================
# 1. 配置部分 (Configuration)
# ==============================================================================

# --- 请在此处填入您的Polygon API密钥 ---
# 建议使用环境变量，以增强安全性。例如: os.environ.get('POLYGON_API_KEY', 'YOUR_DEFAULT_KEY')
POLYGON_API_KEY = "YOUR_POLYGON_API_KEY"

# --- 要分析的加密货币代码 ---
CRYPTO_TICKER = "X:BTC-USD"

# --- K线聚合的时间周期（秒） ---
AGGREGATION_SECONDS = 15

# --- 计算成交量失衡的比例阈值 (例如 3 代表 300%) ---
IMBALANCE_RATIO = 3.0

# --- 仪表盘刷新频率（秒） ---
DASH_REFRESH_INTERVAL_SECONDS = 2

# --- 图表上显示的最大K线数量 ---
MAX_CANDLES_ON_CHART = 100

# ==============================================================================
# 2. 数据连接与并发处理 (Websocket & Multiprocessing)
# ==============================================================================

def websocket_handler(shared_state: Manager, trades_queue: Manager, lock: Lock):
    """
    此进程负责连接Polygon WebSocket，接收Trades和Quotes数据。
    - Quotes数据用于实时更新全局BBO（最佳买卖价）。
    - Trades数据被放入一个队列，由另一个进程进行处理。
    """
    print("[WebSocket Process] 启动...")
    client = WebSocketClient(api_key=POLYGON_API_KEY)

    trade_channel = f"XT.{CRYPTO_TICKER}"
    quote_channel = f"XQ.{CRYPTO_TICKER}"

    def handle_msg(msgs: list[WebSocketMessage]):
        for m in msgs:
            if isinstance(m, CryptoQuote):
                # 当收到报价更新时，锁定并更新全局BBO状态
                with lock:
                    shared_state['bbo'] = {
                        'bid_price': m.bid_price,
                        'ask_price': m.ask_price,
                        'timestamp': m.timestamp
                    }
            elif isinstance(m, CryptoTrade):
                # 当收到成交记录时，将其放入待处理队列
                trades_queue.put({
                    'price': m.price,
                    'size': m.size,
                    'timestamp': m.timestamp
                })

    client.subscribe(trade_channel, quote_channel)
    client.run(handle_msg)

def data_processor(shared_state: Manager, trades_queue: Manager, candles_data: Manager, lock: Lock):
    """
    此进程是核心分析引擎。
    - 从队列中获取原始交易。
    - 应用“攻击方判断”逻辑。
    - 将交易聚合到K线中。
    - 在K线聚合完成时，计算所有指标（POC, Delta, Imbalances）并存入共享列表。
    """
    print("[Processing Process] 启动...")
    current_bar = None
    last_bar_timestamp = None

    while True:
        if not trades_queue.empty():
            trade = trades_queue.get()

            # --- 3. 核心分析逻辑 (Core Analytics) ---

            # 3.1 & 3.2: 攻击方判断 (Aggressor Side Determination)
            with lock:
                bbo = shared_state.get('bbo', None)
                last_trade = shared_state.get('last_trade', None)

            aggressor_side = None
            if bbo:
                if trade['price'] >= bbo['ask_price']:
                    aggressor_side = 'buy'
                elif trade['price'] <= bbo['bid_price']:
                    aggressor_side = 'sell'

            # 如果成交价在买卖价差之间，或BBO尚未获得，则启用次级判断 (Tick Test)
            if aggressor_side is None and last_trade:
                if trade['price'] > last_trade['price']:
                    aggressor_side = 'buy'
                elif trade['price'] < last_trade['price']:
                    aggressor_side = 'sell'
                else:
                    # Zero Tick Rule: 价格相同时，继承上一笔的方向
                    aggressor_side = last_trade['side']

            # 如果是第一笔交易，无法判断，可以默认或跳过
            if aggressor_side is None:
                continue

            # 更新上一笔交易状态
            with lock:
                shared_state['last_trade'] = {'price': trade['price'], 'side': aggressor_side}

            # 3.3: 数据聚合逻辑 (Aggregation Logic)
            trade_timestamp = pd.to_datetime(trade['timestamp'], unit='ns')
            bar_timestamp = trade_timestamp.floor(f'{AGGREGATION_SECONDS}S')

            if bar_timestamp != last_bar_timestamp:
                # 一个聚合周期结束，最终化上一根K线
                if current_bar:
                    finalized_bar = finalize_bar_calculations(current_bar)
                    candles_data.append(finalized_bar)

                # 初始化新的K线
                current_bar = {
                    'timestamp': bar_timestamp,
                    'open': trade['price'],
                    'high': trade['price'],
                    'low': trade['price'],
                    'close': trade['price'],
                    'total_volume': 0,
                    'buy_volume': 0,
                    'sell_volume': 0,
                    # Footprint: {price: {'buy_volume': float, 'sell_volume': float}}
                    'footprint': defaultdict(lambda: {'buy_volume': 0, 'sell_volume': 0})
                }
                last_bar_timestamp = bar_timestamp

            # 更新当前K线数据
            current_bar['high'] = max(current_bar['high'], trade['price'])
            current_bar['low'] = min(current_bar['low'], trade['price'])
            current_bar['close'] = trade['price']
            current_bar['total_volume'] += trade['size']

            price_level = trade['price']
            if aggressor_side == 'buy':
                current_bar['buy_volume'] += trade['size']
                current_bar['footprint'][price_level]['buy_volume'] += trade['size']
            else: # sell
                current_bar['sell_volume'] += trade['size']
                current_bar['footprint'][price_level]['sell_volume'] += trade['size']
        else:
            # 队列为空时短暂休眠，避免CPU空转
            time.sleep(0.01)

def finalize_bar_calculations(bar_data: dict) -> dict:
    """
    对一根聚合完成的K线进行最终的指标计算。
    """
    final_bar = copy.deepcopy(bar_data)

    # 计算 Delta
    final_bar['delta'] = final_bar['buy_volume'] - final_bar['sell_volume']

    # 计算 POC (Point of Control)
    poc_price = None
    max_volume_at_price = 0
    if final_bar['footprint']:
        for price, volumes in final_bar['footprint'].items():
            total_vol = volumes['buy_volume'] + volumes['sell_volume']
            if total_vol > max_volume_at_price:
                max_volume_at_price = total_vol
                poc_price = price
    final_bar['poc'] = poc_price

    # 计算 Imbalances (成交量失衡)
    # 买方失衡: 当前价位的买量 >= 下一档价位的卖量 * 比例
    # 卖方失衡: 当前价位的卖量 >= 上一档价位的买量 * 比例
    imbalances = {'buy': [], 'sell': []}
    sorted_prices = sorted(final_bar['footprint'].keys(), reverse=True)

    for i in range(len(sorted_prices)):
        current_price = sorted_prices[i]
        current_buy_vol = final_bar['footprint'][current_price]['buy_volume']
        current_sell_vol = final_bar['footprint'][current_price]['sell_volume']

        # 检查买方失衡 (与对角线下方比较)
        if i + 1 < len(sorted_prices):
            lower_price = sorted_prices[i+1]
            lower_sell_vol = final_bar['footprint'][lower_price]['sell_volume']
            if lower_sell_vol > 0 and current_buy_vol >= lower_sell_vol * IMBALANCE_RATIO:
                imbalances['buy'].append(current_price)

        # 检查卖方失衡 (与对角线上方比较)
        if i > 0:
            upper_price = sorted_prices[i-1]
            upper_buy_vol = final_bar['footprint'][upper_price]['buy_volume']
            if upper_buy_vol > 0 and current_sell_vol >= upper_buy_vol * IMBALANCE_RATIO:
                imbalances['sell'].append(current_price)

    final_bar['imbalances'] = imbalances

    return final_bar

# ==============================================================================
# 4. 可视化界面 (Dash/Plotly)
# ==============================================================================

app = dash.Dash(__name__, title="金融微观结构分析仪表盘")

app.layout = html.Div([
    html.H1(f"足迹图 (Footprint Chart) - {CRYPTO_TICKER}", style={'textAlign': 'center'}),
    dcc.Graph(id='footprint-chart'),
    dcc.Interval(
        id='interval-component',
        interval=DASH_REFRESH_INTERVAL_SECONDS * 1000,  # in milliseconds
        n_intervals=0
    )
])

@app.callback(
    Output('footprint-chart', 'figure'),
    Input('interval-component', 'n_intervals'),
    prevent_initial_call=True
)
def update_graph(n):
    """
    定时回调函数，用于从共享数据中读取最新K线并更新图表。
    """
    # 从共享列表中复制数据，避免在迭代时被修改
    chart_data = list(candles_data)
    if not chart_data:
        return go.Figure()

    # 仅保留最新的N条K线用于显示
    chart_data = chart_data[-MAX_CANDLES_ON_CHART:]

    df = pd.DataFrame(chart_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 创建包含两个子图的画布：一个用于K线，一个用于Delta
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.8, 0.2]
    )

    # 绘制K线主体
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Candlestick',
            increasing_line_color='rgba(0,255,0,0.8)',
            decreasing_line_color='rgba(255,0,0,0.8)',
        ),
        row=1, col=1
    )

    # 绘制Delta条形图
    colors = ['green' if d >= 0 else 'red' for d in df['delta']]
    fig.add_trace(
        go.Bar(
            x=df['timestamp'],
            y=df['delta'],
            name='Delta',
            marker_color=colors,
        ),
        row=2, col=1
    )

    annotations = []
    shapes = []

    # 为每根K线添加足迹图文本、POC和失衡高亮
    for i, row in df.iterrows():
        candle_width_ms = AGGREGATION_SECONDS * 1000 * 0.8 # K线宽度的80%

        # 高亮POC (Point of Control)
        if row['poc']:
            shapes.append(go.layout.Shape(
                type="rect",
                xref="x", yref="y",
                x0=row['timestamp'] - pd.Timedelta(milliseconds=candle_width_ms/2),
                y0=row['poc'] - 0.01, # 微调以使矩形居中
                x1=row['timestamp'] + pd.Timedelta(milliseconds=candle_width_ms/2),
                y1=row['poc'] + 0.01,
                fillcolor="rgba(128, 128, 128, 0.3)",
                line_color="rgba(128, 128, 128, 0.3)",
            ))

        # 添加足迹图文本和失衡高亮
        sorted_prices = sorted(row['footprint'].keys())
        for price in sorted_prices:
            volumes = row['footprint'][price]
            buy_vol = volumes['buy_volume']
            sell_vol = volumes['sell_volume']

            # 格式化成交量数字，使其更易读 (例如 1.2k)
            buy_vol_str = f"{buy_vol:.1f}" if buy_vol < 1000 else f"{buy_vol/1000:.1f}k"
            sell_vol_str = f"{sell_vol:.1f}" if sell_vol < 1000 else f"{sell_vol/1000:.1f}k"

            # 处理失衡高亮
            buy_style = "color: lightblue; font-weight: bold;" if price in row['imbalances']['buy'] else ""
            sell_style = "color: lightpink; font-weight: bold;" if price in row['imbalances']['sell'] else ""

            text = f"<span style='{sell_style}'>{sell_vol_str}</span> | <span style='{buy_style}'>{buy_vol_str}</span>"

            annotations.append(
                go.layout.Annotation(
                    x=row['timestamp'],
                    y=price,
                    text=text,
                    showarrow=False,
                    font=dict(size=8, color="white"),
                    align="center"
                )
            )

    fig.update_layout(
        title_text=f"{CRYPTO_TICKER} Footprint Chart ({AGGREGATION_SECONDS}s Aggregation)",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        annotations=annotations,
        shapes=shapes,
        yaxis_title="Price (USD)",
        yaxis2_title="Delta",
        showlegend=False
    )
    fig.update_xaxes(showticklabels=True, row=1, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=1)

    return fig


# ==============================================================================
# 5. 主程序入口 (Main Execution)
# ==============================================================================

if __name__ == '__main__':
    if POLYGON_API_KEY == "YOUR_POLYGON_API_KEY":
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR: 请在脚本顶部设置您的 POLYGON_API_KEY。 !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        exit(1)

    # 创建用于进程间通信的共享对象
    manager = Manager()

    # 全局状态管理器，用于存储BBO和last_trade
    shared_state = manager.dict()
    lock = Lock()

    # 待处理的原始交易队列
    trades_queue = manager.Queue()

    # 已完成聚合和计算的K线数据列表 (使用deque以自动限制大小)
    candles_data = manager.list()

    # 启动子进程
    p_ws = Process(target=websocket_handler, args=(shared_state, trades_queue, lock))
    p_proc = Process(target=data_processor, args=(shared_state, trades_queue, candles_data, lock))

    p_ws.start()
    p_proc.start()

    print("[Main Process] 启动Dash Web服务器...")
    print(f"请在浏览器中打开: http://127.0.0.1:8050")

    # 启动Dash Web服务器 (在主进程中)
    app.run_server(debug=False)

    # 当服务器停止时，清理子进程
    print("[Main Process] 正在关闭子进程...")
    p_ws.terminate()
    p_proc.terminate()
    p_ws.join()
    p_proc.join()
    print("[Main Process] 程序已退出。")
