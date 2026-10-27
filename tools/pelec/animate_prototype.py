"""Render true native 3D-field slices. Never synthesize or rotate a wave."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm,Normalize
from matplotlib.cm import ScalarMappable
from matplotlib.animation import FuncAnimation,PillowWriter

def render(run,output):
    run=Path(run);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    data=np.load(run/'preview.npz');c=json.loads((run/'case.json').read_text());checks=json.loads((run/'checks.json').read_text())
    times=data['time_s'];theta=data['theta_rad'];z=data['z_m']*1000;P=data['pressure_Pa']/1e6;T=data['temperature_K']
    th,zz=np.meshgrid(np.r_[theta,2*np.pi],z,indexing='ij');xx=35.6*np.cos(th);yy=35.6*np.sin(th)
    norm=LogNorm(vmin=.1,vmax=max(10,float(np.nanmax(P))));cmap=plt.get_cmap('inferno')
    fig=plt.figure(figsize=(12,6.8),facecolor='#10141c');gs=fig.add_gridspec(2,2,width_ratios=[1.25,1],height_ratios=[1,1],left=.02,right=.90,bottom=.15,top=.85,wspace=.18,hspace=.28)
    ax=fig.add_subplot(gs[:,0],projection='3d',facecolor='#10141c');flat=fig.add_subplot(gs[0,1],facecolor='#10141c');temp=fig.add_subplot(gs[1,1],facecolor='#10141c')
    for a in (ax,flat,temp):
        a.tick_params(colors='#c8ced8',labelsize=8)
        for spine in a.spines.values():spine.set_color('#607080')
    solver=c.get('solver','PeleC');stem=solver.lower()+'_annulus'
    grid=c.get('grid_label',str(c.get('n','?'))+'³ Cartesian grid')
    title=fig.text(.04,.95,'Native '+solver+' · 3D annular prototype',color='white',fontsize=17,weight='bold');stamp=fig.text(.04,.90,'',color='#d8e1ef',fontsize=12)
    species_ok=all(checks['checks'].get(k,True) for k in ('species_nonnegative','species_sum','no_significant_preclip_negative','every_step_species_nonnegative'))
    status=('PASS including logged coarse steps' if 'every_step_species_nonnegative' in checks['checks'] else 'PASS at saved frames') if species_ok else 'FAIL (see quantified audit)'
    fig.text(.04,.055,f'DIAGNOSTIC — species checks {status}. Initialized startup; sustained detonation is not validated.',color='#ffca86',fontsize=10)
    fig.text(.04,.025,'Cylinder shows a slice at r = 35.6 mm from the computed 3D field. Unequal time intervals between saved frames; read the timestamp.',color='#a7b4c8',fontsize=9)
    pc=fig.add_axes([.92,.52,.012,.29]);tc=fig.add_axes([.92,.16,.012,.29])
    for cb in (fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),cax=pc),fig.colorbar(ScalarMappable(norm=Normalize(300,max(4500,float(T.max()))),cmap='magma'),cax=tc)):
        cb.ax.tick_params(colors='#c8ced8',labelsize=7)
    def draw(i):
        ax.clear();ax.set_facecolor('#10141c');ax.tick_params(colors='#c8ced8',labelsize=7)
        values=np.vstack([P[i],P[i,:1]])
        ax.plot_surface(xx,yy,zz,facecolors=cmap(norm(values)),rstride=3,cstride=max(1,len(z)//48),shade=False,linewidth=0,antialiased=False)
        for axis in (ax.xaxis,ax.yaxis,ax.zaxis):
            axis.set_pane_color((.06,.08,.11,1));axis.label.set_color('#c8ced8')
        ax.set(xlim=(-40,40),ylim=(-40,40),zlim=(0,76.2),xlabel='x [mm]',ylabel='y [mm]',zlabel='z [mm]');ax.set_box_aspect((1,1,1));ax.view_init(elev=23,azim=60)
        for a in (flat,temp):a.clear();a.set_facecolor('#10141c');a.tick_params(colors='#c8ced8',labelsize=8)
        flat.pcolormesh(theta*180/np.pi,z,P[i].T,shading='nearest',norm=norm,cmap=cmap)
        temp.pcolormesh(theta*180/np.pi,z,T[i].T,shading='nearest',vmin=300,vmax=max(4500,float(T.max())),cmap='magma')
        flat.set_title('Pressure [MPa] · cylindrical slice',color='white',fontsize=10);temp.set_title('Temperature [K] · same native slice',color='white',fontsize=10)
        for a in (flat,temp):a.set(xlim=(0,360),ylim=(0,76.2));a.set_xlabel('Azimuth [degrees]',color='#c8ced8',fontsize=9);a.set_ylabel('z [mm]',color='#c8ced8',fontsize=9)
        stamp.set_text(f't = {times[i]*1e6:8.3f} μs   |   {grid}   |   13 species / 38 reactions')
        return []
    anim=FuncAnimation(fig,draw,frames=len(times),interval=150,blit=False)
    path=out/(stem+'.gif');anim.save(path,writer=PillowWriter(fps=7),dpi=100)
    draw(len(times)-1);fig.savefig(out/(stem+'_final.png'),dpi=130,facecolor=fig.get_facecolor());plt.close(fig)
    (out/'animation.json').write_text(json.dumps(dict(source=str(run.resolve()),frames=len(times),physical_time_s=float(times[-1]),render='Actual 3D native-field cylindrical slice; no prescribed wave movement',physical_validation_passed=False),indent=2))
    print(path)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('output');a=p.parse_args();render(a.run,a.output)
