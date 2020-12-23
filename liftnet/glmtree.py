import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, LassoCV, LogisticRegression, LogisticRegressionCV
from sklearn.base import RegressorMixin, ClassifierMixin

from .mobtree import MoBTreeRegressor, MoBTreeClassifier

from warnings import simplefilter
from sklearn.exceptions import ConvergenceWarning
simplefilter("ignore", category=ConvergenceWarning)


__all__ = ["GLMTreeRegressor", "GLMTreeClassifier"]


class GLMTreeRegressor(MoBTreeRegressor, RegressorMixin):

    def __init__(self, max_depth=2, min_samples_leaf=10, min_impurity_decrease=0, feature_names=None,
                 split_features=None, n_screen_grid=5, n_feature_search=5, n_split_grid=20, reg_lambda=0, clip_predict=True, random_state=0):

        super(GLMTreeRegressor, self).__init__(max_depth=max_depth,
                                 min_samples_leaf=min_samples_leaf,
                                 min_impurity_decrease=min_impurity_decrease,
                                 feature_names=feature_names,
                                 split_features=split_features,
                                 n_screen_grid=n_screen_grid,
                                 n_feature_search=n_feature_search,
                                 n_split_grid=n_split_grid,
                                 random_state=random_state)
        self.reg_lambda = reg_lambda
        self.clip_predict = clip_predict
        self.base_estimator = LinearRegression()

    def build_root(self):

        self.base_estimator.fit(self.x, self.y)
        root_impurity = self.evaluate_estimator(self.base_estimator, self.x, self.y.ravel())
        return root_impurity

    def build_leaf(self, sample_indice):

        best_estimator = LassoCV(alphas=self.reg_lambda, cv=5, normalize=True, random_state=self.random_state)
        best_estimator.fit(self.x[sample_indice], self.y[sample_indice])
        xmin, xmax = self.x[sample_indice].min(0), self.x[sample_indice].max(0)
        if self.clip_predict:
            predict_func = lambda x: best_estimator.predict(np.clip(x, xmin, xmax))
        else:
            predict_func = lambda x: best_estimator.predict(x)
        best_impurity = self.get_loss(self.y[sample_indice], best_estimator.predict(self.x[sample_indice]))
        return predict_func, best_estimator, best_impurity


class GLMTreeClassifier(MoBTreeClassifier, ClassifierMixin):

    def __init__(self, max_depth=2, min_samples_leaf=10, min_impurity_decrease=0, feature_names=None,
                 split_features=None, n_screen_grid=5, n_feature_search=5, n_split_grid=20, reg_lambda=0, clip_predict=True, random_state=0):

        super(GLMTreeClassifier, self).__init__(max_depth=max_depth,
                                 min_samples_leaf=min_samples_leaf,
                                 min_impurity_decrease=min_impurity_decrease,
                                 feature_names=feature_names,
                                 split_features=split_features,
                                 n_screen_grid=n_screen_grid,
                                 n_feature_search=n_feature_search,
                                 n_split_grid=n_split_grid,
                                 random_state=random_state)
        self.reg_lambda = reg_lambda
        self.clip_predict = clip_predict
        self.base_estimator = LogisticRegression(penalty='none', random_state=self.random_state)

    def build_root(self):

        self.base_estimator.fit(self.x, self.y)
        root_impurity = self.evaluate_estimator(self.base_estimator, self.x, self.y.ravel())
        return root_impurity

    def build_leaf(self, sample_indice):

        if (self.y[sample_indice].std() == 0) | (self.y[sample_indice].sum() < 5) | ((1 - self.y[sample_indice]).sum() < 5):
            best_estimator = None
            p = self.y[sample_indice].mean()
            predict_func = lambda x: p
            best_impurity = - p * np.log2(p) - (1 - p) * np.log2((1 - p)) if (p > 0) and (p < 1) else 0
        else:
            best_estimator = LogisticRegressionCV(Cs=self.reg_lambda, penalty="l1", solver="liblinear",
                                      cv=5, max_iter=1000, random_state=self.random_state)
            mx = self.x[sample_indice].mean(0)
            sx = self.x[sample_indice].std(0) + self.EPSILON
            nx = (self.x[sample_indice] - mx) / sx
            xmin, xmax = nx.min(0), nx.max(0)
            best_estimator.fit(nx, self.y[sample_indice])
            if self.clip_predict:
                predict_func = lambda x: best_estimator.predict_proba(np.clip((x - mx) / sx, xmin, xmax))[:, 1]
            else:
                predict_func = lambda x: best_estimator.predict_proba((x - mx) / sx)[:, 1]
            best_impurity = self.get_loss(self.y[sample_indice], best_estimator.predict_proba(nx)[:, 1])
        return predict_func, best_estimator, best_impurity
