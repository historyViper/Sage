import json, os
import numpy as np
import matplotlib.pyplot as plt

# ========== CONFIG ==========
BACKGROUND = "black"      # "white" or "black"
SAVE_NAME  = "hp_two_vector_overlay.png"
SUMMARY_FILE = "hp_two_point_summary.json"

# ---------- helper ops (copied from core) ----------
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

def unique_eigs(vals, tol=1e-8):
    out=[]
    for v in np.sort(vals):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return np.array(out)

# ========== LOAD SUMMARY ==========
if not os.path.exists(SUMMARY_FILE):
    raise FileNotFoundError(f"{SUMMARY_FILE} not found. Run hp_two_point_balance.py first!")

with open(SUMMARY_FILE) as f:
    info = json.load(f)

M = info["M"]
skip = info["skip"]
N = info["N"]
theta = info["stage0"]["theta"]
c3 = info["stage0"]["c3"]
eps = info["stage3"]["eps"]
theta_sigma = info["stage3"]["theta_sigma"]

# ---------- RECONSTRUCT spectra ----------
# Stage 0 (scalar)
L0 = build_operator(M, theta=theta, c3=c3)
evals0, _ = np.linalg.eigh(L0)
lam0 = np.sort(evals0.real)
lam0 = lam0[lam0 > 1e-12]
lam0 = unique_eigs(lam0)
v1 = np.sqrt(lam0)[skip:][:N]

# Stage 3 (torus)
M_tau = 128; M_sigma = 8
Ltau = build_operator(M_tau, theta=theta)
Lsig = build_operator_sigma(M_sigma, theta_sigma)
L3 = np.kron(Ltau, np.eye(M_sigma)) + eps*np.kron(np.eye(M_tau), Lsig)
evals3, _ = np.linalg.eigh(L3)
lam3 = np.sort(evals3.real)
lam3 = lam3[lam3 > 1e-12]
lam3 = unique_eigs(lam3)
v2 = np.sqrt(lam3)[skip:][:N]

# ---------- PLOT ----------
if BACKGROUND == "black":
    plt.style.use('dark_background')
    color1 = '#00FF66'  # Lime green (Matrix)
    color2 = '#0080FF'  # DOS blue
else:
    plt.style.use('default')
    color1 = '#FF3333'
    color2 = '#0000FF'

x = np.arange(N)
fig, ax = plt.subplots(figsize=(10,5))
ax.set_facecolor(BACKGROUND)

# Lower layer thicker for visibility
ax.plot(x, v1, color=color1, linewidth=3.2, alpha=0.85, label='Stage-0 Scalar')
ax.plot(x, v2, color=color2, linewidth=2.0, alpha=0.9, label='Stage-3 Torus')

ax.set_title("HP Two-Vector Overlay", fontsize=14, weight='bold')
ax.set_xlabel("Mode Index (n)")
ax.set_ylabel("√λₙ")
ax.legend()
ax.grid(True, linestyle='--', alpha=0.3)

plt.tight_layout()
plt.savefig(SAVE_NAME, dpi=200)
plt.show()

print(f"Saved: {SAVE_NAME}")
