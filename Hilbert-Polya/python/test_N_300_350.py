# test_N_300_350.py
# Test N from 300 to 350 to see if drift normalizes

import numpy as np
from scipy.linalg import eigh
from mpmath import zetazero, mp
from math import comb
import pandas as pd

mp.dps = 50

# ——— FIXED PARAMETERS ———
d_max = 5
alpha = 0.7
p = 1.5
n_flux = 25

# ——— RIEMANN ZEROS ———
def get_zeros(K):
    return np.array([float(zetazero(k+1).imag) for k in range(K)], dtype=float)

zeros = get_zeros(73)
train_zeros = zeros[:30]
valid_zeros = zeros[30:58]
extended_zeros = zeros[58:73]

# ——— PASCAL AMPLITUDE ———
def pascal_amp(d):
    if d < 0 or d > 2 * d_max: return 0.0
    k = d // 2
    return np.sqrt(comb(d, k)) / (2 ** d)

# ——— BUILD HAMILTONIAN ———
def build_hamiltonian(N, d_max, alpha, p, n_flux):
    H = np.zeros((N, N), dtype=complex)
    phase_per_hop = 2 * np.pi / n_flux

    for i in range(N):
        for dj in range(-d_max, d_max + 1):
            j = (i + dj) % N
            if j < 0 or j >= N: continue
            d = abs(i - j)
            if d == 0: continue

            A = pascal_amp(d)
            u = (i + j) / (2.0 * N)
            decay = 1.0 / (1.0 + alpha * u**p)
            phase = np.exp(1j * phase_per_hop * dj)

            H[i, j] = -A * decay * phase

    H = (H + H.conj().T) / 2.0
    return H

# ——— TEST N = 300 to 350 ———
N_values = list(range(300, 351, 5))  # 300, 305, 310, ..., 350
results = []

print("="*80)
print("TESTING HIGHER LATTICE SIZES (N = 300 to 350)")
print("="*80)
print(f"{'N':<6} {'Train MAPE':<12} {'Valid MAPE':<12} {'Extend MAPE':<12} {'Coef a':<14} {'Coef b':<14}")
print("-"*80)

for N in N_values:
    # Build and diagonalize
    H = build_hamiltonian(N, d_max, alpha, p, n_flux)
    evals = eigh(H, eigvals_only=True)
    
    # Extract middle band
    start_idx = N // 3
    end_idx = 2 * N // 3
    n_evals = end_idx - start_idx
    
    if n_evals < 73:
        print(f"N={N}: Not enough eigenvalues ({n_evals}), skipping...")
        continue
    
    model_evals = np.sort(evals[start_idx:end_idx])
    
    # Affine fit on training data
    X = np.vstack([model_evals[:30], np.ones(30)]).T
    a, b = np.linalg.lstsq(X, train_zeros, rcond=None)[0]
    
    # Predictions
    pred_train = a * model_evals[:30] + b
    pred_valid = a * model_evals[30:58] + b
    pred_extended = a * model_evals[58:73] + b
    
    # Metrics
    train_mape = np.mean(np.abs((train_zeros - pred_train) / train_zeros)) * 100
    valid_mape = np.mean(np.abs((valid_zeros - pred_valid) / valid_zeros)) * 100
    extended_mape = np.mean(np.abs((extended_zeros - pred_extended) / extended_zeros)) * 100
    
    # Residual drift analysis (validation set)
    residuals_valid = pred_valid - valid_zeros
    drift_first5 = np.mean(residuals_valid[:5])
    drift_middle14 = np.mean(residuals_valid[14:28])
    drift_last5 = np.mean(residuals_valid[-5:])
    
    # Also check specific quartiles for finer resolution
    drift_q1 = np.mean(residuals_valid[:7])
    drift_q2 = np.mean(residuals_valid[7:14])
    drift_q3 = np.mean(residuals_valid[14:21])
    drift_q4 = np.mean(residuals_valid[21:])
    
    results.append({
        'N': N,
        'Train_MAPE': train_mape,
        'Valid_MAPE': valid_mape,
        'Extended_MAPE': extended_mape,
        'Coef_a': a,
        'Coef_b': b,
        'Drift_First5': drift_first5,
        'Drift_Middle14': drift_middle14,
        'Drift_Last5': drift_last5,
        'Drift_Q1': drift_q1,
        'Drift_Q2': drift_q2,
        'Drift_Q3': drift_q3,
        'Drift_Q4': drift_q4,
        'Total_Drift': drift_last5 - drift_first5,
        'Eigenval_Min': model_evals[0],
        'Eigenval_Max': model_evals[-1],
        'Num_Eigenvals': n_evals
    })
    
    print(f"{N:<6} {train_mape:<12.3f} {valid_mape:<12.3f} {extended_mape:<12.3f} {a:<14.3f} {b:<14.3f}")

print("-"*80)

# Convert to DataFrame
df_results = pd.DataFrame(results)

# ——— DETAILED DRIFT ANALYSIS ———
print("\n" + "="*80)
print("RESIDUAL DRIFT ANALYSIS (Validation Set)")
print("="*80)
print(f"{'N':<6} {'First 5':<10} {'Middle 14':<10} {'Last 5':<10} {'Total Drift':<12} {'Status':<15}")
print("-"*80)

for _, row in df_results.iterrows():
    total_drift = row['Total_Drift']
    if abs(total_drift) < 1.0:
        status = "NORMALIZING"
    elif total_drift > 0:
        status = "Under-predict"
    else:
        status = "Over-predict"
    
    print(f"{row['N']:<6.0f} {row['Drift_First5']:<10.4f} {row['Drift_Middle14']:<10.4f} {row['Drift_Last5']:<10.4f} {total_drift:<12.4f} {status:<15}")

print("-"*80)

# ——— STATISTICS ———
print("\n" + "="*80)
print("STATISTICS (N = 300-350)")
print("="*80)
print(f"Valid MAPE - Mean: {df_results['Valid_MAPE'].mean():.3f}%")
print(f"Valid MAPE - Min:  {df_results['Valid_MAPE'].min():.3f}% (N={df_results.loc[df_results['Valid_MAPE'].idxmin(), 'N']:.0f})")

print(f"\nTotal Drift - Mean: {df_results['Total_Drift'].mean():.4f}")
print(f"Total Drift - Min:  {df_results['Total_Drift'].min():.4f} (N={df_results.loc[df_results['Total_Drift'].idxmin(), 'N']:.0f})")

zero_drift_N = df_results.loc[df_results['Total_Drift'].abs().idxmin(), 'N']
zero_drift_val = df_results.loc[df_results['Total_Drift'].abs().idxmin(), 'Total_Drift']
print(f"\nClosest to zero drift: N={zero_drift_N:.0f} with drift={zero_drift_val:.4f}")

# ——— SAVE RESULTS ———
output_dir = '/mnt/user-data/outputs/'
df_results.to_csv(output_dir + 'N_300_350_results.csv', index=False, float_format='%.10f')

print("\n" + "="*80)
print("COMPARISON: N=220 vs N=300-350")
print("="*80)
print("N=220: Valid MAPE = 1.367%, Total Drift = +4.349")
print(f"N=300-350: Valid MAPE = {df_results['Valid_MAPE'].mean():.3f}%, Total Drift = {df_results['Total_Drift'].mean():.3f}")
