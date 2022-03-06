import backtrader as bt
import datetime
import logging
import pika
import json
from cryptobt import CryptoStore
from multiprocessing import Process
from .chat import start_chat_bot

GRANULARITY_SCALE_MAP = {
    bt.TimeFrame.Seconds: 1,
    bt.TimeFrame.Minutes: 60,
    bt.TimeFrame.Days: 1440 * 60,
    bt.TimeFrame.Weeks: 1440 * 7 * 60,
    bt.TimeFrame.Months: 1440 * 30 * 60,
    bt.TimeFrame.Years: 1440 * 365 * 60,
}


def _validate_config(v, name):
    if v is None:
        raise ValueError("%s is not defined in config.json" % name)


def _create_store(config, order_interceptor=None):
    exchange = config.get("exchange", {}).get("name", None)
    exchange_config = config.get("exchange", {}).get("config", None)
    sandbox = config.get("exchange", {}).get("sandbox", True)
    currency = config.get("exchange", {}).get("currency", None)
    retries = config.get("exchange", {}).get("retries", 5)
    debug = config.get("debug", False)

    _validate_config(exchange, "exchange.name")
    _validate_config(exchange_config, "exchange.config")
    _validate_config(currency, "exchange.currency")

    return CryptoStore(exchange=exchange, currency=currency, config=exchange_config,
                       retries=retries, sandbox=sandbox, debug=debug, order_interceptor=order_interceptor)


def _apply_broker(cerebro, store, config):
    broker_mapping = config.get("broker_mapping", None)

    _validate_config(broker_mapping, "broker_mapping")

    broker = store.getbroker(broker_mapping=broker_mapping)
    cerebro.setbroker(broker)


def _apply_data(cerebro, store, start, end, backtest, config):
    exchange = config.get("exchange", {}).get("name", None)
    exchange_config = config.get("exchange", {}).get("config", None)
    currency = config.get("exchange", {}).get("currency", None)
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

        _validate_config(dataname, "datafeeds[%d].dataname" % i)
        _validate_config(name, "datafeeds[%d].name" % i)

        if backtest:
            cash = config.get("backtest", {}).get("cash", 1000)
            short = config.get("backtest", {}).get("short", True)
            commission = config.get("backtest", {}).get("commission", 0)
            cerebro.broker.setcash(cash)
            cerebro.broker.set_shortcash(short)
            cerebro.broker.setcommission(commission=commission)

            data = store.getdata(dataname=dataname, name=name, timeframe=timeframe, fromdate=start,
                                 todate=end, compression=compression, ohlcv_limit=ohlcv_limit, drop_newest=False,
                                 historical=True, debug=debug)
        else:
            start = datetime.datetime.utcnow() - datetime.timedelta(
                seconds=compression * GRANULARITY_SCALE_MAP[timeframe] * ohlcv_limit)
            data = store.getdata(dataname=dataname, name=name, timeframe=timeframe, fromdate=start, debug=debug,
                                 compression=compression, ohlcv_limit=ohlcv_limit, drop_newest=True, historical=False)

        cerebro.adddata(data)


class Bot:
    def __init__(self, config):
        self.config = config
        debug = config.get("debug", False)
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

    def name(self):
        return self.config.get("name", None)

    def backtest(self, strategy, start, end):
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy)
        store = _create_store(self.config)
        _apply_data(cerebro, store, start, end, True, self.config)

        result = cerebro.run()
        cerebro.plot()

    def run(self, strategy, start):
        interceptor = self.config.get("order_interceptor", None)
        if interceptor is not None:
            broker = interceptor.get("broker", None)
            exchange = interceptor.get("exchange", None)
            chatbot = interceptor.get("chatbot", None)

            if broker is not None and chatbot is not None:
                # Install docker and run following commands to start rabbitmq
                # docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.9-management
                connection = pika.BlockingConnection(pika.ConnectionParameters(**broker))
                channel = connection.channel()
                channel.exchange_declare(exchange=exchange, exchange_type='fanout')

                def order_interceptor(symbol, order_type, side, amount, price, params):
                    print("INTERCEPTED ORDER:", symbol, order_type, side, amount, price, params)
                    message = json.dumps({
                        "symbol": symbol,
                        "order_type": order_type,
                        "side": side,
                        "amount": amount,
                        "price": price,
                        "param": params
                    })
                    channel.basic_publish(exchange='orders', routing_key='', body=message)

                background_thread = Process(target=start_chat_bot, args=(chatbot,))
                background_thread.start()
                store = _create_store(self.config, order_interceptor)
        else:
            store = _create_store(self.config)

        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy)

        _apply_broker(cerebro, store, self.config)
        _apply_data(cerebro, store, start, None, False, self.config)

        result = cerebro.run()

    def optimize(self, strategy, start, end):
        cerebro = bt.Cerebro()
        cerebro.optstrategy(strategy)
        store = _create_store(self.config)
        _apply_data(cerebro, store, start, end, True, self.config)
        result = cerebro.run()
