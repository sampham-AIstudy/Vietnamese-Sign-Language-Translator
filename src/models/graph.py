"""
Graph Topology and Adjacency Matrix Builder for 67-Joint VSLR Skeleton
Follows Yan et al. (AAAI 2018) Spatial Temporal Graph Convolutional Networks (ST-GCN).

Joints:
  - 0..24: Upper-body pose (25 joints)
  - 25..45: Left hand (21 joints)
  - 46..66: Right hand (21 joints)
  Total: 67 joints

Partitioning Strategies:
  - 'spatial': Spatial configuration partitioning (K=3: Root, Centripetal, Centrifugal)
  - 'uniform': Standard uniform graph convolution with self-loops (K=1)
"""

import numpy as np
import torch
from typing import List, Tuple, Optional


class VSLGraph:
    """
    Biomechanical Skeleton Graph for 67 MediaPipe Holistic Keypoints.
    """
    def __init__(
        self,
        strategy: str = "spatial",
        max_hop: int = 1,
        dilation: int = 1,
    ):
        self.num_nodes = 67
        self.strategy = strategy
        self.max_hop = max_hop
        self.dilation = dilation

        # 1. Define Edges
        self.edges = self._get_anatomical_edges()
        self.self_loops = [(i, i) for i in range(self.num_nodes)]

        # 2. Compute Hop Distance Matrix
        self.hop_matrix = self._compute_hop_matrix()

        # 3. Choose Center Node: Mid-shoulder anchor (Joints 11 and 12)
        # We define distance from torso center (min distance to joint 11 or 12)
        self.center_nodes = [11, 12]
        self.node_center_distances = self._compute_center_distances()

        # 4. Build Partitioned Adjacency Tensor A of shape [K, V, V]
        self.A = self._build_adjacency_matrix()

    def _get_anatomical_edges(self) -> List[Tuple[int, int]]:
        """
        Defines biomechanically valid edges across upper-body pose and two hands.
        """
        edges = []

        # --- A. Pose Upper-Body (0..24) ---
        # Eyes & Ears
        edges += [(0, 1), (1, 2), (2, 3), (3, 7)]
        edges += [(0, 4), (4, 5), (5, 6), (6, 8)]
        # Mouth
        edges += [(0, 9), (0, 10), (9, 10)]
        # Head to Shoulders & Torso
        edges += [(0, 11), (0, 12)]
        edges += [(11, 12)]  # Shoulder link
        edges += [(11, 23), (12, 24), (23, 24)]  # Torso polygon
        # Left Arm
        edges += [(11, 13), (13, 15)]
        edges += [(15, 17), (15, 19), (15, 21), (17, 19)]
        # Right Arm
        edges += [(12, 14), (14, 16)]
        edges += [(16, 18), (16, 20), (16, 22), (18, 20)]

        # --- B. Wrist-to-Hand Bridges ---
        # Left Wrist (Pose 15) -> Left Hand Root (25)
        edges += [(15, 25)]
        # Right Wrist (Pose 16) -> Right Hand Root (46)
        edges += [(16, 46)]

        # --- C. Left Hand (25..45, offset = 25) ---
        lo = 25
        # Palm root to finger bases
        edges += [(lo + 0, lo + 1), (lo + 0, lo + 5), (lo + 0, lo + 9), (lo + 0, lo + 13), (lo + 0, lo + 17)]
        # Palm knuckle transverse connections
        edges += [(lo + 5, lo + 9), (lo + 9, lo + 13), (lo + 13, lo + 17)]
        # Thumb digit
        edges += [(lo + 1, lo + 2), (lo + 2, lo + 3), (lo + 3, lo + 4)]
        # Index digit
        edges += [(lo + 5, lo + 6), (lo + 6, lo + 7), (lo + 7, lo + 8)]
        # Middle digit
        edges += [(lo + 9, lo + 10), (lo + 10, lo + 11), (lo + 11, lo + 12)]
        # Ring digit
        edges += [(lo + 13, lo + 14), (lo + 14, lo + 15), (lo + 15, lo + 16)]
        # Pinky digit
        edges += [(lo + 17, lo + 18), (lo + 18, lo + 19), (lo + 19, lo + 20)]

        # --- D. Right Hand (46..66, offset = 46) ---
        ro = 46
        # Palm root to finger bases
        edges += [(ro + 0, ro + 1), (ro + 0, ro + 5), (ro + 0, ro + 9), (ro + 0, ro + 13), (ro + 0, ro + 17)]
        # Palm knuckle transverse connections
        edges += [(ro + 5, ro + 9), (ro + 9, ro + 13), (ro + 13, ro + 17)]
        # Thumb digit
        edges += [(ro + 1, ro + 2), (ro + 2, ro + 3), (ro + 3, ro + 4)]
        # Index digit
        edges += [(ro + 5, ro + 6), (ro + 6, ro + 7), (ro + 7, ro + 8)]
        # Middle digit
        edges += [(ro + 9, ro + 10), (ro + 10, ro + 11), (ro + 11, ro + 12)]
        # Ring digit
        edges += [(ro + 13, ro + 14), (ro + 14, ro + 15), (ro + 15, ro + 16)]
        # Pinky digit
        edges += [(ro + 17, ro + 18), (ro + 18, ro + 19), (ro + 19, ro + 20)]

        # Make undirected (bidirectional)
        undirected_edges = set()
        for u, v in edges:
            undirected_edges.add((u, v))
            undirected_edges.add((v, u))

        return sorted(list(undirected_edges))

    def _compute_hop_matrix(self) -> np.ndarray:
        """Computes shortest path hop distance between all pairs of nodes."""
        V = self.num_nodes
        dist = np.full((V, V), np.inf)
        np.fill_diagonal(dist, 0)

        for u, v in self.edges:
            dist[u, v] = 1
            dist[v, u] = 1

        # Floyd-Warshall algorithm for shortest paths
        for k in range(V):
            for i in range(V):
                for j in range(V):
                    if dist[i, k] + dist[k, j] < dist[i, j]:
                        dist[i, j] = dist[i, k] + dist[k, j]

        return dist

    def _compute_center_distances(self) -> np.ndarray:
        """Computes distance of each node to the shoulder/torso center."""
        # Minimum hop distance to either left shoulder (11) or right shoulder (12)
        dists = np.minimum(self.hop_matrix[11, :], self.hop_matrix[12, :])
        return dists

    def _build_adjacency_matrix(self) -> np.ndarray:
        """Builds normalized partitioned adjacency tensor of shape [K, V, V]."""
        V = self.num_nodes

        if self.strategy == "uniform":
            A = np.zeros((1, V, V), dtype=np.float32)
            for u, v in self.edges:
                A[0, u, v] = 1.0
            for i in range(V):
                A[0, i, i] = 1.0

            # Degree normalize: D^{-1} A
            D = np.sum(A[0], axis=1, keepdims=True)
            A[0] = A[0] / np.clip(D, a_min=1e-6, a_max=None)
            return A

        elif self.strategy == "spatial":
            # 3 Subsets:
            # 0: Root node (v_j == v_i)
            # 1: Centripetal (d(v_j, center) < d(v_i, center))
            # 2: Centrifugal (d(v_j, center) > d(v_i, center))
            A = np.zeros((3, V, V), dtype=np.float32)

            for i in range(V):
                for j in range(V):
                    # Neighbors within 1 hop (or self)
                    if self.hop_matrix[i, j] <= 1:
                        if i == j:
                            A[0, i, j] = 1.0  # Root
                        elif self.node_center_distances[j] < self.node_center_distances[i]:
                            A[1, i, j] = 1.0  # Centripetal (closer to torso center)
                        else:
                            A[2, i, j] = 1.0  # Centrifugal (farther or equal)

            # Normalize each partition matrix: D_k^{-1} A_k
            for k in range(3):
                D = np.sum(A[k], axis=1, keepdims=True)
                A[k] = A[k] / np.clip(D, a_min=1e-6, a_max=None)

            return A

        else:
            raise ValueError(f"Unknown graph strategy: {self.strategy}")

    def get_adjacency(self) -> torch.Tensor:
        """Returns adjacency tensor as PyTorch FloatTensor of shape [K, V, V]."""
        return torch.from_numpy(self.A).float()
