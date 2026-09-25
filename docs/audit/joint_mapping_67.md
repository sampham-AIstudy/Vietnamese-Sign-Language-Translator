# SPEC 67-JOINT REPRESENTATION & TOPOLOGY
**Vietnamese Sign Language Recognition (VSLR)**  
**Status:** FROZEN FOR RAW VIDEO PIPELINE  
**Date:** 2026-09-12  
**Specification Owner:** Senior CV + DL Engineer  

---

## 1. Overview & Rationale

1. **Rejection of 76-Joint Fictitious Spec**:
   - The workspace, code, and reference papers contain no definition for 76 joints.
   - Per Global Rule 0 & Rule 3: No ungrounded joint assumptions are permitted.
2. **Adoption of Standard 67-Joint Layout**:
   - The existing code (`src/data/extract_landmarks.py`, `src/models/stgcn.py`) uses $D = 201$ dimensions, which is exactly $67 \text{ joints} \times 3 \text{ coordinates } (x, y, z)$.
   - 67 joints capture:
     - **Upper-body pose** (25 joints): Face silhouette anchor, shoulders, elbows, wrists, torso hips.
     - **Left hand** (21 joints): Full finger articulation.
     - **Right hand** (21 joints): Full finger articulation.
   - Lower body (knees, feet: landmarks 25..32 of MediaPipe Pose) is omitted as signers are seated or standing with hands operating in the upper torso signing space.

---

## 2. Joint Index Table (0 to 66)

### Group A: Upper-Body Pose (Indices 0..24, 25 joints)
Sourced from MediaPipe Holistic Pose landmarks $0$ to $24$:

| Global Index | MediaPipe Landmark Name | Anatomical Description |
| :---: | :--- | :--- |
| **0** | `NOSE` | Center facial anchor / head orientation |
| **1** | `LEFT_EYE_INNER` | Left eye inner corner |
| **2** | `LEFT_EYE` | Left pupil / eye center |
| **3** | `LEFT_EYE_OUTER` | Left eye outer corner |
| **4** | `RIGHT_EYE_INNER` | Right eye inner corner |
| **5** | `RIGHT_EYE` | Right pupil / eye center |
| **6** | `RIGHT_EYE_OUTER` | Right eye outer corner |
| **7** | `LEFT_EAR` | Left ear |
| **8** | `RIGHT_EAR` | Right ear |
| **9** | `MOUTH_LEFT` | Left mouth corner |
| **10** | `MOUTH_RIGHT` | Right mouth corner |
| **11** | `LEFT_SHOULDER` | Left shoulder joint (key torso anchor) |
| **12** | `RIGHT_SHOULDER` | Right shoulder joint (key torso anchor) |
| **13** | `LEFT_ELBOW` | Left elbow |
| **14** | `RIGHT_ELBOW` | Right elbow |
| **15** | `LEFT_WRIST` | Left wrist (pose stream) |
| **16** | `RIGHT_WRIST` | Right wrist (pose stream) |
| **17** | `LEFT_PINKY` | Left hand outer knuckle (pose stream) |
| **18** | `RIGHT_PINKY` | Right hand outer knuckle (pose stream) |
| **19** | `LEFT_INDEX` | Left hand pointer knuckle (pose stream) |
| **20** | `RIGHT_INDEX` | Right hand pointer knuckle (pose stream) |
| **21** | `LEFT_THUMB` | Left hand thumb base (pose stream) |
| **22** | `RIGHT_THUMB` | Right hand thumb base (pose stream) |
| **23** | `LEFT_HIP` | Left hip joint (torso base anchor) |
| **24** | `RIGHT_HIP` | Right hip joint (torso base anchor) |

---

### Group B: Left Hand Articulation (Indices 25..45, 21 joints)
Sourced from MediaPipe Holistic Left Hand landmarks $0$ to $20$:

| Global Index | Local Hand Index | Joint Name | Anatomical Description |
| :---: | :---: | :--- | :--- |
| **25** | 0 | `LH_WRIST` | Left hand wrist root |
| **26** | 1 | `LH_THUMB_CMC` | Thumb carpometacarpal joint |
| **27** | 2 | `LH_THUMB_MCP` | Thumb metacarpophalangeal joint |
| **28** | 3 | `LH_THUMB_IP` | Thumb interphalangeal joint |
| **29** | 4 | `LH_THUMB_TIP` | Thumb tip |
| **30** | 5 | `LH_INDEX_MCP` | Index finger metacarpophalangeal |
| **31** | 6 | `LH_INDEX_PIP` | Index finger proximal interphalangeal |
| **32** | 7 | `LH_INDEX_DIP` | Index finger distal interphalangeal |
| **33** | 8 | `LH_INDEX_TIP` | Index finger tip |
| **34** | 9 | `LH_MIDDLE_MCP` | Middle finger metacarpophalangeal |
| **35** | 10 | `LH_MIDDLE_PIP` | Middle finger proximal interphalangeal |
| **36** | 11 | `LH_MIDDLE_DIP` | Middle finger distal interphalangeal |
| **37** | 12 | `LH_MIDDLE_TIP` | Middle finger tip |
| **38** | 13 | `LH_RING_MCP` | Ring finger metacarpophalangeal |
| **39** | 14 | `LH_RING_PIP` | Ring finger proximal interphalangeal |
| **40** | 15 | `LH_RING_DIP` | Ring finger distal interphalangeal |
| **41** | 16 | `LH_RING_TIP` | Ring finger tip |
| **42** | 17 | `LH_PINKY_MCP` | Pinky finger metacarpophalangeal |
| **43** | 18 | `LH_PINKY_PIP` | Pinky finger proximal interphalangeal |
| **44** | 19 | `LH_PINKY_DIP` | Pinky finger distal interphalangeal |
| **45** | 20 | `LH_PINKY_TIP` | Pinky finger tip |

---

### Group C: Right Hand Articulation (Indices 46..66, 21 joints)
Sourced from MediaPipe Holistic Right Hand landmarks $0$ to $20$:

| Global Index | Local Hand Index | Joint Name | Anatomical Description |
| :---: | :---: | :--- | :--- |
| **46** | 0 | `RH_WRIST` | Right hand wrist root |
| **47** | 1 | `RH_THUMB_CMC` | Thumb carpometacarpal joint |
| **48** | 2 | `RH_THUMB_MCP` | Thumb metacarpophalangeal joint |
| **49** | 3 | `RH_THUMB_IP` | Thumb interphalangeal joint |
| **50** | 4 | `RH_THUMB_TIP` | Thumb tip |
| **51** | 5 | `RH_INDEX_MCP` | Index finger metacarpophalangeal |
| **52** | 6 | `RH_INDEX_PIP` | Index finger proximal interphalangeal |
| **53** | 7 | `RH_INDEX_DIP` | Index finger distal interphalangeal |
| **54** | 8 | `RH_INDEX_TIP` | Index finger tip |
| **55** | 9 | `RH_MIDDLE_MCP` | Middle finger metacarpophalangeal |
| **56** | 10 | `RH_MIDDLE_PIP` | Middle finger proximal interphalangeal |
| **57** | 11 | `RH_MIDDLE_DIP` | Middle finger distal interphalangeal |
| **58** | 12 | `RH_MIDDLE_TIP` | Middle finger tip |
| **59** | 13 | `RH_RING_MCP` | Ring finger metacarpophalangeal |
| **60** | 14 | `RH_RING_PIP` | Ring finger proximal interphalangeal |
| **61** | 15 | `RH_RING_DIP` | Ring finger distal interphalangeal |
| **62** | 16 | `RH_RING_TIP` | Ring finger tip |
| **63** | 17 | `RH_PINKY_MCP` | Pinky finger metacarpophalangeal |
| **64** | 18 | `RH_PINKY_PIP` | Pinky finger proximal interphalangeal |
| **65** | 19 | `RH_PINKY_DIP` | Pinky finger distal interphalangeal |
| **66** | 20 | `RH_PINKY_TIP` | Pinky finger tip |

---

## 3. Coordinate Representation & Missing Landmark Strategy

### 3.1 Dimensions per Frame
* Coordinate format: $(x, y, z) \in \mathbb{R}^3$, normalized image coordinates.
* Sequence shape for $T$ frames:
  - Flattened: $[T, 201]$ where $201 = 67 \times 3$.
  - Structured: $[T, 67, 3]$.
  - PyTorch ST-GCN tensor format: $[B, C=3, T, V=67]$.

### 3.2 Strict Rule on Missing Landmarks (No Zero-Padding)
* **The Problem with Zeros**: In coordinate normalization, $(0.0, 0.0, 0.0)$ is a valid normalized spatial position (often the bounding box top-left corner or torso center). Filling missing hands with zeros creates severe geometric distortion and false motion vectors.
* **New Preprocessing Standard**:
  1. **Binary Visibility / Presence Mask**: For each frame and joint, generate a mask $M_{t, v} \in \{0, 1\}$ indicating whether the landmark was genuinely detected.
  2. **Temporal Interpolation**: If a hand is missing for isolated frames within an active sequence, apply linear interpolation between the nearest detected anchor frames.
  3. **Absence Masking**: If a hand is completely absent throughout the sign (e.g. one-handed signs), its coordinates are held at the corresponding wrist pose anchor (joint 15 or 16) with visibility mask $= 0$, allowing attention/graph layers to ignore inactive nodes.

---

## 4. Anatomical Graph Adjacency for ST-GCN

The adjacency matrix $A \in \{0, 1\}^{67 \times 67}$ reflects real human biomechanics:

1. **Torso & Head Edges**:
   - `(0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6)` (Eyes)
   - `(0, 9), (0, 10), (9, 10)` (Mouth)
   - `(11, 12)` (Shoulder link)
   - `(11, 23), (12, 24), (23, 24)` (Torso polygon)
2. **Arms**:
   - Left: `(11, 13)` (Shoulder-Elbow), `(13, 15)` (Elbow-Wrist)
   - Right: `(12, 14)` (Shoulder-Elbow), `(14, 16)` (Elbow-Wrist)
3. **Wrist-to-Hand Bridge**:
   - Left: `(15, 25)` (Pose left wrist connects to Left hand wrist root)
   - Right: `(16, 46)` (Pose right wrist connects to Right hand wrist root)
4. **Hands Internal (per hand)**:
   - Palm root to metacarpals: `Wrist -> [Thumb CMC, Index MCP, Middle MCP, Ring MCP, Pinky MCP]`
   - Metacarpal base links: `Index MCP - Middle MCP - Ring MCP - Pinky MCP`
   - Finger chain links: `MCP -> PIP -> DIP -> TIP` for all 5 digits.

This adjacency specification replaces the naive uniform matrix in `src/models/stgcn.py` and establishes an audit-safe graph topology.
