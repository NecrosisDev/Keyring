"""Accumulated grime, corrosion islands, pitting and worn scratches."""
import math
import random

SIZE=512

def uv_for(point):
    x,y,z=point
    return (x*.41+y*.23,z*.41+y*.31)

def texture_rgba(material):
    rng=random.Random({'kr_hoop':177,'kr_iron':241,'kr_brass':319}[material])
    fields={n:[[rng.random() for _ in range(n)] for _ in range(n)] for n in (4,11,29,83)}
    def noise(u,v,n):
        x,y=u*n,v*n
        ix,iy=int(x),int(y)
        tx,ty=x-ix,y-iy
        tx,ty=tx*tx*(3-2*tx),ty*ty*(3-2*ty)
        f=fields[n]
        return sum(f[(iy+j)%n][(ix+i)%n]*(tx if i else 1-tx)*(ty if j else 1-ty)
                   for i in (0,1) for j in (0,1))
    pixels=bytearray()
    for y in range(SIZE):
        for x in range(SIZE):
            u,v=x/SIZE,y/SIZE
            grain=noise(u,v,29)
            fine=noise(u,v,83)
            corrosion=max(0.,min(1.,(noise(u,v,11)*.45+grain*.35+fine*.20-.32)*2.6))
            dirt=max(0.,min(1.,(noise(u,v,4)-.36)*2.4))
            clean=.43+.28*grain
            oxide=(.30,.115,.045) if material!='kr_brass' else (.16,.25,.17)
            oxide=tuple(c*(.55+.65*fine) for c in oxide)
            tint=[(clean*(1-corrosion)+c*corrosion)*(1-.79*dirt) for c in oxide]
            pit=max(0.,(.31-fine)*3.0)
            tint=[c*(1-.80*pit)*rng.uniform(.89,1.02) for c in tint]
            pixels.extend([*(max(0,min(255,int(255*c))) for c in tint),255])
    for _ in range(90):
        x,y=rng.randrange(SIZE),rng.randrange(SIZE)
        length=rng.randrange(2,17)
        slope=rng.choice((-.4,-.2,.1,.25))
        for step in range(length):
            if rng.random()<.18:
                continue
            index=(((y+int(step*slope))%SIZE)*SIZE+(x+step)%SIZE)*4
            pixels[index:index+3]=bytes((174,167,148))
    return bytes(pixels)
