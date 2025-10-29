# hp_two_point_balance.py
# Stand-alone: two-point balance for the HP core + optional physical dressing

import sys, json
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
import matplotlib.pyplot as plt

# -------- Riemann zero ordinates (first 50) --------
RIEMANN_T = np.array([
    14.134725141, 21.022039639, 25.010857580, 30.424876126, 32.935061588,
    37.586178159, 40.918719012, 43.327073281, 48.005150881, 49.773832478,
    52.970321478, 56.446247697, 59.347044003, 60.831778525, 65.112544048,
    67.079810529, 69.546401711, 72.067157674, 75.704690699, 77.144840069,
    79.337375020, 82.910380854, 84.735492981, 87.425274613, 88.809111208,
    92.491899271, 94.651344041, 95.870634228, 98.831194218, 101.317851006,
    103.725538040, 105.446623052, 107.168611184, 109.718718201, 111.029535543,
    114.320220915, 116.226680321, 118.790782866, 121.370125002, 122.946829294,
    124.256818554, 127.516683880, 129.578704200, 131.087688531, 133.497737203,
    134.756509753, 138.116042055, 139.736208952, 141.123707404, 143.111845808
])

# -------- Core operator (U=0) --------
def periodic_D1(M, dt):
    D1 = np.zeros((M, M), dtype=complex)
    for i in range(M):
        D1[i, (i+1)%M] =  0.5/dt
        D1[i, (i-1)%M] = -0.5/dt
    return D1

def build_operator(M=256, theta=np.pi, c1=0.0, c2=0.0, c3=0.0, bloch_theta=None):
    """Build HP operator with optional separate Bloch phase for symmetry diagnostics."""
    tau = np.linspace(0, 2*np.pi, M, endpoint=False)
    dt = tau[1] - tau[0]
    # Use bloch_theta for symmetry check, theta for fit
    kappa = (theta if bloch_theta is None else bloch_theta) / (2*np.pi)
    chi = 1.0 + c1*np.cos(tau) + c2*np.cos(2*tau) + c3*np.cos(3*tau)
    chi = np.maximum(chi, 1e-6)
    # U = 0 (massless HP core)
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

# -------- Stage 2: Spinor HP operator --------
SIGMA_X = np.array([[0,1],[1,0]], dtype=complex)
SIGMA_Z = np.array([[1,0],[0,-1]], dtype=complex)
I2      = np.eye(2, dtype=complex)

def build_spinor_operator(M=256, theta=np.pi, c1=0.0, c2=0.0, 
                          m1=0.0, g1=0.0):
    """Build spinor HP operator with tiny couplings.
    
    Constructs: L = Ls⊗I₂ + Mmat⊗σz + Gmat⊗σx
    where Ls is the scalar HP operator and the couplings are harmonic in τ.
    """
    # scalar core
    Ls = build_operator(M, theta, c1, c2)              # (M x M)
    # position-diagonal couplings (harmonic in tau)
    tau = np.linspace(0, 2*np.pi, M, endpoint=False)
    m_tau = m1*np.cos(tau)      # σ_z mass-like
    g_tau = g1*np.cos(tau)      # σ_x mixing
    Mmat = np.diag(m_tau.astype(complex))              # (M x M)
    Gmat = np.diag(g_tau.astype(complex))              # (M x M)
    # Kronecker build: L = Ls⊗I2 + Mmat⊗σz + Gmat⊗σx
    L = np.kron(Ls, I2) + np.kron(Mmat, SIGMA_Z) + np.kron(Gmat, SIGMA_X)
    L = 0.5*(L + L.conj().T)
    return L

def spinor_fit(theta, m1, g1, c1=0.0, c2=0.0, skip=6, N=40, M=256):
    """Fit spinor HP operator spectrum."""
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
    R2 = r2_score(y, yhat); rmse = float(np.sqrt(np.mean((y-yhat)**2)))
    return dict(a=a,b=b,R2=R2,rmse=rmse)

def sweep_spinor_params(theta, skip=6, N=40, M=256, c1=0.0, c2=0.0):
    """Sweep over tiny couplings m1 and g1."""
    test_values = [0.0, 0.01, 0.02, -0.01]
    best = None; best_info = None
    
    print("  Sweeping m1 and g1...")
    for m1 in test_values:
        for g1 in test_values:
            out = spinor_fit(theta, m1, g1, c1=c1, c2=c2, skip=skip, N=N, M=M)
            score = (out['R2'], -out['rmse'])
            if (best is None) or (score > best):
                best = score
                out['m1'] = float(m1)
                out['g1'] = float(g1)
                best_info = out
            print(f"    m1={m1:+.3f} g1={g1:+.3f} → R²={out['R2']:.6f}, RMSE={out['rmse']:.3f}")
    
    return best_info

# -------- Stage 3: 2D Torus operator --------
def build_operator_sigma(Ms=32, theta_s=0.0, bloch_theta=None):
    """Build operator for the sigma (second) direction with uniform chi, U=0."""
    tau = np.linspace(0, 2*np.pi, Ms, endpoint=False)
    dt = tau[1] - tau[0]
    kappa = (theta_s if bloch_theta is None else bloch_theta) / (2*np.pi)
    # uniform chi, U=0 in sigma direction
    D1 = periodic_D1(Ms, dt)
    I  = np.eye(Ms, dtype=complex)
    Dk = D1 + 1j*kappa*I
    Ls = -(Dk @ Dk)          # chi=1 ⇒ ChiInv=Chi=I
    Ls = 0.5*(Ls + Ls.conj().T)
    return Ls

def torus_fit(theta_tau, theta_sigma=0.0, eps=0.02, M_tau=256, M_sigma=32,
              skip=5, N=40):
    """Fit 2D torus spectrum with Kronecker sum."""
    Ltau = build_operator(M_tau, theta_tau, c1=0.0, c2=0.0)    # your 1D best
    Lsig = build_operator_sigma(M_sigma, theta_sigma)
    # Kronecker sum: L = Ltau ⊗ I + eps * (I ⊗ Lsig)
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

def sweep_torus_params(theta_tau, skip=5, N=40, M_tau=128, M_sigma=8):
    """Sweep over epsilon and theta_sigma for 2D torus (optimized for speed)."""
    # Heavily reduced parameter space: 128x8 = 1024 eigenvalues (8x faster than 256x16)
    eps_values = [0.0, 0.01, 0.02, 0.03]  # tiny coupling window
    theta_s_values = [0.0]  # Only test zero phase
    best = None; best_info = None
    
    print("  Sweeping epsilon and theta_sigma (fast mode: M_tau=128, M_sigma=8)...")
    print(f"    Matrix size: {M_tau} x {M_sigma} = {M_tau * M_sigma} eigenvalues")
    for eps in eps_values:
        for ths in theta_s_values:
            out = torus_fit(theta_tau, ths, eps, M_tau=M_tau, M_sigma=M_sigma,
                           skip=skip, N=N)
            score = (out['R2'], -out['rmse'])
            if (best is None) or (score > best):
                best = score
                out['eps'] = float(eps)
                out['theta_sigma'] = float(ths)
                best_info = out
            print(f"    eps={eps:.3f}, θσ={ths:+.3f} ⇒ R²={out['R2']:.6f}, RMSE={out['rmse']:.3f}")
    
    return best_info

# -------- Two-point balances --------
def two_point_ab(t, y, i, j):
    ti, tj, yi, yj = t[i], t[j], y[i], y[j]
    b = (yj - yi) / (tj - ti)
    a = yi - b*ti
    return a, b

def r2_score(y, yhat):
    ss_res = np.sum((y - yhat)**2)
    ss_tot = np.sum((y - y.mean())**2)
    return 1 - ss_res/ss_tot if ss_tot > 0 else np.nan

def two_point_delta_gamma(t, a, b, mp, mq, p, q):
    fp = a + b*t[p]
    fq = a + b*t[q]
    gamma = (mq - mp) / (fq - fp)
    delta = mp - gamma*fp
    return delta, gamma

# -------- Sweep helpers --------
def sweep_anchors(t, y, i_min=4, i_max=14, j_min=22, j_max=36):
    """Sweep anchor points (i,j) to find optimal two-point fit."""
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

def sweep_theta(M=256, thetas=None, skip=5, N=40, c1=0.0, c2=0.0, c3=0.0):
    """Sweep theta values around pi to find optimal operator."""
    if thetas is None:
        thetas = np.linspace(np.pi-0.05, np.pi+0.05, 41)
    best=None; out=None
    for th in thetas:
        L = build_operator(M, theta=th, c1=c1, c2=c2, c3=c3)
        lam = spectrum(L, k=max(N+20, 200))
        y   = np.sqrt(unique_eigs(lam))[skip:][:N]
        t   = RIEMANN_T[:N]
        # use LS (global) for comparison
        X = np.vstack([np.ones(N), t]).T
        a,b = np.linalg.lstsq(X, y, rcond=None)[0]
        yhat = a + b*t
        R2 = r2_score(y, yhat)
        rmse = float(np.sqrt(np.mean((y - yhat)**2)))
        score = (R2, -rmse)
        if (best is None) or (score > best):
            best, out = score, dict(theta=float(th), a=a, b=b, R2=R2, rmse=rmse)
    return out

def sweep_c3(M=256, theta=np.pi, c1=0.0, c2=0.0, c3_range=None, skip=5, N=40):
    """Sweep c3 values to find optimal third harmonic."""
    if c3_range is None:
        c3_range = np.linspace(-0.03, 0.03, 31)
    best=None; out=None
    for c3 in c3_range:
        L = build_operator(M, theta=theta, c1=c1, c2=c2, c3=c3)
        lam = spectrum(L, k=max(N+20, 200))
        y   = np.sqrt(unique_eigs(lam))[skip:][:N]
        t   = RIEMANN_T[:N]
        # use LS (global) for comparison
        X = np.vstack([np.ones(N), t]).T
        a,b = np.linalg.lstsq(X, y, rcond=None)[0]
        yhat = a + b*t
        R2 = r2_score(y, yhat)
        rmse = float(np.sqrt(np.mean((y - yhat)**2)))
        score = (R2, -rmse)
        if (best is None) or (score > best):
            best, out = score, dict(c3=float(c3), a=a, b=b, R2=R2, rmse=rmse)
    return out

def sweep_all_params(M=256, skip=5, N=40):
    """Combined sweep over theta and c3 for best operator."""
    best = None; best_info = None
    
    # First, find best theta without c3
    print("  Step 1: Finding best theta (c3=0)...")
    best_theta = sweep_theta(M=M, c1=0.0, c2=0.0, c3=0.0, skip=skip, N=N)
    theta_opt = best_theta['theta']
    best = best_theta['R2']
    
    # Then optimize c3 with best theta
    print(f"  Step 2: Finding best c3 (theta={theta_opt:.6f})...")
    best_c3 = sweep_c3(M=M, theta=theta_opt, c1=0.0, c2=0.0, skip=skip, N=N)
    
    return dict(theta=theta_opt, c3=best_c3['c3'], 
                a=best_c3['a'], b=best_c3['b'], R2=best_c3['R2'], rmse=best_c3['rmse'])

# -------- Stage 1: Two-θ band merge --------
def merged_theta_fit(theta1, theta2, skip=5, N=40, M=256, c1=0.0, c2=0.0, c3=0.0):
    """Merge spectra from two theta values and fit."""
    L1 = build_operator(M, theta1, c1=c1, c2=c2, c3=c3)
    L2 = build_operator(M, theta2, c1=c1, c2=c2, c3=c3)
    lam1 = spectrum(L1, k=200)
    lam2 = spectrum(L2, k=200)
    lam = np.concatenate([lam1, lam2])
    lam = np.sort(lam[lam > 1e-12])
    lam = unique_eigs(lam, tol=1e-8)  # collapse near-duplicates
    y = np.sqrt(lam)[skip:][:N]
    t = RIEMANN_T[:N]
    X = np.vstack([np.ones(N), t]).T
    a, b = np.linalg.lstsq(X, y, rcond=None)[0]
    yhat = a + b*t
    R2 = r2_score(y, yhat)
    rmse = float(np.sqrt(np.mean((y - yhat)**2)))
    return dict(a=a, b=b, R2=R2, rmse=rmse, y=y, yhat=yhat)

def sweep_two_theta(theta_base, delta_range=None, skip=5, N=40, M=256, c1=0.0, c2=0.0, c3=0.0):
    """Sweep over theta2 = theta_base + delta to find best two-θ merge."""
    if delta_range is None:
        delta_range = np.linspace(0.01, 0.06, 11)  # test delta from 0.01 to 0.06
    best = None; best_info = None
    
    for delta in delta_range:
        theta2 = theta_base + delta
        res = merged_theta_fit(theta_base, theta2, skip=skip, N=N, M=M, 
                               c1=c1, c2=c2, c3=c3)
        score = (res['R2'], -res['rmse'])
        if (best is None) or (score > best):
            best = score
            res['theta1'] = float(theta_base)
            res['theta2'] = float(theta2)
            res['delta'] = float(delta)
            best_info = res
    
    return best_info

# -------- Main experiment --------
def parity_defect_scalar(A):
    """Compute parity defect for scalar operator: || A - P^* A P ||_F / ||A||_F."""
    M = A.shape[0]
    P = np.fliplr(np.eye(M))
    C = A - P.conj().T @ A @ P
    return float(np.linalg.norm(C, ord='fro')) / max(1.0, float(np.linalg.norm(A, ord='fro')))

def parity_defect_torus(A, M_tau, M_sigma):
    """Compute parity defect for torus operator: || A - (P_tau⊗I_sigma)^* A (P_tau⊗I_sigma) ||_F / ||A||_F."""
    P_tau = np.fliplr(np.eye(M_tau))
    P = np.kron(P_tau, np.eye(M_sigma))
    C = A - P.conj().T @ A @ P
    return float(np.linalg.norm(C, ord='fro')) / max(1.0, float(np.linalg.norm(A, ord='fro')))

if __name__ == "__main__":
    # Config (tweak here)
    M      = 256
    # Bloch / Floquet phase (θ); π enforces the half-turn symmetry
    theta  = np.pi       # antiperiodic
    c1,c2  = 0.0, 0.0    # uniform chi best from your sweep
    skip   = 5           # skip early doublets
    N      = 40          # number of modes to fit
    i,j    = 10, 30      # two anchors inside the block (0-based)
    
    # --- MODE TOGGLE ------------------------------------------------------------
    PURE_THEORY_SYM = True   # <= set True to fit at θ = π and enforce τ-parity

    # Optional physical anchors (indices relative to the same block)
    use_physical = False
    # example masses in GeV (replace with your choices)
    p,q = 5, 25
    mp, mq = 0.10566, 91.1876
    
    # Initialize symmetry defect variables
    sym_def_scalar = None
    sym_def_torus = None

    # Full parameter sweep (Stage 0): theta and c3
    print("\n" + "="*60)
    print("STAGE 0: Fine-tuning operator parameters")
    print("="*60)
    
    if PURE_THEORY_SYM:
        # Lock Bloch to θ = π (antiperiodic) for the *fit itself*
        theta_opt = np.pi
        # keep c3=0 for now (you can still sweep c3 if you like)
        c3_opt = 0.0
        # build and evaluate at θ=π
        L0 = build_operator(M, theta=theta_opt, c1=0.0, c2=0.0, c3=c3_opt, bloch_theta=np.pi)
        lam0 = spectrum(L0, k=max(N+20, 200))
        y0   = np.sqrt(unique_eigs(lam0))[skip:][:N]
        t0   = RIEMANN_T[:N]
        X    = np.vstack([np.ones(N), t0]).T
        a0,b0 = np.linalg.lstsq(X, y0, rcond=None)[0]
        yhat0 = a0 + b0*t0
        R2_0  = r2_score(y0, yhat0)
        rmse0 = float(np.sqrt(np.mean((y0 - yhat0)**2)))
        best_params = dict(theta=float(theta_opt), c3=float(c3_opt), a=a0, b=b0, R2=R2_0, rmse=rmse0)
        print("\n[Symmetric mode] Stage 0 locked at θ=π")
        print(f"  R²={R2_0:.6f}, RMSE={rmse0:.6f}")
    else:
        best_params = sweep_all_params(M=M, skip=skip, N=N)
        print(f"\nBest parameters (LS fit):")
        print(f"  theta={best_params['theta']:.6f}")
        print(f"  c3={best_params['c3']:.6f}")
        print(f"  R²={best_params['R2']:.6f}")
        print(f"  RMSE={best_params['rmse']:.6f}")
        theta_opt = best_params['theta']
        c3_opt = best_params['c3']
    
    # Stage 1: Two-θ band merge
    print("\n" + "="*60)
    print("STAGE 1: Two-θ band merge (vectorization)")
    print("="*60)
    
    if PURE_THEORY_SYM:
        print("Symmetric mode: skipping two-θ merge (θ fixed at π).")
        best_merge = dict(theta1=theta_opt, theta2=theta_opt, delta=0.0,
                          R2=best_params['R2'], rmse=best_params['rmse'],
                          y=None, yhat=None)
        use_merged = False
        # use the θ=π scalar spectrum as y_opt
        L_opt = build_operator(M, theta=theta_opt, c1=0.0, c2=0.0, c3=c3_opt, bloch_theta=np.pi)
        lam_opt = spectrum(L_opt, k=max(4*N, 200))
        y_opt   = np.sqrt(unique_eigs(lam_opt))[skip:][:N]
        t_opt   = RIEMANN_T[:N]
    else:
        print(f"Base theta: {theta_opt:.6f}")
        best_merge = sweep_two_theta(theta_base=theta_opt, skip=skip, N=N, M=M,
                                      c1=0.0, c2=0.0, c3=0.0)
        print(f"\nBest two-θ merge:")
        print(f"  theta1={best_merge['theta1']:.6f}, theta2={best_merge['theta2']:.6f}")
        print(f"  delta={best_merge['delta']:.6f}")
        print(f"  R²={best_merge['R2']:.6f}, RMSE={best_merge['rmse']:.6f}")
        
        # Compare with single-θ Stage 0 result
        print(f"\nComparison:")
        print(f"  Stage 0 (single θ): R²={best_params['R2']:.6f}, RMSE={best_params['rmse']:.6f}")
        print(f"  Stage 1 (merged θ): R²={best_merge['R2']:.6f}, RMSE={best_merge['rmse']:.6f}")
        
        # Decide which is better
        if best_merge['R2'] > best_params['R2']:
            print(f"\n✓ Stage 1 improves fit by ΔR²={best_merge['R2'] - best_params['R2']:.6f}")
            # Use merged spectrum
            y_opt = best_merge['y']
            t_opt = RIEMANN_T[:N]
            use_merged = True
        else:
            print(f"\nStage 0 is better. Using single-θ spectrum.")
            # Use single-θ spectrum
            print(f"\nRebuilding operator with single-θ parameters...")
            L_opt = build_operator(M, theta=theta_opt, c1=0.0, c2=0.0, c3=c3_opt,
                                  bloch_theta=(np.pi if PURE_THEORY_SYM else None))
            
            lam_opt = spectrum(L_opt, k=max(4*N, 200))
            lam_u_opt = unique_eigs(lam_opt)
            y_all_opt = np.sqrt(lam_u_opt)
            y_opt = y_all_opt[skip:][:N]
            t_opt = RIEMANN_T[:N]
            use_merged = False
    
    # Stage 2: Spinor HP operator with tiny couplings
    print("\n" + "="*60)
    print("STAGE 2: Spinor HP operator (tiny couplings)")
    print("="*60)
    best_spinor = sweep_spinor_params(theta=theta_opt, skip=skip, N=N, M=M, c1=0.0, c2=0.0)
    print(f"\nBest spinor parameters:")
    print(f"  m1={best_spinor['m1']:.6f}, g1={best_spinor['g1']:.6f}")
    print(f"  R²={best_spinor['R2']:.6f}, RMSE={best_spinor['rmse']:.6f}")
    
    # Compare Stage 0/1 with Stage 2
    stage01_R2 = best_params['R2']
    print(f"\nComparison:")
    print(f"  Stage 0/1 (scalar): R²={stage01_R2:.6f}, RMSE={best_params['rmse']:.6f}")
    print(f"  Stage 2 (spinor): R²={best_spinor['R2']:.6f}, RMSE={best_spinor['rmse']:.6f}")
    
    # Determine which previous stage's R2 to use for comparison
    use_spinor = False  # Initialize
    use_merged = False  # Initialize
    if best_spinor['R2'] > stage01_R2:
        print(f"\n✓ Stage 2 improves fit by ΔR²={best_spinor['R2'] - stage01_R2:.6f}")
        stage_prev_R2 = best_spinor['R2']
        use_spinor_temp = True
    else:
        print(f"\nScalar spectrum is better.")
        use_spinor_temp = False
        stage_prev_R2 = stage01_R2
    
    # Stage 3: 2D Torus operator
    print("\n" + "="*60)
    print("STAGE 3: 2D Torus operator (Kronecker sum)")
    print("="*60)
    # Use smaller dimensions for speed: 128x8 = 1024 eigenvalues
    M_tau_stage3 = 128
    M_sigma = 8
    best_torus = sweep_torus_params(theta_tau=theta_opt, skip=skip, N=N, M_tau=M_tau_stage3, M_sigma=M_sigma)
    print(f"\nBest 2D torus parameters:")
    print(f"  eps={best_torus['eps']:.6f}, theta_sigma={best_torus['theta_sigma']:.6f}")
    print(f"  R²={best_torus['R2']:.6f}, RMSE={best_torus['rmse']:.6f}")
    
    # Compare previous stages with Stage 3
    print(f"\nComparison:")
    print(f"  Previous best (Stage 0-2): R²={stage_prev_R2:.6f}")
    print(f"  Stage 3 (2D torus): R²={best_torus['R2']:.6f}, RMSE={best_torus['rmse']:.6f}")
    
    if best_torus['R2'] > stage_prev_R2:
        print(f"\n✓ Stage 3 improves fit by ΔR²={best_torus['R2'] - stage_prev_R2:.6f}")
        # Build final 2D torus spectrum
        print(f"\nBuilding final 2D torus spectrum...")
        y_torus = torus_fit(theta_opt, best_torus['theta_sigma'], best_torus['eps'],
                            M_tau=M_tau_stage3, M_sigma=M_sigma, skip=skip, N=N)
        # Rebuild to get the actual y values for the fit
        Ltau = build_operator(M_tau_stage3, theta=theta_opt, c1=0.0, c2=0.0,
                              c3=0.0, bloch_theta=(np.pi if PURE_THEORY_SYM else None))
        Lsig = build_operator_sigma(M_sigma, theta_s=best_torus['theta_sigma'])
        L = np.kron(Ltau, np.eye(M_sigma)) + best_torus['eps']*np.kron(np.eye(M_tau_stage3), Lsig)
        
        # Check symmetry at θ=π on τ leg (diagnostic only)
        Ltau_sym = build_operator(M_tau_stage3, theta=theta_opt, c1=0.0, c2=0.0, bloch_theta=np.pi)
        Lsig_sym = build_operator_sigma(M_sigma, theta_s=0.0) # FIXED: changed theta_sigma to theta_s
        L_torus_sym = np.kron(Ltau_sym, np.eye(M_sigma)) + best_torus['eps'] * np.kron(np.eye(M_tau_stage3), Lsig_sym)
        sym_def_torus = parity_defect_torus(L_torus_sym, M_tau_stage3, M_sigma)
        print(f"Symmetry defect (torus, θ=π on τ): {sym_def_torus:.3e}")
        
        evals, _ = np.linalg.eigh(L)
        lam = np.sort(evals.real)
        lam = lam[lam>1e-12]
        lam = unique_eigs(lam, tol=1e-8)
        y_torus_actual = np.sqrt(lam)[skip:][:N]
        y_opt = y_torus_actual
        t_opt = RIEMANN_T[:N]
        use_torus = True
        use_spinor = False  # Using torus, not spinor
    else:
        print(f"\nPrevious spectrum is better.")
        # Build the spectrum from the previous best stage
        if use_spinor_temp and best_spinor['R2'] > stage01_R2:
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
            L_opt = build_operator(M, theta=theta_opt, c1=0.0, c2=0.0, c3=c3_opt,
                                  bloch_theta=(np.pi if PURE_THEORY_SYM else None))
            lam_opt = spectrum(L_opt, k=max(4*N, 200))
            lam_u_opt = unique_eigs(lam_opt)
            y_all_opt = np.sqrt(lam_u_opt)
            y_opt = y_all_opt[skip:][:N]
            t_opt = RIEMANN_T[:N]
        use_torus = False
        use_spinor = False  # Ensure it's set

    # Symmetry diagnostics at θ=π (on τ only)
    print("\n" + "="*60)
    print("Symmetry diagnostics at θ=π")
    print("="*60)
    L_sym_scalar = build_operator(M, theta=theta_opt, c1=0.0, c2=0.0, c3=c3_opt, bloch_theta=np.pi)
    sym_scalar = parity_defect_scalar(L_sym_scalar)
    print(f"  Scalar parity defect: {sym_scalar:.3e}")
    
    if 'use_torus' in locals() and use_torus:
        Ltau_sym = build_operator(M_tau_stage3, theta=theta_opt, c1=0.0, c2=0.0, c3=0.0, bloch_theta=np.pi)
        Lsig_sym = build_operator_sigma(M_sigma, theta_s=best_torus['theta_sigma'])
        L_torus_sym = np.kron(Ltau_sym, np.eye(M_sigma)) + best_torus['eps'] * np.kron(np.eye(M_tau_stage3), Lsig_sym)
        sym_torus = parity_defect_torus(L_torus_sym, M_tau_stage3, M_sigma)
        print(f"  Torus parity defect:  {sym_torus:.3e}")
    else:
        sym_torus = None

    # Two-point fit for a,b with optimized spectrum
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

    # Mini report
    print("\nFirst 12 (aligned block): sqrt(lambda_n)  vs  a + b t_n  (Δ)")
    for k in range(min(12, N)):
        print(f"{k+1:2d}: {y_opt[k]:10.6f}   {yhat2[k]:10.6f}   Δ={y_opt[k]-yhat2[k]:+.6f}")


    # Optional: physical dressing from two masses
    if use_physical:
        delta, gamma = two_point_delta_gamma(t_opt, a2, b2, mp, mq, p, q)
        m_pred = delta + gamma*(a2 + b2*t_opt)
        print(f"\nPhysical dressing from two masses (p={p}, q={q}):")
        print(f"  delta={delta:.6e} GeV,  gamma={gamma:.6e}")
        print("  First 10 predicted masses (GeV):")
        for k in range(min(10, N)):
            print(f"  n={k+1:2d}: {m_pred[k]:.6e}")

    # Save plots
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

    # Export a small JSON summary
    summary = dict(
        M=M,
        mode='symmetric' if PURE_THEORY_SYM else 'empirical',
        stage0=dict(theta=float(theta_opt), c3=float(c3_opt), R2=best_params['R2'], rmse=best_params['rmse']),
        stage1=dict(theta1=best_merge['theta1'], theta2=best_merge['theta2'], 
                    delta=best_merge['delta'], R2=best_merge['R2'], rmse=best_merge['rmse'],
                    improved=use_merged),
        stage2=dict(m1=best_spinor['m1'], g1=best_spinor['g1'], 
                    R2=best_spinor['R2'], rmse=best_spinor['rmse'],
                    improved=use_spinor),
        stage3=dict(eps=best_torus['eps'], theta_sigma=best_torus['theta_sigma'],
                    R2=best_torus['R2'], rmse=best_torus['rmse'],
                    improved=use_torus),
        skip=skip, N=N, anchors=[i,j],
        a=float(a2), b=float(b2), R2=float(R2_2),
        symmetry=dict(
            theta_check=float(np.pi),
            parity_scalar=float(sym_scalar),
            parity_torus=float(sym_torus) if sym_torus is not None else None
        )
    )
    with open("hp_two_point_summary_Theory.json","w") as f:
        json.dump(summary, f, indent=2)
    print("Saved: hp_two_point_summary_Theory.json")
