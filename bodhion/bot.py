import backtrader as bt
import datetime
from ccxtbt import CCXTStore, CCXTFeed

def _validate_config(v, name):
    if v is None:
        raise ValueError("%s is not defined in config.json" % name)

class Bot:
    def __init__(self, config):
        self.config = config

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

    def _apply_data(self, cerebro, store, start, end, config, backtest):
        exchange = config.get("exchange", {}).get("name", None)
        exchange_config = config.get("exchange", {}).get("config", None)
        currency = config.get("exchange", {}).get("currency", None)
        retries = config.get("exchange", {}).get("retries", 5)
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

            if backtest:
                data = CCXTFeed(exchange=exchange,
                                dataname=dataname,
                                timeframe=timeframe,
                                fromdate=start,
                                todate=end,
                                compression=compression,
                                ohlcv_limit=ohlcv_limit,
                                currency=currency,
                                retries=retries,
                                config=exchange_config)
            else:
                data = store.getdata(dataname=dataname, 
                                name=name,
                                timeframe=timeframe,
                                fromdate=start,
                                ohlcv_limit=ohlcv_limit,
                                compression=compression,
                                drop_newest=drop_newest,
                                debug=debug) #, historical=True)

                cerebro.adddata(data)

    def backtest(self, strategy, start, end):
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy)
        self._apply_data(cerebro, None, start, end, self.config, True)
        return cerebro.run()

    def run(self, strategy, start):
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy)
        store = self._create_store(self.config)
        self._apply_broker(cerebro, store, self.config)
        self._apply_data(cerebro, store, start, None, self.config, False)

        return cerebro.run()

    def optimize(self, strategy, start, end):
        cerebro = bt.Cerebro()
        cerebro.optstrategy(strategy)
        self._apply_data(cerebro, None, start, end, self.config, True)
        return cerebro.run()
