# hp_twist_grok.py
# Minimal Hilbert–Pólya test with twisted boundary and analytic parameter fit
# Requirements: numpy, mpmath
import math, argparse, json
import numpy as np
import mpmath as mp

# ---------- settings ----------
mp.mp.dps = 100
np.set_printoptions(precision=12, suppress=False, linewidth=140)

# ---------- Riemann zeros ----------
def riemann_zeros(K: int) -> np.ndarray:
    return np.array([float(mp.zetazero(i+1).imag) for i in range(K)], dtype=float)

# ---------- smooth count for unfolding ----------
def N_smooth(T: float) -> float:
    two_pi = 2.0*math.pi
    return (T/two_pi)*math.log(T/two_pi) - (T/two_pi) + 0.875

def wigner_gue_cdf(s: np.ndarray) -> np.ndarray:
    # Wigner surmise CDF for GUE spacings after unfolding
    a = 4.0/math.pi
    return 1.0 - np.exp(-a*s*s) * (1.0 + (2.0/math.pi)*s*np.sqrt(math.pi*a))

def ks_stat_against_wigner(spacings: np.ndarray) -> float:
    s = np.sort(spacings)
    ecdf = np.arange(1, len(s)+1, dtype=float)/len(s)
    cdf = wigner_gue_cdf(s)
    return float(np.max(np.abs(ecdf - cdf)))

def number_variance(u: np.ndarray, L: float, steps: int = 200) -> float:
    umin, umax = u[0], u[-1]
    if umax - umin <= L or len(u) < 6:
        return float('nan')
    starts = np.linspace(umin, umax - L, steps)
    vals = []
    for a in starts:
        b = a + L
        cnt = np.count_nonzero((u >= a) & (u < b))
        vals.append((cnt - L)**2)
    return float(np.mean(vals))

# ---------- twisted ring operator ----------
def build_twisted_matrix(L: float, M: int, theta: float, V0: float=0.0, k2: float=0.0):
    tau = np.linspace(0.0, L, M, endpoint=False)
    h = L / M
    main = np.full(M, 2.0/(h*h), dtype=complex)
    off  = np.full(M-1, -1.0/(h*h), dtype=complex)
    A = np.zeros((M, M), dtype=complex)
    np.fill_diagonal(A, main)
    np.fill_diagonal(A[1:], off)
    np.fill_diagonal(A[:,1:], off)
    # twisted corners
    phase = np.exp(1j*theta)
    A[0, -1]  = -np.conj(phase)/(h*h)
    A[-1, 0]  = -phase/(h*h)
    # weak potential (optional)
    if V0 != 0.0 or k2 != 0.0:
        V = V0 + k2*(tau - 0.5*L)**2
        A += np.diag(V.astype(complex))
    return A

def eigvals_hermitian(A: np.ndarray, keep: int) -> np.ndarray:
    vals = np.linalg.eigvalsh(A)
    vals = np.real(vals)
    vals = vals[vals > 0]
    return np.sort(vals)[:keep]

# ---------- fitting helpers ----------
def fit_affine(x: np.ndarray, y: np.ndarray):
    X = np.vstack([x, np.ones_like(x)]).T
    a,b = np.linalg.lstsq(X, y, rcond=None)[0]
    pred = a*x + b
    err  = pred - y
    rms  = float(np.sqrt(np.mean(err**2)))
    mae  = float(np.mean(np.abs(err)))
    return (a,b), pred, rms, mae

def grid_theta_L_train_only(K, gam, train_idx, M, L_min, L_max, L_steps, th_min, th_max, th_steps, V0=0.0, k2=0.0):
    best = None
    L_vals  = np.linspace(L_min, L_max, L_steps)
    th_vals = np.linspace(th_min, th_max, th_steps)
    for L in L_vals:
        for th in th_vals:
            A = build_twisted_matrix(L, M, th, V0=V0, k2=k2)
            lam_all = eigvals_hermitian(A, keep=K)
            (a,b), pred_train, rms, mae = fit_affine(lam_all[train_idx], gam[train_idx])
            if (best is None) or (rms < best[0]):
                best = (rms, mae, a, b, th, L, lam_all)
    return best  # (rms, mae, a,b,theta,L, lam_all)

# ---------- closed-form analytic fit for (a,b,theta,L) ----------
def k_square_model(params, n):
    a,b,theta,L = params
    return a*((2.0*math.pi*n + theta)/L)**2 + b

def fit_closed_form_abthL(gam, n_list):
    # simple nonlinear least squares via mp.findroot on derivatives is messy;
    # instead do numpy minimize with finite differences (small scale).
    from math import isfinite
    # initial guesses inspired by earlier runs
    a0, b0, th0, L0 = 0.5, 10.0, math.pi/2, 22.0
    p = np.array([a0,b0,th0,L0], dtype=float)

    def loss(p):
        a,b,theta,L = p
        if L <= 0: return 1e9
        preds = np.array([k_square_model((a,b,theta,L), n) for n in n_list], float)
        err = preds - gam[:len(n_list)]
        return float(np.mean(err*err))

    # basic coordinate descent
    steps = np.array([1e-2, 1e-2, 1e-2, 1e-2])
    best = loss(p)
    for _ in range(2000):
        improved = False
        for i in range(4):
            for sgn in (+1,-1):
                p_try = p.copy()
                p_try[i] += sgn*steps[i]
                val = loss(p_try)
                if val < best:
                    best, p = val, p_try
                    improved = True
        if not improved:
            steps *= 0.5
            if np.max(steps) < 1e-6:
                break
    return p, best

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--K", type=int, default=140)
    ap.add_argument("--train", type=int, default=70)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--M", type=int, default=2000)
    ap.add_argument("--V0", type=float, default=0.0)
    ap.add_argument("--k2", type=float, default=0.0)
    ap.add_argument("--theta-min", type=float, default=0.0)
    ap.add_argument("--theta-max", type=float, default=2*math.pi)
    ap.add_argument("--theta-steps", type=int, default=181)
    ap.add_argument("--L-min", type=float, default=18.0)
    ap.add_argument("--L-max", type=float, default=26.0)
    ap.add_argument("--L-steps", type=int, default=33)
    args = ap.parse_args()

    # zeros
    gam = riemann_zeros(args.K)

    # random split (to avoid position bias)
    rng = np.random.default_rng(args.seed)
    idx = np.arange(len(gam))
    rng.shuffle(idx)
    train = min(args.train, len(gam)-10)
    train_idx, test_idx = idx[:train], idx[train:]

    # grid-search over (theta, L) using TRAIN only
    best = grid_theta_L_train_only(
        K=args.K, gam=gam, train_idx=train_idx,
        M=args.M,
        L_min=args.L_min, L_max=args.L_max, L_steps=args.L_steps,
        th_min=args.theta_min, th_max=args.theta_max, th_steps=args.theta_steps,
        V0=args.V0, k2=args.k2
    )
    rms_tr, mae_tr, a, b, theta, L, lam_all = best

    # predictions on all
    pred_all = a*lam_all + b

    # -------- leak / sanity checks --------
    if pred_all.shape != gam.shape:
        raise RuntimeError("Shape mismatch: pred_all vs gam")
    if np.allclose(pred_all, gam, atol=1e-12):
        raise RuntimeError("Leakage: predictions equal targets at tol=1e-12")
    print("\n[debug] fingerprints]")
    print("  sum(lam_all) =", float(np.sum(lam_all)))
    print("  sum(gam)     =", float(np.sum(gam)))

    # train metrics (on chosen random train_idx)
    tr_err = pred_all[train_idx] - gam[train_idx]
    RMS_train = float(np.sqrt(np.mean(tr_err**2)))
    MAE_train = float(np.mean(np.abs(tr_err)))

    # test metrics
    te_err = pred_all[test_idx] - gam[test_idx]
    RMS_test = float(np.sqrt(np.mean(te_err**2)))
    MAE_test = float(np.mean(np.abs(te_err)))

    # unfold on TEST and compute spacing stats (model)
    # (use predicted gamma on TEST)
    pred_test_sorted = np.sort(pred_all[test_idx])
    u_model = np.array([N_smooth(x) for x in pred_test_sorted], float)
    s_model = u_model[1:] - u_model[:-1]
    s_model /= np.mean(s_model) if np.mean(s_model)!=0 else 1.0
    KS = ks_stat_against_wigner(s_model)
    NV1 = number_variance(u_model, 1.0)
    NV3 = number_variance(u_model, 3.0)
    NV10= number_variance(u_model,10.0)

    # report
    print("\n=== Twisted Boundary Fit (TRAIN) ===")
    print(f"theta={theta:.10f}  (~ {theta/math.pi:.6f} * π),   L={L:.6f}")
    print(f"a={a:.10f}, b={b:.10f}")
    print(f"RMS_train={RMS_train:.6e}, MAE_train={MAE_train:.6e}  (n={len(train_idx)})")

    print("\n=== Validation (TEST, out-of-sample) ===")
    print(f"RMS_test ={RMS_test:.6e}, MAE_test ={MAE_test:.6e}  (n={len(test_idx)})")

    print("\n=== GUE checks on TEST (unfolded, model) ===")
    print(f"KS(model vs Wigner) = {KS:.4f}   (lower better; ~<0.10 decent)")
    print(f"Σ^2(L):  L=1 → {NV1:.3f},  L=3 → {NV3:.3f},  L=10 → {NV10:.3f}")

    # show 10 TEST comparisons
    print("\n=== First 10 TEST zeros: model vs actual (random test split) ===")
    test_sorted = np.sort(test_idx)[:10]
    for j in test_sorted:
        print(f"n={j+1:3d}  model={pred_all[j]:.12f}   zeta={gam[j]:.12f}   diff={(pred_all[j]-gam[j]):+.3e}")

    # ablation: theta=0 using same L
    A_plain = build_twisted_matrix(L, args.M, 0.0, V0=args.V0, k2=args.k2)
    lam_plain = eigvals_hermitian(A_plain, keep=len(gam))
    (a0,b0),_,_,_ = fit_affine(lam_plain[train_idx], gam[train_idx])
    pred_plain = a0*lam_plain + b0
    err_plain  = pred_plain[test_idx] - gam[test_idx]
    RMS_plain  = float(np.sqrt(np.mean(err_plain**2)))
    print(f"\n[ablation] TEST RMS with theta=0: {RMS_plain:.6e} (should be worse)")

    # -------- closed-form fit of (a,b,theta,L) using first 10 indices n=1..10 --------
    n_list = list(range(1, 11))
    p_est, loss_val = fit_closed_form_abthL(gam, n_list)
    a2,b2,th2,L2 = p_est
    print("\n[closed-form fit on n=1..10] params:")
    print(f"a={a2:.10f}, b={b2:.10f}, theta={th2:.10f} (~{th2/math.pi:.6f}*π), L={L2:.10f}, loss={loss_val:.3e}")

    # build analytic model spectrum and score on test
    lam_analytic = np.array([((2.0*math.pi*(n+1) + th2)/L2)**2 for n in range(len(gam))], float)  # using n=1..K
    pred_analytic = a2*lam_analytic + b2
    te_err2 = pred_analytic[test_idx] - gam[test_idx]
    RMS_test2 = float(np.sqrt(np.mean(te_err2**2)))
    MAE_test2 = float(np.mean(np.abs(te_err2)))
    print(f"[closed-form] TEST RMS={RMS_test2:.6e}, MAE={MAE_test2:.6e}")

    # dump summary json
    out = {
        "theta": theta, "L": L, "a": a, "b": b,
        "RMS_train": RMS_train, "MAE_train": MAE_train,
        "RMS_test": RMS_test, "MAE_test": MAE_test,
        "KS_test": KS, "Sigma2": {"1": NV1, "3": NV3, "10": NV10},
        "ablation_theta0_RMS_test": RMS_plain,
        "closed_form": {"a": a2, "b": b2, "theta": th2, "L": L2,
                        "RMS_test": RMS_test2, "MAE_test": MAE_test2, "loss_train10": loss_val}
    }
    with open("hp_twist_summary.json","w") as f:
        json.dump(out, f, indent=2)
    print("\nWrote hp_twist_summary.json")

import sys
sys.argv = ['', '--K', '50', '--train', '25', '--M', '500', '--L-steps', '5', '--L-min', '20', '--L-max', '24', '--theta-steps', '10', '--theta-min', '1', '--theta-max', '2', '--seed', '1337']
main()</parameter
</xai:function_call
