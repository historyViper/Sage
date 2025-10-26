print("\nCROSS-FIELD CONSISTENCY VERIFICATION")
print("="*50)

# Test 1/π constant across domains
domains = {
    "QCD coupling": a_fitted,
    "Lepton masses": -1/np.log(m_μ_pred/m_τ_pred), 
    "Fine structure": -1/np.log(0.00729735),
    "Zero spacing": 1/(mean_spacing * np.log(50/(2*np.pi))/(2*np.pi))
}

print(f"{'Domain':<20} {'1/π estimate':<15} {'Error (%)':<10}")
print("-"*50)

π_ref = 1/π
for domain, estimate in domains.items():
    error = abs(estimate - π_ref) / π_ref * 100
    status = "✅" if error < 5 else "❌"
    print(f"{domain:<20} {estimate:.8f} {error:>8.4f}% {status}")

# MOND parameter check (simplified)
c = 2.99792458e8  # m/s
a_0_observed = 1.2e-10  # m/s²
# Calculate required R_χ
R_χ = c**2 / (π * a_0_observed)  # Should be ~cosmological scale

print(f"\nMOND PARAMETER CONSISTENCY:")
print(f"Observed a₀ = {a_0_observed:.2e} m/s²")
print(f"Required R_χ = {R_χ:.2e} m")
print(f"Cosmological scale: ~10²⁶ m → {'✅' if 1e25 < R_χ < 1e27 else '❌'}")

# Cosmological constant prediction
H_0 = 67.4  # km/s/Mpc (Planck 2018)
H_0_SI = H_0 * 1000 / 3.086e22  # s⁻¹
Λ_pred = H_0_SI**2 / (π * c**2)
Λ_observed = 1.1056e-52  # m⁻² (Planck)

Λ_error = abs(Λ_pred - Λ_observed) / Λ_observed * 100
print(f"\nCOSMOLOGICAL CONSTANT:")
print(f"Predicted Λ = {Λ_pred:.2e} m⁻²")
print(f"Observed Λ = {Λ_observed:.2e} m⁻²") 
print(f"Error: {Λ_error:.2f}% → {'✅' if Λ_error < 5 else '❌'}")
