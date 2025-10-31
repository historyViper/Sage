# test_chiral_phases.py
# Test three different chiral phase schemes to eliminate drift

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

# ——— BUILD HAMILTONIAN WITH CHIRAL PHASE OPTIONS ———
def build_hamiltonian(N, d_max, alpha, p, n_flux, twist_mode='uniform'):
    """
    twist_mode options:
    - 'uniform': original (all sites same phase direction)
    - 'sublattice': alternating (+1,-1,+1,-1,...) staggered
    - 'center': flip at midpoint (left +, right -)
    - 'ramp': smooth continuous chirality from -1 to +1
    """
    H = np.zeros((N, N), dtype=complex)
    phase_per_hop = 2 * np.pi / n_flux
    center = (N - 1) / 2.0

    for i in range(N):
        # Determine chirality factor s_i based on twist_mode
        if twist_mode == 'uniform':
            s_i = 1.0  # original behavior
        elif twist_mode == 'sublattice':
            s_i = 1.0 if (i % 2 == 0) else -1.0
        elif twist_mode == 'center':
            s_i = 1.0 if i <= center else -1.0
        elif twist_mode == 'ramp':
            s_i = (2 * i - (N - 1)) / N  # in [-1, +1]
        else:
            s_i = 1.0
        
        for dj in range(-d_max, d_max + 1):
            j = (i + dj) % N
            if j < 0 or j >= N: continue
            d = abs(i - j)
            if d == 0: continue

            # Pascal amplitude
            A = pascal_amp(d)

            # Position-dependent decay
            u = (i + j) / (2.0 * N)
            decay = 1.0 / (1.0 + alpha * u**p)

            # CHIRAL Berry phase: s_i flips the twist direction
            phase = np.exp(1j * s_i * phase_per_hop * dj)

            H[i, j] = -A * decay * phase

    # Force Hermitian
    H = (H + H.conj().T) / 2.0
    return H

# ——— TEST ALL FOUR MODES ———
modes = ['uniform', 'sublattice', 'center', 'ramp']
N_test_values = [220, 240, 260, 280, 300, 320, 350]

all_results = []

print("="*80)
print("TESTING CHIRAL PHASE MODES")
print("="*80)

for mode in modes:
    print(f"\n{'='*80}")
    print(f"MODE: {mode.upper()}")
    print(f"{'='*80}")
    print(f"{'N':<6} {'Train MAPE':<12} {'Valid MAPE':<12} {'Extend MAPE':<12} {'Total Drift':<12}")
    print("-"*80)
    
    for N in N_test_values:
        # Build and diagonalize
        H = build_hamiltonian(N, d_max, alpha, p, n_flux, twist_mode=mode)
        evals = eigh(H, eigvals_only=True)
        
        # Extract middle band
        start_idx = N // 3
        end_idx = 2 * N // 3
        n_evals = end_idx - start_idx
        
        if n_evals < 73:
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
        
        # Residual drift
        residuals_valid = pred_valid - valid_zeros
        drift_first5 = np.mean(residuals_valid[:5])
        drift_last5 = np.mean(residuals_valid[-5:])
        total_drift = drift_last5 - drift_first5
        
        all_results.append({
            'Mode': mode,
            'N': N,
            'Train_MAPE': train_mape,
            'Valid_MAPE': valid_mape,
            'Extended_MAPE': extended_mape,
            'Total_Drift': total_drift,
            'Coef_a': a,
            'Coef_b': b,
            'Drift_First5': drift_first5,
            'Drift_Last5': drift_last5
        })
        
        print(f"{N:<6} {train_mape:<12.3f} {valid_mape:<12.3f} {extended_mape:<12.3f} {total_drift:<+12.4f}")
    
    print("-"*80)

# Convert to DataFrame
df_all = pd.DataFrame(all_results)

# ——— SUMMARY COMPARISON ———
print("\n" + "="*80)
print("SUMMARY: BEST PERFORMANCE BY MODE")
print("="*80)

for mode in modes:
    df_mode = df_all[df_all['Mode'] == mode]
    best_valid_idx = df_mode['Valid_MAPE'].idxmin()
    best = df_mode.loc[best_valid_idx]
    
    avg_valid = df_mode['Valid_MAPE'].mean()
    avg_drift = df_mode['Total_Drift'].abs().mean()
    
    print(f"\n{mode.upper()}:")
    print(f"  Best Valid MAPE: {best['Valid_MAPE']:.3f}% at N={best['N']:.0f}")
    print(f"  Avg Valid MAPE:  {avg_valid:.3f}%")
    print(f"  Avg |Drift|:     {avg_drift:.3f}")
    print(f"  Best Drift:      {df_mode.loc[df_mode['Total_Drift'].abs().idxmin(), 'Total_Drift']:+.3f} at N={df_mode.loc[df_mode['Total_Drift'].abs().idxmin(), 'N']:.0f}")

# ——— FIND ABSOLUTE BEST ———
print("\n" + "="*80)
print("ABSOLUTE BEST CONFIGURATIONS")
print("="*80)

best_mape_idx = df_all['Valid_MAPE'].idxmin()
best_mape = df_all.loc[best_mape_idx]
print(f"\nLowest Valid MAPE:")
print(f"  Mode: {best_mape['Mode']}, N={best_mape['N']:.0f}")
print(f"  Valid MAPE: {best_mape['Valid_MAPE']:.3f}%")
print(f"  Total Drift: {best_mape['Total_Drift']:+.3f}")

best_drift_idx = df_all['Total_Drift'].abs().idxmin()
best_drift = df_all.loc[best_drift_idx]
print(f"\nSmallest |Drift|:")
print(f"  Mode: {best_drift['Mode']}, N={best_drift['N']:.0f}")
print(f"  Valid MAPE: {best_drift['Valid_MAPE']:.3f}%")
print(f"  Total Drift: {best_drift['Total_Drift']:+.3f}")

# ——— SAVE RESULTS ———
output_dir = '/mnt/user-data/outputs/'
df_all.to_csv(output_dir + 'chiral_phase_comparison.csv', index=False, float_format='%.10f')

# ——— PLOTTING ———
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Valid MAPE by mode
ax1 = axes[0, 0]
for mode in modes:
    df_mode = df_all[df_all['Mode'] == mode]
    ax1.plot(df_mode['N'], df_mode['Valid_MAPE'], 'o-', label=mode, linewidth=2, markersize=6)
ax1.set_xlabel('Lattice Size N', fontsize=11)
ax1.set_ylabel('Validation MAPE (%)', fontsize=11)
ax1.set_title('Validation Error by Twist Mode', fontsize=12, fontweight='bold')
ax1.legend(fontsize=9)
ax1.grid(alpha=0.3)

# Plot 2: Total Drift by mode
ax2 = axes[0, 1]
for mode in modes:
    df_mode = df_all[df_all['Mode'] == mode]
    ax2.plot(df_mode['N'], df_mode['Total_Drift'], 'o-', label=mode, linewidth=2, markersize=6)
ax2.axhline(0, color='k', linestyle='--', linewidth=1, alpha=0.5)
ax2.set_xlabel('Lattice Size N', fontsize=11)
ax2.set_ylabel('Total Drift (Last5 - First5)', fontsize=11)
ax2.set_title('Drift Pattern by Twist Mode', fontsize=12, fontweight='bold')
ax2.legend(fontsize=9)
ax2.grid(alpha=0.3)

# Plot 3: Avg Valid MAPE comparison
ax3 = axes[1, 0]
mode_avgs = [df_all[df_all['Mode'] == mode]['Valid_MAPE'].mean() for mode in modes]
bars = ax3.bar(modes, mode_avgs, color=['blue', 'green', 'orange', 'red'], alpha=0.7)
ax3.set_ylabel('Average Valid MAPE (%)', fontsize=11)
ax3.set_title('Average Performance by Mode', fontsize=12, fontweight='bold')
ax3.grid(alpha=0.3, axis='y')
# Add values on bars
for bar, val in zip(bars, mode_avgs):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
             f'{val:.2f}%', ha='center', va='bottom', fontsize=9)

# Plot 4: Avg |Drift| comparison
ax4 = axes[1, 1]
drift_avgs = [df_all[df_all['Mode'] == mode]['Total_Drift'].abs().mean() for mode in modes]
bars = ax4.bar(modes, drift_avgs, color=['blue', 'green', 'orange', 'red'], alpha=0.7)
ax4.set_ylabel('Average |Drift|', fontsize=11)
ax4.set_title('Average Drift Magnitude by Mode', fontsize=12, fontweight='bold')
ax4.grid(alpha=0.3, axis='y')
# Add values on bars
for bar, val in zip(bars, drift_avgs):
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., height,
             f'{val:.2f}', ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig(output_dir + 'chiral_phase_comparison.png', dpi=150, bbox_inches='tight')
print(f"\nPlots saved to {output_dir}chiral_phase_comparison.png")
plt.close()

print("\n" + "="*80)
print("ANALYSIS COMPLETE!")
print("="*80)
print(f"Results saved to: {output_dir}chiral_phase_comparison.csv")
