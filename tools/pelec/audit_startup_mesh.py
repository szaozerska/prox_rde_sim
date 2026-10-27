"""Audit native EB cut-cell coverage without advancing or modifying solver state."""
import argparse
import json
from pathlib import Path


def audit_mesh(root):
    import numpy as np
    import yt
    yt.set_log_level(40)
    root = Path(root)
    rows = []
    for plot in sorted(root.glob('plt[0-9]*')):
        ds = yt.load(str(plot))
        levels = {}
        for grid in ds.index.grids:
            vf = np.asarray(grid['boxlib', 'vfrac'])
            leaf = grid.child_mask.astype(bool)
            cut = (vf > 0) & (vf < 1)
            level = levels.setdefault(int(grid.Level), {
                'leaf_fluid_cells': 0, 'leaf_cut_cells': 0,
                'cut_cells_covered_by_finer': 0})
            level['leaf_fluid_cells'] += int(np.count_nonzero(leaf & (vf > 0)))
            level['leaf_cut_cells'] += int(np.count_nonzero(leaf & cut))
            level['cut_cells_covered_by_finer'] += int(np.count_nonzero((~leaf) & cut))
            grid.clear_data()
        finest = int(ds.index.max_level)
        rows.append({'plot': plot.name, 'time_s': float(ds.current_time),
                     'finest_level': finest, 'levels': levels,
                     'leaf_cut_cells_below_finest': sum(v['leaf_cut_cells'] for k, v in levels.items() if k < finest)})
    if not rows:
        raise ValueError('No native plotfiles available')
    report = {'rows': rows, 'scope': 'Geometric EB coverage only; this does not establish flow or chemistry correctness.'}
    (root / 'mesh_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root')
    parser.add_argument('--modal-image', help='Run a CPU-only audit on the retained Modal volume')
    args = parser.parse_args()
    if not args.modal_image:
        print(json.dumps(audit_mesh(args.root), indent=2))
        return
    import modal
    image = modal.Image.from_id(args.modal_image).add_local_file(__file__, '/opt/audit_startup_mesh.py', copy=True)
    volume = modal.Volume.from_name('prox-rde-netl-startup')
    app = modal.App('prox-rde-startup-mesh-audit')

    @app.function(image=image, serialized=True, cpu=4, memory=32768,
                  timeout=900, volumes={'/results': volume})
    def remote_audit(run_id):
        import sys
        from pathlib import Path
        sys.path.insert(0, '/opt')
        from audit_startup_mesh import audit_mesh
        base = Path('/results').resolve()
        path = (base / run_id).resolve()
        if not path.is_relative_to(base) or not path.is_dir():
            raise ValueError('Invalid run directory')
        result = audit_mesh(path)
        volume.commit()
        return result

    with app.run():
        print(json.dumps(remote_audit.remote(args.root), indent=2))


if __name__ == '__main__':
    main()
