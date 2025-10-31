# hp_geo_amp_validate.py
import numpy as np
from scipy.special import comb

# ---- Riemann zeros (first 60; extend if Claude has more handy)
RZ = np.array([
  14.134725141734693, 21.022039638771555, 25.010857580145689, 30.424876125859513,
  32.935061587739190, 37.586178158825671, 40.918719012147495, 43.327073280914999,
  48.005150881167160, 49.773832477672302, 52.970321477714461, 56.446247697063395,
  59.347044002602353, 60.831778524609810, 65.112544048081607, 67.079810529494174,
  69.546401711173979, 72.067157674481908, 75.704690699083933, 77.144840068874805,
  79.337375020249368, 82.910380854086030, 84.735492980517050, 87.425274613125229,
  88.809111207634465, 92.491899270558484, 94.651344040519887, 95.870634228245310,
  98.831194218193692, 101.317851005731391,
  103.72553804047834, 105.44662305232609, 107.16861118427641, 111.02953554316967,
  111.87465917699264, 114.32022091545271, 116.22668032085755, 118.79078286597622,
  121.37012500242065, 122.94682929355259, 124.25681855434577, 127.5166838795965,
  129.57870419995606, 131.08768853093266, 133.4977372029976, 134.75650975337387,
  138.11604205453344, 139.7362089521214, 141.12370740402112, 143.11184580762063,
  146.00098248676552, 147.4227653425596, 150.05352042078488, 150.92525761224147,
  153.0246938111989, 156.11290929423787, 157.59759181759406, 158.8499881714205
])

def pascal_amp(d):
    return 1.0 if d == 1 else np.sqrt(comb(d, d//2, exact=True)) / (2.0**d)

def phase_circle(i, j, d, n_quant=25.0):
    return (2*np.pi/n_quant) * d

# Amplitude laws (pure geometry "χ-gradient")
def amp_power(i, j, N, alpha=0.7, p=1.0):
    u = 0.5*(i+j)/N
    return 1.0 / (1.0 + alpha * (u**p))

def amp_log(i, j, N, alpha=0.7):
    u = 0.5*(i+j)
    return 1.0 / (1.0 + alpha * (np.log(2.0+u)/np.log(N)))

def build_H(N=160, dmax=5, n_quant=25.0, amp_mode="power", alpha=0.7, p=1.0):
    H = np.zeros((N, N), dtype=complex)
    for i in range(N):
        jmin, jmax = max(0, i-dmax), min(N, i+dmax+1)
        for j in range(jmin, jmax):
            if i == j: continue
            d = abs(j - i)
            if d == 0 or d > dmax: continue
            a = pascal_amp(d)
            if amp_mode == "power":
                a *= amp_power(i, j, N, alpha=alpha, p=p)
            elif amp_mode == "log":
                a *= amp_log(i, j, N, alpha=alpha)
            phi = phase_circle(i, j, d, n_quant=n_quant)
            hop = -a * (np.exp(1j*phi) if j > i else np.exp(-1j*phi))
            H[i, j] = hop
    return H

def affine_fit(y, t):
    X = np.vstack([y, np.ones_like(y)]).T
    a, b = np.linalg.lstsq(X, t, rcond=None)[0]
    return a, b, a*y + b

def metrics(evals, zeros):
    y = np.sort(evals)[:len(zeros)]
    a,b,aligned = affine_fit(y, zeros)
    res = aligned - zeros
    rmse = float(np.sqrt(np.mean(res**2)))
    mape = float(np.mean(np.abs(res)/zeros)*100.0)
    idx = np.arange(len(res))
    quad = np.polyfit(idx, res, 2)  # quad[0] is curvature sign
    sp_m = np.diff(aligned); sp_m /= np.mean(sp_m)
    sp_t = np.diff(zeros);   sp_t /= np.mean(sp_t)
    corr = float(np.corrcoef(sp_m, sp_t)[0,1])
    # KS on spacing CDFs
    hi = np.percentile(np.r_[sp_m, sp_t], 99)
    h1, edges = np.histogram(sp_m, bins=30, range=(0,hi), density=True)
    h2, _     = np.histogram(sp_t, bins=edges, density=True)
    F1, F2 = np.cumsum(h1), np.cumsum(h2)
    if F1[-1] != 0: F1 /= F1[-1]
    if F2[-1] != 0: F2 /= F2[-1]
    ks = float(np.max(np.abs(F1 - F2)))
    return dict(mape=mape, rmse=rmse, quad_a=quad[0], corr=corr, ks=ks, aligned=aligned)

def run_once(N=160, amp_mode="power", alpha=0.7, p=1.0, n_quant=25.0, dmax=5):
    H = build_H(N=N, dmax=dmax, n_quant=n_quant, amp_mode=amp_mode, alpha=alpha, p=p)
    ev = np.linalg.eigvalsh(H)
    # train on first 30, validate on next 30 (if available)
    take = min(30, len(RZ))
    train = metrics(ev, RZ[:take])
    if len(RZ) >= 60:
        valid = metrics(ev[take:], RZ[take:2*take])  # crude hold-out
    else:
        valid = None
    return train, valid

def main():
    print("PURE GEOMETRY: Pascal couplings + circle phase + amplitude decay")
    best = None
    for amp_mode in ["power", "log"]:
        if amp_mode == "power":
            for alpha in [0.5, 0.7, 1.0]:
                for p in [0.8, 1.0, 1.2, 1.5]:
                    train, valid = run_once(N=160, amp_mode="power", alpha=alpha, p=p)
                    key = (train['mape'], abs(train['quad_a']))
                    print(f"[power α={alpha:.2f}, p={p:.2f}]  "
                          f"train MAPE={train['mape']:.2f}%  RMSE={train['rmse']:.2f}  "
                          f"quad.a={train['quad_a']:+.4f}  corr={train['corr']:.3f}  KS={train['ks']:.3f}")
                    if valid:
                        print(f"   -> valid MAPE={valid['mape']:.2f}%  RMSE={valid['rmse']:.2f}  quad.a={valid['quad_a']:+.4f}")
                    if best is None or key < (best['mape'], abs(best['quad_a'])):
                        best = dict(mode="power", alpha=alpha, p=p, **train)
        else:
            for alpha in [0.4, 0.6, 0.8, 1.0]:
                train, valid = run_once(N=160, amp_mode="log", alpha=alpha)
                key = (train['mape'], abs(train['quad_a']))
                print(f"[log α={alpha:.2f}]  "
                      f"train MAPE={train['mape']:.2f}%  RMSE={train['rmse']:.2f}  "
                      f"quad.a={train['quad_a']:+.4f}  corr={train['corr']:.3f}  KS={train['ks']:.3f}")
                if valid:
                    print(f"   -> valid MAPE={valid['mape']:.2f}%  RMSE={valid['rmse']:.2f}  quad.a={valid['quad_a']:+.4f}")
                if best is None or key < (best['mape'], abs(best['quad_a'])):
                    best = dict(mode="log", alpha=alpha, p=None, **train)

    print("\n=== BEST (train) ===")
    print(best)

    # Scale test: bump N to 220 with best law; see if shape survives
    if best['mode'] == "power":
        train220, valid220 = run_once(N=220, amp_mode="power",
                                      alpha=best['alpha'], p=best['p'])
    else:
        train220, valid220 = run_once(N=220, amp_mode="log",
                                      alpha=best['alpha'])
    print("\n=== N=220 (scale test) ===")
    print("train:", train220)
    if valid220:
        print("valid:", valid220)

if __name__ == "__main__":
    main()
