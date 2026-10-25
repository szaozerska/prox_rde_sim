"""Map finite initial states to the native blockMesh cell centres; no evolution."""
import json,re,math
from pathlib import Path

def read_vectors(path):
    s=Path(path).read_text();m=re.search(r'internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;',s,re.S)
    if not m:raise ValueError('Native cell-centre vector field missing')
    rows=[list(map(float,x.split())) for x in re.findall(r'\(([^()]*)\)',m[2])]
    if len(rows)!=int(m[1]):raise ValueError('Cell count mismatch')
    return rows

def main():
    root=Path('.');c=json.loads((root/'init_annulus.json').read_text());centres=read_vectors(root/'0/C');n=len(centres)
    if n!=c['cells']:raise ValueError('Native mesh cell count mismatch')
    values={name:[] for name in ['p','T','U',*c['species']]}
    for x,y,z in centres:
        r=math.hypot(x,y);theta=math.atan2(y,x);behind=(c['seed_theta']-theta)%(2*math.pi)
        seed=behind*r<c['seed_length'] and z<c['height'];hot=z>=c['height'] or seed
        Y=c['Yseed'] if seed else c['Yprod'] if hot else c['Y'];p=c['seed_p'] if seed else c['p0'];T=c['seed_T'] if seed else c['Tprod'] if hot else c['T0'];u=c['seed_u'] if seed else 0
        values['p'].append(p);values['T'].append(T);values['U'].append((-u*y/r,u*x/r,0))
        for name,val in zip(c['species'],Y):values[name].append(val)
    for name,rows in values.items():
        kind='vector' if name=='U' else 'scalar'
        body='\n'.join('('+' '.join(format(x,'.17g') for x in row)+')' if kind=='vector' else format(row,'.17g') for row in rows)
        field=root/'0'/name;s=field.read_text();s,count=re.subn(r'internalField\s+uniform\s+[^;]+;',f'internalField nonuniform List<{kind}>\n{n}\n(\n{body}\n);',s,count=1)
        if count!=1:raise ValueError('Unexpected initial field')
        field.write_text(s)
    (root/'initialization.json').write_text(json.dumps(dict(cells=n,seed_cells=sum(p==c['seed_p'] for p in values['p']),native_centres=True),indent=2))
    print('Initialized',n,'native cells',flush=True)
if __name__=='__main__':main()
