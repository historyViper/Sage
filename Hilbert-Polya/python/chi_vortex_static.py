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

if __name__ == "__main__":
    theta = np.pi
    c1, c2 = 0.20, -0.10
    u0, u1, u2 = 0.00, 0.10, -0.05

    L, tau, chi, U = build_operator(256, theta, c1, c2, u0, u1, u2)
    lam = spectrum(L, k=60)
    a, b, R2, y, yhat = affine_fit(lam, RIEMANN_T)
    # --- mini report (console) ---
    print("\nFirst 20: model λ_n  vs  a + b t_n  (and residual)")
    for i, (lm, mp) in enumerate(zip(y[:20], yhat[:20]), 1):
        print(f"{i:2d}: {lm:10.6f}   {mp:10.6f}   Δ={lm-mp:+.6f}")
    print("\nResidual stats (fit block):")
    res = y - yhat
    print(f"  mean={res.mean():+.6f},  std={res.std():.6f},  max|Δ|={np.abs(res).max():.6f}")


    print(f"Affine fit: a={a:.6f}, b={b:.6f}, R^2={R2:.4f}")

    # Save plots
    plt.figure(figsize=(6,4)); plt.plot(y, label="Model eigenvalues"); plt.plot(yhat, label="Affine map of ζ zeros")
    plt.title("Eigenvalues vs Affine Map"); plt.xlabel("n"); plt.ylabel("λ / a+b t_n"); plt.legend(); plt.tight_layout()
    plt.savefig("eig_vs_zeros.png", dpi=160)

    plt.figure(figsize=(6,4)); plt.plot(y - yhat)
    plt.title("Residuals"); plt.xlabel("n"); plt.ylabel("Residual"); plt.tight_layout()
    plt.savefig("residuals.png", dpi=160)

    plt.figure(figsize=(6,4)); plt.plot(tau, chi); plt.title("χ(τ)"); plt.xlabel("τ"); plt.ylabel("χ"); plt.tight_layout()
    plt.savefig("chi.png", dpi=160)

    plt.figure(figsize=(6,4)); plt.plot(tau, U); plt.title("U(τ)"); plt.xlabel("τ"); plt.ylabel("U"); plt.tight_layout()
