import numpy as np
from scipy.optimize import differential_evolution

current_masses    = {'up':2.3,'down':4.8,'strange':95.0,'charm':1275.0,'bottom':4180.0,'top':173100.0}
constituent_masses= {'up':336.0,'down':340.0,'strange':486.0,'charm':1550.0,'bottom':4730.0,'top':173400.0}
quarks = ['up','down','strange','charm','bottom','top']
LAMBDA_QCD = 217.0
residues   = [1,7,11,13,17,19,23,29]
angles_720 = {r: 2*360*r/30 for r in residues}
assignment = {'up':19,'down':11,'strange':7,'charm':23,'bottom':13,'top':17}

def geo(t): return max(np.sin(np.radians(t)/2)**2, 1e-6)

def solve(quark, res, a, g, max_iter=300, tol=1e-7):
    t0 = angles_720[res]; m_c = current_masses[quark]
    m  = m_c + a*LAMBDA_QCD/geo(t0)
    for _ in range(max_iter):
        t_eff = t0 + g*(m/LAMBDA_QCD)*(180/np.pi)
        m_new = m_c + a*LAMBDA_QCD/geo(t_eff)
        if abs(m_new-m)/(abs(m)+1e-10) < tol: return m_new
        m = 0.6*m_new + 0.4*m
    return m

def mape(params):
    a,g = params
    if a<=0: return 1e9
    return np.mean([abs(solve(q,assignment[q],a,g)-constituent_masses[q])/constituent_masses[q] for q in quarks])*100

print("Optimizing alpha and gamma...")
res = differential_evolution(mape,[(0.01,5.0),(-1.0,1.0)],seed=42,maxiter=800,tol=1e-9,popsize=25)
a,g = res.x
print(f"\n  alpha = {a:.5f}")
print(f"  gamma = {g:.5f}  (precession coupling)")
print(f"  MAPE  = {res.fun:.3f}%\n")
print(f"{'Quark':>10}  {'Res':>4}  {'t0':>8}  {'t_eff':>8}  {'m_cur':>8}  {'m_QCD':>8}  {'m_model':>9}  {'delta%':>8}")
print("-"*75)
for q in quarks:
    r=assignment[q]; t0=angles_720[r]; m_c=current_masses[q]; m_q=constituent_masses[q]
    m_m=solve(q,r,a,g); t_f=t0+g*(m_m/LAMBDA_QCD)*(180/np.pi)
    print(f"{q:>10}  {r:>4}  {t0:>7.1f}d  {t_f:>7.1f}d  {m_c:>8.1f}  {m_q:>8.1f}  {m_m:>9.1f}  {(m_m-m_q)/m_q*100:>+8.2f}%")

unused=[r for r in residues if r not in assignment.values()]
print(f"\nUnused residues: {unused} -> angles {[angles_720[r] for r in unused]} deg")
print("  (mirror fermion / dark matter slots)")
