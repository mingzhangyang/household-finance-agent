#!/usr/bin/env python3
"""Reproducible annual historical stock/bond scenario analysis.

Requires a dated CSV snapshot. Preserves year-by-year stock/bond joint
observations; does not confuse sample-window frequency with future probability.
This standalone validator is NOT yet wired into audit_plan's funding/tax solver.
"""
import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

SOURCE="https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/histretSPX.html"

class MarketDataError(ValueError): pass

def _rate(x,field):
    try:value=float(x)
    except (ValueError,TypeError) as e:raise MarketDataError("invalid "+field) from e
    if not math.isfinite(value) or value<=-100 or value>500:
        raise MarketDataError(field+" must be a percentage in (-100,500]")
    return value/100

def load_annual_csv(path):
    raw=Path(path).read_bytes()
    rows=list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    if not rows:raise MarketDataError("CSV is empty")
    output=[];years=set()
    for line in rows:
        try:year=int(line["year"])
        except (ValueError,TypeError,KeyError) as e:raise MarketDataError("invalid year") from e
        if year in years:raise MarketDataError("duplicate year")
        years.add(year)
        output.append({"year":year,
                      "equity":_rate(line.get("stocks_total_return_pct"),"stocks_total_return_pct"),
                      "bond":_rate(line.get("bonds_total_return_pct"),"bonds_total_return_pct")})
    output.sort(key=lambda x:x["year"])
    if len(output)<2:raise MarketDataError("need at least two distinct years")
    if any(b["year"]!=a["year"]+1 for a,b in zip(output,output[1:])):
        raise MarketDataError("historical sequence must contain contiguous years")
    return {"rows":output,"sha256":hashlib.sha256(raw).hexdigest(),
            "source_metadata":{"source":SOURCE,"precision":"CSV percentages; source-specific rounding matters",
                               "first_year":output[0]["year"],"last_year":output[-1]["year"]}}

def portfolio_return(row,equity_weight,annual_fee=0):
    if not 0<=equity_weight<=1 or not 0<=annual_fee<1:
        raise MarketDataError("invalid allocation/fee")
    return equity_weight*row["equity"]+(1-equity_weight)*row["bond"]-annual_fee

def calibrate(snapshot):
    rows=snapshot["rows"]
    stocks=[x["equity"] for x in rows]
    bonds=[x["bond"] for x in rows]
    mstock=statistics.mean(stocks)
    mbond=statistics.mean(bonds)
    sstock=statistics.stdev(stocks)
    sbond=statistics.stdev(bonds)
    corr=(statistics.correlation(stocks,bonds) if sstock>0 and sbond>0 else None)
    return {"snapshot_sha256":snapshot["sha256"],
            "years":[rows[0]["year"],rows[-1]["year"]],"observations":len(rows),
            "equity_mean":mstock,"bond_mean":mbond,
            "equity_sample_stdev":sstock,"bond_sample_stdev":sbond,
            "equity_bond_sample_correlation":corr,
            "not_an_estimate_of":["future mean returns","tail risks outside sample","changing market regime","inflation"]}

def rolling_backtest(snapshot,*,years,initial_balance,annual_spending,equity_weight=.6,
                     annual_fee=.003,spending_inflation=.025):
    rows=snapshot["rows"]
    if not isinstance(years,int) or not 1<=years<=len(rows):
        raise MarketDataError("horizon must be within available observations")
    if not math.isfinite(initial_balance) or initial_balance<0 or annual_spending<0:
        raise MarketDataError("invalid balance or annual spending")
    if not 0<=spending_inflation<=.2:
        raise MarketDataError("invalid spending inflation")
    results=[]
    for start in range(len(rows)-years+1):
        balance=float(initial_balance)
        failed_year=None
        for step,row in enumerate(rows[start:start+years]):
            balance*=1+portfolio_return(row,equity_weight,annual_fee)
            expense=annual_spending*(1+spending_inflation)**(step+1)
            if balance+1e-9<expense and failed_year is None:
                failed_year=row["year"]
            balance=max(0.,balance-expense)
        results.append({"start_year":rows[start]["year"],
                        "end_year":rows[start+years-1]["year"],
                        "fully_funded":failed_year is None,
                        "first_unmet_year":failed_year,"terminal_balance":round(balance,2)})
    return {"method":"historical_contiguous_rolling_windows",
            "snapshot_sha256":snapshot["sha256"],
            "horizon_years":years,"window_count":len(results),
            "fully_funded_windows":sum(x["fully_funded"] for x in results),
            "windows":results,
            "warnings":["historical window share is NOT a future success probability",
                        "annual return/expenditure timing; fees deducted from blended return",
                        "no cash drag, real tax engine, portfolio rebalancing drift or inflation data",
                        "data selection and window overlap distort frequency interpretation"]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv",type=Path)
    ap.add_argument("--horizon",type=int,default=10)
    ap.add_argument("--assets",type=float,default=1000000.)
    ap.add_argument("--spending",type=float,default=50000.)
    ap.add_argument("--equity-weight",type=float,default=.6)
    ap.add_argument("--fee",type=float,default=.003)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    snapshot=load_annual_csv(a.csv)
    out={"calibration":calibrate(snapshot),
         "backtest":rolling_backtest(snapshot,years=a.horizon,initial_balance=a.assets,
                    annual_spending=a.spending,equity_weight=a.equity_weight,annual_fee=a.fee)}
    data=json.dumps(out,indent=2,allow_nan=False)
    if a.output:a.output.write_text(data+"\n")
    else:print(data)

if __name__=="__main__":
    main()
