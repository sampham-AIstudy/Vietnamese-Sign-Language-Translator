# Anatomical & Spatial Graph Landmark Mapping Audit Report

This report presents a thorough audit of the spatial graph semantics comparing the current project's 67-joint definition against VSL-GH's extracted landmarks under both **Direct** and **Semantic** mapping configurations.

---

## 1. Summary of Landmark Representations

| Parameter | Current Project (QIPEDC / CleanHolistic) | VSL-GH Raw Keypoints |
| :--- | :--- | :--- |
| **Total Features per Frame** | $67 \times 3 = 201$ | $137 \times 3 = 411$ |
| **Pose Landmarks** | 25 joints (sequential MP Pose 0..24) | 25 joints (selected MP Pose subsets) |
| **Face Landmarks** | Omitted (focus on body & hands) | 70 landmarks (MP FaceMesh subsets) |
| **Left Hand Landmarks** | 21 joints (MP Hands 0..20) | 21 joints (MP Hands 0..20) |
| **Right Hand Landmarks** | 21 joints (MP Hands 0..20) | 21 joints (MP Hands 0..20) |

---

## 2. Joint-by-Joint Semantic Comparison Table (0 to 66)

| Joint ID | Current Project Meaning (`VSLGraph`) | VSL-GH Direct Mode Meaning (`mode="direct"`) | VSL-GH Semantic Mode Meaning (`mode="semantic"`) | Compatibility Status |
| :---: | :--- | :--- | :--- | :---: |
| **0** | Nose (MP 0) | Nose (MP 0) | Nose (MP 0) | Match |
| **1** | Left Eye Inner (MP 1) | Left Eye Inner (MP 1) | Left Eye Inner (MP 1) | Match |
| **2** | Left Eye (MP 2) | Left Eye (MP 2) | Left Eye (MP 2) | Match |
| **3** | Left Eye Outer (MP 3) | Left Eye Outer (MP 3) | Left Eye Outer (MP 3) | Match |
| **4** | Right Eye Inner (MP 4) | Right Eye Inner (MP 4) | Right Eye Inner (MP 4) | Match |
| **5** | Right Eye (MP 5) | Right Eye (MP 5) | Right Eye (MP 5) | Match |
| **6** | Right Eye Outer (MP 6) | Right Eye Outer (MP 6) | Right Eye Outer (MP 6) | Match |
| **7** | Left Ear (MP 7) | Left Ear (MP 7) | Left Ear (MP 7) | Match |
| **8** | Right Ear (MP 8) | Right Ear (MP 8) | Right Ear (MP 8) | Match |
| **9** | **Mouth Left** (MP 9) | **Left Shoulder** (MP 11) | **Mouth Left** (FaceMesh 61) | **Divergence in Direct** |
| **10** | **Mouth Right** (MP 10) | **Right Shoulder** (MP 12) | **Mouth Right** (FaceMesh 291) | **Divergence in Direct** |
| **11** | **Left Shoulder** (MP 11) | **Left Elbow** (MP 13) | **Left Shoulder** (MP 11) | **Divergence in Direct** |
| **12** | **Right Shoulder** (MP 12) | **Right Elbow** (MP 14) | **Right Shoulder** (MP 12) | **Divergence in Direct** |
| **13** | **Left Elbow** (MP 13) | **Left Wrist** (MP 15) | **Left Elbow** (MP 13) | **Divergence in Direct** |
| **14** | **Right Elbow** (MP 14) | **Right Wrist** (MP 16) | **Right Elbow** (MP 14) | **Divergence in Direct** |
| **15** | **Left Wrist** (MP 15) | **Left Pinky** (MP 17) | **Left Wrist** (MP 15) | **Divergence in Direct** |
| **16** | **Right Wrist** (MP 16) | **Right Pinky** (MP 18) | **Right Wrist** (MP 16) | **Divergence in Direct** |
| **17** | **Left Pinky** (MP 17) | **Left Index** (MP 19) | **Left Pinky** (MP 17) | **Divergence in Direct** |
| **18** | **Right Pinky** (MP 18) | **Right Index** (MP 20) | **Right Pinky** (MP 18) | **Divergence in Direct** |
| **19** | **Left Index** (MP 19) | **Left Hip** (MP 23) | **Left Index** (MP 19) | **Divergence in Direct** |
| **20** | **Right Index** (MP 20) | **Right Hip** (MP 24) | **Right Index** (MP 20) | **Divergence in Direct** |
| **21** | **Left Thumb** (MP 21) | **Left Knee** (MP 25) | **Left Thumb** (LH Joint 4 tip) | **Divergence in Direct** |
| **22** | **Right Thumb** (MP 22) | **Right Knee** (MP 26) | **Right Thumb** (RH Joint 4 tip) | **Divergence in Direct** |
| **23** | **Left Hip** (MP 23) | **Left Ankle** (MP 27) | **Left Hip** (MP 23) | **Divergence in Direct** |
| **24** | **Right Hip** (MP 24) | **Right Ankle** (MP 28) | **Right Hip** (MP 24) | **Divergence in Direct** |
| **25..45**| **Left Hand** (21 joints) | **Left Hand** (21 joints) | **Left Hand** (21 joints) | **100% Identical** |
| **46..66**| **Right Hand** (21 joints)| **Right Hand** (21 joints)| **Right Hand** (21 joints)| **100% Identical** |

---

## 3. Impact on Graph Topology (`VSLGraph`) and Spatial Normalization

### 3.1 Anatomical Edge Inconsistencies in Direct Mode
The pre-existing `VSLGraph` (`src/models/graph.py`) encodes specific biomechanical linkages:
1. **Shoulder Link**: Edge `(11, 12)`.
   - In *Semantic Mode*: Connects Left Shoulder (11) to Right Shoulder (12).
   - In *Direct Mode*: Connects Left Elbow (11) to Right Elbow (12).
2. **Arm Chains**: Edges `(11, 13)` and `(13, 15)`.
   - In *Semantic Mode*: Connects Shoulder $\to$ Elbow $\to$ Wrist.
   - In *Direct Mode*: Connects Elbow $\to$ Wrist $\to$ Pinky.
3. **Hand Bridges**: Edges `(15, 25)` (Left) and `(16, 46)` (Right).
   - In *Semantic Mode*: Connects Pose Wrist (15) to Left Hand Root (25).
   - In *Direct Mode*: Connects Pose Pinky (15) to Left Hand Root (25).
4. **Torso Connections**: Edges `(11, 23)` and `(12, 24)`.
   - In *Semantic Mode*: Connects Shoulders to Hips.
   - In *Direct Mode*: Connects Elbows to Ankles.
5. **Graph Center Nodes**: `self.center_nodes = [11, 12]`.
   - Expected: Mid-shoulder.
   - In *Direct Mode*: Centers on mid-elbow.

### 3.2 Spatial Normalizer Impact
In `SpatialNormalizer` (`src/data/preprocessing/spatial.py`):
```python
NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24
```
If `mode="direct"` is used, spatial normalization centers around the elbows instead of shoulders, and scales relative to inter-elbow distance instead of shoulder width.

---

## 4. Canonical Decision

### Recommended Decision: **SEMANTIC MAPPING (`mode="semantic"`)**
**Reasoning**:
1. **Graph Preservation**: The pretrained spatial weights of ST-GCN in `stgcn_best.pt` (`blocks.0`, `blocks.1`, `blocks.2`) were learned on adjacency matrix $A$ where node 11 is Shoulder, node 13 is Elbow, node 15 is Wrist, and node 25 is Left Hand Root.
2. **Transfer Learning**: Transferring weights from `stgcn_best.pt` into CSLR requires semantic correspondence; feeding scrambled joint indices through pretrained GCN edge importance weights degrades spatial inductive bias.
3. **Face Information**: Semantic mapping recovers mouth corners from VSL-GH's face mesh (indices 61 and 291), providing facial articulation cues critical for distinguishing homophenous Vietnamese signs.
4. **Hand Consistency**: Both hands (joints 25..66, 42 joints) are completely identical across both modes.

### Provability Status:
- **Verified**: Tensor shapes, absence of NaNs, and graph edge traversal have been verified.
- **Empirical Confirmation Test Plan**: In the dry-run and future baseline validation, we evaluate both modes; semantic mapping is set as canonical default for CSLR.
