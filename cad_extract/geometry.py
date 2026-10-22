"""Geometric operations with explicit coordinate frames and feature roles."""
import math
import numpy as np


def vector(value, name):
    a = np.asarray(value, dtype=float)
    if a.shape != (3,) or not np.isfinite(a).all():
        raise ValueError(f'{name} must be a finite 3-vector')
    return a


def unit(value):
    a = vector(value, 'axis')
    norm = np.linalg.norm(a)
    if norm < 1e-12:
        raise ValueError('axis cannot be zero')
    return a / norm


def rigid_transform(spec):
    r = np.asarray(spec['rotation'], dtype=float)
    t = vector(spec['translation_m'], 'translation')
    if (r.shape != (3, 3) or not np.isfinite(r).all()
            or not np.allclose(r.T @ r, np.eye(3), atol=1e-9, rtol=0)
            or not np.isclose(np.linalg.det(r), 1, atol=1e-9, rtol=0)):
        raise ValueError('transform must be a proper rigid rotation, not scale or reflection')
    return r, t


def cylinder(face, transform):
    if face['kind'] != 'Cylinder':
        raise ValueError('selected feature is not an analytic cylinder')
    r, t = rigid_transform(transform)
    p = r @ vector(face['axis_point_m'], 'axis point') + t
    a = unit(r @ unit(face['axis']))
    interval = np.asarray(face['support_interval_m'], dtype=float)
    if interval.shape != (2,) or not np.isfinite(interval).all() or interval[1] <= interval[0]:
        raise ValueError('invalid cylinder support interval')
    radius = float(face['radius_m'])
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError('invalid cylinder radius')
    return dict(point=p, axis=a, radius=radius, ends=p + interval[:, None]*a,
                face_tags=[face['tag']])


def plane_axial_position(face, transform, origin, axis, angular_tol=1e-7):
    if face['kind'] != 'Plane' or len(face['properties']) != 4:
        raise ValueError('axial datum must select a planar face')
    p = np.asarray(face['properties'], dtype=float)
    if not np.isfinite(p).all() or np.linalg.norm(p[:3]) < 1e-12:
        raise ValueError('invalid plane')
    point = -p[3]*p[:3]/np.dot(p[:3], p[:3])
    r, t = rigid_transform(transform)
    if np.linalg.norm(np.cross(unit(r @ p[:3]), axis)) > angular_tol:
        raise ValueError('datum plane must be perpendicular to engine axis')
    return float(np.dot(r @ point + t - origin, axis))


def canonical_line(c):
    a = c['axis'].copy()
    if a[np.argmax(np.abs(a))] < 0:
        a = -a
    # Closest point on the infinite axis to the coordinate origin.
    p = c['point'] - a*np.dot(c['point'], a)
    return a, p


def unique_bores(cylinders, length_tol=1e-8, angle_tol=1e-7):
    """Join split faces on the same radius/axis; never count face patches as holes."""
    groups = []
    for candidate in cylinders:
        a, p = canonical_line(candidate)
        for group in groups:
            b, q = canonical_line(group)
            if (abs(candidate['radius']-group['radius']) <= length_tol
                    and np.linalg.norm(np.cross(a, b)) <= angle_tol
                    and np.linalg.norm(p-q) <= length_tol):
                group['face_tags'] += candidate['face_tags']
                break
        else:
            groups.append({**candidate, 'face_tags': list(candidate['face_tags'])})
    return groups


def annulus(ro, ri, length, injector_area):
    if not all(math.isfinite(v) for v in [ro, ri, length, injector_area]):
        raise ValueError('non-finite geometry')
    if not 0 < ri < ro or length <= 0 or injector_area < 0:
        raise ValueError('constant annulus requires 0 < inner < outer and positive length')
    area = math.pi*(ro*ro-ri*ri)
    if injector_area > area:
        raise ValueError('injector throat area exceeds annular area')
    rm = .5*(ro+ri)
    return dict(r_outer_m=ro, r_inner_m=ri, length_m=length, gap_m=ro-ri,
                r_mean_m=rm, circumference_m=2*math.pi*rm,
                exit_area_m2=area, volume_m3=area*length,
                hydraulic_diameter_m=2*(ro-ri), inner_wall_area_m2=2*math.pi*ri*length,
                outer_wall_area_m2=2*math.pi*ro*length,
                injector_open_area_m2=injector_area, area_ratio=injector_area/area)


def bore_record(c, origin, engine_axis):
    a = c['axis'].copy()
    if np.dot(a, engine_axis) < 0:
        a = -a
    dot = float(np.dot(a, engine_axis))
    angle = math.degrees(math.acos(np.clip(abs(dot), 0, 1)))
    point = c['point']
    crossing = None if abs(dot) < 1e-10 else point + a*np.dot(origin-point, engine_axis)/dot
    return dict(face_tags=c['face_tags'], radius_m=c['radius'], axis=a.tolist(),
                axis_point_m=point.tolist(), inclination_deg=angle,
                inlet_axis_intersection_m=None if crossing is None else crossing.tolist())


def impingement(fuel, oxidizer, origin, axis, tolerance_m):
    """Pair by azimuth at the inlet, then intersect extrapolated bore axes.

    This is geometric jet-centerline extrapolation, not a mixing calculation.
    """
    if len(fuel) != len(oxidizer) or not fuel:
        return dict(available=False, reason='unequal or empty bore families')
    pairs, used = [], set()
    for f in fuel:
        p = f['inlet_axis_intersection_m']
        if p is None:
            return dict(available=False, reason='a bore is parallel to the inlet plane')
        p = np.asarray(p)
        radial = p-origin
        radial -= axis*np.dot(radial, axis)
        if np.linalg.norm(radial) < tolerance_m:
            return dict(available=False, reason='bore on engine axis has no azimuth')
        radial /= np.linalg.norm(radial)
        distances = []
        for o in oxidizer:
            if o['inlet_axis_intersection_m'] is None:
                return dict(available=False, reason='oxidizer bore parallel to inlet')
            q = np.asarray(o['inlet_axis_intersection_m'])
            rad = q-origin-axis*np.dot(q-origin, axis)
            if np.linalg.norm(rad) < tolerance_m:
                return dict(available=False, reason='oxidizer on engine axis')
            distances.append(np.linalg.norm(rad/np.linalg.norm(rad)-radial))
        order = np.argsort(distances)
        j = int(order[0])
        if j in used or distances[j] > .01 or (len(order)>1 and abs(distances[order[1]]-distances[j]) < 1e-8):
            return dict(available=False, reason='ambiguous azimuthal pair assignment')
        used.add(j)
        q = np.asarray(oxidizer[j]['inlet_axis_intersection_m'])
        a, b = np.asarray(f['axis']), np.asarray(oxidizer[j]['axis'])
        matrix = np.column_stack((a, -b))
        solution, _, rank, _ = np.linalg.lstsq(matrix, q-p, rcond=None)
        if rank < 2:
            return dict(available=False, reason='parallel jet axes')
        x, y = p+solution[0]*a, q+solution[1]*b
        if np.linalg.norm(x-y) > tolerance_m or min(solution) < 0:
            return dict(available=False, reason='axes do not meet downstream within tolerance')
        meet = (x+y)/2-origin
        height = float(np.dot(meet, axis))
        radius = float(np.linalg.norm(meet-axis*height))
        pairs.append(dict(height_m=height, radius_m=radius, miss_distance_m=float(np.linalg.norm(x-y)),
                          fuel_faces=f['face_tags'], oxidizer_faces=oxidizer[j]['face_tags']))
    return dict(available=True, method='azimuth-matched infinite bore-axis intersections',
                count=len(pairs), height_m=float(np.mean([p['height_m'] for p in pairs])),
                diameter_m=float(2*np.mean([p['radius_m'] for p in pairs])),
                max_miss_distance_m=max(p['miss_distance_m'] for p in pairs), pairs=pairs)
