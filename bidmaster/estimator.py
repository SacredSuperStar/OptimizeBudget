import pygam
import numpy as np

#common library for both eBay and Amazon
#LinearGAM with modifications
#  monotinic increase
#  non-negative

class Estimator:
    def __init__(self, n_splines=8, spline_order=3, lam=0.2):
        self.n_splines = n_splines
        self.spline_order = spline_order
        self.lam = lam
        self.gam = None

    def fit(self,X,y,weights=None):
        X = X.ravel()
        self.center = round((X.min()+X.max())/2)
        lam = self.lam * min(max(len(np.unique(X)) - 2, 0) / 8,1)
        self.gam = pygam.LinearGAM(pygam.s(0, n_splines=self.n_splines, spline_order=self.spline_order), lam=lam)
        self.gam.fit(X,y,weights=weights)

    def predict(self, X, monotonic_inc=True):
        predictions = self.gam.predict(X)
        if monotonic_inc:
            for i in range(self.center - 1, -1, -1):
                if predictions[i] > predictions[i + 1]:
                    predictions[i] = predictions[i + 1]
            for i in range(self.center + 1, len(predictions)):
                if predictions[i] < predictions[i - 1]:
                    predictions[i] = predictions[i - 1]
        return [ max(0,p) for p in predictions ]

    def predict_scaled(self, X, monotonic_inc=True):
        predictions = self.predict(X, monotonic_inc)
        max_prediction = max(predictions) or 1
        return [ p / max_prediction for p in predictions ]
