from .main import optimal_keyword_bids_budget, optimal_keyword_bids

# These variables and functions must be overriden (dependency injection)
DEFAULT_CTR = None
DEFAULT_CR = None

def get_keyword_row(kid):
    raise NotImplementedError

def keyword_log_search(keyword_id, days):
    raise NotImplementedError

def adreport_search(kid, days):
    raise NotImplementedError

