# hp_vs_riemann_overlay.py
# Overlay: model √λ_n (HP spectrum) vs fitted Riemann line a + b t_n
# Thick neon lines + residuals

import os, json
import numpy as np
import matplotlib.pyplot as plt

# ---------- config ----------
SUMMARY_FILE = "hp_two_point_summary.json"
BACKGROUND   = "black"  # "white" or "black"
SAVE_PLOT    = "hp_vs_riemann_overlay.png"

# Riemann ordinates (first 50)
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

# ---------- helpers ----------
def periodic_D1(M, dt):
    D1 = np.zeros((M, M), dtype=complex)
    for i in range(M):
        D1[i, (i+1) % M] =  0.5 / dt
        D1[i, (i-1) % M] = -0.5 / dt
    return D1

def build_operator(M=256, theta=np.pi, c1=0.0, c2=0.0, c3=0.0):
    tau = np.linspace(0, 2*np.pi, M, endpoint=False)
    dt = tau[1] - tau[0]
    kappa = theta / (2*np.pi)
    # χ(τ) with small harmonics (often best is c1=c2=c3=0)
    chi = 1.0 + c1*np.cos(tau) + c2*np.cos(2*tau) + c3*np.cos(3*tau)
    chi = np.maximum(chi, 1e-6)

    D1 = periodic_D1(M, dt)
    I  = np.eye(M, dtype=complex)
    Dk = D1 + 1j*kappa*I

    Chi = np.diag(chi.astype(complex))
    ChiInv = np.diag((1.0/chi).astype(complex))

    L = - ChiInv @ (Dk @ (Chi @ Dk))
    L = 0.5 * (L + L.conj().T)
    return L

def unique_eigs(vals, tol=1e-8):
    out = []
    for v in np.sort(vals):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return np.array(out)

def r2_score(y, yhat):
    ss_res = np.sum((y - yhat)**2)
    ss_tot = np.sum((y - y.mean())**2)
    return 1 - ss_res/ss_tot if ss_tot > 0 else np.nan

# ---------- load summary ----------
if not os.path.exists(SUMMARY_FILE):
    raise FileNotFoundError(f"{SUMMARY_FILE} not found")

with open(SUMMARY_FILE) as f:
    info = json.load(f)

M    = info.get("M", 256)
skip = info.get("skip", 5)
N    = info.get("N", 40)
a    = info.get("a")   # two-point a if present
b    = info.get("b")   # two-point b if present

# Stage-0 operator params (always present in your runs)
theta0 = info["stage0"]["theta"]
c3_0   = info["stage0"].get("c3", 0.0)

# ---------- build spectrum once ----------
L0 = build_operator(M, theta=theta0, c3=c3_0)
evals0, _ = np.linalg.eigh(L0)
lam0 = np.sort(evals0.real)
lam0 = lam0[lam0 > 1e-12]
lam0 = unique_eigs(lam0)
y = np.sqrt(lam0)[skip:][:N]          # model √λ_n
t = RIEMANN_T[:N]                     # Riemann ordinates

# If a,b not in summary (rare), compute LS now
if a is None or b is None:
    X = np.vstack([np.ones(N), t]).T
    a, b = np.linalg.lstsq(X, y, rcond=None)[0]

yhat = a + b*t
R2   = r2_score(y, yhat)
rmse = float(np.sqrt(np.mean((y - yhat)**2)))

# ---------- plot ----------
if BACKGROUND == "black":
    plt.style.use("dark_background")
    neon, dos = "#00FF66", "#0080FF"
    grid_alpha = 0.25
else:
    plt.style.use("default")
    neon, dos = "#FF3333", "#0033CC"
    grid_alpha = 0.35

x = np.arange(N)

fig = plt.figure(figsize=(12,6.5))
ax  = fig.add_subplot(2,1,1)

# shadow/glow for readability
ax.plot(x, y,    color="black", linewidth=8.0, alpha=0.55, zorder=1)
ax.plot(x, yhat, color="black", linewidth=8.0, alpha=0.55, zorder=1)

# main lines
ax.plot(x, y,    color=neon, linewidth=4.8, alpha=0.98, zorder=2, label="HP √λₙ (model)")
ax.plot(x, yhat, color=dos,  linewidth=3.8, alpha=0.98, zorder=3, label="a + b · tₙ (Riemann)")

ax.set_title(f"HP vs Riemann Overlay  (R²={R2:.4f}, RMSE={rmse:.3f})", fontsize=18, weight="bold")
ax.set_xlabel("mode index n")
ax.set_ylabel("√λₙ  /  a + b·tₙ")
ax.grid(True, linestyle="--", alpha=grid_alpha)
ax.legend(frameon=True, loc="upper left")

# residuals
ax2 = fig.add_subplot(2,1,2)
res = y - yhat
ax2.axhline(0, color="#999999", linewidth=1.5, alpha=0.6)
ax2.plot(x, res, color=neon, linewidth=2.5)
ax2.set_title("Residuals (HP √λₙ  −  a + b·tₙ)")
ax2.set_xlabel("mode index n")
ax2.set_ylabel("residual")
ax2.grid(True, linestyle="--", alpha=grid_alpha)

plt.tight_layout()
plt.savefig(SAVE_PLOT, dpi=220)
print(f"Saved: {SAVE_PLOT}")