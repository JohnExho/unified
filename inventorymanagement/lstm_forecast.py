"""
Pure-Python Minimal LSTM for Inventory Transaction Time-Series Forecasting.
No external dependencies (no NumPy, no scikit-learn, no TensorFlow).

Architecture
------------
  Input  → LSTM (hidden units) → Linear → scalar output
Trained with truncated BPTT + gradient clipping + SGD.
"""
import math
import random


# ---------------------------------------------------------------------------
# Activation helpers
# ---------------------------------------------------------------------------

def _sig(x):
    x = max(-500.0, min(500.0, float(x)))
    return 1.0 / (1.0 + math.exp(-x))


def _tanh(x):
    return math.tanh(max(-500.0, min(500.0, float(x))))


# ---------------------------------------------------------------------------
# LSTM Forecaster
# ---------------------------------------------------------------------------

class LSTMForecast:
    """
    Single-layer LSTM with scalar input and scalar output.

    Parameters
    ----------
    hidden      : LSTM hidden units (default 8; keep small for speed)
    look_back   : sliding-window length used during training
    forecast    : number of future time-steps to predict
    lr          : SGD learning rate
    epochs      : training passes over the windowed dataset
    seed        : RNG seed for weight initialisation
    """

    def __init__(self, hidden=8, look_back=5, forecast=7,
                 lr=0.02, epochs=50, seed=42):
        self.H   = hidden
        self.L   = look_back
        self.F   = forecast
        self.lr  = lr
        self.ep  = epochs
        self._mu      = 0.0
        self._std     = 1.0
        self._fitted  = False
        self._last_loss = None
        random.seed(seed)
        self._init_params()

    # ------------------------------------------------------------------
    def _init_params(self):
        H = self.H
        C = 1 + H  # concat dim: input(1) + hidden(H)

        def _w(rows, cols):
            lim = math.sqrt(6.0 / (rows + cols))
            return [random.uniform(-lim, lim) for _ in range(rows * cols)]

        # Gates: Wf/Wi/Wc/Wo each shaped [H × C]; biases [H]
        # Forget-gate bias initialised to 1.0 (helps gradient flow early on)
        self.Wf = _w(H, C);  self.bf = [1.0] * H
        self.Wi = _w(H, C);  self.bi = [0.0] * H
        self.Wc = _w(H, C);  self.bc = [0.0] * H
        self.Wo = _w(H, C);  self.bo = [0.0] * H
        # Output projection: Wy [1 × H], by [1]
        self.Wy = _w(1, H);  self.by = [0.0]

    # ------------------------------------------------------------------
    def _step(self, x, h, c):
        """Single LSTM cell forward pass.
        Returns (h_new, c_new, y_hat, cache).
        cache stores everything needed for backward pass.
        """
        H = self.H
        C = 1 + H
        xh = [x] + h  # concatenated input: length C

        zf = [sum(self.Wf[i*C+j]*xh[j] for j in range(C)) + self.bf[i] for i in range(H)]
        zi = [sum(self.Wi[i*C+j]*xh[j] for j in range(C)) + self.bi[i] for i in range(H)]
        zg = [sum(self.Wc[i*C+j]*xh[j] for j in range(C)) + self.bc[i] for i in range(H)]
        zo = [sum(self.Wo[i*C+j]*xh[j] for j in range(C)) + self.bo[i] for i in range(H)]

        f  = [_sig(v)  for v in zf]
        ig = [_sig(v)  for v in zi]
        g  = [_tanh(v) for v in zg]
        o  = [_sig(v)  for v in zo]

        c_new = [f[k]*c[k] + ig[k]*g[k]   for k in range(H)]
        h_new = [o[k]*_tanh(c_new[k])      for k in range(H)]
        y_hat = sum(self.Wy[k]*h_new[k]    for k in range(H)) + self.by[0]

        return h_new, c_new, y_hat, (h, c, f, ig, g, o, xh, c_new, h_new)

    # ------------------------------------------------------------------
    def _forward(self, xs, h0=None, c0=None):
        """Sequential forward pass over a list of scalar inputs xs."""
        h = h0[:] if h0 else [0.0] * self.H
        c = c0[:] if c0 else [0.0] * self.H
        outs, caches = [], []
        for x in xs:
            h, c, y, cache = self._step(x, h, c)
            outs.append(y)
            caches.append(cache)
        return outs, caches, h, c

    # ------------------------------------------------------------------
    def _backward(self, caches, outs, targets):
        """BPTT over the sequence stored in caches.
        Returns gradient tuple + mean MSE loss.
        """
        H = self.H
        C = 1 + H

        dWf = [0.0]*(H*C); dbf = [0.0]*H
        dWi = [0.0]*(H*C); dbi = [0.0]*H
        dWc = [0.0]*(H*C); dbc = [0.0]*H
        dWo = [0.0]*(H*C); dbo = [0.0]*H
        dWy = [0.0]*H;      dby = [0.0]

        dh_next = [0.0]*H
        dc_next = [0.0]*H
        loss    = 0.0

        for t in reversed(range(len(caches))):
            h_prev, c_prev, f, ig, g, o, xh, c_new, h_new = caches[t]

            # Output-layer gradient (MSE)
            dy = outs[t] - targets[t]
            loss += dy * dy
            for k in range(H):
                dWy[k] += dy * h_new[k]
            dby[0] += dy

            # Gradient into h_new
            dh = [self.Wy[k]*dy + dh_next[k] for k in range(H)]

            # Output gate + cell state
            tc  = [_tanh(c_new[k])                         for k in range(H)]
            do  = [dh[k]*tc[k]                             for k in range(H)]
            dc  = [dh[k]*o[k]*(1-tc[k]**2) + dc_next[k]  for k in range(H)]

            # Gate gradients
            df   = [dc[k]*c_prev[k] for k in range(H)]
            di   = [dc[k]*g[k]      for k in range(H)]
            dg   = [dc[k]*ig[k]     for k in range(H)]
            dc_p = [dc[k]*f[k]      for k in range(H)]

            # Through activation derivatives
            do_r = [do[k]*o[k]*(1-o[k])   for k in range(H)]
            df_r = [df[k]*f[k]*(1-f[k])   for k in range(H)]
            di_r = [di[k]*ig[k]*(1-ig[k]) for k in range(H)]
            dg_r = [dg[k]*(1-g[k]**2)     for k in range(H)]

            # Accumulate weight gradients
            for k in range(H):
                b = k * C
                for j in range(C):
                    dWf[b+j] += df_r[k]*xh[j]
                    dWi[b+j] += di_r[k]*xh[j]
                    dWc[b+j] += dg_r[k]*xh[j]
                    dWo[b+j] += do_r[k]*xh[j]
                dbf[k] += df_r[k]
                dbi[k] += di_r[k]
                dbc[k] += dg_r[k]
                dbo[k] += do_r[k]

            # Propagate gradient to previous h
            dxh = [0.0]*C
            for j in range(C):
                for k in range(H):
                    bk = k*C+j
                    dxh[j] += (self.Wf[bk]*df_r[k] + self.Wi[bk]*di_r[k]
                                + self.Wc[bk]*dg_r[k] + self.Wo[bk]*do_r[k])
            dh_next = dxh[1:]  # skip input dimension
            dc_next = dc_p

        return (dWf,dbf,dWi,dbi,dWc,dbc,dWo,dbo,dWy,dby), loss / len(caches)

    # ------------------------------------------------------------------
    def _update(self, grads, clip=5.0):
        """Apply clipped SGD update to all parameters."""
        dWf,dbf,dWi,dbi,dWc,dbc,dWo,dbo,dWy,dby = grads
        lr = self.lr

        def _upd(W, dW):
            for k in range(len(W)):
                W[k] -= lr * max(-clip, min(clip, dW[k]))

        _upd(self.Wf, dWf); _upd(self.bf, dbf)
        _upd(self.Wi, dWi); _upd(self.bi, dbi)
        _upd(self.Wc, dWc); _upd(self.bc, dbc)
        _upd(self.Wo, dWo); _upd(self.bo, dbo)
        _upd(self.Wy, dWy); _upd(self.by, dby)

    # ------------------------------------------------------------------
    def fit(self, series):
        """Train on a list of daily counts (ints or floats).
        Requires len(series) > look_back + 1.
        """
        mu  = sum(series) / len(series)
        var = sum((v - mu)**2 for v in series) / max(len(series) - 1, 1)
        std = math.sqrt(var) if var > 1e-8 else 1.0
        self._mu, self._std = mu, std

        ns = [(v - mu) / std for v in series]
        L  = self.L

        # Sliding windows: input xs (length L) → one-step-ahead targets ys
        X = [ns[i:i+L]     for i in range(len(ns) - L)]
        Y = [ns[i+1:i+L+1] for i in range(len(ns) - L)]

        for _ in range(self.ep):
            ep_loss = 0.0
            for xs, ys in zip(X, Y):
                outs, caches, _, _ = self._forward(xs)
                grads, loss = self._backward(caches, outs, ys)
                self._update(grads)
                ep_loss += loss
            self._last_loss = round(ep_loss / max(len(X), 1), 6)

        self._fitted = True
        return self

    # ------------------------------------------------------------------
    def predict(self, seed_series):
        """Autoregressively generate F-step forecast.
        seed_series: raw (unnormalised) values; the last L points are used.
        Returns: list of F floats (unnormalised, clipped ≥ 0).
        """
        L         = self.L
        mu, std   = self._mu, self._std

        ns        = [(v - mu) / std for v in seed_series[-L:]]
        _, _, h, c = self._forward(ns)

        preds = []
        last  = ns[-1]
        for _ in range(self.F):
            outs, _, h, c = self._forward([last], h, c)
            y_norm = outs[0]
            preds.append(max(0.0, round(y_norm * std + mu, 2)))
            last = y_norm

        return preds
