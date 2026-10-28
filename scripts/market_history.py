#!/usr/bin/env python3
"""Auditable annual stock/bond history and paired block-bootstrap, not a forecast."""
from __future__ import annotations
import csv
import hashlib
import math
import random
import statistics
from pathlib import Path

class MarketDataError(ValueError): pass

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
