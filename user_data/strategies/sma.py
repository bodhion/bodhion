import backtrader as bt
import numpy as np

class SMA(bt.Strategy):
    params = (('period', 500),)

    def __init__(self):
        self.dataclose = self.datas[0].close
        
        self.sma = bt.indicators.SimpleMovingAverage(self.datas[0], period = int(self.params.period))
        self.cross = bt.ind.CrossOver(self.dataclose, self.sma)

        # To keep track of pending orders and buy price/commission
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        self.order = None

    def next(self):
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return
        
        # Amount is quantity of the instrument equal to current portfolio value times quantity factor
        amount = self.broker.getvalue() # / self.dataclose[0]

        pos = abs(self.position.size) 
        buy_sig = self.buy_signal()
        sell_sig = self.sell_signal()

        dt = self.datas[0].datetime.datetime(0)
        # print('%s closing price: %s, buy_sig: %s, sell_sig: %s, pos: %s, value: %s' % (dt.isoformat(), self.datas[0].close[0], buy_sig, sell_sig, self.position.size, amount))

        if buy_sig:
            if self.position.size < 0: # already short, need to also buy back the short position
                amount = pos + amount

            if self.position.size <= 0:
                print(self.datas[0].datetime.datetime(), "BUY", amount)
                self.order = self.buy(size = amount)
        elif sell_sig:
            if self.position.size > 0: # already long, need to sell the current long position
                amount = pos + amount

            if self.position.size >= 0:
                print(self.datas[0].datetime.datetime(), "SELL", amount)
                self.order = self.sell(size = amount)

    def buy_signal(self):
        return self.cross > 0

    def sell_signal(self):
        return self.cross < 0
