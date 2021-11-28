import backtrader as bt
import backtrader.analyzers as btanalyzers
import datetime, logging
from .ccxtbt import CCXTStore, CCXTFeed

GRANULARITY_SCALE_MAP = {
    bt.TimeFrame.Minutes: 1,
    bt.TimeFrame.Days: 1440,
    bt.TimeFrame.Weeks: 1440*7,
    bt.TimeFrame.Months: 1440*30,
    bt.TimeFrame.Years: 1440*365,
}



def _validate_config(v, name):
    if v is None:
        raise ValueError("%s is not defined in config.json" % name)

class Bot:
    def __init__(self, config):
        self.config = config
        # debug = config.get("debug", False)
        # if debug:
        #     logging.basicConfig(level=logging.DEBUG)
        # else:
        #     logging.basicConfig(level=logging.INFO)

    def name(self):
        return self.config.get("name", None)

    def _create_store(self, config):
        exchange = config.get("exchange", {}).get("name", None)
        exchange_config = config.get("exchange", {}).get("config", None)
        sandbox = config.get("exchange", {}).get("sandbox", True)
        currency = config.get("exchange", {}).get("currency", None)
        retries = config.get("exchange", {}).get("retries", 5)
        debug = config.get("debug", False)

        _validate_config(exchange, "exchange.name")
        _validate_config(exchange_config, "exchange.config")
        _validate_config(currency, "exchange.currency")

        return CCXTStore(exchange=exchange, currency=currency, config=exchange_config, retries=retries, sandbox=sandbox, debug=debug)

    def _apply_broker(self, cerebro, store, config):
        broker_mapping = config.get("broker_mapping", None)

        _validate_config(broker_mapping, "broker_mapping")

        broker = store.getbroker(broker_mapping=broker_mapping)
        cerebro.setbroker(broker)

    def _apply_data(self, cerebro, store, start, end, backtest, config):
        exchange = config.get("exchange", {}).get("name", None)
        exchange_config = config.get("exchange", {}).get("config", None)
        currency = config.get("exchange", {}).get("currency", None)
        retries = config.get("exchange", {}).get("retries", 5)
        sandbox = config.get("exchange", {}).get("sandbox", True)
        debug = config.get("debug", False)

        _validate_config(exchange, "exchange.name")
        _validate_config(exchange_config, "exchange.config")
        _validate_config(currency, "exchange.currency")

        for i, datafeed in enumerate(config.get("datafeeds", [])):
            timeframe = getattr(bt.TimeFrame, datafeed.get("timeframe", "Minutes"))
            dataname = datafeed.get("dataname", None)
            name = datafeed.get("name", None)
            ohlcv_limit = datafeed.get("ohlcv_limit", 20)
            compression = datafeed.get("compression", 1)
            todate = datafeed.get("todate", datetime.datetime.utcnow())
            drop_newest = datafeed.get("drop_newest", False)

            _validate_config(dataname, "datafeeds[%d].dataname"%i)
            _validate_config(name, "datafeeds[%d].name"%i)

            # if store is None:
            #     cash = config.get("backtest", {}).get("cash", 1000)
            #     short = config.get("backtest", {}).get("short", True)
            #     commission = config.get("backtest", {}).get("commission", 0)
            #     cerebro.broker.setcash(cash)
            #     cerebro.broker.set_shortcash(short)
            #     cerebro.broker.setcommission(commission = commission)

            #     data = CCXTFeed(exchange=exchange,
            #                     dataname=dataname,
            #                     timeframe=timeframe,
            #                     fromdate=start,
            #                     todate=end,
            #                     sandbox=sandbox,
            #                     compression=compression,
            #                     ohlcv_limit=ohlcv_limit,
            #                     currency=currency,
            #                     retries=retries,
            #                     config=exchange_config)
            # else:
            if backtest:                
                cash = config.get("backtest", {}).get("cash", 1000)
                short = config.get("backtest", {}).get("short", True)
                commission = config.get("backtest", {}).get("commission", 0)
                cerebro.broker.setcash(cash)
                cerebro.broker.set_shortcash(short)
                cerebro.broker.setcommission(commission = commission)

                data = store.getdata(dataname=dataname, 
                                name=name,
                                timeframe=timeframe,
                                fromdate=start,
                                todate=end,
                                ohlcv_limit=ohlcv_limit,
                                compression=compression,
                                drop_newest=drop_newest,
                                debug=debug, historical=True)
            else:
                start = datetime.datetime.utcnow() - datetime.timedelta(minutes=compression * GRANULARITY_SCALE_MAP[timeframe] * ohlcv_limit)
                print("!!!!!", start)
                data = store.getdata(dataname=dataname, 
                                name=name,
                                timeframe=timeframe,
                                fromdate=start,
                                ohlcv_limit=ohlcv_limit,
                                compression=compression,
                                drop_newest=drop_newest,
                                debug=debug, historical=False)

            cerebro.adddata(data)

    def backtest(self, strategy, start, end):
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy)
        store = self._create_store(self.config)
        self._apply_data(cerebro, store, start, end, True, self.config)

        # cerebro.addanalyzer(btanalyzers.SharpeRatio_A, _name='SharpeRatio')
        # cerebro.addanalyzer(btanalyzers.PeriodStats, _name='PeriodStats')
        # cerebro.addanalyzer(btanalyzers.AnnualReturn, _name='AnnualReturn')
        # cerebro.addanalyzer(btanalyzers.DrawDown, _name='DrawDown')
        # cerebro.addanalyzer(btanalyzers.TimeReturn, timeframe=bt.TimeFrame.NoTimeFrame, _name='TimeReturn')

        result = cerebro.run()

        cerebro.plot()

    def run(self, strategy, start):
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy)
        store = self._create_store(self.config)
        self._apply_broker(cerebro, store, self.config)
        self._apply_data(cerebro, store, start, None, False, self.config)

        result = cerebro.run()

    def optimize(self, strategy, start, end):
        cerebro = bt.Cerebro()
        cerebro.optstrategy(strategy)
        store = self._create_store(self.config)
        self._apply_data(cerebro, store, start, end, True, self.config)
        result = cerebro.run()
