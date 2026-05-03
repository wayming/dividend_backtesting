import abc
import dataclasses
import pprint
import logging

OPERATION_BUY = "buy"
OPERATION_SELL = "sell"


@dataclasses.dataclass
class Holding:
    symbol: str
    shares: float = 0.0
    holding_price: float = 0.0 # For calculating take profit and avg down price
    market_price: float = 0.0
    avg_down_price: float = 0.0
    take_profit_price: float = 0.0
    position_value: float = 0.0
    total_dividend_received: float = 0.0
    total_purchase_cost: float = 0.0
    last_avg_down_price: float = 0.0
    initial_shares: float = 0.0
    initial_price: float = 0.0
    
    # Immutable after the initial buy
    floor_shares: float = 0.0

    buys: dict = dataclasses.field(default_factory=dict)
    sells: dict = dataclasses.field(default_factory=dict)

    
    def export(self):
        return pprint.pformat(dataclasses.asdict(self))

class TradingStrategy(abc.ABC):
    @abc.abstractmethod
    def execute(self, date, cash, holding: Holding, market_data) -> list[tuple[str, str, float]]:
        """
        Execute trading strategy and return list of operations.
        
        Args:
            date: Current date
            cash: Current cash balance
            holding: Current holding
            market_data: Dictionary of symbol -> market data (e.g., Close price)
            
        Returns:
            List of tuples (operation, symbol, amount) where:
            - operation: "buy" or "sell"
            - symbol: Stock symbol
            - amount: Dollar amount to trade
        """
        pass


class TakeProfitPercentageStrategy(TradingStrategy):
    def __init__(self, take_profit_rate: float = 2, take_profit_sell_ratio: float = 0.2) -> None:
        super().__init__()
        self.take_profit_rate = take_profit_rate
        self.take_profit_sell_ratio = take_profit_sell_ratio
        
    def execute(self, date, cash, holdings: dict, market_data) -> list[tuple[str, str, float]]:
        symbols = list(market_data.keys())
        if not symbols:
            return []
        operations = []

        for symbol, holding in holdings.items():
            avg_cost_per_share = holding.total_purchase_cost/holding.shares
            if market_data[symbol]["Close"] > avg_cost_per_share * self.take_profit_rate:
                operations.append((OPERATION_SELL, symbol, holding.shares * self.take_profit_sell_ratio))
        
        return operations

class AverageDownStrategy(TradingStrategy):
    def __init__(self, average_down_rate: float = 0.5, average_down_buy_ratio: float = 1.0) -> None:
        super().__init__()
        self.average_down_rate = average_down_rate
        self.average_down_buy_ratio = average_down_buy_ratio
        
    def execute(self, date, cash, holdings: dict, market_data) -> list[tuple[str, str, float]]:
        # Buy all stocks with equal weight
        symbols = list(market_data.keys())
        if not symbols:
            return []
        
        operations = []

        for symbol, holding in holdings.items():
            avg_cost_per_share = holding.total_purchase_cost/holding.shares
            if market_data[symbol]["Close"] < avg_cost_per_share * self.average_down_rate:
                operations.append((OPERATION_BUY, symbol, holding.shares * self.average_down_buy_ratio))
        
        return operations

class AverageDownCostBasedStrategy(TradingStrategy):
    def __init__(self, symbols) -> None:
        super().__init__()
        self.symbols = symbols
        # 补仓逻辑：基于当前持仓成本的跌幅
        # (成本跌幅阈值, 投入金额占Cap的比例)
        self.average_down_bands = {
            "band1": (0.80, 0.2), # 现价比成本低 20%，投入 0.2倍 Cap
            "band2": (0.70, 0.5), # 现价比成本低 30%，投入 0.5倍 Cap
            "band3": (0.50, 1.0), # 现价比成本低 50%，投入 1.0倍 Cap (腰斩重仓)
            "band4": (0.30, 2.0), # 现价比成本低 70%，投入 2.0倍 Cap (终极低吸)
        }
        self.triggered_bands = {symbol: set() for symbol in self.symbols}
        self.cap = 0
        
    def execute(self, date, cash, holdings: dict, market_data) -> list[tuple[str, str, float]]:
        operations = []
        for symbol, holding in holdings.items():
            if symbol not in market_data: continue
            if holding.shares <= 0: continue
            
            self.cap = holding.initial_shares * holding.initial_price
            
            avg_cost_per_share = holding.total_purchase_cost/holding.shares
            close_price = market_data[symbol]["Close"]
            
            if close_price > avg_cost_per_share * 1.20:
                self.triggered_bands[symbol].clear() # 价格回升超过20%，重置补仓档位
                continue
            
            for band, (price_threshold, buy_ratio) in self.average_down_bands.items():
                if band in self.triggered_bands[symbol]:
                    continue # 已经触发过这个档位了
                
                if close_price < avg_cost_per_share * price_threshold:
                    target_buy_amount = self.cap * buy_ratio
                    target_buy_shares = target_buy_amount // close_price
                    operations.append((OPERATION_BUY, symbol, target_buy_shares))
                    self.triggered_bands[symbol].add(band)
                    logging.info(f"Average down: {symbol} trigger {band} at price {close_price}, avg cost {avg_cost_per_share}, buy {target_buy_shares} shares at {close_price}")
        return operations
    
# Average down by MA250
# Each band only trigger once, and restart from band1 when MA250 exceeds initial price
class AverageDownByMA250Strategy(TradingStrategy):
    def __init__(self, symbols) -> None:
        super().__init__()
        self.symbols = symbols
        self.average_down_bands = {
            "band1": (0.80, 0.15), # 跌 20% 才开始第一笔
            "band2": (0.60, 0.20), # 跌 40% 第二笔
            "band3": (0.45, 0.25), # 跌 55% 第三笔
            "band4": (0.30, 0.30), # 跌 70% 第四笔
            "band5": (0.15, 0.35), # 极速深坑
            "band6": (None, None),
        }
        self.state = {symbol: "band1" for symbol in self.symbols}
        self.cap = 20000
    def next_band(self, band:str):
        bands = list(self.average_down_bands.keys())
        current_index = bands.index(band)
        return bands[current_index + 1] if current_index < len(bands) - 1 else band
    
    def execute(self, date, cash, holdings: dict, market_data) -> list[tuple[str, str, float]]:
        # Buy all stocks with equal weight
        symbols = list(market_data.keys())
        if not symbols:
            return []

        operations = []
        for symbol, holding in holdings.items():
            current_state = self.state[symbol]
            band_threshold, band_buy_ratio = self.average_down_bands[current_state]
            close_price = market_data[symbol]["Close"]
            ma250 = market_data[symbol]["MA250"]

            if close_price > ma250 * 1.05:
                if self.state[symbol] != "band1":
                    logging.info(f"{symbol} close price exceeds MA250, reset average down band")
                    self.state[symbol] = "band1"
                continue # 既然已经回升，本轮就不再判断补仓逻辑
            
            # 只有在定义了阈值的情况下才执行
            if band_threshold:
                # 触发补仓：现价低于阈值
                if close_price < ma250 * band_threshold:
                    # 用初始股数作为基准
                    target_buy_shares = int(holding.shares * band_buy_ratio)
                    
                    # 检查是否超过单笔上限
                    buy_amount = target_buy_shares * close_price
                    if buy_amount > self.cap:
                        target_buy_shares = self.cap // close_price
                    
                    if target_buy_shares > 0:
                        operations.append((OPERATION_BUY, symbol, target_buy_shares))
                        # 只有成功发出指令后才推送到下一个阶段
                        self.state[symbol] = self.next_band(current_state)
                        logging.info(f"Average down by MA250: {symbol} {target_buy_shares} shares at {market_data[symbol]['Close']}, next band {self.state[symbol]}")

        return operations

# Buy all stocks with equal weight
class CashSplitEvenlyStrategy(TradingStrategy):
    def execute(self, date, cash, holdings: dict, market_data) -> list[tuple[str, str, float]]:
        # Buy all stocks with equal weight
        symbols = [s for s in market_data if market_data[s].get("Close", 0) > 0]
        if not symbols:
            return []

        operations = []

        if cash < sum([market_data[symbol]["Close"] for symbol in symbols]):
            logging.debug(f"Cash is not enough for buying all stocks")
            return []

        cash_per_stock = cash / len(symbols)
        for symbol in symbols:
            operations.append((OPERATION_BUY, symbol, int(cash_per_stock/market_data[symbol]["Close"])))

        return operations


# Buy the stock with the highest dividend yield
class CashForHighDivStrategy(TradingStrategy):
    def execute(self, date, cash, holdings: dict, market_data) -> list[tuple[str, str, float]]:
        # Buy all stocks with equal weight
        symbols = list(market_data.keys())
        if not symbols:
            return []
                
        _, highest_yield_symbol = max([(data["Yield"], symbol) for symbol, data in market_data.items() if data["Yield"] is not None])
        if cash < market_data[highest_yield_symbol]["Close"]:
            logging.debug(f"Cash is not enough for buying {highest_yield_symbol}")
            return []
        
        return [(OPERATION_BUY, highest_yield_symbol, int(cash/market_data[highest_yield_symbol]["Close"]))]
        
