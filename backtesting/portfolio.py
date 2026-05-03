import dataclasses
import datetime
import logging
import pprint
from .strategy import *

from backtesting.strategy import TradingStrategy

@dataclasses.dataclass
class Portfolio_Conifg:
    # Sell 20% when price doubled
    take_profit_ratio : float = 2
    take_profit_sell_ratio: float = 0.2
    
    # Buy with external fund when stock drops to avg_down_trigger_ratio to average down the holding price
    # Total fund is the percentage of stock that meet the critera multiply by the total market value after drop.
    avg_down_trigger_ratio: float = 0.5
    
    initial_fund: float = 100000
    
    floor_shares_rate:float = 0.2
    regular_investment_rate : float = 0.5

    def export(self):
        return pprint.pformat(dataclasses.asdict(self))
    

class Portfolio:
    def __init__(self, config:Portfolio_Conifg):
        self.stock_holding : dict[str, Holding] = {}
        self.total_invest = 0 # Excludes the dividend investment
        self.cash = 0
        self.config = config
        self.balance_strategies : list[TradingStrategy] = []
        self.pending_operations : list[tuple[str, str, float]] = []
        self.cash_split_strategy : TradingStrategy = CashForHighDivStrategy()
        self.initial_equity_distribution_strategy : TradingStrategy = CashSplitEvenlyStrategy()

    def initial_equity(self, date, cash, market_data):
        operations = self.initial_equity_distribution_strategy.execute(date, cash, {}, market_data)
        for operation in operations:
            self.pending_operations.append(operation)
    
    def add_balance_strategy(self, strategy:TradingStrategy):
        self.balance_strategies.append(strategy)    
    
    def add_cash(self, date, cash: float):
        logging.info(f"[{date}] Transfer cash {cash}")
        self.cash += cash
        self.total_invest += cash

    def buy(self, date:datetime.date, symbol:str, shares:int, unit_price:float):

        if self.cash < shares * unit_price:
            logging.info(f"Not enough cash to buy {symbol} {shares} shares at {unit_price}")
            return
        
        if symbol not in self.stock_holding:
            holding = Holding(symbol = symbol)
            self.stock_holding[symbol] = holding
        
        holding = self.stock_holding[symbol]
        fund_to_use = shares * unit_price
        old_holing_price = holding.holding_price
        holding.holding_price = (holding.holding_price * holding.shares + fund_to_use)/(holding.shares + shares)
        holding.market_price = unit_price
        holding.position_value = holding.market_price * holding.shares
        if holding.shares == 0:
            # New buy
            holding.floor_shares = self.config.floor_shares_rate * shares
            holding.initial_price = unit_price
            holding.initial_shares = shares
        holding.shares += shares
        holding.avg_down_price = holding.holding_price * self.config.avg_down_trigger_ratio # Price down
        holding.take_profit_price = holding.holding_price * self.config.take_profit_ratio # Price double
        holding.total_purchase_cost += fund_to_use
        logging.info(f"[{date}] Buy {symbol} at price {unit_price} with fund_to_use {fund_to_use}"
        f" get {shares} shares, old holding price at {old_holing_price}, new holding price at {holding.holding_price}"
        f" new holding shares {holding.shares}")
        holding.buys[date] = {
            "fund": fund_to_use,
            "unit_price": unit_price,
            "shares": shares
        }
        self.cash -= fund_to_use

        if self.cash < 0:
            self.cash = 0 # Set to 0 if negative (should be non-trivial)
        logging.info(f"[{date}] Cash after buy {self.cash}")
        pass
    
    def sell(self, date:datetime.date, symbol:str, sell_shares:int, unit_price:float):
        if symbol not in self.stock_holding:
            raise KeyError(f"No holdings for {symbol}")
    
        holding = self.stock_holding[symbol]
        if holding.shares <= holding.floor_shares:
            logging.info(f"{symbol} reach floor shares {holding.floor_shares}, current shares {holding.shares}, no sell")
            return
        self.cash += sell_shares * unit_price
        holding.shares -= sell_shares
        holding.market_price = unit_price
        holding.position_value = holding.market_price * holding.shares
        logging.info(f"[{date}] Sell {symbol} shares {sell_shares} at {unit_price},"
        f" holding price {holding.market_price}, return cash {sell_shares * unit_price}"
        f" new holding shares {holding.shares}")
        holding.sells[date] = {
            "shares": sell_shares,
            "unit_price": unit_price,
            "return_cash": sell_shares * unit_price
        }
        pass

    def dividend(self, date:datetime.date, symbol:str, dividen_per_share: float, market_data: dict = None):
        if symbol not in self.stock_holding:
            raise KeyError(f"No holdings for {symbol}")

        if dividen_per_share == 0:
            return
        
        holding = self.stock_holding[symbol]
        dividend_cash = holding.shares * dividen_per_share
        
        # 收到分红现金
        holding.total_dividend_received += dividend_cash
        self.cash += dividend_cash
        logging.info(f"Receive dividend for {symbol}, {dividen_per_share} per share, return cash {dividend_cash}")
        
        # 立即将分红现金用于再投资（如果有价格信息）
        if dividend_cash > 0 and market_data:
            for op, symbol, shares in self.cash_split_strategy.execute(date, dividend_cash, self.stock_holding, market_data):
                if op == OPERATION_BUY:
                    self.buy(date, symbol, shares, market_data[symbol]["Close"])
                elif op == OPERATION_SELL:
                    raise ValueError("Cash split strategy should not sell")
        
        # 更新所有股票的市场价格
        if market_data:
            self.populate_position(market_data)

    
    def rebalance(self, date:datetime.date, market_data: dict):
        cash_required = 0

        for strategy in self.balance_strategies:
            self.pending_operations.extend(strategy.execute(date, self.cash, self.stock_holding, market_data))
        if self.pending_operations:
            logging.info(f"pending operations: {self.pending_operations}")

        buys = [op for op in self.pending_operations if op[0] == OPERATION_BUY]
        sells = [op for op in self.pending_operations if op[0] == OPERATION_SELL]
        for _, symbol, shares in sells:
            self.sell(date, symbol, shares, market_data[symbol]["Close"])
        
        for _, symbol, shares in buys:
            if symbol not in self.stock_holding:
                holding = Holding(symbol = symbol)
                self.stock_holding[symbol] = holding
            if self.cash < shares * market_data[symbol]["Close"]:
                cash_required += shares * market_data[symbol]["Close"]
                logging.info(f"Not enough cash to buy {shares} shares of {symbol} at {market_data[symbol]['Close']}, required {cash_required}, available {self.cash}")
                continue
            self.buy(date, symbol, shares, market_data[symbol]["Close"])
        
        if self.cash > 0 and self.cash_split_strategy:
            for op, symbol, shares in self.cash_split_strategy.execute(date, self.cash, self.stock_holding, market_data):
                if op == OPERATION_BUY:
                    self.buy(date, symbol, shares, market_data[symbol]["Close"])
                elif op == OPERATION_SELL:
                    raise ValueError("Cash split strategy should not sell")

        self.populate_position(market_data)
        self.pending_operations = []

        return cash_required
    
    def populate_position(self, market_data: dict):
        for sym, data in market_data.items():
            self.stock_holding[sym].market_price = data["Close"]
            self.stock_holding[sym].position_value = self.stock_holding[sym].shares * data["Close"]
            
    def stats(self, market_data:dict):
        result_stats = {}
        market_data_iter = iter(market_data.keys())

        first = True
        while date := next(market_data_iter, None):
            position_values = [holding.shares * market_data[date][symbol]["Close"] for symbol, holding in self.stock_holding.items()]
            dividend_receiveds = [holding.shares * market_data[date][symbol]["Close"] * market_data[date][symbol]["Yield"] for symbol, holding in self.stock_holding.items()]
            if first:
                result_stats["dividend_received_end_year"] = float(sum(dividend_receiveds))
                result_stats["position_value_end_year"] = float(sum(position_values))
                result_stats["cash_end_year"] = self.cash
                result_stats["total_equity_end_year"] = result_stats["position_value_end_year"] + result_stats["cash_end_year"]
                first = False
            else:
                result_stats["dividend_received_" + date.date().strftime("%Y-%m-%d")] = float(sum(dividend_receiveds))
                result_stats["position_value_" + date.date().strftime("%Y-%m-%d")] = float(sum(position_values))

        result_stats["total_invest_cost"] = self.total_invest
        result_stats["total_dividend_received"] = sum(holding.total_dividend_received for _, holding in self.stock_holding.items())
        result_stats["cumulative_return"] = round((result_stats["position_value_end_year"] - result_stats["total_invest_cost"])/result_stats["total_invest_cost"], 2)
        return result_stats

    def show(self):
        for symbol, holding in self.stock_holding.items():
            logging.info(f"\n{holding.export()}")