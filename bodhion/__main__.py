import argparse
import datetime
import importlib.util
import json
import os

import backtrader as bt

from .bot import Bot


def parse_strategy(basedir, name):
    for path in os.listdir(basedir):
        if ".py" in path:
            spec = importlib.util.spec_from_file_location("bodhion", os.path.join(basedir, path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr in dir(mod):
                if attr == name:
                    obj = getattr(mod, attr)
                    if issubclass(obj, bt.Strategy):
                        return obj


def load_config(basedir):
    with open(os.path.join(basedir, "config.json")) as f:
        return json.load(f)


if __name__ == "__main__":
    DT_FORMAT = "%Y-%m-%dT%H:%M:%S"
    userdir = os.getcwd()

    parser = argparse.ArgumentParser(prog='bodhion',
                                     description='Bodhion - Crypto Currency Trading Bot')
    parser.add_argument('--userdir', metavar='userdir', default=userdir,
                        help='User directory where user defined strategies and configuration are located (default: %s)' % userdir)
    subparsers = parser.add_subparsers(title='commands', dest="command")
    parser_bt = subparsers.add_parser('backtest', help='Back test specified strategy')
    parser_opt = subparsers.add_parser('optimize', help='Optimize specified strategy')
    parser_live = subparsers.add_parser('run', help='Run live trade for specified strategy')

    start = (datetime.datetime.utcnow() - datetime.timedelta(minutes=600)).strftime(DT_FORMAT)
    end = (datetime.datetime.utcnow() - datetime.timedelta(minutes=1)).strftime(DT_FORMAT)

    for p in [parser_bt, parser_opt, parser_live]:
        p.add_argument('--start', metavar='start_time', default=start,
                       type=lambda s: datetime.datetime.strptime(s, DT_FORMAT),
                       help='Start time (Default value. %s)' % start)

        if p != parser_live:
            p.add_argument('--end', metavar='end_time', default=end,
                           type=lambda s: datetime.datetime.strptime(s, DT_FORMAT),
                           help='End time (Default value. %s)' % end)

        p.add_argument('--strategy', required=True, metavar='strategy',
                       help='Strategy name defined under userdir/strategies')

    args = parser.parse_args()
    if hasattr(args, "strategy"):
        strategy = parse_strategy(os.path.join(args.userdir, "strategies"), args.strategy)

        if strategy is None:
            print("Strategy %s is not defined" % args.strategy)
        else:
            config = load_config(args.userdir)
            bot = Bot(config)
            if args.command == "run":
                bot.run(strategy=strategy, start=args.start)
            elif args.command == "backtest":
                bot.backtest(strategy=strategy, start=args.start, end=args.end)
            elif args.command == "optimize":
                bot.optimize(strategy=strategy, start=args.start, end=args.end)
    else:
        parser.print_help()
