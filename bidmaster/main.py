#!/usr/bin/python3
import os
import signal
import psutil
import random
from .keywordmodel import predict_impressions, expected_ctr_cr
from .pulp_opt import select_bids
from . import constants


def timeout_handler(signum, frame):
    raise TimeoutError()


signal.signal(signal.SIGBREAK, timeout_handler)


def bid_impressions(kid):
    bid_impressions = {}
    for bid, impressions, uncertainty in predict_impressions(kid):
        noise = random.gauss(0, uncertainty * constants.UNCERTAINTY_MULTIPLIER)
        # print(uncertainty * constants.UNCERTAINTY_MULTIPLIER)
        bid_impressions[bid] = max(0, impressions + noise)
        # bid_impressions[bid] = max(0, impressions)
    return bid_impressions


def optimal_keyword_bids_budget(kids, budget):
    kid_bid_impressions = {kid: bid_impressions(kid) for kid in kids}
    kid_ctr_cr = {kid: expected_ctr_cr(kid) for kid in kids}
    try:
        # signal.alarm(300)
        resp = select_bids(kids, budget, kid_bid_impressions, kid_ctr_cr, max_budget=budget, maximize='sales')
    except TimeoutError:
        for proc in psutil.Process(os.getpid()).children(recursive=True):
            if proc.name() == 'cbc':
                proc.terminate()
        raise
    finally:
        pass
        # signal.alarm(0)
    return resp['bid_selections'], resp['spend'], resp['sales']


def optimal_keyword_bids(kids, profit, **kwargs):
    kid_bid_impressions = {kid: bid_impressions(kid) for kid in kids}
    kid_ctr_cr = {kid: expected_ctr_cr(kid) for kid in kids}
    res = select_bids(kids, profit, kid_bid_impressions, kid_ctr_cr, **kwargs)
    return res['bid_selections'], res['spend'], res['sales'], res['spend']
