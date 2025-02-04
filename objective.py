from benchopt import BaseObjective, safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np
    from numpy.linalg import norm

    select_lambdas = import_ctx.import_from("utils", "select_lambdas")


class Objective(BaseObjective):
    name = "Lasso Path"

    install_cmd = "conda"
    requirements = ["r-base", "rpy2", "r-glmnet", "r-matrix"]

    parameters = {
        "fit_intercept": [True, False],
        "n_lambda": [100],
    }

    def __init__(self, fit_intercept=False, n_lambda=100):
        self.fit_intercept = fit_intercept
        self.n_lambda = n_lambda

    def _get_lambda_max(self):
        if self.fit_intercept:
            return abs(self.X.T @ (self.y - self.y.mean())).max()
        else:
            return abs(self.X.T.dot(self.y)).max()

    def set_data(self, X, y):
        self.X, self.y = X, y
        self.n_samples, self.n_features = X.shape
        self.lambdas = select_lambdas(X, y, self.fit_intercept)

    def get_one_solution(self):
        return np.zeros([self.n_features, len(self.lambdas)])

    def compute(self, coefs):
        if self.fit_intercept:
            betas = coefs[: self.n_features, :]
            intercepts = coefs[-1, :]
        else:
            betas = coefs
            intercepts = np.zeros(self.n_features)

        path_length = len(self.lambdas)

        primals = np.empty(path_length, dtype=np.float64)
        duals = np.empty(path_length, dtype=np.float64)

        for i in range(path_length):
            beta = betas[:, i]

            residual = self.y - self.X @ beta - intercepts[i]

            dual_scale = max(1, norm(self.X.T @ residual, ord=np.inf) / self.lambdas[i])

            primals[i] = 0.5 * norm(residual) ** 2 + self.lambdas[i] * norm(beta, 1)
            duals[i] = (
                0.5 * norm(self.y) ** 2
                - 0.5 * norm(self.y - residual / dual_scale) ** 2
            )

        gaps = primals - duals

        max_rel_duality_gap = np.max(gaps / primals)
        max_abs_duality_gap = np.max(gaps)
        mean_rel_duality_gaps = np.mean(gaps / primals)
        mean_abs_duality_gaps = np.mean(gaps)

        return dict(
            value=np.sum(primals),
            max_rel_duality_gap=max_rel_duality_gap,
            max_abs_duality_gap=max_abs_duality_gap,
            mean_rel_duality_gaps=mean_rel_duality_gaps,
            mean_abs_duality_gaps=mean_abs_duality_gaps,
        )

    def to_dict(self):
        return dict(
            X=self.X,
            y=self.y,
            lambdas=self.lambdas,
            fit_intercept=self.fit_intercept,
        )
