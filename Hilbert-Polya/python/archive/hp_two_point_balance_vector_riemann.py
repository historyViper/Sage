# hp_two_point_balance_vector_riemann.py
# Stand-alone pipeline using actual Riemann zeros (computed & cached) to kill the wobble.

import sys, json, os
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# --------- NEW: Riemann zeros (vector) via mpmath, with caching ----------
def load_or_compute_riemann_zeros(N=50, cache_path="riemann_zeros.json", mp_dps=80):
    """
    Returns the first N ordinates t_n (imag parts) of zeros on the critical line,
    using mpmath.zetazero(n). Caches to JSON so later runs are instant.
    """
    try:
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                data = json.load(f)
            ts = np.array(data.get(str(N)) or [], dtype=float)
            # If exact N not cached, fall through and compute
            if ts.size == N:
                print(f"Loaded Riemann zeros from {cache_path} (N={N}).")
                return ts
    except Exception:
        pass

    import mpmath as mp
    mp.mp.dps = int(mp_dps)

    print(f"Computing first {N} Riemann zeros (mpmath, dps={mp_dps})...")
    ts = []
    for k in range(1, N+1):
        z = mp.zetazero(k)  # complex ~ 0.5 + i t_k
        ts.append(float(mp.im(z)))
    ts = np.array(ts, dtype=float)

    # append/update cache
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    cache[str(N)] = ts.tolist()
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"Saved Riemann zeros to {cache_path} (N={N}).")
    return ts

# ---------------- Core operator (U=0) ----------------
def periodic_D1(M, dt):
    D1 = np.zeros((M, M), dtype=complex)
    for i in range(M):
        D1[i, (i+1)%M] =  0.5/dt
        D1[i, (i-1)%M] = -0.5/dt
    return D1

def build_operator(M=256, theta=np.pi, c1=0.0, c2=0.0, c3=0.0):
    tau = np.linspace(0, 2*np.pi, M, endpoint=False)
    dt = tau[1] - tau[0]
    kappa = theta/(2*np.pi)
    chi = 1.0 + c1*np.cos(tau) + c2*np.cos(2*tau) + c3*np.cos(3*tau)
    chi = np.maximum(chi, 1e-6)
    D1 = periodic_D1(M, dt)
    I  = np.eye(M, dtype=complex)
    Dk = D1 + 1j*kappa*I
    Chi    = np.diag(chi.astype(complex))
    ChiInv = np.diag((1.0/chi).astype(complex))
    L = - ChiInv @ (Dk @ (Chi @ Dk))
    L = 0.5*(L + L.conj().T)
    return L

def spectrum(L, k=200):
    evals, _ = np.linalg.eigh(L)
    lam = np.sort(evals.real)
    lam = lam[lam > 1e-12]
    return lam[:k]

def unique_eigs(vals, tol=1e-6):
    out=[]
    for v in np.sort(vals):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return np.array(out)

# ---------------- Stage 2: Spinor HP operator ----------------
SIGMA_X = np.array([[0,1],[1,0]], dtype=complex)
SIGMA_Z = np.array([[1,0],[0,-1]], dtype=complex)
I2      = np.eye(2, dtype=complex)

def build_spinor_operator(M=256, theta=np.pi, c1=0.0, c2=0.0, m1=0.0, g1=0.0):
    Ls = build_operator(M, theta, c1, c2)              # (M x M)
    tau = np.linspace(0, 2*np.pi, M, endpoint=False)
    m_tau = m1*np.cos(tau)      # σ_z mass-like
    g_tau = g1*np.cos(tau)      # σ_x mixing
    Mmat = np.diag(m_tau.astype(complex))
    Gmat = np.diag(g_tau.astype(complex))
    L = np.kron(Ls, I2) + np.kron(Mmat, SIGMA_Z) + np.kron(Gmat, SIGMA_X)
    L = 0.5*(L + L.conj().T)
    return L

def r2_score(y, yhat):
    ss_res = np.sum((y - yhat)**2)
    ss_tot = np.sum((y - y.mean())**2)
    return 1 - ss_res/ss_tot if ss_tot > 0 else np.nan

def spinor_fit(RIEMANN_T, theta, m1, g1, c1=0.0, c2=0.0, skip=6, N=40, M=256):
    L = build_spinor_operator(M, theta, c1, c2, m1=m1, g1=g1)
    evals, _ = np.linalg.eigh(L)
    lam = np.sort(evals.real)
    lam = lam[lam>1e-12]
    lam = unique_eigs(lam, tol=1e-8)
    y = np.sqrt(lam)[skip:][:N]
    t = RIEMANN_T[:N]
    X = np.vstack([np.ones(N), t]).T
    a,b = np.linalg.lstsq(X, y, rcond=None)[0]
    yhat = a + b*t
    R2 = r2_score(y, yhat)
    rmse = float(np.sqrt(np.mean((y-yhat)**2)))
    return dict(a=a,b=b,R2=R2,rmse=rmse)

def sweep_spinor_params(RIEMANN_T, theta, skip=6, N=40, M=256, c1=0.0, c2=0.0):
    test_values = [0.0, 0.01, 0.02, -0.01]
    best = None; best_info = None
    print("  Sweeping m1 and g1...")
    for m1 in test_values:
        for g1 in test_values:
            out = spinor_fit(RIEMANN_T, theta, m1, g1, c1=c1, c2=c2, skip=skip, N=N, M=M)
            score = (out['R2'], -out['rmse'])
            if (best is None) or (score > best):
                best = score
                out['m1'] = float(m1)
                out['g1'] = float(g1)
                best_info = out
            print(f"    m1={m1:+.3f} g1={g1:+.3f} → R²={out['R2']:.6f}, RMSE={out['rmse']:.3f}")
    return best_info

# ---------------- Stage 3: 2D Torus operator ----------------
def build_operator_sigma(Ms=32, theta_s=0.0):
    tau = np.linspace(0, 2*np.pi, Ms, endpoint=False)
    dt = tau[1] - tau[0]
    kappa = theta_s/(2*np.pi)
    D1 = periodic_D1(Ms, dt)
    I  = np.eye(Ms, dtype=complex)
    Dk = D1 + 1j*kappa*I
    Ls = -(Dk @ Dk)
    Ls = 0.5*(Ls + Ls.conj().T)
    return Ls

def torus_fit(RIEMANN_T, theta_tau, theta_sigma=0.0, eps=0.02, M_tau=256, M_sigma=32,
              skip=5, N=40):
    Ltau = build_operator(M_tau, theta_tau, c1=0.0, c2=0.0)
    Lsig = build_operator_sigma(M_sigma, theta_sigma)
    L = np.kron(Ltau, np.eye(M_sigma)) + eps*np.kron(np.eye(M_tau), Lsig)
    evals, _ = np.linalg.eigh(L)
    lam = np.sort(evals.real)
    lam = lam[lam>1e-12]
    lam = unique_eigs(lam, tol=1e-8)
    y = np.sqrt(lam)[skip:][:N]
    t = RIEMANN_T[:N]
    X = np.vstack([np.ones(N), t]).T
    a,b = np.linalg.lstsq(X, y, rcond=None)[0]
    yhat = a + b*t
    R2 = r2_score(y, yhat)
    rmse = float(np.sqrt(np.mean((y-yhat)**2)))
    return dict(R2=R2, rmse=rmse, a=a, b=b)

def sweep_torus_params(RIEMANN_T, theta_tau, skip=5, N=40, M_tau=256, M_sigma=8):
    eps_values = [0.0, 0.01, 0.02, 0.03]
    theta_s_values = [0.0]
    best = None; best_info = None
    print("  Sweeping epsilon and theta_sigma (M_tau matches Stage-0 to avoid grid artifacts)...")
    print(f"    Matrix size: {M_tau} x {M_sigma} = {M_tau * M_sigma} eigenvalues")
    for eps in eps_values:
        for ths in theta_s_values:
            out = torus_fit(RIEMANN_T, theta_tau, ths, eps, M_tau=M_tau, M_sigma=M_sigma,
                           skip=skip, N=N)
            score = (out['R2'], -out['rmse'])
            if (best is None) or (score > best):
                best = score
                out['eps'] = float(eps)
                out['theta_sigma'] = float(ths)
                best_info = out
            print(f"    eps={eps:.3f}, θσ={ths:+.3f} ⇒ R²={out['R2']:.6f}, RMSE={out['rmse']:.3f}")
    return best_info

# ---------------- Two-point & helpers ----------------
def two_point_ab(t, y, i, j):
    ti, tj, yi, yj = t[i], t[j], y[i], y[j]
    b = (yj - yi) / (tj - ti)
    a = yi - b*ti
    return a, b

def two_point_delta_gamma(t, a, b, mp, mq, p, q):
    fp = a + b*t[p]
    fq = a + b*t[q]
    gamma = (mq - mp) / (fq - fp)
    delta = mp - gamma*fp
    return delta, gamma

def sweep_anchors(t, y, i_min=4, i_max=14, j_min=22, j_max=36):
    best=None; best_info=None
    for i in range(i_min, i_max+1):
        for j in range(max(i+3, j_min), j_max+1):
            a2,b2 = two_point_ab(t, y, i, j)
            yhat  = a2 + b2*t
            R2    = r2_score(y, yhat)
            rmse  = float(np.sqrt(np.mean((y - yhat)**2)))
            score = (R2, -rmse)
            if (best is None) or (score > best):
                best, best_info = score, dict(i=i,j=j,a=a2,b=b2,R2=R2,rmse=rmse)
    return best_info

def sweep_theta(RIEMANN_T, M=256, thetas=None, skip=5, N=40, c1=0.0, c2=0.0, c3=0.0):
    if thetas is None:
        thetas = np.linspace(np.pi-0.05, np.pi+0.05, 41)
    best=None; out=None
    for th in thetas:
        L = build_operator(M, theta=th, c1=c1, c2=c2, c3=c3)
        lam = spectrum(L, k=max(N+20, 200))
        y   = np.sqrt(unique_eigs(lam))[skip:][:N]
        t   = RIEMANN_T[:N]
        X = np.vstack([np.ones(N), t]).T
        a,b = np.linalg.lstsq(X, y, rcond=None)[0]
        yhat = a + b*t
        R2 = r2_score(y, yhat)
        rmse = float(np.sqrt(np.mean((y - yhat)**2)))
        score = (R2, -rmse)
        if (best is None) or (score > best):
            best, out = score, dict(theta=float(th), a=a, b=b, R2=R2, rmse=rmse)
    return out

def sweep_c3(RIEMANN_T, M=256, theta=np.pi, c1=0.0, c2=0.0, c3_range=None, skip=5, N=40):
    if c3_range is None:
        c3_range = np.linspace(-0.03, 0.03, 31)
    best=None; out=None
    for c3 in c3_range:
        L = build_operator(M, theta=theta, c1=c1, c2=c2, c3=c3)
        lam = spectrum(L, k=max(N+20, 200))
        y   = np.sqrt(unique_eigs(lam))[skip:][:N]
        t   = RIEMANN_T[:N]
        X = np.vstack([np.ones(N), t]).T
        a,b = np.linalg.lstsq(X, y, rcond=None)[0]
        yhat = a + b*t
        R2 = r2_score(y, yhat)
        rmse = float(np.sqrt(np.mean((y - yhat)**2)))
        score = (R2, -rmse)
        if (best is None) or (score > best):
            best, out = score, dict(c3=float(c3), a=a, b=b, R2=R2, rmse=rmse)
    return out

def sweep_all_params(RIEMANN_T, M=256, skip=5, N=40):
    print("  Step 1: Finding best theta (c3=0)...")
    best_theta = sweep_theta(RIEMANN_T, M=M, c1=0.0, c2=0.0, c3=0.0, skip=skip, N=N)
    theta_opt = best_theta['theta']
    print(f"  Step 2: Finding best c3 (theta={theta_opt:.6f})...")
    best_c3 = sweep_c3(RIEMANN_T, M=M, theta=theta_opt, c1=0.0, c2=0.0, skip=skip, N=N)
    return dict(theta=theta_opt, c3=best_c3['c3'],
                a=best_c3['a'], b=best_c3['b'], R2=best_c3['R2'], rmse=best_c3['rmse'])

# ---------------- Stage 1: two-θ band merge ----------------
def merged_theta_fit(RIEMANN_T, theta1, theta2, skip=5, N=40, M=256, c1=0.0, c2=0.0, c3=0.0):
    L1 = build_operator(M, theta1, c1=c1, c2=c2, c3=c3)
    L2 = build_operator(M, theta2, c1=c1, c2=c2, c3=c3)
    lam1 = spectrum(L1, k=200)
    lam2 = spectrum(L2, k=200)
    lam = np.concatenate([lam1, lam2])
    lam = np.sort(lam[lam > 1e-12])
    lam = unique_eigs(lam, tol=1e-8)
    y = np.sqrt(lam)[skip:][:N]
    t = RIEMANN_T[:N]
    X = np.vstack([np.ones(N), t]).T
    a, b = np.linalg.lstsq(X, y, rcond=None)[0]
    yhat = a + b*t
    R2 = r2_score(y, yhat)
    rmse = float(np.sqrt(np.mean((y - yhat)**2)))
    return dict(a=a, b=b, R2=R2, rmse=rmse, y=y, yhat=yhat)

def sweep_two_theta(RIEMANN_T, theta_base, delta_range=None, skip=5, N=40, M=256, c1=0.0, c2=0.0, c3=0.0):
    if delta_range is None:
        delta_range = np.linspace(0.01, 0.06, 11)
    best = None; best_info = None
    for delta in delta_range:
        theta2 = theta_base + delta
        res = merged_theta_fit(RIEMANN_T, theta_base, theta2, skip=skip, N=N, M=M, c1=c1, c2=c2, c3=c3)
        score = (res['R2'], -res['rmse'])
        if (best is None) or (score > best):
            best = score
            res['theta1'] = float(theta_base)
            res['theta2'] = float(theta2)
            res['delta'] = float(delta)
            best_info = res
    return best_info

# ---------------- Main ----------------
if __name__ == "__main__":
    # Config (tweak here)
    M      = 256
    skip   = 5
    N      = 40
    i,j    = 10, 30
    use_physical = False
    p,q = 5, 25
    mp, mq = 0.10566, 91.1876

    # Use actual Riemann zeros (vector) instead of a fixed table
    RIEMANN_T = load_or_compute_riemann_zeros(N=50, cache_path="riemann_zeros.json", mp_dps=80)

    print("\n" + "="*60)
    print("STAGE 0: Fine-tuning operator parameters")
    print("="*60)
    best_params = sweep_all_params(RIEMANN_T, M=M, skip=skip, N=N)
    print(f"\nBest parameters (LS fit):")
    print(f"  theta={best_params['theta']:.6f}")
    print(f"  c3={best_params['c3']:.6f}")
    print(f"  R²={best_params['R2']:.6f}")
    print(f"  RMSE={best_params['rmse']:.6f}")

    theta_opt = best_params['theta']
    c3_opt    = best_params['c3']

    print("\n" + "="*60)
    print("STAGE 1: Two-θ band merge (vectorization)")
    print("="*60)
    print(f"Base theta: {theta_opt:.6f}")
    best_merge = sweep_two_theta(RIEMANN_T, theta_base=theta_opt, skip=skip, N=N, M=M, c1=0.0, c2=0.0, c3=0.0)
    print(f"\nBest two-θ merge:")
    print(f"  theta1={best_merge['theta1']:.6f}, theta2={best_merge['theta2']:.6f}")
    print(f"  delta={best_merge['delta']:.6f}")
    print(f"  R²={best_merge['R2']:.6f}, RMSE={best_merge['rmse']:.6f}")

    print(f"\nComparison:")
    print(f"  Stage 0 (single θ): R²={best_params['R2']:.6f}, RMSE={best_params['rmse']:.6f}")
    print(f"  Stage 1 (merged θ): R²={best_merge['R2']:.6f}, RMSE={best_merge['rmse']:.6f}")

    if best_merge['R2'] > best_params['R2']:
        print(f"\n✓ Stage 1 improves fit by ΔR²={best_merge['R2'] - best_params['R2']:.6f}")
        y_opt = best_merge['y']
        t_opt = RIEMANN_T[:N]
        use_merged = True
    else:
        print(f"\nStage 0 is better. Using single-θ spectrum.")
        L_opt = build_operator(M, theta=theta_opt, c1=0.0, c2=0.0, c3=c3_opt)
        lam_opt = spectrum(L_opt, k=max(4*N, 200))
        lam_u_opt = unique_eigs(lam_opt)
        y_all_opt = np.sqrt(lam_u_opt)
        y_opt = y_all_opt[skip:][:N]
        t_opt = RIEMANN_T[:N]
        use_merged = False

    print("\n" + "="*60)
    print("STAGE 2: Spinor HP operator (tiny couplings)")
    print("="*60)
    best_spinor = sweep_spinor_params(RIEMANN_T, theta=theta_opt, skip=skip, N=N, M=M, c1=0.0, c2=0.0)
    print(f"\nBest spinor parameters:")
    print(f"  m1={best_spinor['m1']:.6f}, g1={best_spinor['g1']:.6f}")
    print(f"  R²={best_spinor['R2']:.6f}, RMSE={best_spinor['rmse']:.6f}")

    # Best-of Stage 0/1 as baseline for 2/3
    stage01_best_R2   = max(best_params['R2'], best_merge['R2'])
    stage01_best_tag  = 'Stage 1 (two-θ)' if best_merge['R2'] > best_params['R2'] else 'Stage 0 (single θ)'
    stage01_best_RMSE = best_merge['rmse'] if best_merge['R2'] > best_params['R2'] else best_params['rmse']
    print(f"\nBaseline before Stage 2/3: {stage01_best_tag} with R²={stage01_best_R2:.6f}")
    print(f"\nComparison:")
    print(f"  Baseline {stage01_best_tag}: R²={stage01_best_R2:.6f}, RMSE={stage01_best_RMSE:.6f}")
    print(f"  Stage 2 (spinor): R²={best_spinor['R2']:.6f}, RMSE={best_spinor['rmse']:.6f}")

    use_spinor_temp = best_spinor['R2'] > stage01_best_R2
    stage_prev_R2   = max(stage01_best_R2, best_spinor['R2'])

    print("\n" + "="*60)
    print("STAGE 3: 2D Torus operator (Kronecker sum)")
    print("="*60)
    M_tau_stage3 = M     # match Stage-0 grid to avoid artifacts
    M_sigma = 8          # keep small for speed
    best_torus = sweep_torus_params(RIEMANN_T, theta_tau=theta_opt, skip=skip, N=N, M_tau=M_tau_stage3, M_sigma=M_sigma)
    print(f"\nBest 2D torus parameters:")
    print(f"  eps={best_torus['eps']:.6f}, theta_sigma={best_torus['theta_sigma']:.6f}")
    print(f"  R²={best_torus['R2']:.6f}, RMSE={best_torus['rmse']:.6f}")

    print(f"\nComparison:")
    print(f"  Previous best (Stage 0/1 vs 2): R²={stage_prev_R2:.6f}")
    print(f"  Stage 3 (2D torus): R²={best_torus['R2']:.6f}, RMSE={best_torus['rmse']:.6f}")

    baseline_rmse_for_tie = best_spinor['rmse'] if use_spinor_temp else stage01_best_RMSE
    r2_better   = best_torus['R2'] > stage_prev_R2 + 1e-3
    r2_tied     = abs(best_torus['R2'] - stage_prev_R2) <= 1e-3
    rmse_better = best_torus['rmse'] < (baseline_rmse_for_tie - 1e-3)

    # Require real coupling to switch
    eps_min_select = 5e-3
    select_torus = (best_torus['eps'] is not None) and (best_torus['eps'] >= eps_min_select) \
                   and (r2_better or (r2_tied and rmse_better))

    if select_torus:
        print(f"\n✓ Stage 3 selected (ε={best_torus['eps']:.3f}, R² {'improved' if r2_better else 'tied'}, RMSE better).")
        Ltau = build_operator(M_tau_stage3, theta=theta_opt, c1=0.0, c2=0.0)
        Lsig = build_operator_sigma(M_sigma, best_torus['theta_sigma'])
        L = np.kron(Ltau, np.eye(M_sigma)) + best_torus['eps']*np.kron(np.eye(M_tau_stage3), Lsig)
        evals, _ = np.linalg.eigh(L)
        lam = np.sort(evals.real)
        lam = lam[lam>1e-12]
        lam = unique_eigs(lam, tol=1e-8)
        y_torus_actual = np.sqrt(lam)[skip:][:N]
        y_opt = y_torus_actual
        t_opt = RIEMANN_T[:N]
        use_torus = True
        use_spinor = False

        # Figure 2 overlay (scalar vs torus)
        try:
            L_scalar = build_operator(M, theta=theta_opt, c1=0.0, c2=0.0, c3=c3_opt)
            lam_scalar = spectrum(L_scalar, k=max(4*N, 200))
            y_scalar = np.sqrt(unique_eigs(lam_scalar))[skip:][:N]

            X = np.vstack([np.ones(N), RIEMANN_T[:N]]).T
            a_s, b_s = np.linalg.lstsq(X, y_scalar, rcond=None)[0]
            yhat_s = a_s + b_s*RIEMANN_T[:N]
            R2_scalar = r2_score(y_scalar, yhat_s)

            a_t, b_t = np.linalg.lstsq(X, y_opt, rcond=None)[0]
            yhat_t = a_t + b_t*RIEMANN_T[:N]
            R2_torus = r2_score(y_opt, yhat_t)

            plt.figure(figsize=(12,6), facecolor='black')
            ax = plt.gca(); ax.set_facecolor('black')
            plt.plot(RIEMANN_T[:N], y_scalar, '-', lw=2.25, color='#ff4444',
                     label=f"Scalar HP (R²={R2_scalar:.3f})", zorder=2)
            plt.plot(RIEMANN_T[:N], y_opt, '-', lw=4.5, color='#00e5ff',
                     label=f"Torus HP (R²={R2_torus:.3f})", zorder=1)
            plt.legend(facecolor='black', edgecolor='white', labelcolor='white')
            plt.xlabel(r"Riemann ordinate $t_n$", color='white')
            plt.ylabel(r"$\sqrt{\lambda_n}$", color='white')
            plt.title("Figure 2. Parabolic Drift Suppression via Torus Coupling",
                      color='white', pad=12)
            for spine in ax.spines.values(): spine.set_color('white')
            ax.tick_params(colors='white', which='both')
            plt.grid(alpha=0.25, color='white', linestyle='--')
            plt.tight_layout()
            plt.savefig("figure2_torus_overlay.png", dpi=200, facecolor='black')
            print("Saved: figure2_torus_overlay.png")
        except Exception as e:
            print("Figure 2 overlay generation skipped:", e)

    else:
        if best_torus.get('eps', 0.0) < eps_min_select:
            print("\nNote: Best Stage 3 has ~zero coupling (ε≈0). Treating as scalar—keeping previous spectrum.")
        else:
            print(f"\nPrevious spectrum is better (kept).")
        if use_spinor_temp and best_spinor['R2'] > stage01_best_R2:
            use_spinor = True
            L_spinor = build_spinor_operator(M, theta=theta_opt, c1=0.0, c2=0.0,
                                             m1=best_spinor['m1'], g1=best_spinor['g1'])
            evals, _ = np.linalg.eigh(L_spinor)
            lam = np.sort(evals.real)
            lam = lam[lam>1e-12]
            lam = unique_eigs(lam, tol=1e-8)
            y_spinor = np.sqrt(lam)[skip:][:N]
            y_opt = y_spinor
            t_opt = RIEMANN_T[:N]
        else:
            L_opt = build_operator(M, theta=theta_opt, c1=0.0, c2=0.0, c3=c3_opt)
            lam_opt = spectrum(L_opt, k=max(4*N, 200))
            lam_u_opt = unique_eigs(lam_opt)
            y_all_opt = np.sqrt(lam_u_opt)
            y_opt = y_all_opt[skip:][:N]
            t_opt = RIEMANN_T[:N]
            use_spinor = False
        use_torus = False

    # Two-point fit on optimized spectrum
    print("\nFinding best anchors with optimized spectrum...")
    best_anchors_opt = sweep_anchors(t_opt, y_opt)
    print("Best two-point:", best_anchors_opt)

    i, j = best_anchors_opt['i'], best_anchors_opt['j']
    a2, b2 = two_point_ab(t_opt, y_opt, i, j)
    yhat2  = a2 + b2*t_opt
    R2_2   = r2_score(y_opt, yhat2)

    print(f"\nTwo-point balance on sqrt(lambda):")
    print(f"  skip={skip}, N={N}, anchors i={i}, j={j}")
    print(f"  a={a2:.6f}, b={b2:.6f},  R^2={R2_2:.4f}")

    print("\nFirst 12 (aligned block): sqrt(lambda_n)  vs  a + b t_n  (Δ)")
    for k in range(min(12, N)):
        print(f"{k+1:2d}: {y_opt[k]:10.6f}   {yhat2[k]:10.6f}   Δ={y_opt[k]-yhat2[k]:+.6f}")

    # Optional physical mapping
    if use_physical:
        delta, gamma = two_point_delta_gamma(t_opt, a2, b2, mp, mq, p, q)
        m_pred = delta + gamma*(a2 + b2*t_opt)
        print(f"\nPhysical dressing from two masses (p={p}, q={q}):")
        print(f"  delta={delta:.6e} GeV,  gamma={gamma:.6e}")
        print("  First 10 predicted masses (GeV):")
        for k in range(min(10, N)):
            print(f"  n={k+1:2d}: {m_pred[k]:.6e}")

    # Figure 1-style twin (fit + residuals)
    plt.figure(figsize=(10,6))
    plt.subplot(2,1,1)
    plt.plot(y_opt, 'o-', label='sqrt(lambda)')
    plt.plot(yhat2, 's-', label='a + b*t_n')
    plt.title(f"Two-point fit (R^2={R2_2:.4f})")
    plt.xlabel("mode index (after skipping)"); plt.ylabel("sqrt(eigenvalue)")
    plt.legend()

    plt.subplot(2,1,2)
    plt.plot(y_opt - yhat2)
    plt.title("Residuals")
    plt.xlabel("mode index"); plt.ylabel("residual")

    plt.tight_layout()
    plt.savefig("hp_two_point_fit.png", dpi=160)
    print("\nSaved: hp_two_point_fit.png")

    # JSON export (richer)
    summary_arrays = dict(
        t_opt = t_opt.tolist(),
        y_opt = y_opt.tolist(),
        yhat  = (a2 + b2*t_opt).tolist()
    )
    stage3_block = dict(
        eps=float(best_torus.get('eps', 0.0)),
        theta_sigma=float(best_torus.get('theta_sigma', 0.0)),
        R2=float(best_torus.get('R2', float('nan'))),
        rmse=float(best_torus.get('rmse', float('nan'))),
        improved=bool('use_torus' in locals() and use_torus)
    )
    summary = dict(
        M=M,
        stage0=dict(theta=float(theta_opt), c3=float(c3_opt), R2=float(best_params['R2']), rmse=float(best_params['rmse'])),
        stage1=dict(theta1=float(best_merge['theta1']), theta2=float(best_merge['theta2']),
                    delta=float(best_merge['delta']), R2=float(best_merge['R2']),
                    rmse=float(best_merge['rmse']),
                    improved=bool(best_merge['R2'] > best_params['R2'])),
        stage2=dict(m1=float(best_spinor['m1']), g1=float(best_spinor['g1']),
                    R2=float(best_spinor['R2']), rmse=float(best_spinor['rmse']),
                    improved=bool(use_spinor_temp and best_spinor['R2'] > stage01_best_R2)),
        stage3=stage3_block,
        skip=skip, N=N, anchors=[int(i), int(j)],
        a=float(a2), b=float(b2), R2=float(R2_2),
        arrays=summary_arrays
    )
    with open("hp_two_point_summary.json","w") as f:
        json.dump(summary, f, indent=2)
    print("Saved: hp_two_point_summary.json")
