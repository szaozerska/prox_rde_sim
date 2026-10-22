"""Run from repository root: python -m cad_extract --help."""
import argparse
import json
from pathlib import Path
import sys

import yaml

from .pipeline import export_case, extract, report_markdown, write_preview
from .step import inspect_step, sha256


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def main():
    parser=argparse.ArgumentParser(description='Read STEP geometry and explicitly reduce it for the existing RDE solver.')
    sub=parser.add_subparsers(dest='command', required=True)
    p=sub.add_parser('inspect',help='inventory analytic faces of one STEP file')
    p.add_argument('file',type=Path);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('extract',help='apply a reviewed, source-locked mapping')
    p.add_argument('--mapping',type=Path,required=True)
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--base-case',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--acknowledge-reduction',action='store_true',help='also export provisional reduced cases with recorded omissions')
    p=sub.add_parser('reference',help='export the paper-only Run 937 geometry without CAD dependencies')
    p.add_argument('--base-case',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--acknowledge-reduction',action='store_true')
    args=parser.parse_args()
    if args.out.exists():
        parser.error('output already exists; choose a new path to preserve prior evidence')
    try:
        if args.command=='inspect':
            result=inspect_step(args.file)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            save_json(args.out,result)
        elif args.command=='reference':
            base=yaml.safe_load(args.base_case.read_text())
            result=export_case(base,None,'paper',acknowledge_reduction=args.acknowledge_reduction)
            result['cad_provenance']['base_case_sha256']=sha256(args.base_case)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(yaml.safe_dump(result,sort_keys=False))
        else:
            mapping=json.loads(args.mapping.read_text())
            manifest,inventories=extract(mapping,args.source_dir)
            manifest['provenance']['mapping_sha256']=sha256(args.mapping)
            manifest['provenance']['base_case_sha256']=sha256(args.base_case)
            base=yaml.safe_load(args.base_case.read_text())
            cases={basis:export_case(base,manifest,basis,acknowledge_reduction=True)
                   for basis in ['paper','cad']} if args.acknowledge_reduction else {}
            args.out.mkdir(parents=True)
            save_json(args.out/'manifest.json',manifest)
            save_json(args.out/'inventory.json',inventories)
            (args.out/'report.md').write_text(report_markdown(manifest))
            for basis,case in cases.items():
                case['cad_provenance']['mapping_sha256']=sha256(args.mapping)
                case['cad_provenance']['base_case_sha256']=sha256(args.base_case)
                (args.out/f'case.{basis}.yaml').write_text(yaml.safe_dump(case,sort_keys=False))
            write_preview(manifest,args.out/'preview.png')
        print(args.out.resolve())
    except (ValueError,RuntimeError,KeyError,OSError) as exc:
        parser.exit(2,f'CAD extraction failed: {exc}\n')


if __name__=='__main__':
    main()
