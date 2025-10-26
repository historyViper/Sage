print("\nSPECTRAL VALIDATION: RIEMANN ZEROS CORRELATION")
print("="*50)

# Sample first 20 Riemann zeros (known values)
riemann_zeros = np.array([
    14.134725, 21.022040, 25.010858, 30.424876, 32.935062,
    37.586178, 40.918719, 43.327073, 48.005151, 49.773832,
    52.970321, 56.446248, 59.347044, 60.831779, 65.112544,
    67.079811, 69.546402, 72.067158, 75.704691, 77.144840
])

# Calculate spacings and check 1/π correlation
spacings = np.diff(riemann_zeros)
mean_spacing = np.mean(spacings)
expected_spacing = 2 * np.pi / np.log(riemann_zeros[:-1]/(2*np.pi))

spacing_correlation = np.corrcoef(spacings, expected_spacing)[0,1]

print(f"Riemann Zero Analysis:")
print(f"Mean spacing: {mean_spacing:.6f}")
print(f"Expected mean: {np.mean(expected_spacing):.6f}") 
print(f"Spacing correlation: {spacing_correlation:.6f}")
print(f"Spectral consistency: {'✅' if spacing_correlation > 0.95 else '❌'}")

# Vortex eigenvalue prediction
vortex_eigenvalues = np.array([3/4, 5/6, 7/8, 8/9, 9/10])
normalized_zeros = (riemann_zeros[:5] - riemann_zeros[0]) / (riemann_zeros[4] - riemann_zeros[0])
eigen_correlation = np.corrcoef(vortex_eigenvalues, normalized_zeros)[0,1]

print(f"Vortex eigenvalue correlation: {eigen_correlation:.6f}")
