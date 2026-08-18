"""Render the README figures: a lipid dish assembling from a disordered start.

Run:  bazel run //projects/vivarium:make_figures
"""
import math
import subprocess

import numpy as np
from bilayer3d import build, metrics

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
W = 460
C1=math.sqrt(3/(4*math.pi)); C2=math.sqrt(15/(4*math.pi))
C3=math.sqrt(5/(16*math.pi)); C4=math.sqrt(15/(16*math.pi))
def shdot(c,x,y,z):
    v=c[0]*C1*y+c[1]*C1*z+c[2]*C1*x
    if len(c)>=8: v+=c[3]*C2*x*y+c[4]*C2*y*z+c[5]*C3*(3*z*z-1)+c[6]*C2*x*z+c[7]*C4*(x*x-y*y)
    return v

def frame(e, title, hide_water=False):
    B=e.cfg.pos_bound; sc=(W*0.44)/B; cx=cy=W/2
    ROT,TILT=0.7,0.30
    ca,sa=math.cos(ROT),math.sin(ROT); cb,sb=math.cos(TILT),math.sin(TILT); FOC=4.0*B
    # UNWRAP before projecting. Raw wrapped coordinates render an aggregate that straddles the
    # periodic boundary as scattered debris, which silently misrepresents the structure -- the same
    # class of error that corrupted the bond measurements. Reference the largest cluster's first bead.
    # Unwrap through the harness (BFS over the molecule graph). A single-reference unwrap only works
    # when the whole structure is within L/2 of the reference, so on a real aggregate the far side
    # folded onto the near side and the image showed scattered debris that was actually coherent.
    P=e.X[:,:3].copy()
    if getattr(e, "_mol", None) is not None and e._mol.size:
        from harness import unwrap as _unwrap
        idx = np.arange(len(P))
        P = _unwrap(e, idx)[:, :3]
    cam=[(ca*p[0]-sa*p[2], -sb*sa*p[0]+cb*p[1]-sb*ca*p[2], cb*sa*p[0]+sb*p[1]+cb*ca*p[2]) for p in P]
    zs=[c[2] for c in cam]; zmin,zmax=min(zs),max(zs); zr=(zmax-zmin) or 1
    def proj(i):
        x,y,z=cam[i]; pp=FOC/(FOC+z+B)
        return cx+x*sc*pp, cy-y*sc*pp, (zmax-z)/zr, pp
    sp=e.species; C=e._contour()
    COL={0:(56,189,248),5:(96,165,250),6:(249,146,58)}
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}"><rect width="{W}" height="{W}" fill="#0b0e13"/>']
    n=len(e._mol)*(e._mol.shape[1]-1)   # BACKBONE bonds only, any chain length
    for a,b in zip(e._bond_i[:n], e._bond_j[:n]):
        d=P[b]-P[a]
        if np.abs(d).max() > B: continue
        X1,Y1,d1,_=proj(a); X2,Y2,d2,_=proj(b); dep=(d1+d2)/2
        out.append(f'<line x1="{X1:.1f}" y1="{Y1:.1f}" x2="{X2:.1f}" y2="{Y2:.1f}" stroke="#cbd5e1" stroke-width="{max(1,0.05*sc*(0.7+0.4*dep)):.1f}" stroke-linecap="round" opacity="{0.35+0.45*dep:.2f}"/>')
    for i in sorted(range(len(cam)), key=lambda i:-cam[i][2]):
        s2=int(sp[i])
        if hide_water and s2==0: continue
        X,Y,dep,pp=proj(i); col=COL.get(s2,(203,213,225))
        cc=C[i]; mag=float(np.linalg.norm(cc)); op=0.32+0.68*dep
        base=(0.42 if s2==0 else 0.50)*sc*pp
        if mag>0.5:
            pts=[]
            for k in range(25):
                ph=k/24*2*math.pi; cp,s3=math.cos(ph),math.sin(ph)
                nf=shdot(cc, ca*cp-sb*sa*s3, cb*s3, -sa*cp-sb*ca*s3)
                rr=base*(1+0.42*math.tanh(nf)); pts.append("%.1f,%.1f"%(X+rr*cp, Y-rr*s3))
            out.append(f'<polygon points="{" ".join(pts)}" fill="rgb{col}" opacity="{op:.2f}"/>')
        else:
            out.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{base:.1f}" fill="rgb{col}" opacity="{op:.2f}"/>')
    out.append(f'<rect x="0" y="{W-26}" width="{W}" height="26" fill="#0b0e13" opacity="0.85"/>')
    out.append(f'<text x="10" y="{W-9}" fill="#e2e8f0" font-family="monospace" font-size="13">{title}</text></svg>')
    return "".join(out)

if __name__ == "__main__":
    e = build(seed=1, n_lip=48, bound=3.4, kt=0.02, speed=0.08, repel=12.0,
              k_bond=8.0, satt=0.55, spol=0.90, plant=False)
    shots=[(0,"t=0  disordered"),(30000,"t=30k  tails burying"),(90000,"t=90k  aggregate")]
    prev=0
    for t,label in shots:
        for _ in range(t-prev): e.step()
        prev=t
        b,h,n,o,c = metrics(e)
        svg = frame(e, f"{label}   burial {b:.2f}")
        fn=f"{OUT}/assembly_{t}"
        open(fn+".svg","w").write(svg)
        subprocess.run(["google-chrome","--headless","--disable-gpu","--no-sandbox",
                        f"--user-data-dir=/tmp/cr_fig_{t}", f"--screenshot={fn}.png",
                        f"--window-size={W+16},{W+16}", f"file://{fn}.svg"],
                       capture_output=True)
        print(f"{label}: burial {b:.3f} hydration {h:.3f} nematic {n:+.3f} -> {fn}.png", flush=True)
