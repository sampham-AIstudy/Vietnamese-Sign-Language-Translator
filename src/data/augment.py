"""
Keypoint Augmentation Module for VSL Recognition.
Applies transformations directly on landmark sequences (T, D) and static keypoints (D):
- Gaussian jitter (small noise)
- Spatial scaling (zoom in / zoom out)
- Random 2D/3D rotation around center of mass
- Temporal warping / frame dropout (simulation of signing speed variations)
- Keypoint masking (simulating partial occlusion of hand or body)
"""

import numpy as np
from typing import Optional, Tuple


class KeypointAugmenter:
    def __init__(
        self,
        jitter_std: float = 0.008,
        scale_range: tuple = (0.9, 1.1),
        rotate_angle_range: float = 10.0,  # in degrees
        shear_range: float = 0.05,
        time_warp_ratio: float = 0.15,
        mask_prob: float = 0.05,
    ):
        self.jitter_std = jitter_std
        self.scale_range = scale_range
        self.rotate_angle_range = rotate_angle_range
        self.shear_range = shear_range
        self.time_warp_ratio = time_warp_ratio
        self.mask_prob = mask_prob

    def add_jitter(self, keypoints: np.ndarray) -> np.ndarray:
        """Adds small Gaussian noise to keypoints."""
        noise = np.random.normal(0, self.jitter_std, size=keypoints.shape).astype(np.float32)
        # Avoid adding noise to zero-padded entries
        mask = (keypoints != 0).astype(np.float32)
        return keypoints + noise * mask

    def random_scale(self, keypoints: np.ndarray) -> np.ndarray:
        """Scales keypoint positions around their center."""
        scale = np.random.uniform(self.scale_range[0], self.scale_range[1])
        return keypoints * scale

    def random_rotate_2d(self, keypoints: np.ndarray) -> np.ndarray:
        """
        Rotates (x, y) coordinates by a small random angle around the origin.
        Handles both (T, D) and (D,) where D can be flattened (N, 2) or (N, 3).
        """
        angle = np.radians(np.random.uniform(-self.rotate_angle_range, self.rotate_angle_range))
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        rot_matrix = np.array([[cos_a, -sin_a], [sin_a, cos_a]], dtype=np.float32)

        orig_shape = keypoints.shape
        data = keypoints.copy()

        if len(orig_shape) == 1 and orig_shape[0] % 2 == 0 and orig_shape[0] == 42:
            # 21 points * 2
            pts = data.reshape(-1, 2)
            pts_rot = np.dot(pts, rot_matrix)
            return pts_rot.flatten()
        elif len(orig_shape) == 2 and orig_shape[1] == 201:
            # 67 points * 3 per frame (pose 25, lh 21, rh 21)
            T, D = orig_shape
            pts = data.reshape(T, 67, 3)
            # Rotate xy plane
            xy = pts[:, :, :2]
            xy_rot = np.matmul(xy, rot_matrix)
            pts[:, :, :2] = xy_rot
            return pts.reshape(T, D)

        return data

    def time_warp(self, sequence: np.ndarray) -> np.ndarray:
        """Slightly speeds up or slows down temporal pacing of the gesture sequence."""
        T, D = sequence.shape
        warp_factor = np.random.uniform(1.0 - self.time_warp_ratio, 1.0 + self.time_warp_ratio)
        new_T = max(10, int(T * warp_factor))

        old_indices = np.linspace(0, T - 1, new_T)
        warped = np.zeros((new_T, D), dtype=np.float32)
        for d in range(D):
            warped[:, d] = np.interp(old_indices, np.arange(T), sequence[:, d])

        # Resample back to original T=60
        resampled_indices = np.linspace(0, new_T - 1, T)
        final_seq = np.zeros((T, D), dtype=np.float32)
        for d in range(D):
            final_seq[:, d] = np.interp(resampled_indices, np.arange(new_T), warped[:, d])

        return final_seq

    def keypoint_mask(self, sequence: np.ndarray) -> np.ndarray:
        """Randomly masks out keypoints (e.g. hand temporarily occluded)."""
        data = sequence.copy()
        if np.random.rand() < self.mask_prob:
            # Mask left hand (indices 75 to 138) or right hand (138 to 201)
            hand_choice = np.random.choice(["left", "right"])
            if hand_choice == "left" and data.shape[1] == 201:
                data[:, 75:138] = 0.0
            elif hand_choice == "right" and data.shape[1] == 201:
                data[:, 138:201] = 0.0
        return data

    def augment_sequence(self, sequence: np.ndarray) -> np.ndarray:
        """Applies full augmentation pipeline for a temporal gesture sequence (T, 201)."""
        seq = sequence.copy()
        if np.random.rand() > 0.5:
            seq = self.add_jitter(seq)
        if np.random.rand() > 0.5:
            seq = self.random_scale(seq)
        if np.random.rand() > 0.5:
            seq = self.random_rotate_2d(seq)
        if np.random.rand() > 0.5:
            seq = self.time_warp(seq)
        if np.random.rand() > 0.3:
            seq = self.keypoint_mask(seq)
        return seq

    def augment_static(self, keypoints: np.ndarray) -> np.ndarray:
        """Applies augmentation pipeline for static hand keypoints (42,)."""
        kp = keypoints.copy()
        if np.random.rand() > 0.5:
            kp = self.add_jitter(kp)
        if np.random.rand() > 0.5:
            kp = self.random_scale(kp)
        if np.random.rand() > 0.5:
            kp = self.random_rotate_2d(kp)
        return kp

    def augment_vsl_sequence(
        self,
        sequence: np.ndarray,
        joint_mask: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Augmentation pipeline for 67-joint normalized sequence [T, 67, 3] and joint_mask [T, 67].
        Guarantees:
          - No NaNs or Infs
          - Inactive/masked joints remain zero and mask is preserved
          - Spatial and temporal invariance learning
        """
        seq = sequence.copy().astype(np.float32)
        jmask = joint_mask.copy().astype(np.float32)
        T, V, C = seq.shape

        # 1. Random Scale (Zoom in / Zoom out)
        if np.random.rand() > 0.3:
            scale = np.random.uniform(self.scale_range[0], self.scale_range[1])
            seq = seq * scale

        # 2. Random 2D Rotation (Roll in xy plane around origin)
        if np.random.rand() > 0.3:
            angle = np.radians(np.random.uniform(-self.rotate_angle_range, self.rotate_angle_range))
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            rot_matrix = np.array([[cos_a, -sin_a], [sin_a, cos_a]], dtype=np.float32)
            xy = seq[:, :, :2]
            xy_rot = np.matmul(xy, rot_matrix)
            seq[:, :, :2] = xy_rot

        # 3. Random 2D Shear
        if np.random.rand() > 0.5:
            shear = np.random.uniform(-self.shear_range, self.shear_range)
            seq[:, :, 0] = seq[:, :, 0] + shear * seq[:, :, 1]

        # 4. Temporal Time Warping (Pacing / Speed Variation)
        if np.random.rand() > 0.4:
            warp_factor = np.random.uniform(1.0 - self.time_warp_ratio, 1.0 + self.time_warp_ratio)
            new_T = max(20, int(T * warp_factor))
            old_idx = np.linspace(0, T - 1, new_T)
            warped_seq = np.zeros((new_T, V, C), dtype=np.float32)
            for v in range(V):
                for c in range(C):
                    warped_seq[:, v, c] = np.interp(old_idx, np.arange(T), seq[:, v, c])
            
            resampled_idx = np.linspace(0, new_T - 1, T)
            for v in range(V):
                for c in range(C):
                    seq[:, v, c] = np.interp(resampled_idx, np.arange(new_T), warped_seq[:, v, c])

        # 5. Gaussian Jitter (applied only to active joints)
        if np.random.rand() > 0.3:
            noise = np.random.normal(0, self.jitter_std, size=seq.shape).astype(np.float32)
            seq = seq + noise * jmask[:, :, None]

        # 6. Random Partial Hand Occlusion
        if np.random.rand() < self.mask_prob:
            # 25..45 is left hand, 46..66 is right hand
            drop_hand = np.random.choice(["lh", "rh"])
            hand_slice = slice(25, 46) if drop_hand == "lh" else slice(46, 67)
            jmask[:, hand_slice] = 0.0
            seq[:, hand_slice, :] = 0.0

        return seq.astype(np.float32), jmask.astype(np.float32)
