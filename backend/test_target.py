import backtester
import strategy
import sys

def test():
    # Grid search Breakout
    rsi_lowers = [60, 65]
    stops = [1.2, 1.5]
    targets = [3.0, 4.0, 5.0]

    for rl in rsi_lowers:
        for st in stops:
            for tg in targets:
                strategy.RSI_LOWER = rl
                strategy.RSI_UPPER = 85
                strategy.VOL_SURGE_MULTIPLIER = 1.2
                
                strategy.ATR_STOP_MULTIPLIER = st
                backtester.ATR_STOP_MULTIPLIER = st
                strategy.ATR_TARGET_MULTIPLIER = tg
                backtester.ATR_TARGET_MULTIPLIER = tg
                
                res = backtester.run_backtest(1000.0, use_time_stop=True)
                m = res['metrics']
                sys.stdout.write(f"RL: {rl}, Stop: {st}, Target: {tg} -> PF: {m['profit_factor']}, WR: {m['win_rate']}%, Trades: {m['total_trades']}\n")

if __name__ == "__main__":
    import builtins
    old_print = builtins.print
    builtins.print = lambda *a, **k: None
    test()
    builtins.print = old_print
