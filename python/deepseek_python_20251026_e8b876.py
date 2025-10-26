print("\nSENSITIVITY ANALYSIS: ±1% HARMONIC PERTURBATION")
print("="*50)

# Test stability against harmonic ratio variations
base_harmonics = np.array([3/4, 5/6, 7/8])
perturbations = [0.99, 1.00, 1.01]  # ±1%

sensitivity_results = []

for perturb in perturbations:
    perturbed_harmonics = base_harmonics * perturb
    m_e_pert = perturbed_harmonics[0] * exp_terms[0] * m_scale
    m_μ_pert = perturbed_harmonics[1] * exp_terms[1] * m_scale
    m_τ_pert = perturbed_harmonics[2] * exp_terms[2] * m_scale
    
    errors = [
        abs(m_e_pert - m_e_exp) / m_e_exp * 100,
        abs(m_μ_pert - m_μ_exp) / m_μ_exp * 100, 
        abs(m_τ_pert - m_τ_exp) / m_τ_exp * 100
    ]
    max_error = max(errors)
    sensitivity_results.append((perturb, max_error))

print(f"{'Perturbation':<12} {'Max Error (%)':<15} {'Robust':<10}")
print("-"*50)
for perturb, error in sensitivity_results:
    robust = "✅" if error < 1.0 else "❌"
    print(f"{perturb:>8.2f}     {error:>10.4f}%     {robust:<10}")

# π-law universality test
π_estimates = [
    1/a_fitted,  # From α_s fit
    1/(-np.log(m_μ_pred/m_τ_pred)),  # From lepton ratio
    1/(-np.log(0.00729735)),  # From fine structure
]

π_std = np.std(π_estimates)
print(f"\nπ-LAW UNIVERSALITY:")
print(f"π estimates: {[f'{x:.6f}' for x in π_estimates]}")
print(f"Standard deviation: {π_std:.6f}")
print(f"Universality: {'✅' if π_std <= 0.02 else '❌'} (σ ≤ 0.02)")