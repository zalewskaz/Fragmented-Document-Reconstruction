import cv2
import numpy as np
import math
import copy
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class EdgeSegment:
    frag_idx: int
    edge_idx: int
    p1: np.ndarray          # Start point (x, y) in local fragment coordinates
    p2: np.ndarray          # End point (x, y) in local fragment coordinates
    midpoint: np.ndarray    # Midpoint (x, y)
    length: float           # Length in pixels
    tangent_angle: float    # Angle in degrees (-180 to 180)
    profile: np.ndarray     # 1D array of grayscale intensities sampled inside the edge
    gradient_profile: np.ndarray  # 1D derivative along the edge (captures text strokes)
    texture_std: float      # Standard deviation of the profile (measures information content)


@dataclass
class EdgeMatch:
    src_frag: int
    src_edge: int
    dst_frag: int
    dst_edge: int
    src_offset_t: float     # Normalized position [0, 1] along src_edge
    dst_offset_t: float     # Normalized position [0, 1] along dst_edge
    cost: float             # Lower is better


def estimate_text_angle(frag_data: np.ndarray) -> float:
    """
    Estimates the upright text line angle in [0, 360) degrees.
    First finds line orientation in [-90, 90) via horizontal projection variance,
    then resolves 0 vs 180-degree upside-down ambiguity using ascender/descender asymmetry.
    """
    alpha = frag_data[:, :, 3]
    gray = cv2.cvtColor(frag_data[:, :, :3], cv2.COLOR_BGR2GRAY)
    mask = alpha > 127

    ink = ((gray < 180) & mask).astype(np.uint8)
    if np.sum(ink) < 150:
        return None

    scale = min(1.0, 250.0 / max(ink.shape))
    if scale < 1.0:
        new_size = (max(1, int(ink.shape[1] * scale)), max(1, int(ink.shape[0] * scale)))
        ink = cv2.resize(ink, new_size, interpolation=cv2.INTER_NEAREST)

    h, w = ink.shape
    center = (w // 2, h // 2)
    best_angle = 0.0
    best_score = -1.0

    for angle in np.arange(-90.0, 90.0, 2.0):
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(ink, M, (w, h), flags=cv2.INTER_NEAREST)
        row_sums = np.sum(rotated, axis=1, dtype=np.float32)
        score = float(np.var(row_sums))
        if score > best_score:
            best_score = score
            best_angle = float(angle)

    for angle in np.arange(best_angle - 2.0, best_angle + 2.1, 0.25):
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(ink, M, (w, h), flags=cv2.INTER_NEAREST)
        row_sums = np.sum(rotated, axis=1, dtype=np.float32)
        score = float(np.var(row_sums))
        if score > best_score:
            best_score = score
            best_angle = float(angle)

    # Resolve 180-degree flip: Latin text has more ascenders (top half of lines) than descenders
    M_up = cv2.getRotationMatrix2D(center, best_angle, 1.0)
    rot_up = cv2.warpAffine(ink, M_up, (w, h), flags=cv2.INTER_NEAREST)
    row_profile = np.sum(rot_up, axis=1, dtype=np.float32)

    # Compare sharp upward jumps (top of capitals/ascenders) vs downward drops
    diffs = np.diff(row_profile)
    # In upright text, ink density ramps up sharply from top line spacing into ascenders/x-height
    top_heavy_score = float(np.sum(np.maximum(0.0, diffs) ** 2))
    bottom_heavy_score = float(np.sum(np.maximum(0.0, -diffs) ** 2))

    if bottom_heavy_score > top_heavy_score * 1.08:
        best_angle = (best_angle + 180.0) % 360.0

    return best_angle % 360.0


def extract_fragment_edges(fragments, min_edge_len: float = 35.0, sample_depth_px: int = 4) -> List[List[EdgeSegment]]:
    """
    Approximates each fragment's alpha contour as a polygon and extracts edge segments
    with multi-depth grayscale and gradient profiles.
    """
    all_edges: List[List[EdgeSegment]] = []

    for frag_idx, frag in enumerate(fragments):
        alpha = frag.data[:, :, 3]
        gray = cv2.cvtColor(frag.data[:, :, :3], cv2.COLOR_BGR2GRAY).astype(np.float32)
        # Light Gaussian blur reduces scanner grain noise while preserving text strokes
        gray_smooth = cv2.GaussianBlur(gray, (3, 3), 0)
        h, w = gray.shape

        binary_mask = (alpha > 127).astype(np.uint8)
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        if not contours:
            all_edges.append([])
            continue

        main_contour = max(contours, key=cv2.contourArea)
        epsilon = 0.012 * cv2.arcLength(main_contour, True)
        poly = cv2.approxPolyDP(main_contour, epsilon, True).reshape(-1, 2)
        num_vertices = len(poly)

        frag_edges: List[EdgeSegment] = []
        edge_counter = 0

        for i in range(num_vertices):
            p1 = poly[i].astype(np.float32)
            p2 = poly[(i + 1) % num_vertices].astype(np.float32)
            edge_vec = p2 - p1
            length = float(np.linalg.norm(edge_vec))

            if length < min_edge_len:
                continue

            unit_tangent = edge_vec / length
            tangent_angle = math.degrees(math.atan2(edge_vec[1], edge_vec[0]))

            perp_left = np.array([-unit_tangent[1], unit_tangent[0]], dtype=np.float32)
            perp_right = -perp_left
            mid = (p1 + p2) * 0.5

            test_left = np.clip(np.round(mid + perp_left * 6.0).astype(int), [0, 0], [w - 1, h - 1])
            inward_normal = perp_left if binary_mask[test_left[1], test_left[0]] > 0 else perp_right

            num_samples = max(12, int(length * 0.9))
            t_vals = np.linspace(0.05, 0.95, num_samples)

            # Average intensities across depths 2px..5px inward to capture both edge tone and cut text
            profiles_stack = []
            for d in range(2, sample_depth_px + 2):
                sample_pts = p1[None, :] + t_vals[:, None] * edge_vec[None, :] + inward_normal[None, :] * float(d)
                xs = np.clip(np.round(sample_pts[:, 0]).astype(int), 0, w - 1)
                ys = np.clip(np.round(sample_pts[:, 1]).astype(int), 0, h - 1)
                profiles_stack.append(gray_smooth[ys, xs])

            profile = np.mean(profiles_stack, axis=0)
            grad_profile = np.gradient(profile)
            texture_std = float(np.std(profile))

            frag_edges.append(EdgeSegment(
                frag_idx=frag_idx,
                edge_idx=edge_counter,
                p1=p1,
                p2=p2,
                midpoint=mid,
                length=length,
                tangent_angle=tangent_angle,
                profile=profile,
                gradient_profile=grad_profile,
                texture_std=texture_std
            ))
            edge_counter += 1

        all_edges.append(frag_edges)

    return all_edges


def compute_pairwise_matches(
    all_edges: List[List[EdgeSegment]],
    text_angles: List[float],
    top_k: int = 15
) -> Dict[Tuple[int, int], List[EdgeMatch]]:
    matches_map: Dict[Tuple[int, int], List[EdgeMatch]] = {}
    num_frags = len(all_edges)

    for i in range(num_frags):
        for edge_a in all_edges[i]:
            candidates: List[EdgeMatch] = []

            for j in range(num_frags):
                if i == j:
                    continue

                for edge_b in all_edges[j]:
                    rel_rot = (edge_b.tangent_angle - edge_a.tangent_angle - 180.0) % 360.0

                    if text_angles[i] is not None and text_angles[j] is not None:
                        # Check full 360-degree upright alignment (prevents upside-down 180 flips)
                        aligned_text_j = (text_angles[j] - rel_rot) % 360.0
                        ref_text_i = text_angles[i] % 360.0
                        angle_diff = abs(aligned_text_j - ref_text_i)
                        angle_diff = min(angle_diff, 360.0 - angle_diff)

                        # Allow small penalty if flipped 180 (in case ascender heuristic was uncertain on short text),
                        # but strictly reject sideways (90/270 deg) matches
                        if 15.0 < angle_diff < 165.0:
                            continue
                        orientation_penalty = angle_diff * 8.0
                    else:
                        orientation_penalty = 0.0

                    prof_a = edge_a.profile
                    prof_b_rev = edge_b.profile[::-1]
                    grad_a = edge_a.gradient_profile
                    grad_b_rev = -edge_b.gradient_profile[::-1]

                    len_a = len(prof_a)
                    len_b = len(prof_b_rev)
                    if min(len_a, len_b) < 12:
                        continue

                    length_ratio = min(edge_a.length, edge_b.length) / max(edge_a.length, edge_b.length)

                    # Corner snapping: if edges have nearly identical length, align midpoint-to-midpoint
                    if length_ratio > 0.90:
                        res_len = min(len_a, len_b)
                        pa = cv2.resize(prof_a.reshape(1, -1), (res_len, 1)).flatten()
                        pb = cv2.resize(prof_b_rev.reshape(1, -1), (res_len, 1)).flatten()
                        ga = cv2.resize(grad_a.reshape(1, -1), (res_len, 1)).flatten()
                        gb = cv2.resize(grad_b_rev.reshape(1, -1), (res_len, 1)).flatten()

                        best_visual_cost = float(np.mean((pa - pb) ** 2) + 2.5 * np.mean((ga - gb) ** 2))
                        best_src_t = 0.5
                        best_dst_t = 0.5
                    else:
                        best_visual_cost = float('inf')
                        best_src_t = 0.5
                        best_dst_t = 0.5

                        if len_a >= len_b:
                            max_shift = len_a - len_b
                            step = max(1, max_shift // 25) if max_shift > 0 else 1
                            for shift in range(0, max_shift + 1, step):
                                w_prof = prof_a[shift : shift + len_b]
                                w_grad = grad_a[shift : shift + len_b]
                                cost = float(np.mean((w_prof - prof_b_rev) ** 2) + 2.5 * np.mean((w_grad - grad_b_rev) ** 2))
                                if cost < best_visual_cost:
                                    best_visual_cost = cost
                                    best_src_t = (shift + len_b * 0.5) / len_a
                                    best_dst_t = 0.5
                        else:
                            max_shift = len_b - len_a
                            step = max(1, max_shift // 25) if max_shift > 0 else 1
                            for shift in range(0, max_shift + 1, step):
                                w_prof = prof_b_rev[shift : shift + len_a]
                                w_grad = grad_b_rev[shift : shift + len_a]
                                cost = float(np.mean((prof_a - w_prof) ** 2) + 2.5 * np.mean((grad_a - w_grad) ** 2))
                                if cost < best_visual_cost:
                                    best_visual_cost = cost
                                    best_src_t = 0.5
                                    best_dst_t = 1.0 - ((shift + len_a * 0.5) / len_b)

                    combined_std = min(edge_a.texture_std, edge_b.texture_std)
                    if combined_std < 6.0:
                        blank_edge_penalty = 650.0
                    else:
                        blank_edge_penalty = -min(350.0, combined_std * 8.0)

                    length_penalty = (1.0 - length_ratio) * 600.0
                    total_cost = best_visual_cost + orientation_penalty + blank_edge_penalty + length_penalty

                    candidates.append(EdgeMatch(
                        src_frag=i,
                        src_edge=edge_a.edge_idx,
                        dst_frag=j,
                        dst_edge=edge_b.edge_idx,
                        src_offset_t=best_src_t,
                        dst_offset_t=best_dst_t,
                        cost=total_cost
                    ))

            candidates.sort(key=lambda m: m.cost)
            matches_map[(i, edge_a.edge_idx)] = candidates[:top_k]

    return matches_map


def _transform_point(pt: Tuple[float, float], orig_w: int, orig_h: int, angle_deg: float) -> Tuple[Tuple[float, float], int, int]:
    center_x, center_y = orig_w // 2, orig_h // 2
    M = cv2.getRotationMatrix2D((center_x, center_y), angle_deg, 1.0)

    cos_val = np.abs(M[0, 0])
    sin_val = np.abs(M[0, 1])
    new_w = int((orig_h * sin_val) + (orig_w * cos_val))
    new_h = int((orig_h * cos_val) + (orig_w * sin_val))

    M[0, 2] += (new_w / 2.0) - center_x
    M[1, 2] += (new_h / 2.0) - center_y

    px, py = pt
    rot_x = M[0, 0] * px + M[0, 1] * py + M[0, 2]
    rot_y = M[1, 0] * px + M[1, 1] * py + M[1, 2]

    return (rot_x, rot_y), new_w, new_h


def _rotate_mask(mask: np.ndarray, angle: float) -> np.ndarray:
    h, w = mask.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    cos_val = np.abs(M[0, 0])
    sin_val = np.abs(M[0, 1])
    new_w = int((h * sin_val) + (w * cos_val))
    new_h = int((h * cos_val) + (w * sin_val))

    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]

    return cv2.warpAffine(mask, M, (new_w, new_h), flags=cv2.INTER_NEAREST)


class BeamState:
    def __init__(self, placed: Dict[int, List[float]], used_edges: set, seam_cost: float):
        self.placed = placed
        self.used_edges = used_edges
        self.seam_cost = seam_cost
        self.total_score = seam_cost


def solve_with_beam_search(
    fragments,
    all_edges: List[List[EdgeSegment]],
    matches_map: Dict[Tuple[int, int], List[EdgeMatch]],
    text_angles: List[float],
    board_width: int,
    board_height: int,
    beam_width: int = 80,
    scale_factor: float = 4.0,
    max_overlap_ratio: float = 0.025
) -> List[List[float]]:
    num_frags = len(fragments)

    # Hard spatial limits in downscaled coordinates (with 12% tolerance for irregular cuts)
    max_allowed_w = (board_width / scale_factor) * 1.12
    max_allowed_h = (board_height / scale_factor) * 1.12

    scaled_masks = []
    frag_areas = []
    for frag in fragments:
        alpha = frag.data[:, :, 3]
        binary = (alpha > 127).astype(np.uint8)
        frag_areas.append(int(np.sum(binary)))
        new_size = (max(1, int(binary.shape[1] / scale_factor)), max(1, int(binary.shape[0] / scale_factor)))
        scaled_masks.append(cv2.resize(binary, new_size, interpolation=cv2.INTER_NEAREST))

    root_idx = int(np.argmax(frag_areas))
    if text_angles[root_idx] is not None:
        root_rot = text_angles[root_idx] % 360.0
    elif all_edges[root_idx]:
        longest_edge = max(all_edges[root_idx], key=lambda e: e.length)
        nearest_90 = round(longest_edge.tangent_angle / 90.0) * 90.0
        root_rot = (longest_edge.tangent_angle - nearest_90) % 360.0
    else:
        root_rot = 0.0

    initial_state = BeamState(
        placed={root_idx: [0.0, 0.0, root_rot]},
        used_edges=set(),
        seam_cost=0.0
    )
    beam: List[BeamState] = [initial_state]

    for step in range(1, num_frags):
        next_candidates: List[BeamState] = []
        seen_signatures = set()

        for state in beam:
            for p_frag_idx, (px, py, prot) in state.placed.items():
                p_h, p_w = fragments[p_frag_idx].data.shape[:2]

                for p_edge in all_edges[p_frag_idx]:
                    if (p_frag_idx, p_edge.edge_idx) in state.used_edges:
                        continue

                    top_matches = matches_map.get((p_frag_idx, p_edge.edge_idx), [])
                    for match in top_matches:
                        c_frag_idx = match.dst_frag
                        if c_frag_idx in state.placed:
                            continue

                        c_edge = all_edges[c_frag_idx][match.dst_edge]
                        c_h, c_w = fragments[c_frag_idx].data.shape[:2]

                        p_global_tangent = (p_edge.tangent_angle - prot) % 360.0
                        target_c_tangent = (p_global_tangent + 180.0) % 360.0
                        c_rot = (c_edge.tangent_angle - target_c_tangent) % 360.0

                        p_local_pt = p_edge.p1 + match.src_offset_t * (p_edge.p2 - p_edge.p1)
                        c_local_pt = c_edge.p1 + match.dst_offset_t * (c_edge.p2 - c_edge.p1)

                        (p_rot_x, p_rot_y), _, _ = _transform_point((float(p_local_pt[0]), float(p_local_pt[1])), p_w, p_h, prot)
                        (c_rot_x, c_rot_y), _, _ = _transform_point((float(c_local_pt[0]), float(c_local_pt[1])), c_w, c_h, c_rot)

                        cx = (px + p_rot_x) - c_rot_x
                        cy = (py + p_rot_y) - c_rot_y

                        sig = (
                            tuple(sorted(list(state.placed.keys()) + [c_frag_idx])),
                            c_frag_idx,
                            int(round(cx / 15.0)),
                            int(round(cy / 15.0)),
                            int(round(c_rot / 5.0))
                        )
                        if sig in seen_signatures:
                            continue
                        seen_signatures.add(sig)

                        is_valid, overlap_penalty, bbox_fill_ratio, total_contact_px = _evaluate_placement(
                            placed=state.placed,
                            cand_idx=c_frag_idx,
                            cand_pose=[cx, cy, c_rot],
                            scaled_masks=scaled_masks,
                            scale_factor=scale_factor,
                            max_overlap_ratio=max_overlap_ratio,
                            max_w=max_allowed_w,
                            max_h=max_allowed_h
                        )

                        if not is_valid:
                            continue

                        new_placed = copy.deepcopy(state.placed)
                        new_placed[c_frag_idx] = [cx, cy, c_rot]

                        new_used_edges = set(state.used_edges)
                        new_used_edges.add((p_frag_idx, p_edge.edge_idx))
                        new_used_edges.add((c_frag_idx, c_edge.edge_idx))

                        new_seam_cost = state.seam_cost + match.cost
                        empty_space_penalty = (1.0 - bbox_fill_ratio) * 2800.0
                        contact_bonus = total_contact_px * 3.5

                        total_score = new_seam_cost + overlap_penalty + empty_space_penalty - contact_bonus

                        cand_state = BeamState(new_placed, new_used_edges, new_seam_cost)
                        cand_state.total_score = total_score
                        next_candidates.append(cand_state)

        # Fallback: relax board-size constraint only if zero valid placements exist
        if not next_candidates and beam:
            fallback_state = beam[0]
            unplaced = [idx for idx in range(num_frags) if idx not in fallback_state.placed]
            if unplaced:
                c_idx = unplaced[0]
                max_right = max(pose[0] + fragments[f_id].data.shape[1] for f_id, pose in fallback_state.placed.items())
                new_placed = copy.deepcopy(fallback_state.placed)
                c_rot = (text_angles[c_idx] % 360.0) if text_angles[c_idx] is not None else 0.0
                new_placed[c_idx] = [max_right + 10.0, 0.0, c_rot]
                next_candidates.append(BeamState(new_placed, set(fallback_state.used_edges), fallback_state.seam_cost + 5000.0))

        next_candidates.sort(key=lambda s: s.total_score)
        beam = next_candidates[:beam_width]

    best_state = beam[0]
    return [best_state.placed[i] for i in range(num_frags)]


def _evaluate_placement(
    placed: Dict[int, List[float]],
    cand_idx: int,
    cand_pose: List[float],
    scaled_masks: List[np.ndarray],
    scale_factor: float,
    max_overlap_ratio: float,
    max_w: float,
    max_h: float
) -> Tuple[bool, float, float, int]:
    all_items = list(placed.items()) + [(cand_idx, cand_pose)]
    rotated_items = []

    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')

    for f_idx, (gx, gy, rot) in all_items:
        rmask = _rotate_mask(scaled_masks[f_idx], rot)
        rh, rw = rmask.shape
        sx = int(round(gx / scale_factor))
        sy = int(round(gy / scale_factor))

        min_x = min(min_x, sx)
        min_y = min(min_y, sy)
        max_x = max(max_x, sx + rw)
        max_y = max(max_y, sy + rh)
        rotated_items.append((f_idx, sx, sy, rmask))

    canvas_w = max(1, max_x - min_x)
    canvas_h = max(1, max_y - min_y)

    # Hard rejection if the assembled cluster exceeds the target A4 page dimensions
    if canvas_w > max_w or canvas_h > max_h:
        return False, float('inf'), 0.0, 0

    board = np.zeros((canvas_h, canvas_w), dtype=np.int16)
    edge_board = np.zeros((canvas_h, canvas_w), dtype=np.int16)
    kernel = np.ones((3, 3), np.uint8)

    cand_area = 0
    for f_idx, sx, sy, rmask in rotated_items:
        rh, rw = rmask.shape
        dx = sx - min_x
        dy = sy - min_y
        board[dy : dy + rh, dx : dx + rw] += rmask

        border = cv2.dilate(rmask, kernel, iterations=1) - rmask
        edge_board[dy : dy + rh, dx : dx + rw] += border

        if f_idx == cand_idx:
            cand_area = max(1, int(np.sum(rmask)))

    overlap_pixels = int(np.sum(board[board > 1] - 1))
    if (overlap_pixels / cand_area) > max_overlap_ratio:
        return False, float('inf'), 0.0, 0

    filled_area = int(np.sum(board > 0))
    bbox_area = max(1, canvas_w * canvas_h)
    bbox_fill_ratio = filled_area / bbox_area
    total_contact_px = int(np.sum((edge_board >= 2) & (board == 0)))

    return True, overlap_pixels * 250.0, bbox_fill_ratio, total_contact_px


def render_reconstruction(best_layout: List[List[float]], fragments, board_width: int, board_height: int) -> np.ndarray:
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    placed_pieces = []

    for i, (x, y, rot) in enumerate(best_layout):
        fragment = fragments[i]
        h, w = fragment.data.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, rot, 1.0)

        cos_val = np.abs(M[0, 0])
        sin_val = np.abs(M[0, 1])
        new_w = int((h * sin_val) + (w * cos_val))
        new_h = int((h * cos_val) + (w * sin_val))

        start_x = int(round(x))
        start_y = int(round(y))

        min_x = min(min_x, start_x)
        min_y = min(min_y, start_y)
        max_x = max(max_x, start_x + new_w)
        max_y = max(max_y, start_y + new_h)

        placed_pieces.append({
            'fragment': fragment, 'x': start_x, 'y': start_y, 'rot': rot,
            'new_w': new_w, 'new_h': new_h, 'center': center
        })

    cluster_cx = (min_x + max_x) / 2.0
    cluster_cy = (min_y + max_y) / 2.0
    frame_x1 = int(round(cluster_cx - board_width / 2.0))
    frame_y1 = int(round(cluster_cy - board_height / 2.0))
    frame_x2 = frame_x1 + board_width
    frame_y2 = frame_y1 + board_height

    min_x = min(min_x, frame_x1)
    min_y = min(min_y, frame_y1)
    max_x = max(max_x, frame_x2)
    max_y = max(max_y, frame_y2)

    canvas_width = max(1, max_x - min_x)
    canvas_height = max(1, max_y - min_y)
    canvas = np.full((canvas_height, canvas_width, 4), 0, dtype=np.uint8)

    cv2.rectangle(
        canvas,
        (frame_x1 - min_x, frame_y1 - min_y),
        (frame_x2 - min_x, frame_y2 - min_y),
        (255, 0, 0, 80),
        4
    )

    for p in placed_pieces:
        M = cv2.getRotationMatrix2D(p['center'], p['rot'], 1.0)
        M[0, 2] += (p['new_w'] / 2) - p['center'][0]
        M[1, 2] += (p['new_h'] / 2) - p['center'][1]

        rotated_piece = cv2.warpAffine(
            p['fragment'].data, M, (p['new_w'], p['new_h']),
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0)
        )

        draw_x = p['x'] - min_x
        draw_y = p['y'] - min_y

        roi = canvas[draw_y : draw_y + p['new_h'], draw_x : draw_x + p['new_w']]
        alpha_mask = rotated_piece[:, :, 3] > 0
        roi[alpha_mask] = rotated_piece[alpha_mask]

    return canvas


def calculate_optimal_board_size(fragments, aspect_ratio: float = 1.414, margin_multiplier: float = 1.15) -> Tuple[int, int]:
    total_area = 0
    max_piece_diagonal = 0

    for frag in fragments:
        alpha_channel = frag.data[:, :, 3]
        total_area += int(np.sum(alpha_channel > 127))
        h, w = frag.data.shape[:2]
        max_piece_diagonal = max(max_piece_diagonal, math.sqrt(w**2 + h**2))

    target_area = total_area * margin_multiplier
    width = max(math.sqrt(target_area / aspect_ratio), max_piece_diagonal)
    height = max(width * aspect_ratio, max_piece_diagonal * aspect_ratio)

    return int(width), int(height)


def run_beam_search_reconstruction(fragments) -> np.ndarray:
    """
    Main entry point: detects text line orientations, extracts multi-depth edge profiles,
    computes pairwise compatibility, assembles the 2D layout via wide Beam Search,
    and renders the final BGRA image.
    """
    board_width, board_height = calculate_optimal_board_size(fragments)
    text_angles = [estimate_text_angle(frag.data) for frag in fragments]
    all_edges = extract_fragment_edges(fragments)
    matches_map = compute_pairwise_matches(all_edges, text_angles, top_k=15)

    best_layout = solve_with_beam_search(
        fragments=fragments,
        all_edges=all_edges,
        matches_map=matches_map,
        text_angles=text_angles,
        beam_width=60,
        scale_factor=4.0,
        max_overlap_ratio=0.025,
        board_width=board_width,
        board_height=board_height
    )

    return render_reconstruction(best_layout, fragments, board_width, board_height)