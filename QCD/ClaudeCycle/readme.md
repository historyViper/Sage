# Exact Chirality Structure in the Claude Hamiltonian Cycle Construction

This repository contains analysis of the Hamiltonian cycle decomposition discovered by Claude Opus 4.6 and reported by Donald Knuth (2026) for the Cayley digraph:

Cay(Z_m^3, {e0, e1, e2})

The work identifies a structural invariant called **cycle chirality** and proves an exact theorem describing the chirality of the three cycles.

## Main Result

For odd m ≥ 3, the three Hamiltonian cycles satisfy:

χ̂(C0) = 0  
χ̂(C1) = −3m(m−1)  
χ̂(C2) = −3

Thus one cycle accumulates quadratic chirality while the other two remain bounded.

## Contents

paper/  
Mathematical note describing the theorem and proof.

code/  
Python scripts verifying the chirality counts computationally.

data/  
Verification results for tested values of m.

## Reference

Donald E. Knuth, *Claude's Cycles*, Stanford CS Department, 2026.
