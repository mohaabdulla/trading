import sys
import backtester
import strategy

def test():
    best_pf = 0
    best_wr = 0
    
    # We want WR >= 60, PF > 1.6
    rsi_lowers = [65, 70]
    stops = [1.2, 1.5, 1.8]
    targets = [3.0, 4.0, 5.0]
    time_stops = [True, False]
    
    strategy.VOL_SURGE_MULTIPLIER = 1.2
    strategy.MIN_VOLATILITY_PCT = 0.02
    
    for rl in rsi_lowers:
        for st in stops:
            for tg in targets:
                for ts in time_stops:
                    strategy.RSI_LOWER = rl
                    strategy.ATR_STOP_MULTIPLIER = st
                    backtester.ATR_STOP_MULTIPLIER = st
                    strategy.ATR_TARGET_MULTIPLIER = tg
                    backtester.ATR_TARGET_MULTIPLIER = tg
                    
                    res = backtester.run_backtest(1000.0, use_time_stop=ts)
                    m = res['metrics']
                    pf = m['profit_factor']
                    wr = m['win_rate']
                    trades = m['total_trades']
                    
                    if wr >= 58.0 and pf >= 1.5:
                        sys.stdout.write(f"RL: {rl}, Stop: {st}, Target: {tg}, TimeStop: {ts} -> PF: {pf}, WR: {wr}%, Trades: {trades}\n")

if __name__ == "__main__":
    import builtins
    old_print = builtins.print
    builtins.print = lambda *a, **k: None
    test()
    builtins.print = old_print
