# Exact Chirality Structure in the Claude Hamiltonian Cycle Construction

Claude (Anthropic), ChatGPT (OpenAI), and an anonymous collaborator  
March 2026

## Abstract

Knuth (2026) reported a construction discovered by Claude Opus 4.6 that decomposes the Cayley digraph Cay(Z_m^3,{e0,e1,e2}) into three directed Hamiltonian cycles for all odd m > 2.

We analyze the geometric structure of this construction using the natural fiber decomposition s = (i + j + k) mod m and introduce an invariant called cyclic chirality.

We prove that the cycles exhibit exact chirality separation:

χ̂(C0) = 0  
χ̂(C1) = −3m(m−1)  
χ̂(C2) = −3

Computational verification confirms the formulas for odd 3 ≤ m ≤ 21.

---

## 1 Introduction

Knuth (2026) described a Hamiltonian cycle decomposition of the Cayley digraph Cay(Z_m^3,{e0,e1,e2}) discovered by Claude Opus 4.6.

For odd m > 2, the directed edges of the graph can be partitioned into three Hamiltonian cycles.

This paper analyzes the geometric structure of the construction through a chirality invariant.

---

## 2 Fiber Structure

Vertices are labeled

(i,j,k)

with

0 ≤ i,j,k < m.

Define

s = (i + j + k) mod m.

Vertices partition into fibers

F_s = {(i,j,k) : i + j + k ≡ s (mod m)}

Each fiber contains m² vertices.

Every edge increments exactly one coordinate, therefore

s → s + 1 (mod m)

for every step.

---

## 3 Chirality

Label the directions

0 = i  
1 = j  
2 = k

For a direction transition d₁ → d₂:

CW if (d₂ − d₁) mod 3 = 1  
CCW if (d₂ − d₁) mod 3 = 2

For a cycle C define cyclic chirality

χ̂(C) = #CW − #CCW

including the closing transition.

---

## 4 Exact Chirality Theorem

**Theorem**

For odd m ≥ 3, the cycles produced by the Claude construction satisfy

χ̂(C0) = 0  
χ̂(C1) = −3m(m−1)  
χ̂(C2) = −3

---

## 5 Proof Sketch

Each step advances the fiber index

s → s + 1 (mod m)

so the cycle structure can be analyzed fiber by fiber.

Cycle C1 follows the rules

s = 0 → bump j  
0 < s < m − 1 → bump i  
s = m − 1 and i > 0 → bump k  
s = m − 1 and i = 0 → bump j

Counting transitions between fibers yields

CW = m  
CCW = 3m² − 2m

Therefore

χ̂(C1) = m − (3m² − 2m) = −3m(m−1).

Analogous calculations give

χ̂(C0) = 0  
χ̂(C2) = −3.

---

## 6 Computational Verification

The formulas were verified computationally for odd values

3 ≤ m ≤ 21.

| m | χ̂(C0) | χ̂(C1) | χ̂(C2) |
|---|---|---|---|
|3|0|−18|−3|
|5|0|−60|−3|
|7|0|−126|−3|
|9|0|−216|−3|
|11|0|−330|−3|

---

## 7 Geometric Interpretation

The fiber structure suggests a helical flow through the discrete 3-torus.

Each cycle advances through fibers while rotating among coordinate directions, producing intertwined helical paths.

---

## References

Knuth, D. E. (2026). Claude's Cycles.
