
import pandas as pd
import matplotlib.pyplot as plt
import logging
import os

def plot_report(history: pd.DataFrame, title: str = "Backtest Report", output: str = None, symbols: str = ""):
    if history.empty:
        print("No history data to plot")
        return

    if output is None:
        output = "./backtest_report.png"

    full_title = f"{title}\nSymbols: {symbols}" if symbols else title

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(full_title, fontsize=14)

    # 图1: 总权益曲线 (Equity Curve)
    ax1 = axes[0, 0]
    ax1.plot(history.index, history["equity_total"], label="Total Equity", linewidth=1.5)
    ax1.plot(history.index, history["position_value"], label="Position Value (no cash)", linewidth=1, linestyle="--", alpha=0.7)
    ax1.set_title("Equity Curve (Log Scale)")
    ax1.set_yscale("log")
    ax1.set_ylabel("Value")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 图2: 分红现金流 (Dividend Flow)
    ax2 = axes[0, 1]
    dividend_cumsum = history["dividend_received"].cumsum()
    ax2.bar(history.index, history["dividend_received"], width=1, alpha=0.6, label="Daily Dividend", color="green")
    ax2_twin = ax2.twinx()
    ax2_twin.plot(history.index, dividend_cumsum, color="darkgreen", linewidth=2, label="Cumulative Dividend")
    ax2_twin.set_ylabel("Cumulative Dividend", color="darkgreen")
    ax2.set_title("Dividend Cash Flow")
    ax2.legend(loc="upper left")
    ax2_twin.legend(loc="upper right")
    ax2.grid(True, alpha=0.3)

    # 图3: 仓位暴露 (Exposure)
    ax3 = axes[1, 0]
    ax3.fill_between(history.index, history["exposure"], alpha=0.5, color="orange")
    ax3.set_title("Exposure (Position Value / Total Equity)")
    ax3.set_ylabel("Exposure Ratio")
    ax3.set_ylim(0, 1.1)
    ax3.grid(True, alpha=0.3)

    # 图4: 回撤 (Drawdown)
    ax4 = axes[1, 1]
    # 计算真正的回撤：从历史高点开始
    rolling_max = history["equity_total"].cummax()
    drawdown = (history["equity_total"] - rolling_max) / rolling_max
    ax4.fill_between(history.index, drawdown, 0, alpha=0.7, color="red")
    ax4.set_title("Drawdown")
    ax4.set_ylabel("Drawdown %")
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    # 保存到文件而不是 show()
    plt.savefig(output, dpi=150)
    plt.close()
    logging.info(f"Chart saved to: {output}")
    return output


def plot_rolling_results(rolling_results, output, symbols: str = ""):
    import pandas as pd
    import matplotlib.pyplot as plt

    df = pd.DataFrame(rolling_results)
    df["start_year"] = df["start_date"].dt.year

    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    title = f"Rolling 10-Year Backtest Results (2005-2015 Start Dates)"
    if symbols:
        title += f"\nSymbols: {symbols}"
    fig.suptitle(title, fontsize=14)

    # 图1: CAGR by Start Year
    ax1 = axes[0, 0]
    ax1.bar(df["start_year"], df["cagr"] * 100, color="steelblue", alpha=0.7)
    ax1.axhline(y=df["cagr"].mean() * 100, color="red", linestyle="--", label=f"Mean: {df['cagr'].mean()*100:.1f}%")
    ax1.set_title("CAGR by Start Year")
    ax1.set_xlabel("Start Year")
    ax1.set_ylabel("CAGR (%)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 图2: Max Drawdown by Start Year
    ax2 = axes[0, 1]
    ax2.bar(df["start_year"], df["max_drawdown"] * 100, color="red", alpha=0.7)
    ax2.axhline(y=df["max_drawdown"].mean() * 100, color="darkred", linestyle="--", label=f"Mean: {df['max_drawdown'].mean()*100:.1f}%")
    ax2.set_title("Max Drawdown by Start Year")
    ax2.set_xlabel("Start Year")
    ax2.set_ylabel("Max Drawdown (%)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 图3: Risk-Return (CAGR vs Max Drawdown)
    ax3 = axes[0, 2]
    scatter = ax3.scatter(df["max_drawdown"] * 100, df["cagr"] * 100, c=df["start_year"], cmap="viridis", s=80, alpha=0.7)
    ax3.set_title("Risk-Return (Color = Start Year)")
    ax3.set_xlabel("Max Drawdown (%)")
    ax3.set_ylabel("CAGR (%)")
    plt.colorbar(scatter, ax=ax3, label="Start Year")
    ax3.grid(True, alpha=0.3)

    # 图4: Final Position Value by Last Backtest Year
    ax4 = axes[1, 0]
    ax4.bar(df["start_year"], df["final_position_value"], color="teal", alpha=0.7)
    ax4.axhline(y=df["final_position_value"].mean(), color="darkred", linestyle="--", label=f"Mean: ${df['final_position_value'].mean():.0f}")
    ax4.set_title("Final Position Value by Last Backtest Year")
    ax4.set_xlabel("Start Year")
    ax4.set_ylabel("Position Value ($)")
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 图5: Projected Final Position Value
    ax5 = axes[1, 1]
    ax5.bar(df["start_year"], df["projected_position_value"], color="teal", alpha=0.7)
    ax5.axhline(y=df["projected_position_value"].mean(), color="darkred", linestyle="--", label=f"Mean: ${df['projected_position_value'].mean():.0f}")
    ax5.set_title("Projected Final Position Value (2025 Close)")
    ax5.set_xlabel("Start Year")
    ax5.set_ylabel("Position Value ($)")
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 图6: Total Investment
    ax6 = axes[1, 2]
    ax6.bar(df["start_year"], df["total_invest"], color="orange", alpha=0.7)
    ax6.axhline(y=df["total_invest"].mean(), color="darkorange", linestyle="--", label=f"Mean: ${df['total_invest'].mean():.0f}")
    ax6.set_title("Total Investment (10 Years)")
    ax6.set_xlabel("Start Year")
    ax6.set_ylabel("Total Investment ($)")
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    # 图7: Total Dividend Received
    ax7 = axes[2, 0]
    ax7.bar(df["start_year"], df["total_dividend"], color="green", alpha=0.7)
    ax7.axhline(y=df["total_dividend"].mean(), color="darkgreen", linestyle="--", label=f"Mean: ${df['total_dividend'].mean():.0f}")
    ax7.set_title("Total Dividend Received (10 Years)")
    ax7.set_xlabel("Start Year")
    ax7.set_ylabel("Total Dividend ($)")
    ax7.legend()
    ax7.grid(True, alpha=0.3)

    # 图8: Annual Dividend of Last Backtest Year
    ax8 = axes[2, 1]
    ax8.bar(df["start_year"], df["last_year_dividend"], color="brown", alpha=0.7)
    ax8.axhline(y=df["last_year_dividend"].mean(), color="darkred", linestyle="--", label=f"Mean: ${df['last_year_dividend'].mean():.0f}")
    ax8.set_title("Annual Dividend of Last Backtest Year")
    ax8.set_xlabel("Start Year")
    ax8.set_ylabel("Dividend ($/year)")
    ax8.legend()
    ax8.grid(True, alpha=0.3)

    # 图9: Projected Annual Dividend
    ax9 = axes[2, 2]
    ax9.bar(df["start_year"], df["projected_dividend"], color="purple", alpha=0.7)
    ax9.axhline(y=df["projected_dividend"].mean(), color="purple", linestyle="--", label=f"Mean: ${df['projected_dividend'].mean():.0f}")
    ax9.set_title("Projected Annual Dividend (End Shares × 2025 DPS)")
    ax9.set_xlabel("Start Year")
    ax9.set_ylabel("Projected Dividend ($/year)")
    ax9.legend()
    ax9.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    logging.info(f"\nRolling chart saved to: {output}")

    # 打印统计摘要
    logging.info("\n=== Rolling Backtest Summary ===")
    logging.info(f"Number of start dates: {len(df)}")
    logging.info(f"CAGR: Mean={df['cagr'].mean()*100:.2f}%, Min={df['cagr'].min()*100:.2f}%, Max={df['cagr'].max()*100:.2f}%")
    logging.info(f"Max Drawdown: Mean={df['max_drawdown'].mean()*100:.2f}%, Min={df['max_drawdown'].min()*100:.2f}%, Max={df['max_drawdown'].max()*100:.2f}%")
    logging.info(f"Total Investment: Mean=${df['total_invest'].mean():.0f}, Min=${df['total_invest'].min():.0f}, Max=${df['total_invest'].max():.0f}")
    logging.info(f"Projected Dividend: Mean=${df['projected_dividend'].mean():.0f}, Min=${df['projected_dividend'].min():.0f}, Max=${df['projected_dividend'].max():.0f}")
