from unittest import result
import pandas as pd
import backtrader as bt
import backtrader.indicators as btind
import backtrader.feeds as btfeeds
import datetime
import math
import os
from pathlib import Path

import numpy as np


# data_path = Path('./data')




# in case add self-defined features
class PandasData_more(bt.feeds.PandasData):
    lines = ('ret_etf', 'ret', 'xi', 'kappa', 'beta',
             'signal', )  # add self-defined data

    params = (
        ('ret_etf', -1),
        ('ret', -2),
        ('xi', -3),
        ('kappa', -4),
        ('beta', -5),
        ('signal', -6),
    )


def feedData(cerebro, tickers, ind_path, df_empty):
    for ticker in tickers:
        data_temp = pd.read_csv(Path.joinpath(
            ind_path, ticker+'.csv'), index_col=0, parse_dates=True)
        data_temp = df_empty.join(data_temp, how='left')
        # data_temp[['close', 'vol', 'beta', 'kappa', 'xi']] = data_temp[[
        #     'close', 'vol', 'beta', 'kappa', 'xi']].fillna(method='ffill')

        data_temp = data_temp.fillna(method="ffill")
        data_temp['signal'] = data_temp['signal'].fillna(0)
        data_temp = data_temp.fillna(method="bfill")  


        data = PandasData_more(dataname=data_temp,
                               open='close',
                               high=-1,
                               close='close',
                               volume='vol',
                               low=-1,
                               openinterest=-1,
                               fromdate=data_temp.index[0], todate=data_temp.index[-1]
                               )
        cerebro.adddata(data, name=ticker)
        # print(f"Ticker: {ticker} Done!")
    

def pnl_curve(name, results):
    # 提取收益序列
    pnl = pd.Series(results[0].analyzers._TimeReturn.get_analysis())
    # 计算累计收益
    cumulative = (pnl + 1).cumprod()
    # 计算回撤序列
    max_return = cumulative.cummax()
    drawdown = (cumulative - max_return) / max_return
    # 计算收益评价指标
    import pyfolio as pf
    # 按年统计收益指标
    perf_stats_year = (pnl).groupby(pnl.index.to_period('y')).apply(lambda data: pf.timeseries.perf_stats(data)).unstack()
    # 统计所有时间段的收益指标
    perf_stats_all = pf.timeseries.perf_stats((pnl)).to_frame(name='all')
    perf_stats = pd.concat([perf_stats_year, perf_stats_all.T], axis=0)
    perf_stats_ = round(perf_stats,4).reset_index()


    # 绘制图形
    import matplotlib.pyplot as plt
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
    import matplotlib.ticker as ticker  # 导入设置坐标轴的模块
    # plt.rcParams['figure.figsize'] = 30, 15
    plt.style.use('seaborn')  # plt.style.use('dark_background')


    fig, (ax0, ax1) = plt.subplots(2,1, gridspec_kw = {'height_ratios':[1.5, 4]}, figsize=(20,14))
    cols_names = ['date', 'Annual\nreturn', 'Cumulative\nreturns', 'Annual\nvolatility',
        'Sharpe\nratio', 'Calmar\nratio', 'Stability', 'Max\ndrawdown',
        'Omega\nratio', 'Sortino\nratio', 'Skew', 'Kurtosis', 'Tail\nratio',
        'Daily value\nat risk']

    # 绘制表格
    ax0.set_axis_off()  # 除去坐标轴
    table = ax0.table(cellText = perf_stats_.values, 
                    bbox=(0,0,1,1),  # 设置表格位置， (x0, y0, width, height)
                    rowLoc = 'right',  # 行标题居中
                    cellLoc='right' ,
                    colLabels = cols_names, # 设置列标题
                    colLoc = 'right',  # 列标题居中
                    edges = 'open' # 不显示表格边框
                    )
    table.set_fontsize(13)

    # 绘制累计收益曲线
    ax2 = ax1.twinx()
    ax1.yaxis.set_ticks_position('right') # 将回撤曲线的 y 轴移至右侧
    ax2.yaxis.set_ticks_position('left') # 将累计收益曲线的 y 轴移至左侧
    # 绘制回撤曲线
    drawdown.plot.area(ax=ax1, label='drawdown (right)', rot=0, alpha=0.3, fontsize=13, grid=False)
    # 绘制累计收益曲线
    (cumulative).plot(ax=ax2, color='#F1C40F' , lw=3.0, label='cumret (left)', rot=0, fontsize=13, grid=False)
    # 不然 x 轴留有空白
    ax2.set_xbound(lower=cumulative.index.min(), upper=cumulative.index.max())
    # 主轴定位器：每 5 个月显示一个日期：根据具体天数来做排版
    ax2.xaxis.set_major_locator(ticker.MultipleLocator(100)) 
    # 同时绘制双轴的图例
    h1,l1 = ax1.get_legend_handles_labels()
    h2,l2 = ax2.get_legend_handles_labels()
    plt.legend(h1+h2,l1+l2, fontsize=12, loc='upper left', ncol=1)

    fig.tight_layout() # 规整排版

    result = results[0]
    openlong = result.params.openlong
    openshort = result.params.openshort
    
    closelong = result.params.closelong
    closeshort = result.params.closeshort
    kappa_threshold = result.params.kappa_threshold

    file_path = Path("plot")
    plt.savefig(file_path / f"cumret_{name}_{openlong:.1f}_{closelong:.1f}_{kappa_threshold:.1f}.png")
    plt.show()