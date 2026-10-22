"""Forged hoop passing directly through the bows of two plain warded keys."""
import math

KEYS = ((-math.pi / 2 - .38, 4.65), (-math.pi / 2 + .38, 3.95))
KEY_TILTS = (55.,65.)
METALS = {'kr_hoop': ((.12, .135, .15), .14),
          'kr_iron': ((.40, .42, .44), .18),
          'kr_brass': ((.34, .24, .12), .16)}

def frame(angle, radial, up=0.):
    r = (math.cos(angle), 0., math.sin(angle))
    t = (-math.sin(angle), 0., math.cos(angle))
    return r, t, (r[0]*radial, up, r[2]*radial)

def key_frame(index,angle):
    radial,tangent,center=frame(angle,2.8)
    tilt=math.radians(KEY_TILTS[index])
    across=tuple(tangent[k]*math.cos(tilt)+(math.sin(tilt) if k==1 else 0.) for k in range(3))
    inward=tuple(-v for v in radial)
    normal=(across[1]*inward[2]-across[2]*inward[1],across[2]*inward[0]-across[0]*inward[2],across[0]*inward[1]-across[1]*inward[0])
    return center,across,inward,normal

def bow_profile(index,angle):
    x,z=math.cos(angle),math.sin(angle)
    if index==1:
        x=math.copysign(math.sqrt(abs(x)),x)
        z=math.copysign(math.sqrt(abs(z)),z)
    return .60*x,.74*z

def components(segments, sides):
    result = []
    def torus(name, material, center, axis_u, axis_v, radius_u, radius_v, wire, count, bow_index=None):
        points, faces = [], []
        normal = (axis_u[1]*axis_v[2]-axis_u[2]*axis_v[1],
                  axis_u[2]*axis_v[0]-axis_u[0]*axis_v[2],
                  axis_u[0]*axis_v[1]-axis_u[1]*axis_v[0])
        for i in range(count):
            a = i*math.tau/count
            px,pz=(radius_u*math.cos(a),radius_v*math.sin(a)) if bow_index is None else bow_profile(bow_index,a)
            for j in range(sides):
                b = j*math.tau/sides
                points.append(tuple(center[k]+axis_u[k]*(px+wire*math.cos(b)*math.cos(a))
                    +axis_v[k]*(pz+wire*math.cos(b)*math.sin(a))+normal[k]*wire*math.sin(b) for k in range(3)))
        for i in range(count):
            for j in range(sides):
                a,b=i*sides+j,i*sides+(j+1)%sides
                c,d=((i+1)%count)*sides+j,((i+1)%count)*sides+(j+1)%sides
                faces.extend(((a,c,b),(b,c,d)))
        result.append((name,material,points,faces))

    def round_shaft(name,length,place):
        points=[place((.105*math.cos(j*math.tau/sides),.105*math.sin(j*math.tau/sides),z))
                for z in (-length,-.62) for j in range(sides)]
        faces=[]
        for j in range(sides):
            a,b=j,(j+1)%sides
            faces.extend(((a,b,a+sides),(b,b+sides,a+sides)))
        for end,z in ((0,-length),(1,-.62)):
            center=len(points)
            points.append(place((0.,0.,z)))
            for j in range(sides):
                a,b=end*sides+j,end*sides+(j+1)%sides
                faces.append((center,b,a) if end==0 else (center,a,b))
        result.append((name,'kr_iron',points,faces))

    def box(name, material, center, half, transform=lambda p:p):
        x,y,z=center
        hx,hy,hz=half
        corners=((-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
                 (-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz))
        radius=min(half)*.28
        points,faces,lookup=[],[],{}
        steps=(0.,radius/(2*max(half)),1.-radius/(2*max(half)),1.)
        def vertex(p):
            inner=tuple(max(-h+radius,min(h-radius,v)) for v,h in zip(p,half))
            delta=tuple(p[k]-inner[k] for k in range(3))
            length=math.sqrt(sum(v*v for v in delta))
            q=tuple(inner[k]+radius*delta[k]/length for k in range(3))
            key=tuple(round(v,9) for v in q)
            if key not in lookup:
                lookup[key]=len(points)
                points.append(transform((x+q[0],y+q[1],z+q[2])))
            return lookup[key]
        for a,b,c,d in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)):
            grid=[]
            for v in steps:
                grid.append([vertex(tuple(corners[a][k]*(1-u)*(1-v)+corners[b][k]*u*(1-v)
                    +corners[c][k]*u*v+corners[d][k]*(1-u)*v for k in range(3))) for u in steps])
            for j in range(3):
                for i in range(3):
                    aa,bb,cc,dd=grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]
                    faces.extend(((aa,bb,cc),(aa,cc,dd)))
        result.append((name,material,points,faces))

    torus('hoop','kr_hoop',(0.,0.,0.),(1.,0.,0.),(0.,0.,1.),2.6,2.6,.19,segments)
    box('clasp','kr_hoop',(2.6,0.,0.),(.24,.235,.36))
    for i,(angle,length) in enumerate(KEYS):
        key_center,across,inward,normal=key_frame(i,angle)
        material='kr_iron' if i==0 else 'kr_brass'
        torus(f'bow{i}',material,key_center,across,inward,.60,.74,.12,max(32,segments//3),i)
        def place(p):
            x,y,z=p
            return tuple(key_center[k]+across[k]*x+normal[k]*y+inward[k]*z for k in range(3))
        if i==0:
            round_shaft(f'shaft{i}',length,place)
            box(f'bit{i}a','kr_iron',(.28,0.,-length+.18),(.34,.13,.17),place)
            box(f'bit{i}b','kr_iron',(.21,0.,-length+.67),(.27,.13,.13),place)
            box(f'neck{i}','kr_iron',(0.,0.,-.96),(.15,.14,.09),place)
        else:
            box(f'shaft{i}',material,(0.,0.,-(length+.62)*.5),(.14,.11,(length-.62)*.5),place)
            box(f'bit{i}bridge',material,(-.20,0.,-length+.48),(.14,.15,.47),place)
            for tooth,z in enumerate((.12,.48,.84)):
                box(f'bit{i}tooth{tooth}',material,(-.45,0.,-length+z),(.25,.15,.10),place)
    return result

def geometry(segments, sides):
    vertices, uv, faces = [], [], []
    for _,_,points,triangles in components(segments,sides):
        offset=len(vertices)
        vertices.extend(points)
        uv.extend([(0.,0.)]*len(points))
        faces.extend(tuple(offset+i for i in tri) for tri in triangles)
    return vertices,uv,faces

def collision_spheres():
    spheres=[(2.6*math.cos(i*math.tau/24),0.,2.6*math.sin(i*math.tau/24),.24) for i in range(24)]
    for index,(angle,length) in enumerate(KEYS):
        center,across,inward,_=key_frame(index,angle)
        spheres.extend([tuple(center[k]+across[k]*bow_profile(index,a)[0]+inward[k]*bow_profile(index,a)[1] for k in range(3))+(.15,)
                        for a in (i*math.tau/8 for i in range(8))])
        r,_,_=frame(angle,0.)
        spheres.extend([(r[0]*(2.8+length*i/7),0.,r[2]*(2.8+length*i/7),.23) for i in range(8)])
    return spheres

def attachment_clearance(samples=360):
    """Conservative centreline distance bounds, minus both wires and sample error."""
    hoop=[(2.6*math.cos(i*math.tau/samples),0.,2.6*math.sin(i*math.tau/samples)) for i in range(samples)]
    bounds=[]
    for index,(angle,_) in enumerate(KEYS):
        center,across,inward,_=key_frame(index,angle)
        bow=[tuple(center[k]+across[k]*bow_profile(index,a)[0]+inward[k]*bow_profile(index,a)[1] for k in range(3))
             for a in (i*math.tau/samples for i in range(samples))]
        sampled=min(math.dist(a,b) for a in hoop for b in bow)
        profile=[bow_profile(index,i*math.tau/samples) for i in range(samples+1)]
        error=2.6*math.tau/samples+max(math.dist(a,b) for a,b in zip(profile,profile[1:]))
        bounds.append(sampled-.19-.12-error)
    return bounds
