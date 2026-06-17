#!/usr/bin/env python3
"""
SPXW 1 DTE Put Backtest Script

Strategy:
- Every day, 15 min before market close (15:45 ET), sell a PUT option.
- Expiration: 1 DTE (the next available expiration date strictly greater than current date).
- Target Premium: Mid price >= 0.2, selecting the strike with mid price closest to 0.2.
- Exit: Hold to expiration. Use the 15:45 ET snapshot on the expiration day as the exit price.
- Fallback: If no option snapshot exists on expiration day, use intrinsic value: max(strike - underlying_price, 0).
"""

import pandas as pd
import numpy as np
import glob
import os
import json
import yfinance as yf
from datetime import timedelta

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================
DATA_DIR = "db/old"
SYMBOL = "SPXW"
TARGET_PREMIUM = 0.3
MIN_PREMIUM = 0.3
VIX_RANGE = [0, 100.0]  # Trade only if daily VIX close is within this range [min, max]
SLIPPAGE_PCT = 0.0
COMMISSION_PER_TRADE = 0.0
MULTIPLIER = 100
INITIAL_CAPITAL = 100000.0
OUTPUT_HTML = "backtest_spxw_1dte_dashboard.html"


def get_vix_data(start_str: str, end_str: str) -> dict[str, float]:
    """Fetch daily VIX close prices for the given date range."""
    try:
        vix_df = yf.download("^VIX", start=start_str, end=end_str, progress=False)
        if vix_df is None or vix_df.empty:
            return {}
        
        # Handle potential MultiIndex columns in newer yfinance versions
        if isinstance(vix_df.columns, pd.MultiIndex):
            close_col = next((c for c in vix_df.columns if c[0] == 'Close'), None)
            if close_col:
                close_series = vix_df[close_col]
            else:
                return {}
        else:
            if 'Close' in vix_df.columns:
                close_series = vix_df['Close']
            else:
                return {}
                
        close_series = close_series.dropna().astype(float)
        close_series.index = pd.to_datetime(close_series.index).strftime('%Y-%m-%d')
        return close_series.to_dict()
    except Exception:
        return {}


def load_data() -> pd.DataFrame:
    """Load and concatenate all SPXW parquet files from the local db/old directory."""
    files = glob.glob(os.path.join(DATA_DIR, f"{SYMBOL}_*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found for {SYMBOL} in {DATA_DIR}")
    
    dfs = [pd.read_parquet(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    
    # Ensure timestamp is datetime with timezone
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    if df['timestamp'].dt.tz is None:
        df['timestamp'] = df['timestamp'].dt.tz_localize('America/New_York')
    
    # Ensure expiration is string for consistent comparison
    df['expiration'] = pd.to_datetime(df['expiration']).dt.date.astype(str)
    
    # Sort for efficient querying
    df = df.sort_values(['timestamp', 'expiration', 'strike']).reset_index(drop=True)
    return df


def generate_signals(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Identify trades and generate a verbose calculation log."""
    # Precompute date strings for fast filtering
    df_1545 = df[df['timestamp'].dt.strftime('%H:%M') == '15:45'].copy()
    df_1545['date_str'] = df_1545['timestamp'].dt.strftime('%Y-%m-%d')
    
    trade_dates = sorted(df_1545['date_str'].unique())
    
    if not trade_dates:
        return pd.DataFrame(), pd.DataFrame()
        
    # Fetch VIX data for the valid date range
    vix_data = get_vix_data(trade_dates[0], trade_dates[-1])
    
    trades = []
    logs = []
    
    for t_str in trade_dates:
        # Check VIX filter
        vix_value = vix_data.get(t_str)
        if vix_value is None or pd.isna(vix_value):
            logs.append({
                "date": t_str, 
                "action": "SKIP", 
                "reason": f"VIX data missing for {t_str}"
            })
            continue
            
        if not (VIX_RANGE[0] <= float(vix_value) <= VIX_RANGE[1]):
            logs.append({
                "date": t_str, 
                "action": "SKIP", 
                "reason": f"VIX {vix_value:.2f} outside range {VIX_RANGE[0]}-{VIX_RANGE[1]}"
            })
            continue
            
        current_data = df_1545[df_1545['date_str'] == t_str]
        if current_data.empty:
            continue
            
        # Find next expiration (1 DTE)
        future_expirations = current_data[current_data['expiration'] > t_str]['expiration'].unique()
        if len(future_expirations) == 0:
            logs.append({"date": t_str, "action": "SKIP", "reason": "No future expiration available"})
            continue
            
        next_expiration = min(future_expirations)
        
        # Filter for PUTs with this expiration
        puts = current_data[(current_data['expiration'] == next_expiration) & (current_data['right'] == 'PUT')].copy()
        
        # Calculate mid price
        puts['mid'] = (puts['bid'] + puts['ask']) / 2.0
        
        # Filter for mid >= MIN_PREMIUM
        valid_puts = puts[puts['mid'] >= MIN_PREMIUM].copy()
        
        if valid_puts.empty:
            logs.append({
                "date": t_str, 
                "action": "SKIP", 
                "expiration": next_expiration,
                "reason": f"No puts with mid >= {MIN_PREMIUM}"
            })
            continue
            
        # Find closest to TARGET_PREMIUM
        valid_puts['diff'] = np.abs(valid_puts['mid'] - TARGET_PREMIUM)
        valid_puts = valid_puts.sort_values('diff')
        
        top_candidates = valid_puts.head(3)[['strike', 'mid', 'diff']].to_dict('records')
        best_put = valid_puts.iloc[0]
        
        strike = best_put['strike']
        entry_mid = best_put['mid']
        underlying_price = best_put['underlying_price']
        
        logs.append({
            "date": t_str,
            "action": "ENTRY",
            "expiration": next_expiration,
            "strike": strike,
            "entry_mid": entry_mid,
            "underlying_price": underlying_price,
            "vix": f"{vix_value:.2f}",
            "reason": f"Closest to {TARGET_PREMIUM} (diff: {best_put['diff']:.4f}). Top candidates: {top_candidates}"
        })
        
        # Find exit data on expiration day at 15:45
        exit_data = df_1545[
            (df_1545['date_str'] == next_expiration) &
            (df_1545['expiration'] == next_expiration) &
            (df_1545['strike'] == strike) &
            (df_1545['right'] == 'PUT')
        ]
        
        if not exit_data.empty:
            exit_row = exit_data.iloc[0]
            exit_mid = (exit_row['bid'] + exit_row['ask']) / 2.0
            exit_underlying = exit_row['underlying_price']
            logs.append({
                "date": next_expiration,
                "action": "EXIT",
                "strike": strike,
                "exit_mid": exit_mid,
                "exit_underlying": exit_underlying,
                "reason": "Snapshot 15 min before close on expiration day"
            })
        else:
            # Fallback to intrinsic value if no option data
            exp_underlying_data = df_1545[df_1545['date_str'] == next_expiration]
            if not exp_underlying_data.empty:
                exit_underlying = exp_underlying_data.iloc[0]['underlying_price']
            else:
                exit_underlying = underlying_price
                
            exit_mid = max(strike - exit_underlying, 0.0)
            logs.append({
                "date": next_expiration,
                "action": "EXIT_INTRINSIC",
                "strike": strike,
                "exit_mid": exit_mid,
                "exit_underlying": exit_underlying,
                "reason": f"No option snapshot, used intrinsic value: max({strike} - {exit_underlying}, 0)"
            })
            
        # Calculate PnL (Short Put: profit if price goes down)
        gross_pnl = (entry_mid - exit_mid) * MULTIPLIER
        commission = COMMISSION_PER_TRADE * 2  # entry and exit
        slippage = entry_mid * SLIPPAGE_PCT * MULTIPLIER
        net_pnl = gross_pnl - commission - slippage
        
        trades.append({
            "entry_date": t_str,
            "vix_entry": f"{vix_value:.2f}",
            "expiration_date": next_expiration,
            "strike": strike,
            "entry_mid": entry_mid,
            "exit_mid": exit_mid,
            "entry_underlying": underlying_price,
            "exit_underlying": exit_underlying,
            "gross_pnl": gross_pnl,
            "commission": commission,
            "slippage": slippage,
            "net_pnl": net_pnl
        })
        
    return pd.DataFrame(trades), pd.DataFrame(logs)


def calculate_metrics(trades_df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Calculate standard quantitative performance metrics."""
    if trades_df.empty:
        return {
            "total_trades": 0, "total_return_pct": 0.0, "total_return_abs": 0.0,
            "cagr_pct": 0.0, "sharpe_ratio": 0.0, "max_drawdown_abs": 0.0,
            "max_drawdown_duration_trades": 0, "win_rate_pct": 0.0, "profit_factor": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0, "win_loss_ratio": 0.0, "final_equity": INITIAL_CAPITAL
        }, trades_df
    
    trades_df = trades_df.sort_values('expiration_date').reset_index(drop=True)
    trades_df['cumulative_net_pnl'] = trades_df['net_pnl'].cumsum()
    trades_df['equity'] = INITIAL_CAPITAL + trades_df['cumulative_net_pnl']
    
    total_return = trades_df['cumulative_net_pnl'].iloc[-1]
    
    start_date = pd.to_datetime(trades_df['entry_date'].min())
    end_date = pd.to_datetime(trades_df['expiration_date'].max())
    years = max((end_date - start_date).days / 365.25, 1e-6)
    cagr = ((INITIAL_CAPITAL + total_return) / INITIAL_CAPITAL) ** (1 / years) - 1
    
    daily_returns = trades_df.groupby('expiration_date')['net_pnl'].sum() / INITIAL_CAPITAL
    mean_daily_return = daily_returns.mean()
    std_daily_return = daily_returns.std()
    sharpe = (mean_daily_return / std_daily_return) * np.sqrt(252) if std_daily_return > 0 else 0.0
    
    peak = trades_df['equity'].cummax()
    drawdown_abs = trades_df['equity'] - peak
    max_drawdown_abs = drawdown_abs.min()
    
    # Drawdown duration in trades
    in_dd = (trades_df['equity'] < trades_df['equity'].cummax())
    dd_groups = (in_dd != in_dd.shift(1)).cumsum()
    dd_durations = trades_df[in_dd].groupby(dd_groups).size()
    max_dd_duration_trades = int(dd_durations.max()) if not dd_durations.empty else 0
    
    winning_trades = trades_df[trades_df['net_pnl'] > 0]
    losing_trades = trades_df[trades_df['net_pnl'] <= 0]
    
    win_rate = len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0.0
    gross_profit = winning_trades['net_pnl'].sum()
    gross_loss = abs(losing_trades['net_pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
    
    avg_win = winning_trades['net_pnl'].mean() if len(winning_trades) > 0 else 0.0
    avg_loss = losing_trades['net_pnl'].mean() if len(losing_trades) > 0 else 0.0
    win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
    
    metrics = {
        "total_trades": len(trades_df),
        "total_return_pct": (total_return / INITIAL_CAPITAL) * 100,
        "total_return_abs": total_return,
        "cagr_pct": cagr * 100,
        "sharpe_ratio": sharpe,
        "max_drawdown_abs": max_drawdown_abs,
        "max_drawdown_duration_trades": max_dd_duration_trades,
        "win_rate_pct": win_rate * 100,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "win_loss_ratio": win_loss_ratio,
        "final_equity": INITIAL_CAPITAL + total_return
    }
    
    return metrics, trades_df


def calculate_monthly_matrix(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate monthly return matrix in absolute dollar value."""
    if trades_df.empty:
        return pd.DataFrame()
    
    df = trades_df.copy()
    df['exp_year'] = pd.to_datetime(df['expiration_date']).dt.year
    df['exp_month'] = pd.to_datetime(df['expiration_date']).dt.month
    
    monthly_pnl = df.groupby(['exp_year', 'exp_month'])['net_pnl'].sum().unstack(fill_value=0)
    
    for i in range(1, 13):
        if i not in monthly_pnl.columns:
            monthly_pnl[i] = 0
            
    monthly_pnl = monthly_pnl.reindex(columns=range(1, 13))
    monthly_pnl['Annual Total'] = monthly_pnl.sum(axis=1)
    
    return monthly_pnl


def generate_html(metrics: dict, trades_df: pd.DataFrame, logs_df: pd.DataFrame, monthly_matrix: pd.DataFrame) -> str:
    """Generate a self-contained static HTML dashboard."""
    trades_json = trades_df.to_dict(orient='records')
    logs_json = logs_df.to_dict(orient='records')
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    if monthly_matrix.empty:
        matrix_html = "<p class='text-muted'>No trades generated to display matrix.</p>"
    else:
        matrix_html = "<table class='table table-bordered table-sm text-end'><thead><tr><th>Year</th>"
        for m in month_names:
            matrix_html += f"<th>{m}</th>"
        matrix_html += "<th>Annual Total</th></tr></thead><tbody>"
        
        for year, row in monthly_matrix.iterrows():
            matrix_html += f"<tr><td>{int(year)}</td>"
            annual_total = row['Annual Total']
            for i in range(1, 13):
                val = row[i]
                color = "text-success" if val >= 0 else "text-danger"
                matrix_html += f"<td class='{color}'>${val:,.2f}</td>"
            matrix_html += f"<td class='fw-bold'>${annual_total:,.2f}</td></tr>"
        matrix_html += "</tbody></table>"

    equity_curve_data = []
    drawdown_data = []
    
    if not trades_df.empty:
        for _, row in trades_df.iterrows():
            equity_curve_data.append([pd.to_datetime(row['expiration_date']).timestamp() * 1000, row['equity']])
        
        peak = INITIAL_CAPITAL
        for _, row in trades_df.iterrows():
            peak = max(peak, row['equity'])
            drawdown_data.append([pd.to_datetime(row['expiration_date']).timestamp() * 1000, row['equity'] - peak])

    return_str_color = "text-success" if metrics['total_return_abs'] >= 0 else "text-danger"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPXW 1 DTE Put Backtest Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://unpkg.com/highcharts@11.1.0/highcharts.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        body {{ padding: 20px; background-color: #f8f9fa; }}
        .card {{ margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 1.5rem; font-weight: bold; }}
        .metric-label {{ font-size: 0.9rem; color: #6c757d; }}
        #chart-equity, #chart-drawdown {{ height: 400px; }}
        .nav-tabs .nav-link.active {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h2 class="mb-4">SPXW 1 DTE Put Backtest Dashboard</h2>
        
        <ul class="nav nav-tabs" id="myTab" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="overview-tab" data-bs-toggle="tab" data-bs-target="#overview" type="button" role="tab">Overview</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="trades-tab" data-bs-toggle="tab" data-bs-target="#trades" type="button" role="tab">Trade List</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="logs-tab" data-bs-toggle="tab" data-bs-target="#logs" type="button" role="tab">Calculation Log</button>
            </li>
        </ul>
        
        <div class="tab-content bg-white border border-top-0 p-4 rounded-bottom" id="myTabContent">
            <div class="tab-pane fade show active" id="overview" role="tabpanel">
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card p-3 text-center">
                            <div class="metric-label">Total Return</div>
                            <div class="metric-value {return_str_color}">${metrics['total_return_abs']:,.2f} ({metrics['total_return_pct']:.2f}%)</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card p-3 text-center">
                            <div class="metric-label">CAGR</div>
                            <div class="metric-value">{metrics['cagr_pct']:.2f}%</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card p-3 text-center">
                            <div class="metric-label">Sharpe Ratio</div>
                            <div class="metric-value">{metrics['sharpe_ratio']:.2f}</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card p-3 text-center">
                            <div class="metric-label">Max Drawdown</div>
                            <div class="metric-value text-danger">${metrics['max_drawdown_abs']:,.2f}</div>
                        </div>
                    </div>
                </div>
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card p-3 text-center">
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value">{metrics['win_rate_pct']:.2f}%</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card p-3 text-center">
                            <div class="metric-label">Profit Factor</div>
                            <div class="metric-value">{metrics['profit_factor']:.2f}</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card p-3 text-center">
                            <div class="metric-label">Avg Win / Avg Loss</div>
                            <div class="metric-value">{metrics['win_loss_ratio']:.2f}</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card p-3 text-center">
                            <div class="metric-label">Total Trades</div>
                            <div class="metric-value">{metrics['total_trades']}</div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-12">
                        <div class="card p-3">
                            <h5>Equity Curve</h5>
                            <div id="chart-equity"></div>
                        </div>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-12">
                        <div class="card p-3">
                            <h5>Drawdown ($)</h5>
                            <div id="chart-drawdown"></div>
                        </div>
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-12">
                        <div class="card p-3">
                            <h5>Monthly Return Matrix (Absolute Dollar Value)</h5>
                            {matrix_html}
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="tab-pane fade" id="trades" role="tabpanel">
                <table id="trades-table" class="table table-striped table-hover" style="width:100%">
                    <thead>
                        <tr>
                            <th>Entry Date</th>
                            <th>VIX</th>
                            <th>Expiration</th>
                            <th>Strike</th>
                            <th>Entry Mid</th>
                            <th>Exit Mid</th>
                            <th>Entry Und.</th>
                            <th>Exit Und.</th>
                            <th>Gross PnL</th>
                            <th>Comm.</th>
                            <th>Net PnL</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
            
            <div class="tab-pane fade" id="logs" role="tabpanel">
                <table id="logs-table" class="table table-sm table-hover" style="width:100%">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>VIX</th>
                            <th>Action</th>
                            <th>Expiration</th>
                            <th>Strike</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        $(document).ready(function() {{
            $('#trades-table').DataTable({{
                data: {json.dumps(trades_json)},
                columns: [
                    {{ data: 'entry_date' }},
                    {{ data: 'vix_entry' }},
                    {{ data: 'expiration_date' }},
                    {{ data: 'strike' }},
                    {{ data: 'entry_mid', render: $.fn.dataTable.render.number(',', '.', 2, '$') }},
                    {{ data: 'exit_mid', render: $.fn.dataTable.render.number(',', '.', 2, '$') }},
                    {{ data: 'entry_underlying', render: $.fn.dataTable.render.number(',', '.', 2, '$') }},
                    {{ data: 'exit_underlying', render: $.fn.dataTable.render.number(',', '.', 2, '$') }},
                    {{ data: 'gross_pnl', render: $.fn.dataTable.render.number(',', '.', 2, '$') }},
                    {{ data: 'commission', render: $.fn.dataTable.render.number(',', '.', 2, '$') }},
                    {{ data: 'net_pnl', render: function(data, type, row) {{
                        return '<span class="' + (data >= 0 ? 'text-success' : 'text-danger') + '">' + $.fn.dataTable.render.number(',', '.', 2, '$').display(data) + '</span>';
                    }} }}
                ],
                order: [[0, 'desc']]
            }});
            
            $('#logs-table').DataTable({{
                data: {json.dumps(logs_json)},
                columns: [
                    {{ data: 'date' }},
                    {{ data: 'vix', defaultContent: '-' }},
                    {{ data: 'action' }},
                    {{ data: 'expiration', defaultContent: '-' }},
                    {{ data: 'strike', defaultContent: '-' }},
                    {{ data: 'reason' }}
                ],
                order: [[0, 'desc']],
                pageLength: 50
            }});
            
            Highcharts.chart('chart-equity', {{
                chart: {{ type: 'line' }},
                title: {{ text: null }},
                xAxis: {{ type: 'datetime' }},
                yAxis: {{ title: {{ text: 'Equity ($)' }} }},
                series: [{{
                    name: 'Total Equity',
                    data: {json.dumps(equity_curve_data)},
                    color: '#0d6efd'
                }}]
            }});
            
            Highcharts.chart('chart-drawdown', {{
                chart: {{ type: 'area' }},
                title: {{ text: null }},
                xAxis: {{ type: 'datetime' }},
                yAxis: {{ title: {{ text: 'Drawdown ($)' }}, reversed: true }},
                series: [{{
                    name: 'Drawdown ($)',
                    data: {json.dumps(drawdown_data)},
                    color: '#dc3545',
                    fillColor: {{
                        linearGradient: {{ x1: 0, y1: 0, x2: 0, y2: 1 }},
                        stops: [[0, 'rgba(220, 53, 69, 0.5)'], [1, 'rgba(220, 53, 69, 0.0)']]
                    }}
                }}]
            }});
        }});
    </script>
</body>
</html>
"""
    return html


def main():
    print("Loading data...")
    df = load_data()
    print(f"Loaded {len(df)} records.")
    
    print("Generating signals and logs...")
    trades_df, logs_df = generate_signals(df)
    print(f"Generated {len(trades_df)} trades.")
    
    print("Calculating metrics...")
    metrics, trades_df = calculate_metrics(trades_df)
    
    print("Calculating monthly matrix...")
    monthly_matrix = calculate_monthly_matrix(trades_df)
    
    print("Generating HTML dashboard...")
    html_content = generate_html(metrics, trades_df, logs_df, monthly_matrix)
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Dashboard successfully generated: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
