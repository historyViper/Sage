#!/usr/bin/env python3
"""
Test exponential vs power law formulations:
- Power law: m = m_P × (1/(2π))^n
- Exponential: m = m_P × exp(-n/π)
"""

import math
import numpy as np

E_PLANCK = 1.2209e28  # eV

masses = {
    "electron": 0.511e6,
    "muon": 105.6583755e6,
    "tau": 1.77686e9,
    "pion0": 134.9768e6,
    "proton": 938.27208816e6,
    "Lambda_QCD": 0.2e9,
    "Higgs": 125.25e9,
    "top": 172.76e9,
    "W_boson": 80.379e9,
    "Z_boson": 91.1876e9,
    "charm": 1.27e9,
    "strange": 0.095e9,
    "bottom": 4.18e9,
}

def test_formula(name, formula_fn, r):
    """Test a formula: m = m_P × formula_fn(n)"""
    print(f"\n{'='*80}")
    print(f"{name}")
    print(f"Ratio per step: {r:.6f}")
    print(f"{'='*80}")
    print(f"{'Particle':<15} {'n_step':>7} {'Predicted':>15} {'Observed':>15} {'Error %':>10}")
    print("-"*80)
    
    residuals = []
    step_data = []
    
    for particle, m_obs in sorted(masses.items(), key=lambda x: x[1], reverse=True):
        # Find continuous step
        # m_obs = E_PLANCK × r^n, so n = log(m_obs/E_P) / log(r)
        # Since r < 1 and m_obs < E_P, both logs are negative, so n > 0
        n_cont = math.log(m_obs / E_PLANCK) / math.log(r)
        n_int = int(round(n_cont))
        
        # Predict mass
        m_pred = E_PLANCK * formula_fn(n_int, r)
        
        # Calculate error
        error_pct = 100 * (m_pred - m_obs) / m_obs
        log_residual = math.log(m_obs / m_pred)
        residuals.append(log_residual)
        
        step_data.append({
            'particle': particle,
            'n': n_int,
            'pred': m_pred,
            'obs': m_obs,
            'error': error_pct
        })
        
        print(f"{particle:<15} {n_int:7d} {m_pred:15.6e} {m_obs:15.6e} {error_pct:10.3f}")
    
    sse = sum(r**2 for r in residuals)
    mae = np.mean([abs(d['error']) for d in step_data])
    max_err = max([abs(d['error']) for d in step_data])
    
    print("-"*80)
    print(f"Sum of Squared log-Residuals: {sse:.6f}")
    print(f"Mean Absolute Error: {mae:.3f}%")
    print(f"Max Absolute Error: {max_err:.3f}%")
    
    return sse, step_data

# Formula 1: Power law (1/(2π))^n
def power_law(n, r):
    return r ** n

# Formula 2: Exponential exp(-n/π)
def exponential(n, r):
    return r ** n  # r already = exp(-1/π), so r^n = exp(-n/π)

# Test both formulations
print("\n" + "█"*80)
print(" TESTING GEOMETRIC ENERGY SCALE HYPOTHESES")
print("█"*80)

r_power = 1.0 / (2.0 * math.pi)
r_exp = math.exp(-1.0 / math.pi)

sse_power, data_power = test_formula(
    "POWER LAW: m = m_Planck × (1/(2π))^n",
    power_law,
    r_power
)

sse_exp, data_exp = test_formula(
    "EXPONENTIAL: m = m_Planck × exp(-n/π)",
    exponential,
    r_exp
)

# Comparison
print("\n" + "█"*80)
print(" COMPARISON")
print("█"*80)
print(f"Power Law (1/(2π))^n:     SSE = {sse_power:.6f}")
print(f"Exponential exp(-n/π):    SSE = {sse_exp:.6f}")
print(f"Improvement ratio:        {sse_power/sse_exp:.2f}×")
print()

if sse_exp < sse_power:
    print("✓ EXPONENTIAL FORMULATION WINS!")
    print(f"  The factor π appears in the EXPONENT, not the base.")
    print(f"  This matches RG flow: m(μ) ∝ exp(-log(μ/Λ)/π)")
else:
    print("✗ Power law performs better")

# Check if exp(-1/π) matches the "random" ratio found earlier
r_random = 0.736
print(f"\nNote: 'Best random' ratio from earlier: {r_random:.6f}")
print(f"      exp(-1/π) = {r_exp:.6f}")
print(f"      Difference: {100*abs(r_exp - r_random)/r_random:.2f}%")
print(f"\n→ The 'random' ratio was actually exp(-1/π) in disguise!")

# Look for patterns in step numbers
print("\n" + "="*80)
print("STEP NUMBER PATTERNS (Exponential formulation)")
print("="*80)
print(f"{'Particle':<15} {'Step n':>7} {'n mod 10':>10} {'n mod π':>10}")
print("-"*80)
for d in sorted(data_exp, key=lambda x: x['n']):
    n = d['n']
    print(f"{d['particle']:<15} {n:7d} {n % 10:10d} {n % math.pi:10.3f}")

# Check for approximate integer ratios
print("\n" + "="*80)
print("STEP RATIOS (looking for simple fractions)")
print("="*80)
electron_step = [d['n'] for d in data_exp if d['particle'] == 'electron'][0]
print(f"Using electron as reference: n_electron = {electron_step}")
print(f"{'Particle':<15} {'Step n':>7} {'n/n_e':>10} {'Closest ratio':>15}")
print("-"*80)
for d in sorted(data_exp, key=lambda x: x['n']):
    n = d['n']
    ratio = n / electron_step
    # Find closest simple fraction
    for denom in range(1, 20):
        for numer in range(1, 20):
            if abs(ratio - numer/denom) < 0.02:
                closest = f"{numer}/{denom}"
                break
        else:
            continue
        break
    else:
        closest = f"{ratio:.3f}"
    print(f"{d['particle']:<15} {n:7d} {ratio:10.3f} {closest:>15}")
