# chi_vortex_static.py
import numpy as np
import matplotlib.pyplot as plt

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

def periodic_D1(M, dt):
    D1 = np.zeros((M, M), dtype=complex)
    for i in range(M):
        D1[i, (i+1)%M] =  0.5/dt
        D1[i, (i-1)%M] = -0.5/dt
    return D1

def build_operator(M=256, theta=np.pi, c1=0.2, c2=-0.1, u0=0.0, u1=0.1, u2=-0.05):
    tau = np.linspace(0, 2*np.pi, M, endpoint=False)
    dt = tau[1] - tau[0]
    kappa = theta/(2*np.pi)
    chi = 1.0 + c1*np.cos(tau) + c2*np.cos(2*tau)
    chi = np.maximum(chi, 1e-6)
    U = u0 + u1*np.cos(tau) + u2*np.cos(2*tau)

    D1 = periodic_D1(M, dt)
    I  = np.eye(M, dtype=complex)
    Dk = D1 + 1j*kappa*I

    Chi    = np.diag(chi.astype(complex))
    ChiInv = np.diag((1.0/chi).astype(complex))
    Umat   = np.diag(U.astype(complex))

    L = - ChiInv @ (Dk @ (Chi @ Dk)) + ChiInv @ Umat
    L = 0.5*(L + L.conj().T)   # hermitize tiny FD asymmetries
    return L, tau, chi, U

def spectrum(L, k=60):
    evals, _ = np.linalg.eigh(L)
    lam = evals.real
    lam = lam[lam > 1e-10]
    lam.sort()
    return lam[:k]

def affine_fit(y, t):
    N = min(len(y), len(t))
    y = y[:N]
    X = np.vstack([np.ones(N), t[:N]]).T
    a, b = np.linalg.lstsq(X, y, rcond=None)[0]
    yhat = a + b*t[:N]
    ss_res = np.sum((y - yhat)**2)
    ss_tot = np.sum((y - y.mean())**2)
    R2 = 1 - ss_res/ss_tot if ss_tot > 0 else np.nan
    return a, b, R2, y, yhat

def unique_eigs(vals, tol=1e-6):
    """Remove degenerate eigenvalues within tolerance"""
    out = []
    for v in np.sort(vals[vals > 1e-12]):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return np.array(out)

def affine_fit_block(lam, t, transform='sqrt', skip=2, N=None):
    """Fit sqrt(lambda) vs t_n, skipping early doublets"""
    lam_u = unique_eigs(lam)
    yraw = np.sqrt(lam_u) if transform == 'sqrt' else lam_u
    y = yraw[skip:]
    N = min(len(y), len(t)) if N is None else min(N, len(t), len(y))
    y = y[:N]
    tt = t[:N]
    X = np.vstack([np.ones(N), tt]).T
    a, b = np.linalg.lstsq(X, y, rcond=None)[0]
    yhat = a + b*tt
    ss_res = np.sum((y - yhat)**2)
    ss_tot = np.sum((y - y.mean())**2)
    R2 = 1 - ss_res/ss_tot if ss_tot > 0 else np.nan
    return a, b, R2, y, yhat

def dressed_map(y_core, t, a, b, delta=0.0, gamma=1.0):
    """
    Map core spectrum to physical via: phys ≈ delta + gamma*(a + b t)
    delta ~ Higgs-scale additive shift; gamma ~ Planck-scale normalization.
    """
    return delta + gamma*(a + b*t)

def analyze_higgs_effect():
    """Compare spectrum with and without Higgs potential"""
    theta = np.pi
    c1, c2 = 0.20, -0.10
    
    # Without potential
    L_no_U, _, _, _ = build_operator(256, theta, c1, c2, 0, 0, 0)
    lam_no_U = spectrum(L_no_U, k=60)
    _, _, R2_no_U, _, _ = affine_fit(lam_no_U, RIEMANN_T)
    
    # With potential  
    L_with_U, _, _, _ = build_operator(256, theta, c1, c2, 0.00, 0.10, -0.05)
    lam_with_U = spectrum(L_with_U, k=60)
    _, _, R2_with_U, _, _ = affine_fit(lam_with_U, RIEMANN_T)
    
    print("\n" + "="*60)
    print("HIGGS EFFECT ANALYSIS")
    print("="*60)
    print(f"\nR² without U: {R2_no_U:.6f}")
    print(f"R² with U:    {R2_with_U:.6f}")
    print(f"\nDifference:    {R2_with_U - R2_no_U:.6f}")
    print("\nEigenvalue shifts (first 10):")
    print("  n | λ(U=0)   | λ(U≠0)   | Shift")
    print("-" * 40)
    for i in range(min(10, len(lam_no_U), len(lam_with_U))):
        shift = lam_with_U[i] - lam_no_U[i]
        print(f" {i+1:2d} | {lam_no_U[i]:8.4f} | {lam_with_U[i]:8.4f} | {shift:+.4f}")
    
    return lam_no_U, lam_with_U

def parameter_sweep():
    """Find optimal U parameters to minimize residuals vs Riemann zeros"""
    theta = np.pi
    c1, c2 = 0.20, -0.10
    best_R2 = -np.inf
    best_params = None
    best_y = None
    best_yhat = None
    
    print("Sweeping potential parameters...")
    for u0 in np.linspace(-0.1, 0.1, 11):
        for u1 in np.linspace(-0.1, 0.1, 11):
            for u2 in np.linspace(-0.1, 0.1, 11):
                try:
                    L, tau, chi, U = build_operator(256, theta, c1, c2, u0, u1, u2)
                    lam = spectrum(L, k=60)
                    a, b, R2, y, yhat = affine_fit(lam, RIEMANN_T)
                    if R2 > best_R2:
                        best_R2 = R2
                        best_params = (u0, u1, u2)
                        best_y = y
                        best_yhat = yhat
                except:
                    continue
    
    return best_params, best_R2, best_y, best_yhat

if __name__ == "__main__":
    print("=" * 70)
    print("SURGICAL HP FIT: Skip early doublets, lock U=0 core, dress at mapping")
    print("=" * 70)
    
    theta = np.pi
    c1, c2 = 0.20, -0.10
    
    # 1) Core HP fit (massless): U=0, get more modes
    print("\n[1] Building HP operator with U=0 (massless limit)...")
    L, tau, chi, U = build_operator(256, theta, c1, c2, u0=0.0, u1=0.0, u2=0.0)
    lam = spectrum(L, k=120)
    
    # 2) Better alignment: sqrt transform, skip doublets
    print("[2] Fitting sqrt(lambda) vs t_n, skipping first 2 doublets...")
    a, b, R2, y, yhat = affine_fit_block(lam, RIEMANN_T, transform='sqrt', skip=2, N=40)
    
    print(f"\nHP CORE FIT: a={a:.6f}, b={b:.6f}, R^2={R2:.4f}")
    print(f"Transform: sqrt(lambda), Skip first 2 doublets")
    print(f"Using {len(y)} modes (skipped 2 early modes)")
    
    # Show first 20 with residuals
    print("\nFirst 20: sqrt(lambda_n) vs a + b*t_n")
    print("  n | sqrt(lam) | fitted   | residual")
    print("-" * 50)
    for i in range(min(20, len(y))):
        print(f" {i+1:2d} | {y[i]:8.4f} | {yhat[i]:8.4f} | {y[i]-yhat[i]:+.4f}")
    
    # 3) Optional: Higgs/Planck dressing at mapping stage
    print("\n" + "="*70)
    print("OPTIONAL: Higgs/Planck dressing at mapping stage")
    print("="*70)
    
    vH = 246.0        # GeV
    MPl = 1.22e19     # GeV  
    alpha = 1.0       # try 0..2
    delta = 0.0       # additive shift
    gamma = (vH/MPl)**alpha
    
    print(f"\nHiggs scale: vH = {vH:.2e} GeV")
    print(f"Planck scale: MPl = {MPl:.2e} GeV")
    print(f"Dressing: gamma = (vH/MPl)^{alpha} = {gamma:.6e}")
    print(f"Additive shift: delta = {delta:.2f} GeV")
    
    # Map to physical scale
    t_sub = RIEMANN_T[:len(y)]
    yhat_phys = dressed_map(y, t_sub, a, b, delta=delta, gamma=gamma)
    
    print("\nFirst 10: Core vs Physical mapping")
    print("  n | core   | physical | t_n")
    print("-" * 50)
    for i in range(min(10, len(y))):
        print(f" {i+1:2d} | {y[i]:7.4f} | {yhat_phys[i]:8.4f} | {t_sub[i]:7.2f}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY:")
    print("="*70)
    print("[OK] HP core locked at U=0 (conformal limit)")
    print("[OK] Skip early doublets for clean fit")
    print("[OK] Higgs/Planck dressing applied at mapping, not in operator")
    print("[OK] Separation: L remains clean; physics enters via gamma & delta")
    
    # Save plots
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    plt.plot(y, 'o-', label='sqrt(lambda)', markersize=4)
    plt.plot(yhat, 's-', label='a + b*t_n', markersize=4)
    plt.xlabel('mode index (after skipping)')
    plt.ylabel('sqrt(eigenvalue)')
    plt.title(f'HP Core Fit (R^2={R2:.4f})')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.subplot(2, 1, 2)
    plt.plot(y - yhat)
    plt.xlabel('mode index')
    plt.ylabel('residual')
    plt.title('Residuals')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('hp_core_fit.png', dpi=160)
    print("\nSaved: hp_core_fit.png")
