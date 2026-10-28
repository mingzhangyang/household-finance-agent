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
import random
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
    if not math.isfinite(initial_balance) or not math.isfinite(annual_spending) or initial_balance<0 or annual_spending<0:
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

# Decimal-return CSV / bootstrap API retained from main.
REQUIRED = {'year','equity_total_return','bond_total_return'}


def load_history(path, *, source_url, verified_by_user=False):
    if not source_url or not isinstance(source_url,str):
        raise MarketDataError('source URL is required')
    raw = Path(path).read_bytes()
    rows = list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
    if not rows or not REQUIRED.issubset(rows[0]):
        raise MarketDataError('requires year, equity_total_return, bond_total_return')
    if len(rows) < 5:
        raise MarketDataError('at least five years required to characterize a return series')
    data=[]
    for r in rows:
        try:
            year = int(r['year'])
            eq = float(r['equity_total_return'])
            bond = float(r['bond_total_return'])
        except (ValueError,TypeError) as e:
            raise MarketDataError('malformed numeric input') from e
        if not (1870 <= year <= 2100 and all(math.isfinite(v) and -1 <= v <= 5 for v in (eq,bond))):
            raise MarketDataError('year/return out of range or not finite')
        data.append({'year':year,'equity':eq,'bond':bond})
    years=[r['year'] for r in data]
    if years!=list(range(min(years),max(years)+1)):
        raise MarketDataError('missing, duplicated or unordered years')
    return {'rows':data,'source_url':source_url,'source_sha256':hashlib.sha256(raw).hexdigest(),
            'external_source_verified':bool(verified_by_user)}


def metrics(series):
    rows=series['rows'];eq=[r['equity'] for r in rows];bond=[r['bond'] for r in rows]
    corr=statistics.correlation(eq,bond) if statistics.stdev(eq)>0 and statistics.stdev(bond)>0 else None
    return {'start_year':rows[0]['year'],'end_year':rows[-1]['year'],'observations':len(rows),
            'equity_arithmetic_mean':statistics.mean(eq),'bond_arithmetic_mean':statistics.mean(bond),
            'equity_sample_sd':statistics.stdev(eq),'bond_sample_sd':statistics.stdev(bond),
            'equity_bond_sample_correlation':corr,'provenance':series['source_url'],
            'external_source_verified':series['external_source_verified']}


def historical_windows(series, horizon, equity_weight, fee=0.):
    """Consecutive actual-year windows; no wraparound; preserve paired returns."""
    if not isinstance(horizon,int) or horizon<1 or horizon>len(series['rows']):
        raise MarketDataError('invalid window horizon')
    if not 0<=equity_weight<=1 or not 0<=fee<1:raise MarketDataError('bad weights or fees')
    rows=series['rows'];out=[]
    for start in range(len(rows)-horizon+1):
        subset=rows[start:start+horizon]
        rate=[equity_weight*r['equity']+(1-equity_weight)*r['bond']-fee for r in subset]
        out.append({'start_year':subset[0]['year'],'end_year':subset[-1]['year'],'returns':rate,
                    'growth_of_one':math.prod(1+x for x in rate)})
    return out


def paired_block_bootstrap(series, *, horizon, draws, block_years, equity_weight, seed, fee=0.):
    """Resample paired equity/bond years in contiguous circular blocks.

    Captures historical within-block correlation, but cannot establish
    future distribution validity or the probability of financial success.
    """
    if not all(isinstance(n,int) for n in (horizon,draws,block_years,seed)):
        raise MarketDataError('integer horizon/draws/block_years/seed required')
    if not 1<=horizon<=110 or not 1<=draws<=10000 or not 1<=block_years<=len(series['rows']):
        raise MarketDataError('invalid bootstrap settings')
    if not 0<=equity_weight<=1 or not 0<=fee<1: raise MarketDataError('bad weights or fees')
    rng=random.Random(seed);rs=series['rows'];outputs=[]
    for _ in range(draws):
        picks=[]
        while len(picks)<horizon:
            start=rng.randrange(len(rs))
            picks += [(start+j)%len(rs) for j in range(block_years)]
        picks=picks[:horizon]
        outputs.append({'sampled_years':[rs[i]['year'] for i in picks],
            'returns':[equity_weight*rs[i]['equity']+(1-equity_weight)*rs[i]['bond']-fee for i in picks]})
    return {'series_sha256':series['source_sha256'],'seed':seed,'draws':outputs,
            'method':'circular paired moving-block bootstrap','calibrated_future_probability':False}


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
