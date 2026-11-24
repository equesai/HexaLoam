"""
gait_motion.py - CAD-derived 3R inverse-kinematics gait pose generator.

Generates tripod, ripple, and wave gait pose sequences for the hexapod robot
from the Simscape Multibody XML export (Full_Robot_Assembly.xml).

Prescribed Kinematic Assumptions & Actual CAD Geometry:
------------------------------------------------------
1. Coordinate System:
   - World convention: Up is +Y, Forward is +X, Right is +Z.
   - 57 flat XML instances exported with row-major 3x3 rotation matrix R and
     3x1 translation vector t mapping part local coordinates (m) to world:
       p_world = R @ p_local + t

2. Foot Sphere Geometry:
   - Native CAD foot sphere radius: 0.025 m (25 mm).
   - Local sphere center in L3 part frame:
       [0.11697358574556834, 0.01757714870716707, 0.0] meters.

3. Leg Indexing & Hinge Identification:
   - Legs: 2=LM (Left Middle), 3=LR (Left Rear), 4=RR (Right Rear),
           5=RM (Right Middle), 6=RF (Right Front), 7=LF (Left Front).
   - Standard output leg ordering: ['LF', 'LM', 'LR', 'RF', 'RM', 'RR']
     corresponding to leg indices [7, 2, 3, 6, 5, 4].
   - Hinges derived from XML Concentric constraints:
     - Hip yaw hinge: Concentric mate on L1 with vertical axis (+/-Y).
     - Hip pitch hinge: Concentric mate on L1 with horizontal axis.
     - Knee pitch hinge: Concentric mate on L3.
     Hinge anchor positions and rotation axes in world/body coordinates are
     obtained by transforming local constraint Position and Axis by instance (R, t).

4. Kinematic Chain & Transforms:
   - L1: Yaw rotation around hip yaw hinge.
   - L2: Yaw * Pitch rotation around hip pitch hinge.
   - L3: Yaw * Pitch * Knee rotation around knee pitch hinge.
   - Revolutions occur around source CAD hinge points:
       M(p, a, theta): x -> R_a(theta)(x - p) + p

5. Rigid Grouping for Pose Generation:
   - Body-mounted (15 instances):
     Robot_Base-1, RP-Lidar-1, LidarCover-1, and Servo Motor MG996R-1 through 12.
   - Leg links and attached motors (42 instances, 7 per leg):
     - L1-k moves with L1 yaw transform.
     - L2-k and its 4 servos move with L2 yaw*pitch transform:
       Leg 2: Servo Motor MG996R-17..20
       Leg 3: Servo Motor MG996R-21..24
       Leg 4: Servo Motor MG996R-25..28
       Leg 5: Servo Motor MG996R-29..32
       Leg 6: Servo Motor MG996R-33..36
       Leg 7: Servo Motor MG996R-37..40
     - L3-k moves with L3 yaw*pitch*knee transform.
   - Total: 15 + 42 = 57 instances. (Native export has no motors 13-16).

6. Gait Specifications:
   - Stance foot sphere centers are at Y = -0.200 m. The ground plane is 25 mm lower.
   - Shared forward stride: 0.060 m per cycle.
   - Peak swing clearance: 0.022 m above ground.
   - Stance phase: foot remains strictly fixed in world coordinates (zero slip).
   - Swing phase: cycloidal horizontal progression and smooth vertical clearance.
   - Gait Duty Factors and Sequencing:
     - Tripod: alternating [LF, RM, LR] and [RF, LM, RR], duty 0.5.
     - Ripple: duty 2/3, staggered liftoffs (LR, RM, LF, RR, LM, RF) spaced 1/6 cycle.
     - Wave: duty 5/6, separate liftoffs (LR, LM, LF, RR, RM, RF) spaced 1/6 cycle.
   - Timing: 24 FPS, 120 frames/cycle (5.0 s/cycle), 240 frames total (10.0 s, 2 full cycles).
"""

import os
import argparse
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation as R_scipy
from scipy.optimize import least_squares

NS = {'sm': 'urn:mathworks:SimscapeMultibody:import'}

# Leg label order and mapping to leg index
LEG_ORDER = ['LF', 'LM', 'LR', 'RF', 'RM', 'RR']
LEG_MAP = {
    'LF': 7,
    'LM': 2,
    'LR': 3,
    'RF': 6,
    'RM': 5,
    'RR': 4,
}

# Rigid grouping definitions
BODY_INSTANCES = [
    'Robot_Base-1',
    'RP-Lidar-1',
    'LidarCover-1',
] + [f'Servo Motor MG996R-{i}' for i in range(1, 13)]

LEG_MOTORS = {
    2: [f'Servo Motor MG996R-{i}' for i in range(17, 21)],
    3: [f'Servo Motor MG996R-{i}' for i in range(21, 25)],
    4: [f'Servo Motor MG996R-{i}' for i in range(25, 29)],
    5: [f'Servo Motor MG996R-{i}' for i in range(29, 33)],
    6: [f'Servo Motor MG996R-{i}' for i in range(33, 37)],
    7: [f'Servo Motor MG996R-{i}' for i in range(37, 41)],
}

FOOT_LOCAL = np.array([0.11697358574556834, 0.01757714870716707, 0.0], dtype=np.float64)
FOOT_RADIUS = 0.025


def parse_cad_assembly(xml_path):
    """
    Parses the Simscape Multibody XML assembly file.
    Returns:
        instances: dict mapping UID to {'R': (3,3), 't': (3,), 'T': (4,4)}
        instance_order: list of 57 instance UIDs in file order
        leg_hinges: dict mapping leg_idx to hinge info
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ra = root.find('sm:RootAssembly', NS)
    it = ra.find('sm:InstanceTree', NS)

    instances = {}
    instance_order = []
    for inst in it.findall('sm:Instance', NS):
        uid = inst.attrib['uid']
        instance_order.append(uid)
        tr = inst.find('sm:Transform', NS)
        r_text = tr.find('sm:Rotation', NS).text.split()
        t_text = tr.find('sm:Translation', NS).text.split()
        R = np.array([float(x) for x in r_text], dtype=np.float64).reshape((3, 3))
        t = np.array([float(x) for x in t_text], dtype=np.float64)
        T = np.eye(4, dtype=np.float64)
        T[:3, :3] = R
        T[:3, 3] = t
        instances[uid] = {'R': R, 't': t, 'T': T}

    constraints = ra.find('sm:Constraints', NS)
    leg_hinges = {}

    for leg in [2, 3, 4, 5, 6, 7]:
        l1_name = f'L1-{leg}'
        l3_name = f'L3-{leg}'
        p_cad_foot = instances[l3_name]['R'] @ FOOT_LOCAL + instances[l3_name]['t']

        yaw_p, yaw_a = None, None
        pitch_p, pitch_a = None, None
        knee_p, knee_a = None, None

        for c in constraints:
            if c.tag.endswith('Concentric'):
                geoms = c.findall('sm:ConstraintGeometry', NS)
                uids = [g.find('sm:InstancePath', NS).find('sm:Uid', NS).text for g in geoms]
                if l1_name in uids:
                    g = [geom for geom in geoms if geom.find('sm:InstancePath', NS).find('sm:Uid', NS).text == l1_name][0]
                    p_pos = np.array([float(x) for x in g.find('sm:Position', NS).text.split()], dtype=np.float64)
                    p_axis = np.array([float(x) for x in g.find('sm:Axis', NS).text.split()], dtype=np.float64)
                    pw = instances[l1_name]['R'] @ p_pos + instances[l1_name]['t']
                    aw = instances[l1_name]['R'] @ p_axis
                    aw = aw / np.linalg.norm(aw)
                    if abs(abs(aw[1]) - 1.0) < 1e-3:
                        yaw_p, yaw_a = pw, aw
                    else:
                        pitch_p, pitch_a = pw, aw

                if l3_name in uids:
                    g = [geom for geom in geoms if geom.find('sm:InstancePath', NS).find('sm:Uid', NS).text == l3_name][0]
                    p_pos = np.array([float(x) for x in g.find('sm:Position', NS).text.split()], dtype=np.float64)
                    p_axis = np.array([float(x) for x in g.find('sm:Axis', NS).text.split()], dtype=np.float64)
                    pw = instances[l3_name]['R'] @ p_pos + instances[l3_name]['t']
                    aw = instances[l3_name]['R'] @ p_axis
                    aw = aw / np.linalg.norm(aw)
                    knee_p, knee_a = pw, aw

        leg_hinges[leg] = {
            'yaw_p': yaw_p, 'yaw_a': yaw_a,
            'pitch_p': pitch_p, 'pitch_a': pitch_a,
            'knee_p': knee_p, 'knee_a': knee_a,
            'foot_cad': p_cad_foot,
        }

    return instances, instance_order, leg_hinges


def axis_angle_transform(p, a, theta):
    """
    Computes 4x4 transform for rotation by theta around axis 'a' passing through point 'p'.
    """
    R = R_scipy.from_rotvec(a * theta).as_matrix()
    t = p - R @ p
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def leg_forward_kinematics(leg_info, angles):
    """
    Computes body-relative FK foot position and link transforms for a 3R leg.
    angles: [theta_yaw, theta_pitch, theta_knee]
    Returns:
        foot_pos: (3,) array
        T_rel_L1: (4,4)
        T_rel_L2: (4,4)
        T_rel_L3: (4,4)
    """
    T1 = axis_angle_transform(leg_info['yaw_p'], leg_info['yaw_a'], angles[0])
    T2 = axis_angle_transform(leg_info['pitch_p'], leg_info['pitch_a'], angles[1])
    T3 = axis_angle_transform(leg_info['knee_p'], leg_info['knee_a'], angles[2])

    T_L1 = T1
    T_L2 = T1 @ T2
    T_L3 = T1 @ T2 @ T3

    foot_cad_homo = np.append(leg_info['foot_cad'], 1.0)
    foot_pos = (T_L3 @ foot_cad_homo)[:3]

    return foot_pos, T_L1, T_L2, T_L3


def leg_inverse_kinematics(leg_info, target_body_pos, init_angles=None):
    """
    Solves 3R inverse kinematics for desired body-relative foot position.
    """
    if init_angles is None:
        init_angles = np.zeros(3, dtype=np.float64)

    def residual(th):
        p, _, _, _ = leg_forward_kinematics(leg_info, th)
        return p - target_body_pos

    res = least_squares(residual, init_angles, method='lm', ftol=1e-12, xtol=1e-12)
    return res.x, np.linalg.norm(res.fun)


def generate_foot_trajectory(k, k_lift, duty, F_cycle, stride, x_neutral, y_ground, h_swing):
    """
    Computes world foot position and swing state for a leg at frame k.
    Quantized timing, smooth horizontal cycloidal swing, smooth vertical clearance,
    and stationary stance foot in world coordinates.
    """
    F_swing = int(round((1.0 - duty) * F_cycle))
    phase = (k - k_lift) % F_cycle
    c = (k - k_lift) // F_cycle
    is_swing = (phase < F_swing)

    # Touchdown plant position in world coordinates:
    # Stance stroke is centered around x_neutral relative to body.
    # Mid-stance is at k_mid = c*F_cycle + k_lift + (1 - 0.5*duty)*F_cycle.
    x_plant = x_neutral + (c * F_cycle + k_lift + (1.0 - 0.5 * duty) * F_cycle) * (stride / F_cycle)

    if is_swing:
        s = phase / F_swing
        # Cycloidal interpolation has zero horizontal velocity and acceleration at each end.
        h = s - np.sin(2.0 * np.pi * s) / (2.0 * np.pi)
        x_prev = x_plant - stride
        xw = x_prev + h * stride
        # Smooth vertical swing clearance profile
        yw = y_ground + h_swing * (np.sin(np.pi * s) ** 2)
    else:
        xw = x_plant
        yw = y_ground

    return xw, yw, is_swing


def solve_gait(gait_name, instances, instance_order, leg_hinges,
               fps=24, n_cycles=2, stride=0.060, y_ground=-0.200, h_swing=0.022):
    """
    Solves full gait motion for the specified gait.
    Emits data dict with NPZ keys: names, transforms, leg_names, swing, feet, body_x.
    """
    F_cycle = 120  # 5.0 s per cycle at 24 FPS
    N = n_cycles * F_cycle  # 240 frames (10.0 s)
    v_body = stride / F_cycle

    # Define duty factor and liftoff offsets (in frames within cycle 0)
    if gait_name == 'tripod':
        duty = 0.5
        # Alternating [LF, RM, LR] and [RF, LM, RR]
        liftoff_map = {
            'LF': 0, 'RM': 0, 'LR': 0,
            'RF': 60, 'LM': 60, 'RR': 60,
        }
    elif gait_name == 'ripple':
        duty = 2.0 / 3.0
        # Staggered 1/6 cycle (20 frames): LR, RM, LF, RR, LM, RF
        liftoff_map = {
            'LR': 0,
            'RM': 20,
            'LF': 40,
            'RR': 60,
            'LM': 80,
            'RF': 100,
        }
    elif gait_name == 'wave':
        duty = 5.0 / 6.0
        # Separate liftoffs spaced 1/6 cycle: LR, LM, LF, RR, RM, RF
        liftoff_map = {
            'LR': 0,
            'LM': 20,
            'LF': 40,
            'RR': 60,
            'RM': 80,
            'RF': 100,
        }
    else:
        raise ValueError(f"Unknown gait name: {gait_name}")

    body_x = np.arange(N, dtype=np.float64) * v_body

    # Neutral foot positions in body coordinates
    neutral_feet = {}
    for leg_lbl in LEG_ORDER:
        leg_idx = LEG_MAP[leg_lbl]
        cad_foot = leg_hinges[leg_idx]['foot_cad']
        neutral_feet[leg_lbl] = np.array([cad_foot[0], y_ground, cad_foot[2]], dtype=np.float64)

    # Solve 1 cycle (F_cycle frames) for body-relative kinematics
    # Then reuse per-cycle solves and translate in world frame
    cycle_rel_transforms = {leg_lbl: [] for leg_lbl in LEG_ORDER}
    cycle_swing = {leg_lbl: [] for leg_lbl in LEG_ORDER}

    max_ik_err = 0.0
    warm_start_angles = {leg_lbl: np.zeros(3, dtype=np.float64) for leg_lbl in LEG_ORDER}

    for k in range(F_cycle):
        bx_k = body_x[k]
        for leg_lbl in LEG_ORDER:
            leg_idx = LEG_MAP[leg_lbl]
            k_lift = liftoff_map[leg_lbl]
            x_neu = neutral_feet[leg_lbl][0]
            z_neu = neutral_feet[leg_lbl][2]

            xw, yw, is_sw = generate_foot_trajectory(
                k, k_lift, duty, F_cycle, stride, x_neu, y_ground, h_swing
            )
            # Body-relative target
            target_body = np.array([xw - bx_k, yw, z_neu], dtype=np.float64)

            # Solve IK
            angles, ik_err = leg_inverse_kinematics(
                leg_hinges[leg_idx], target_body, warm_start_angles[leg_lbl]
            )
            max_ik_err = max(max_ik_err, ik_err)
            warm_start_angles[leg_lbl] = angles

            _, T_L1, T_L2, T_L3 = leg_forward_kinematics(leg_hinges[leg_idx], angles)

            cycle_rel_transforms[leg_lbl].append({
                'L1': T_L1, 'L2': T_L2, 'L3': T_L3
            })
            cycle_swing[leg_lbl].append(is_sw)

    # Now construct the full world trajectory for all N frames and all 57 instances
    num_instances = len(instance_order)
    transforms_out = np.zeros((N, num_instances, 4, 4), dtype=np.float64)
    feet_out = np.zeros((N, 6, 3), dtype=np.float64)
    swing_out = np.zeros((N, 6), dtype=bool)

    # Pre-map instances to their update roles
    # Body instances
    body_indices = [instance_order.index(uid) for uid in BODY_INSTANCES]

    # Leg instances
    leg_inst_map = {}
    for leg_idx in [2, 3, 4, 5, 6, 7]:
        leg_inst_map[leg_idx] = {
            'idx_L1': instance_order.index(f'L1-{leg_idx}'),
            'idx_L2': instance_order.index(f'L2-{leg_idx}'),
            'idx_L3': instance_order.index(f'L3-{leg_idx}'),
            'idx_motors': [instance_order.index(m_uid) for m_uid in LEG_MOTORS[leg_idx]],
        }

    for k in range(N):
        k0 = k % F_cycle
        bx = body_x[k]
        T_body = np.eye(4, dtype=np.float64)
        T_body[0, 3] = bx

        # 1. Body-mounted instances
        for idx in body_indices:
            uid = instance_order[idx]
            transforms_out[k, idx] = T_body @ instances[uid]['T']

        # 2. Leg instances
        for leg_col, leg_lbl in enumerate(LEG_ORDER):
            leg_idx = LEG_MAP[leg_lbl]
            rel_T = cycle_rel_transforms[leg_lbl][k0]
            m = leg_inst_map[leg_idx]

            # L1
            transforms_out[k, m['idx_L1']] = T_body @ rel_T['L1'] @ instances[f'L1-{leg_idx}']['T']

            # L2 and attached motors
            T_world_L2 = T_body @ rel_T['L2']
            transforms_out[k, m['idx_L2']] = T_world_L2 @ instances[f'L2-{leg_idx}']['T']
            for m_idx in m['idx_motors']:
                m_uid = instance_order[m_idx]
                transforms_out[k, m_idx] = T_world_L2 @ instances[m_uid]['T']

            # L3
            transforms_out[k, m['idx_L3']] = T_body @ rel_T['L3'] @ instances[f'L3-{leg_idx}']['T']

            # Foot sphere center in world coordinates
            # Exactly matches T_world_L3 @ [FOOT_LOCAL; 1]
            foot_w = (transforms_out[k, m['idx_L3']] @ np.append(FOOT_LOCAL, 1.0))[:3]
            feet_out[k, leg_col] = foot_w

            # Swing state
            # Determine swing state from generator for frame k
            swing_out[k, leg_col] = cycle_swing[leg_lbl][k0]

    # Verification metrics
    # 1. Stance slip
    max_stance_slip = 0.0
    for leg_col in range(6):
        for k in range(N - 1):
            if not swing_out[k, leg_col] and not swing_out[k + 1, leg_col]:
                slip = np.linalg.norm(feet_out[k + 1, leg_col] - feet_out[k, leg_col])
                max_stance_slip = max(max_stance_slip, slip)

    # 2. Swing clearance
    max_swing_clearance = 0.0
    for leg_col in range(6):
        for k in range(N):
            if swing_out[k, leg_col]:
                clearance = feet_out[k, leg_col, 1] - y_ground
                max_swing_clearance = max(max_swing_clearance, clearance)

    # 3. Finite matrix check
    is_finite = np.all(np.isfinite(transforms_out)) and np.all(np.isfinite(feet_out))

    metrics = {
        'max_ik_err': max_ik_err,
        'max_stance_slip': max_stance_slip,
        'max_swing_clearance': max_swing_clearance,
        'is_finite': is_finite,
        'num_frames': N,
        'duration_s': N / fps,
        'total_travel_m': body_x[-1] + v_body,
    }

    result = {
        'names': np.array(instance_order, dtype=str),
        'transforms': transforms_out,
        'leg_names': np.array(LEG_ORDER, dtype=str),
        'swing': swing_out,
        'feet': feet_out,
        'body_x': body_x,
        'fps': np.asarray(fps),
    }

    return result, metrics


def main():
    parser = argparse.ArgumentParser(description="CAD-derived 3R inverse-kinematics hexapod gait pose generator.")
    parser.add_argument('--xml', required=True, help="Path to Full_Robot_Assembly.xml")
    parser.add_argument('--output', required=True, help="Output directory for generated .npz files")
    parser.add_argument('--fps', type=int, default=24, help="Frames per second (default: 24)")
    parser.add_argument('--stride', type=float, default=0.060, help="Stride length in meters (default: 0.060)")
    parser.add_argument('--ground-y', type=float, default=-0.200, help="Common ground height for foot sphere centers (default: -0.200)")
    parser.add_argument('--swing-height', type=float, default=0.022, help="Peak swing vertical clearance (default: 0.022)")
    args = parser.parse_args()
    if args.fps <= 0 or args.stride <= 0 or args.swing_height <= 0:
        parser.error("Frame rate, stride and swing height must be positive.")

    os.makedirs(args.output, exist_ok=True)

    instances, instance_order, leg_hinges = parse_cad_assembly(args.xml)

    gaits = ['tripod', 'ripple', 'wave']
    all_metrics = {}

    for gait in gaits:
        res, m = solve_gait(
            gait, instances, instance_order, leg_hinges,
            fps=args.fps, n_cycles=2, stride=args.stride,
            y_ground=args.ground_y, h_swing=args.swing_height
        )
        if not m['is_finite'] or m['max_ik_err'] > 1e-4 or m['max_stance_slip'] > 1e-4:
            raise ValueError(f"{gait}: the requested trajectory exceeds the 0.1 mm tolerance. "
                             "Check stride, stance height and swing height.")
        out_path = os.path.join(args.output, f"{gait}.npz")
        np.savez(out_path, **res)
        all_metrics[gait] = m

    for gait in gaits:
        m = all_metrics[gait]
        print(f"[{gait.upper()}] frames={m['num_frames']} ({m['duration_s']:.1f}s) "
              f"max_IK_err={m['max_ik_err']:.2e}m max_slip={m['max_stance_slip']*1000:.4f}mm "
              f"peak_clearance={m['max_swing_clearance']*1000:.2f}mm finite={m['is_finite']}")


if __name__ == '__main__':
    main()
