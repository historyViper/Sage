# test_multiple_N.py
# Test N from 160 to 300 to verify consistent parabolic drift

import numpy as np
from scipy.linalg import eigh
from mpmath import zetazero, mp
from math import comb
import pandas as pd
import matplotlib.pyplot as plt

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

# ——— TEST RANGE OF N VALUES ———
N_values = list(range(160, 301, 10))  # 160, 170, 180, ..., 300
results = []

print("="*80)
print("TESTING MULTIPLE LATTICE SIZES (N = 160 to 300)")
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
    drift_middle14 = np.mean(residuals_valid[14:28])  # indices 14-27 (middle 14)
    drift_last5 = np.mean(residuals_valid[-5:])
    
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
print(f"{'N':<6} {'First 5':<12} {'Middle 14':<12} {'Last 5':<12} {'Total Drift':<12}")
print("-"*80)

for _, row in df_results.iterrows():
    total_drift = row['Drift_Last5'] - row['Drift_First5']
    print(f"{row['N']:<6.0f} {row['Drift_First5']:<12.4f} {row['Drift_Middle14']:<12.4f} {row['Drift_Last5']:<12.4f} {total_drift:<12.4f}")

print("-"*80)

# ——— STATISTICS ———
print("\n" + "="*80)
print("STATISTICS ACROSS ALL N VALUES")
print("="*80)
print(f"Valid MAPE - Mean: {df_results['Valid_MAPE'].mean():.3f}%")
print(f"Valid MAPE - Std:  {df_results['Valid_MAPE'].std():.3f}%")
print(f"Valid MAPE - Min:  {df_results['Valid_MAPE'].min():.3f}% (N={df_results.loc[df_results['Valid_MAPE'].idxmin(), 'N']:.0f})")
print(f"Valid MAPE - Max:  {df_results['Valid_MAPE'].max():.3f}% (N={df_results.loc[df_results['Valid_MAPE'].idxmax(), 'N']:.0f})")

print(f"\nCoef a - Mean: {df_results['Coef_a'].mean():.3f}")
print(f"Coef a - Std:  {df_results['Coef_a'].std():.3f}")

print(f"\nTotal Drift - Mean: {(df_results['Drift_Last5'] - df_results['Drift_First5']).mean():.4f}")
print(f"Total Drift - Std:  {(df_results['Drift_Last5'] - df_results['Drift_First5']).std():.4f}")

# ——— SAVE RESULTS ———
output_dir = '/mnt/user-data/outputs/'
df_results.to_csv(output_dir + 'N_sweep_results.csv', index=False, float_format='%.10f')

# ——— PLOTTING ———
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: MAPE vs N
ax1 = axes[0, 0]
ax1.plot(df_results['N'], df_results['Train_MAPE'], 'ro-', label='Training MAPE', linewidth=2, markersize=6)
ax1.plot(df_results['N'], df_results['Valid_MAPE'], 'b^-', label='Validation MAPE', linewidth=2, markersize=6)
ax1.plot(df_results['N'], df_results['Extended_MAPE'], 'gs-', label='Extended MAPE', linewidth=2, markersize=6)
ax1.set_xlabel('Lattice Size N', fontsize=11)
ax1.set_ylabel('MAPE (%)', fontsize=11)
ax1.set_title('Prediction Error vs Lattice Size', fontsize=12, fontweight='bold')
ax1.legend(fontsize=9)
ax1.grid(alpha=0.3)

# Plot 2: Affine coefficients vs N
ax2 = axes[0, 1]
ax2_twin = ax2.twinx()
line1 = ax2.plot(df_results['N'], df_results['Coef_a'], 'ro-', label='Coefficient a', linewidth=2, markersize=6)
line2 = ax2_twin.plot(df_results['N'], df_results['Coef_b'], 'b^-', label='Coefficient b', linewidth=2, markersize=6)
ax2.set_xlabel('Lattice Size N', fontsize=11)
ax2.set_ylabel('Coefficient a', fontsize=11, color='red')
ax2_twin.set_ylabel('Coefficient b', fontsize=11, color='blue')
ax2.tick_params(axis='y', labelcolor='red')
ax2_twin.tick_params(axis='y', labelcolor='blue')
ax2.set_title('Affine Fit Coefficients vs N', fontsize=12, fontweight='bold')
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax2.legend(lines, labels, fontsize=9, loc='upper left')
ax2.grid(alpha=0.3)

# Plot 3: Drift pattern
ax3 = axes[1, 0]
ax3.plot(df_results['N'], df_results['Drift_First5'], 'ro-', label='First 5 (31-35)', linewidth=2, markersize=6)
ax3.plot(df_results['N'], df_results['Drift_Middle14'], 'b^-', label='Middle 14 (45-58)', linewidth=2, markersize=6)
ax3.plot(df_results['N'], df_results['Drift_Last5'], 'gs-', label='Last 5 (54-58)', linewidth=2, markersize=6)
ax3.axhline(0, color='k', linestyle='--', linewidth=1, alpha=0.5)
ax3.set_xlabel('Lattice Size N', fontsize=11)
ax3.set_ylabel('Mean Residual (Predicted - True)', fontsize=11)
ax3.set_title('Residual Drift Pattern (Validation Set)', fontsize=12, fontweight='bold')
ax3.legend(fontsize=9)
ax3.grid(alpha=0.3)

# Plot 4: Total drift magnitude
ax4 = axes[1, 1]
total_drift = df_results['Drift_Last5'] - df_results['Drift_First5']
ax4.plot(df_results['N'], total_drift, 'mo-', linewidth=2, markersize=6)
ax4.axhline(total_drift.mean(), color='k', linestyle='--', linewidth=1, alpha=0.5, label=f'Mean: {total_drift.mean():.3f}')
ax4.set_xlabel('Lattice Size N', fontsize=11)
ax4.set_ylabel('Total Drift (Last5 - First5)', fontsize=11)
ax4.set_title('Total Residual Drift Across Validation Set', fontsize=12, fontweight='bold')
ax4.legend(fontsize=9)
ax4.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(output_dir + 'N_sweep_analysis.png', dpi=150, bbox_inches='tight')
print(f"\nPlots saved to {output_dir}N_sweep_analysis.png")
plt.close()

print("\n" + "="*80)
print("ANALYSIS COMPLETE!")
print("="*80)
print(f"Results saved to: {output_dir}N_sweep_results.csv")
