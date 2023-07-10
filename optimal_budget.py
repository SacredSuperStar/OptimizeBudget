#!/usr/bin/python3
import sys
import numpy as np
from scipy import stats
import bidmaster
# import listingslib
import persist

DEBUG = False

PersistKV = persist.persistKV('data.sqlite3')
mock_data = {
    'data': PersistKV('data'),
    'get_keyword_row': PersistKV('get_keyword_row'),
    'keyword_log_search': PersistKV('keyword_log_search'),
    'adreport_search': PersistKV('adreport_search'),
    'amazon_keyword_search': PersistKV('amazon_keyword_search'),
    'amazon_adreport_search': PersistKV('amazon_adreport_search'),
    'cid_gross_profit': PersistKV('cid_gross_profit'),
}
impressions = mock_data['data']['impressions']
clicks = mock_data['data']['clicks']
sales = mock_data['data']['sales']

bidmaster.DEFAULT_CTR = clicks / impressions
bidmaster.DEFAULT_CR = sales / clicks
# bidmaster.get_keyword_row = lambda kid: listingslib.amazon_keyword_search(kid=kid)[0]
# bidmaster.keyword_log_search = lambda keyword_id, days: listingslib.amazon_keyword_log_search(amazon_keyword_id=keyword_id,days=days)
# bidmaster.adreport_search = lambda kid, days: listingslib.amazon_adreport_search(kid=kid,days=days)
bidmaster.get_keyword_row = lambda kid: mock_data['get_keyword_row'][kid]
bidmaster.keyword_log_search = lambda keyword_id, days: mock_data['keyword_log_search'][(keyword_id, days)]
bidmaster.adreport_search = lambda kid, days: mock_data['adreport_search'][(kid, days)]


def predict_sales(cid, budget):
    # rows = listingslib.amazon_keyword_search(cid=cid)
    rows = mock_data['amazon_keyword_search'][cid]
    # adreport = listingslib.amazon_adreport_search(cid=cid,days=7)
    adreport = mock_data['amazon_adreport_search'][cid]
    kids_to_optimize = []
    for row in rows:
        if sum([_row['impressions'] for _row in adreport if _row['kid'] == row['kid']]):
            kids_to_optimize.append(row['kid'])
    if kids_to_optimize:
        optimal_bids, spend, sales = bidmaster.optimal_keyword_bids_budget(kids_to_optimize, budget=budget)
        return spend, sales
    return 0, 0


def frange(start, end, increment):
    current = start
    while current < end:
        yield current
        current += increment


def calc_optimal_budget(cid, gross_profit, start=1, increment=0.5):
    # select the first budget where the cumulative incremental cost per sale exceeds the gross profit
    budget_data = []
    incremental_spend = []
    incremental_sales = []

    for budget in frange(start, start + increment * 100, increment):
        spend, sales = predict_sales(cid, budget)
        if budget_data:
            incremental_spend.append(spend - budget_data[-1]['spend'])
            incremental_sales.append(sales - budget_data[-1]['sales'])
            if len(incremental_spend) >= 3:
                z_scores = np.abs(stats.zscore(incremental_sales[-5:]))
                filtered_incremental_spend = [x for x, z in zip(incremental_spend[-5:], z_scores) if z <= 1]
                filtered_incremental_sales = [x for x, z in zip(incremental_sales[-5:], z_scores) if z <= 1]
                incremental_spend_per_sale = sum(filtered_incremental_spend) / sum(filtered_incremental_sales)
                if DEBUG:
                    print(f"budget: {budget}, spend: {round(spend, 2)}, sales: {round(sales, 2)}")
                    print(
                        f"incremental sales: {round(incremental_sales[-1], 2)}, spend: {round(incremental_spend[-1], 2)}, spend_per_sale: {round(incremental_spend_per_sale, 2)}")
                    print('-' * 20)
                if len(budget_data) >= 2 and incremental_spend_per_sale > gross_profit:
                    break
        budget_data.append({'budget': budget, 'spend': spend, 'sales': sales})

    selected_budget = budget_data[-2]['budget']
    return selected_budget, budget_data[-2]['spend'], budget_data[-2]['sales']

def calc_optimal_budget_high_profit(cid, gross_profit):
    rows = mock_data['amazon_keyword_search'][cid]
    # adreport = listingslib.amazon_adreport_search(cid=cid,days=7)
    adreport = mock_data['amazon_adreport_search'][cid]
    kids_to_optimize = []
    for row in rows:
        if sum([_row['impressions'] for _row in adreport if _row['kid'] == row['kid']]):
            kids_to_optimize.append(row['kid'])
    if kids_to_optimize:
        optimal_bids, spend, sales, optimal_budget = bidmaster.optimal_keyword_bids(
            kids_to_optimize,
            gross_profit,
            max_budget=None,
            min_sales=None,
            min_profit=None,
            maximize='profit'
        )
        return optimal_budget, spend, sales
    return None, None, None

if __name__ == '__main__':
    import time
    for cid in mock_data['data']['cids'][:]:
        s = time.time()
        try:
            gross_profit = mock_data['cid_gross_profit'][cid]
            # optimal_budget, spend, sales = calc_optimal_budget(cid, gross_profit, start=0.5)
            optimal_budget, spend, sales = calc_optimal_budget_high_profit(cid, gross_profit)
            if optimal_budget is None:
                continue
            print(f"CID: {cid}, profit: {gross_profit}, optimal budget: {optimal_budget}, Total Profit: {sales * gross_profit - spend}, spend: {spend}, sales: {sales}, Time: {time.time() - s}")
        except KeyError as e:
            print(f"RuntimeError: Key not Found {e.args[0]}")
