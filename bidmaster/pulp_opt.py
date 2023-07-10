import pulp as plp
from pulp import PULP_CBC_CMD
import numpy as np


# def select_bids(kids, budget, kid_bid_impressions, kid_ctr_cr):
#     bids = set()
#     for bid_impressions in kid_bid_impressions.values():
#         for bid in bid_impressions.keys():
#             bids.add(bid)
#     bids = list(bids)
#     total_points = len(bids) + len(kids) + 2
#     cost_sales = []
#     cost_spend = []
#     kid_bid_matches = []
#     kid_bids = []
#     for i in range(len(kids)):
#         temp = []
#         bid_temp = []
#         for j in range(len(bids)):
#             kid, bid = kids[i], bids[j]
#             try:
#                 clicks = kid_bid_impressions[kid][bid] * kid_ctr_cr[kid][0]
#                 cost_sales.append(clicks * kid_ctr_cr[kid][1])
#                 cost_spend.append(clicks * float(bid))
#                 temp.append(len(cost_sales) - 1)
#                 bid_temp.append(j)
#             except KeyError:
#                 continue
#         kid_bid_matches.append(temp)
#         kid_bids.append(bid_temp)
#     cost_sales, cost_spend = np.array(cost_sales), np.array(cost_spend)
#     problem = plp.LpProblem("Maximize", plp.LpMaximize)
#     x_vars = {i: plp.LpVariable(cat=plp.LpBinary, name="x_{0}".format(i)) for i in range(len(cost_sales))}
#     problem += plp.lpSum(x_vars[i] * cost_spend[i] for i in range(len(cost_sales))) <= budget
#     for bid_requires in kid_bid_matches:
#         problem += plp.lpSum(x_vars[i] for i in bid_requires) == 1
#     problem += plp.lpSum(x_vars[i] * cost_sales[i] for i in range(len(cost_sales)))
#     status = problem.solve(PULP_CBC_CMD(msg=False))
#     if status == -1:
#         return None
#     x = np.zeros(len(cost_sales))
#     for i in range(len(cost_sales)):
#         x[i] = plp.value(x_vars[i])
#     bid_selections = dict()
#     for i in range(len(kids)):
#         kid = kids[i]
#         bid_requires = kid_bid_matches[i]
#         for j, param_index in enumerate(bid_requires):
#             if x[param_index] == 1:
#                 bid_selections[kid] = bids[kid_bids[i][j]]
#     return {
#         'bid_selections': bid_selections,
#         'spend': (cost_spend.reshape(1, -1) @ x)[0],
#         'sales': (cost_sales.reshape(1, -1) @ x)[0],
#     }


def select_bids(kids, profit, kid_bid_impressions, kid_ctr_cr, max_budget=None, min_sales=None, min_profit=None, maximize='profit'):
    bids = set()
    for bid_impressions in kid_bid_impressions.values():
        for bid in bid_impressions.keys():
            bids.add(bid)
    bids = list(bids)
    cost_sales = []
    cost_spend = []
    kid_bid_matches = []
    kid_bids = []
    for i in range(len(kids)):
        temp = []
        bid_temp = []
        for j in range(len(bids)):
            kid, bid = kids[i], bids[j]
            try:
                clicks = kid_bid_impressions[kid][bid] * kid_ctr_cr[kid][0]
                cost_sales.append(clicks * kid_ctr_cr[kid][1])
                cost_spend.append(clicks * float(bid))
                temp.append(len(cost_sales) - 1)
                bid_temp.append(j)
            except KeyError:
                continue
        kid_bid_matches.append(temp)
        kid_bids.append(bid_temp)
    cost_sales, cost_spend = np.array(cost_sales), np.array(cost_spend)
    problem = plp.LpProblem("Maximize", plp.LpMaximize)
    x_vars = {i: plp.LpVariable(cat=plp.LpBinary, name="x_{0}".format(i)) for i in range(len(cost_sales))}
    if max_budget:
        problem += plp.lpSum(x_vars[i] * cost_spend[i] for i in range(len(cost_sales))) <= max_budget
    if min_sales:
        problem += plp.lpSum(x_vars[i] * cost_sales[i] for i in range(len(cost_sales))) >= min_sales
    if min_profit:
        problem += plp.lpSum(x_vars[i] * (profit * cost_sales[i] - cost_spend[i]) for i in range(len(cost_sales))) >= min_profit

    for bid_requires in kid_bid_matches:
        problem += plp.lpSum(x_vars[i] for i in bid_requires) == 1
    if maximize == 'profit':
        problem += plp.lpSum(x_vars[i] * (profit * cost_sales[i] - cost_spend[i]) for i in range(len(cost_sales)))
    elif maximize == 'sales':
        problem += plp.lpSum(x_vars[i] * cost_sales[i] for i in range(len(cost_sales)))
    else:
        raise NotImplementedError()
    status = problem.solve(PULP_CBC_CMD(msg=False))
    if status == -1:
        raise "UnSolvable"
    x = np.zeros(len(cost_sales))
    for i in range(len(cost_sales)):
        x[i] = plp.value(x_vars[i])
    bid_selections = dict()
    for i in range(len(kids)):
        kid = kids[i]
        bid_requires = kid_bid_matches[i]
        for j, param_index in enumerate(bid_requires):
            if x[param_index] == 1:
                bid_selections[kid] = bids[kid_bids[i][j]]
    return {
        'bid_selections': bid_selections,
        'spend': (cost_spend.reshape(1, -1) @ x)[0],
        'sales': (cost_sales.reshape(1, -1) @ x)[0],
        'profit': ((profit * cost_sales.reshape(1, -1) - cost_spend.reshape(1, -1)) @ x)[0]
    }
