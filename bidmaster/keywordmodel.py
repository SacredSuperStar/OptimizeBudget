#!/usr/bin/python3
import sys
import datetime
import random

import numpy as np
import scipy.interpolate as spi
import scipy.stats
from scipy.stats import beta
import statsmodels.api as sm
from scipy.interpolate import interp1d

import bidmaster
from .estimator import Estimator
from . import constants


class UncertaintyEstimator:
    def __init__(self):
        self.interpolator = None
        self.density_interpolator = None

    def fit(self, X, residuals):
        X = X.ravel() + np.random.normal(0, 1e-8, size=len(X))  # perturbation
        sorted_indices = np.argsort(X)
        X = X[sorted_indices]
        residuals = residuals[sorted_indices]
        loess_model = sm.nonparametric.lowess
        loess_results = loess_model(np.abs(residuals), X, frac=1 / 3, it=3)
        self.interpolator = spi.interp1d(
            loess_results[:, 0],
            loess_results[:, 1],
            kind='linear',
            bounds_error=False,
            fill_value=(0, loess_results[:, 1][-1])
        )
        X = np.append(X, [0, 0, 0, 0, 0])
        kde = scipy.stats.gaussian_kde(X, bw_method=0.3)
        self.density_interpolator = lambda X: kde(np.array(X).ravel()).reshape(-1, 1)

    def predict(self, X):
        std_devs = np.abs(self.interpolator(X))
        density = self.density_interpolator(X)
        std_dev_weight = np.maximum(np.minimum(density, 1.0), 0)
        adjusted_std_devs = (std_devs * std_dev_weight) + (max(std_devs) * (1 - std_dev_weight))
        return adjusted_std_devs.ravel()


def generate_date_bid_dict(data):
    first_date_str = data[0]['datetime'][:10]
    last_date_str = data[-1]['datetime'][:10]
    first_date = datetime.datetime.strptime(first_date_str, '%Y-%m-%d').date()
    last_date = datetime.datetime.strptime(last_date_str, '%Y-%m-%d').date()
    date_bid_dict = {}
    current_bid = data[0]['bid']
    data_index = 1
    for n in range((last_date - first_date).days + 1):
        current_date = first_date + datetime.timedelta(days=n)
        current_date_str = current_date.strftime('%Y-%m-%d')
        if data_index < len(data) and data[data_index]['datetime'][:10] == current_date_str:
            current_bid = data[data_index]['bid']
            data_index += 1
        date_bid_dict[current_date_str] = current_bid
    return date_bid_dict


def kid_data(kid):
    keyword_row = bidmaster.get_keyword_row(kid)
    bid_log = bidmaster.keyword_log_search(keyword_row['id'], constants.LOOKBACK)
    if not bid_log:
        return []
    dbd = generate_date_bid_dict(bid_log)
    rows = bidmaster.adreport_search(kid, constants.LOOKBACK)
    for row in rows:
        row['bid'] = dbd.get(row['date'])
    return [{
        'date': row['date'],
        'bid': dbd[row['date']],
        'impressions': max(row['impressions'], 0.1),
        'clicks': row['clicks'],
        'sold': row['sold'],
    } for row in rows if row['date'] in dbd]


def date_weight(date_str):
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    days_ago = (datetime.date.today() - date).days
    return (1 / 2) ** (days_ago / constants.HALF_LIFE)


def plot_fitted_curve(X, y, model, uncertainty_model):
    import matplotlib.pyplot as plt
    X_range = np.linspace(min(X), max(X) * 1.1, num=100).reshape(-1, 1)
    predicted_y = model.predict(X_range)
    uncertainty = uncertainty_model.predict(X_range)

    plt.scatter(X, y, label='Actual data', color='blue', alpha=0.5)
    plt.plot(X_range, predicted_y, label='GAM Fitted curve', color='red', linewidth=2)
    plt.fill_between(X_range.flatten(), (predicted_y - uncertainty), (predicted_y + uncertainty),
                     color='gray', alpha=0.3, label='Uncertainty')

    plt.xlabel('Bid values')
    plt.ylabel('Impressions')
    plt.title('Fitted curve using GAM with uncertainty')
    plt.legend()
    plt.show()


def predict_impressions(kid, num_higher_bids=10, plot=False):
    data = kid_data(kid)  # {bid, impressions, clicks, sold, date}
    if not data:
        return [(i / 100, 1, 1) for i in range(2, 21)]
    points = [(row['bid'], row['impressions']) for row in data]
    sample_weights = [date_weight(row['date']) for row in data]

    # Fit the GAM model
    bids = [x for x, y in points]
    scores = [y for x, y in points]
    bids.append(0)
    scores.append(0)
    sample_weights.append(1)
    X = np.array(bids).reshape(-1, 1)
    y = np.array(scores)
    impression_estimator = Estimator()
    impression_estimator.fit(X, y, weights=sample_weights)

    min_bid = 0.02
    max_bid = max(row['bid'] for row in data)

    X_range = [i / 100 for i in range(int(min_bid * 100), int(max_bid * 100) + num_higher_bids)]
    _bids = [(bid,) for bid in X_range]
    predictions = impression_estimator.predict(_bids)

    gam_residuals = y - impression_estimator.predict(X, monotonic_inc=False)
    uncertainty_estimator = UncertaintyEstimator()
    uncertainty_estimator.fit(X, gam_residuals)
    uncertainty = uncertainty_estimator.predict(_bids)

    if plot:
        plot_fitted_curve(bids, scores, impression_estimator, uncertainty_estimator)
    return list(zip(X_range, predictions, uncertainty))


def expected_ctr_cr(kid, lookback=365, half_life=90):
    ctr_prior_mean, ctr_prior_alpha = bidmaster.DEFAULT_CTR, constants.PRIOR_CTR_WEIGHT
    cr_prior_mean, cr_prior_alpha = bidmaster.DEFAULT_CR, constants.PRIOR_CR_WEIGHT
    ctr_prior_beta = ctr_prior_alpha * (1 - ctr_prior_mean) / ctr_prior_mean
    cr_prior_beta = cr_prior_alpha * (1 - cr_prior_mean) / cr_prior_mean

    total_impressions = 0
    total_clicks = 0
    total_sales = 0
    total_weight = 0
    for row in bidmaster.adreport_search(kid, lookback):
        date = datetime.datetime.strptime(row['date'], '%Y-%m-%d').date()
        days_ago = (datetime.date.today() - date).days
        weight = (1 / 2) ** (days_ago / half_life)
        total_impressions += row['impressions'] * weight
        total_clicks += row['clicks'] * weight
        total_sales += row['sold'] * weight
        total_weight += weight

    ctr_alpha = total_clicks + ctr_prior_alpha
    ctr_beta = total_impressions - total_clicks + ctr_prior_beta
    cr_alpha = total_sales + cr_prior_alpha
    cr_beta = total_clicks - total_sales + cr_prior_beta

    ctr_model = beta(ctr_alpha, ctr_beta)
    cr_model = beta(cr_alpha, cr_beta)
    expected_ctr = ctr_model.mean()
    expected_cr = cr_model.mean()
    return expected_ctr, expected_cr
