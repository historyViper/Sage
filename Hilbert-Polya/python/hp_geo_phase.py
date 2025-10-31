# hp_geo_phase.py
# Geometry-first Hilbert–Pólya toy: Pascal couplings + geometric phases only.
# No ad-hoc diagonal bowls/peaks. Saves PNGs; prints stats. No CSVs.

import numpy as np
import matplotlib.pyplot as plt
from scipy.special import comb

# ---- First 30 (or 100) Riemann zeros (imag parts). Use 30 for fast iteration.
RIEMANN = np.array([
    14.134725141734693, 21.022039638771555, 25.010857580145689, 30.424876125859513,
    32.935061587739190, 37.586178158825671, 40.918719012147495, 43.327073280914999,
    48.005150881167160, 49.773832477672302, 52.970321477714461, 56.446247697063395,
    59.347044002602353, 60.831778524609810, 65.112544048081607, 67.079810529494174,
    69.546401711173979, 72.067157674481908, 75.704690699083933, 77.144840068874805,
    79.337375020249368, 82.910380854086030, 84.735492980517050, 87.425274613125229,
    88.809111207634465, 92.491899270558484, 94.651344040519887, 95.870634228245310,
    98.831194218193692, 101.317851005731391
])

# ----- Helpers -----
def primes_up_to(n=200):
    sieve = np.ones(n+1, dtype=bool); sieve[:2] = False
    for p in range(2, int(n**0.5)+1):
        if sieve[p]:
            sieve[p*p::p] = False
    return np.nonzero(sieve)[0].tolist()

PRIMES = primes_up_to(200)
NPR = len(PRIMES)

def pascal_amp(d):
    return 1.0 if d == 1 else np.sqrt(comb(d, d//2, exact=True)) / (2.0**d)

# Optional mild edge amplitude taper (OFF by default)
def edge_taper_vec(N, eps=0.0, sigma=6.0):
    i = np.arange(N, dtype=float)
    return 1 - eps*(np.exp(-(i/sigma)**2) + np.exp(-((N-1-i)/sigma)**2))

# ----- Phase kernels (GEOMETRIC ONLY) -----
def phase_circle(i, j, d, n_quant=25.0):
    # φ = (2π/n)*d (constant per hop)
    return (2*np.pi/n_quant) * d

def phase_prime_sum(i, j, d):
    # φ ∝ d * (idx_i + idx_j)
    pi = (i % NPR); pj = (j % NPR)
    return np.pi * d * (pi + pj) / (2.0 * NPR)

def phase_prime_single(i, j, d):
    # φ ∝ d * idx_i
    pi = (i % NPR)
    return np.pi * d * pi / NPR

def phase_log(i, j, d, N, beta=1.0):
    # LOG-SCALED PHASE: φ ∝ d * log(1 + (i+j)/2) / log(N)
    avg = 0.5*(i + j)
    return beta * d * np.log(1.0 + avg) / np.log(N)

def phase_log_inverted(i, j, d, N, beta=1.0):
    # INVERTED LOG: Creates M-shape (concave-down)
    avg = 0.5*(i + j)
    return -beta * d * np.log(1.0 + avg) / np.log(N)

def phase_reciprocal(i, j, d, N, beta=1.0):
    # RECIPROCAL: 1/log naturally bends down
    avg = 0.5*(i + j)
    return beta * d / np.log(2.0 + avg)  # +2 to avoid log(1)=0

def phase_hybrid(i, j, d, N, n_quant=25.0, beta=1.0):
    # HYBRID: circle quantization modulated by log curvature
    return (2*np.pi/n_quant) * d * (1.0 + beta * np.log(1.0 + 0.5*(i+j)) / np.log(N))

def phase_hybrid_inverted(i, j, d, N, n_quant=25.0, beta=1.0):
    # INVERTED HYBRID: Creates M-shape
    return (2*np.pi/n_quant) * d * (1.0 - beta * np.log(1.0 + 0.5*(i+j)) / np.log(N))

def phase_hybrid_blend(i, j, d, N, n_quant=25.0, beta=1.0, gamma=0.8):
    # BLENDED: Smooth inversion with reciprocal term
    avg = 0.5*(i + j)
    return (2*np.pi/n_quant) * d * (1.0 - beta * np.log(1.0 + avg) / np.log(N) 
                                    + gamma / (1.0 + avg))

# NEW: Position-dependent amplitude modulation
def amplitude_modulation(i, j, N, alpha=0.0):
    """Modulate Pascal amplitude by position to create curvature"""
    if alpha == 0.0:
        return 1.0
    avg = 0.5 * (i + j)
    # Amplitude decreases with position → upper states bunch together
    return 1.0 / (1.0 + alpha * avg / N)

# ----- Build operator with a chosen phase kernel -----
def build_operator(N, max_distance, phase_fn, phase_kwargs=None, taper_eps=0.0, amp_alpha=0.0):
    if phase_kwargs is None: phase_kwargs = {}
    H = np.zeros((N, N), dtype=complex)
    taper = edge_taper_vec(N, eps=taper_eps, sigma=6.0)

    for i in range(N):
        jmin, jmax = max(0, i-max_distance), min(N, i+max_distance+1)
        for j in range(jmin, jmax):
            if i == j: continue
            d = abs(j - i)
            if d == 0 or d > max_distance: continue
            amp = pascal_amp(d)
            
            # Apply position-dependent amplitude modulation
            if amp_alpha != 0.0:
                amp *= amplitude_modulation(i, j, N, amp_alpha)
            
            phi = phase_fn(i, j, d, N=N, **phase_kwargs) if 'N' in phase_fn.__code__.co_varnames else phase_fn(i, j, d, **phase_kwargs)
            hop = -amp * (np.exp(1j*phi) if j > i else np.exp(-1j*phi))
            hop *= np.sqrt(taper[i]*taper[j])
            H[i, j] = hop
    return H

# ----- Fit & metrics -----
def affine_fit(model_vals, target):
    X = np.vstack([model_vals, np.ones_like(model_vals)]).T
    a, b = np.linalg.lstsq(X, target, rcond=None)[0]
    aligned = a*model_vals + b
    return a, b, aligned

def stats(evals, zeros):
    ev = np.sort(evals)[:len(zeros)]
    a, b, aligned = affine_fit(ev, zeros)
    res = aligned - zeros
    idx = np.arange(len(res))
    quad = np.polyfit(idx, res, 2)
    rmse = float(np.sqrt(np.mean(res**2)))
    mape = float(np.mean(np.abs(res)/zeros)*100.0)
    sp_m = np.diff(aligned); sp_m /= np.mean(sp_m)
    sp_t = np.diff(zeros);   sp_t /= np.mean(sp_t)
    corr = float(np.corrcoef(sp_m, sp_t)[0,1])
    hi = np.percentile(np.r_[sp_m, sp_t], 99)
    h1, edges = np.histogram(sp_m, bins=30, range=(0,hi), density=True)
    h2, _     = np.histogram(sp_t, bins=edges, density=True)
    F1, F2 = np.cumsum(h1), np.cumsum(h2)
    if F1[-1] != 0: F1 /= F1[-1]
    if F2[-1] != 0: F2 /= F2[-1]
    ks = float(np.max(np.abs(F1 - F2)))
    return dict(a=a,b=b,aligned=aligned,res=res,quad=quad,rmse=rmse,mape=mape,corr=corr,ks=ks)

def plots(tag, info, zeros):
    aligned, res, quad = info['aligned'], info['res'], info['quad']
    x = np.arange(len(aligned))

    # 1) alignment
    plt.figure(figsize=(9,4))
    plt.plot(zeros[:len(aligned)], 'ro-', label='Riemann', ms=4)
    plt.plot(aligned, 'bo-', label='Model', ms=3, alpha=0.8)
    plt.grid(alpha=0.3); plt.legend()
    plt.title(f'{tag} | MAPE={info["mape"]:.2f}%, RMSE={info["rmse"]:.2f}')
    plt.tight_layout(); plt.savefig(f'{tag}_alignment.png', dpi=140)

    # 2) residuals + quad fit
    plt.figure(figsize=(9,4))
    plt.plot(res, 'g.-', label='Residual')
    plt.plot(np.polyval(quad, x), 'k--', label=f'Quad a={quad[0]:.4f}')
    plt.axhline(0, color='k', lw=1)
    plt.grid(alpha=0.3); plt.legend()
    plt.title(f'{tag} residuals (corr={info["corr"]:.3f}, KS={info["ks"]:.3f})')
    plt.tight_layout(); plt.savefig(f'{tag}_residuals.png', dpi=140)

    # 3) spacing hist vs Wigner-GUE
    plt.figure(figsize=(6,4))
    s = np.linspace(0,3,200)
    gue = (np.pi/2)*s*np.exp(-np.pi*s**2/4)
    plt.hist(info['sp_m'] if 'sp_m' in info else np.diff(aligned)/np.mean(np.diff(aligned)),
             bins=25, density=True, alpha=0.6, label='Model')
    sp_t = np.diff(zeros[:len(aligned)])
    sp_t /= np.mean(sp_t)
    plt.hist(sp_t, bins=25, density=True, alpha=0.6, label='Riemann')
    plt.plot(s, gue, 'k-', lw=2, label='GUE')
    plt.grid(alpha=0.3); plt.legend()
    plt.title(f'{tag} spacings')
    plt.tight_layout(); plt.savefig(f'{tag}_spacing.png', dpi=140)

def run_all():
    N = 160
    take = 30
    zeros = RIEMANN[:take]
    dmax = 5
    taper_eps = 0.00  # edge taper OFF by default; set 0.04 for tiny corner cleanup

    configs = [
        # Baseline (W-shape, wrong curvature)
        ("circle_n25",           phase_circle,      dict(n_quant=25.0), 0.0),
        ("prime_sum",            phase_prime_sum,   dict(),             0.0),
        
        # AMPLITUDE MODULATION (geometric curvature control!)
        ("circle_amp0.3",        phase_circle,      dict(n_quant=25.0), 0.3),
        ("circle_amp0.5",        phase_circle,      dict(n_quant=25.0), 0.5),
        ("circle_amp0.7",        phase_circle,      dict(n_quant=25.0), 0.7),
        ("circle_amp1.0",        phase_circle,      dict(n_quant=25.0), 1.0),
        
        ("prime_amp0.3",         phase_prime_sum,   dict(),             0.3),
        ("prime_amp0.5",         phase_prime_sum,   dict(),             0.5),
        ("prime_amp0.7",         phase_prime_sum,   dict(),             0.7),
        ("prime_amp1.0",         phase_prime_sum,   dict(),             1.0),
    ]

    best = None
    for name, fn, kw, amp_alpha in configs:
        H = build_operator(N, dmax, fn, phase_kwargs=kw, taper_eps=taper_eps, amp_alpha=amp_alpha)
        ev = np.linalg.eigvalsh(H)
        info = stats(ev, zeros)
        print(f"\n[{name}]  MAPE={info['mape']:.2f}%  RMSE={info['rmse']:.2f}  "
              f"quad.a={info['quad'][0]:+.4f}  corr={info['corr']:.3f}  KS={info['ks']:.3f}")
        plots(name, info, zeros)
        key = (info['mape'], abs(info['quad'][0]), info['rmse'])
        if best is None or key < (best['mape'], abs(best['quad'][0]), best['rmse']):
            best = dict(tag=name, **info)

    print("\n=== BEST (geometry-only) ===")
    print(f"tag={best['tag']}, MAPE={best['mape']:.2f}%, RMSE={best['rmse']:.2f}, "
          f"quad.a={best['quad'][0]:+.4f}, corr={best['corr']:.3f}, KS={best['ks']:.3f}")
    print("Saved *_alignment.png, *_residuals.png, *_spacing.png for each model.")

if __name__ == "__main__":
    run_all()
