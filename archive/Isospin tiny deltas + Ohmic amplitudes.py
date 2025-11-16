# TFFT – QED E·logE + isospin tiny deltas + Ohmic amplitudes (single script)
# No external files; uses only standard library + numpy.

import math, numpy as np

# ---------------------------
# Data (charged fermions)
# ---------------------------
# (name, n_index, class_tag, experimental mass [MeV], family_tag)
DATA = [
    ("t",   0, "q_up_g3", 173000.0, "up"),
    ("b",   4, "q_dn_g3",   4180.0, "down"),
    ("c",   5, "q_up_g2",   1270.0, "up"),
    ("s",   6, "q_dn_g2",     95.0, "down"),
    ("d",   7, "q_dn_g1",    4.70,  "down"),
    ("u",   7, "q_up_g1",    2.20,  "up"),
    ("tau", 5, "lep",      1777.0,  "lep"),
    ("mu",  6, "lep",       105.7,  "lep"),
    ("e",   8, "lep",         0.511,"lep"),
]

names   = np.array([r[0] for r in DATA])
n_vals  = np.array([r[1] for r in DATA], dtype=float)
klass   = np.array([r[2] for r in DATA])
m_exp   = np.array([r[3] for r in DATA], dtype=float)
family  = np.array([r[4] for r in DATA])

# ---------------------------
# Model constants
# ---------------------------
E0_FIXED = 105.7      # MeV (locked to muon)
M_TOP    = 173000.0   # MeV (anchor in slope term)

# ---------------------------
# Helpers
# ---------------------------
def predict_masses(params):
    """
    params = (R, S, c,
              d_up_g1, d_dn_g1, d_up_g2, d_dn_g2, d_up_g3, d_dn_g3, d_lep,
              A_up, A_down, A_lep)
    """
    (R, S, c,
     d_up_g1, d_dn_g1, d_up_g2, d_dn_g2, d_up_g3, d_dn_g3, d_lep,
     A_up, A_down, A_lep) = params

    d_map = {
        "q_up_g1": d_up_g1, "q_dn_g1": d_dn_g1,
        "q_up_g2": d_up_g2, "q_dn_g2": d_dn_g2,
        "q_up_g3": d_up_g3, "q_dn_g3": d_dn_g3,
        "lep": d_lep
    }
    A_map = {"up": A_up, "down": A_down, "lep": A_lep}

    deltas = np.array([d_map[k] for k in klass], dtype=float)
    A_vec  = np.array([A_map[f] for f in family], dtype=float)

    # log m = log(E0) + (S/M_TOP) * A_family * R^n - (c + δ_iso)
    logm = math.log(E0_FIXED) + (S / M_TOP) * A_vec * (R ** n_vals) - (c + deltas)
    return np.exp(logm)

def loss(params):
    (R, S, c,
     d_up_g1, d_dn_g1, d_up_g2, d_dn_g2, d_up_g3, d_dn_g3, d_lep,
     A_up, A_down, A_lep) = params

    # Constraints
    if R <= 1.0 or S <= 0:
        return 1e12
    if max(abs(d_up_g1),abs(d_dn_g1),abs(d_up_g2),abs(d_dn_g2),
           abs(d_up_g3),abs(d_dn_g3),abs(d_lep)) > 0.03:
        return 1e12
    if not (0.95 <= A_up   <= 1.05): return 1e12
    if not (0.95 <= A_down <= 1.05): return 1e12
    if not (0.95 <= A_lep  <= 1.05): return 1e12

    m_pred = predict_masses(params)
    # log-domain MSE
    return float(np.mean((np.log(m_pred) - np.log(m_exp))**2))

# ---------------------------
# Random-restart fit
# ---------------------------
def fit(seed=0, iters=120000):
    rng = np.random.default_rng(seed)
    best_L = float('inf')
    best = None

    for _ in range(iters):
        R = 1.5 + 8.5 * rng.random()                 # 1.5 .. 10
        S = 1e3 * 10**(3 * rng.random())             # 1e3 .. 1e6 (MeV)
        c = -6 + 12 * rng.random()                   # -6 .. 6

        # 7 isospin deltas in [-0.03, 0.03]
        deltas = -0.03 + 0.06 * rng.random(7)
        d_up_g1, d_dn_g1, d_up_g2, d_dn_g2, d_up_g3, d_dn_g3, d_lep = deltas

        # Ohmic amplitudes (±5%)
        A_up   = 0.95 + 0.10 * rng.random()
        A_down = 0.95 + 0.10 * rng.random()
        A_lep  = 0.95 + 0.10 * rng.random()

        params = (R, S, c,
                  d_up_g1, d_dn_g1, d_up_g2, d_dn_g2, d_up_g3, d_dn_g3, d_lep,
                  A_up, A_down, A_lep)

        L = loss(params)
        if L < best_L:
            best_L = L
            best = params

    return best_L, best

def metrics_and_print(params, title="Fit results"):
    m_pred = predict_masses(params)
    rel_err_pct = (m_pred - m_exp) / m_exp * 100.0
    rmse = float(np.sqrt(np.mean((m_pred - m_exp)**2)))
    mape = float(np.mean(np.abs(rel_err_pct)))

    (R, S, c,
     d_up_g1, d_dn_g1, d_up_g2, d_dn_g2, d_up_g3, d_dn_g3, d_lep,
     A_up, A_down, A_lep) = params

    print("\n" + "="*len(title))
    print(title)
    print("="*len(title))
    print(f"E0 (locked)   : {E0_FIXED} MeV")
    print(f"R             : {R:.6g}")
    print(f"S [MeV]       : {S:.6g}")
    print(f"c             : {c:.6g}")
    print(f"A_up/A_down/A_lep : {A_up:.6g} / {A_down:.6g} / {A_lep:.6g}")
    print(f"δ_up_g1, δ_dn_g1  : {d_up_g1:.6g}, {d_dn_g1:.6g}")
    print(f"δ_up_g2, δ_dn_g2  : {d_up_g2:.6g}, {d_dn_g2:.6g}")
    print(f"δ_up_g3, δ_dn_g3  : {d_up_g3:.6g}, {d_dn_g3:.6g}")
    print(f"δ_lep             : {d_lep:.6g}")
    print(f"\nRMSE [MeV]    : {rmse:.6g}")
    print(f"MAPE [%]      : {mape:.6g}\n")

    # Table
    header = f"{'particle':>8} {'n':>2} {'class':>9} {'family':>6}  {'m_exp [MeV]':>12}  {'m_pred [MeV]':>13}  {'Δ% err':>8}"
    print(header)
    print("-"*len(header))
    for i in range(len(DATA)):
        print(f"{names[i]:>8} {int(n_vals[i]):>2} {klass[i]:>9} {family[i]:>6}  "
              f"{m_exp[i]:12.6g}  {m_pred[i]:13.6g}  {rel_err_pct[i]:8.3f}")

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    best_L, best_params = fit(seed=42, iters=120000)   # increase iters if you want a tighter fit
    metrics_and_print(best_params, title="Ohmic-amplitude + isospin-delta fit")
