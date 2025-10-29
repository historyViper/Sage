import numpy as np
import matplotlib.pyplot as plt
from mpmath import zetazero

K = 50
gam = np.array([float(zetazero(i+1).imag) for i in range(1, K+1)])

# From final fit
theta, L, a, b = 1.5707963268, 22.0, 0.4999999999, 10.0
n = np.arange(1, K+1)
lam = ((2*np.pi*n + theta)/L)**2
pred = a*lam + b

plt.figure(figsize=(10,6))
plt.plot(n, gam, 'o', label='Riemann zeros $\\gamma_n$', ms=6)
plt.plot(n, pred, '^', label='Model: $a[(2\\pi n + \\theta)/L]^2 + b$', ms=5)
plt.xlabel('Zero index $n$')
plt.ylabel('$\\gamma_n$')
plt.legend()
plt.title('Hilbert--Pólya Operator: Model vs Riemann Zeros')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('hp_zeros.pdf', dpi=300)
print("Saved hp_zeros.pdf")
