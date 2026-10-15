import bpy, bmesh, math, os
from mathutils import Vector
D=os.path.dirname(os.path.abspath(__file__))
os.makedirs(D+'/export',exist_ok=True); os.makedirs(D+'/render',exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.unit_settings.system='METRIC'; sc.unit_settings.scale_length=1.0; sc.unit_settings.length_unit='METERS'
cols={n:bpy.data.collections.new(n) for n in ('Model','Lights','Camera')}
for c in cols.values(): sc.collection.children.link(c)

def hexrgb(h):
    h=h.lstrip('#'); r,g,b=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    f=lambda c:(c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4)
    return (f(r),f(g),f(b),1)
mats={}
def mat(name,hexc,rough=0.85):
    m=bpy.data.materials.new('Mat_'+name); m.use_nodes=True
    b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=hexrgb(hexc); b.inputs['Roughness'].default_value=rough
    b.inputs['Metallic'].default_value=0.0
    mats[name]=m
mat('Ink','#FF6A00'); mat('Skin','#FFDCC2'); mat('EyeWhite','#FFFFFF',0.5); mat('Pupil','#1A1020',0.4)
mat('EyeRim','#2A1830',0.5); mat('Shirt','#F2F2F2'); mat('Shorts','#2B3A67'); mat('Shoes','#3A3A44')

def link(o,coll='Model'):
    for c in o.users_collection: c.objects.unlink(o)
    cols[coll].objects.link(o)
def sphere(name,m,loc,scale,rot=(0,0,0),seg=16,rings=10):
    me=bpy.data.meshes.new(name); bm=bmesh.new()
    bmesh.ops.create_uvsphere(bm,u_segments=seg,v_segments=rings,radius=1.0)
    bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new(name,me); link(o)
    o.location=loc; o.scale=scale; o.rotation_euler=rot
    o.data.materials.append(mats[m])
    for p in me.polygons: p.use_smooth=True
    return o
def limb(name,m,a,b,r0,r1,seg=12):
    a=Vector(a); b=Vector(b); d=b-a
    me=bpy.data.meshes.new(name); bm=bmesh.new()
    bmesh.ops.create_cone(bm,cap_ends=True,segments=seg,radius1=r0,radius2=r1,depth=d.length)
    bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new(name,me); link(o)
    o.location=(a+b)/2
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    o.data.materials.append(mats[m])
    for p in me.polygons: p.use_smooth=True
    return o

# ---- body (faces -Y) ----
H=Vector((0,0,0.86))
sphere('Head','Skin',H,(0.22,0.21,0.22),seg=32,rings=20)
sphere('Hair_Cap','Ink',(0,0.035,0.915),(0.238,0.225,0.205),seg=32,rings=20)
sphere('Torso','Shirt',(0,0,0.51),(0.16,0.11,0.19))
sphere('Pelvis','Shorts',(0,0,0.36),(0.165,0.115,0.1))
for s,n in ((1,'R'),(-1,'L')):
    limb('Leg_'+n,'Skin',(0.085*s,0,0.33),(0.085*s,0,0.1),0.055,0.045)
    sphere('Shoe_'+n,'Shoes',(0.085*s,-0.035,0.05),(0.075,0.14,0.055))
    limb('Arm_'+n,'Skin',(0.185*s,0,0.62),(0.25*s,-0.03,0.40),0.04,0.035)
    sphere('Sleeve_'+n,'Shirt',(0.2*s,0,0.62),(0.075,0.07,0.07))
    sphere('Hand_'+n,'Skin',(0.255*s,-0.03,0.37),(0.045,0.045,0.045),seg=10,rings=8)
    # eyes: ellipse, outer corner raised (slanted)
    ex=0.085*s
    tilt=math.radians(-18)*s   # rotation about Y -> outer end up
    sphere('EyeRim_'+n,'EyeRim',(ex,-0.168,0.865),(0.082,0.03,0.064),rot=(0,tilt,0),seg=20,rings=10)
    sphere('EyeWhite_'+n,'EyeWhite',(ex,-0.185,0.865),(0.07,0.03,0.052),rot=(0,tilt,0),seg=16,rings=10)
    sphere('Pupil_'+n,'Pupil',(ex*0.95,-0.208,0.862),(0.04,0.018,0.036),rot=(0,tilt,0),seg=12,rings=8)
    sphere('Cheek_'+n,'Ink',(0.125*s,-0.17,0.775),(0.001,0.001,0.001),seg=4,rings=3).hide_render=True

# ---- tentacle hair ----
def bez(p0,p1,p2,p3,t):
    return ((1-t)**3)*p0+3*((1-t)**2)*t*p1+3*(1-t)*t*t*p2+t**3*p3
def tentacle(name,pts,r0,r1,n=18,sx=1.0):
    p0,p1,p2,p3=[Vector(p) for p in pts]
    objs=[]
    for i in range(n):
        t=i/(n-1); p=bez(p0,p1,p2,p3,t)
        r=r0+(r1-r0)*t**0.8
        tn=(bez(p0,p1,p2,p3,min(t+0.02,1))-bez(p0,p1,p2,p3,max(t-0.02,0))).normalized()
        o=sphere(f'{name}_{i}','Ink',p,(r*1.0,r*1.0,r*1.0),seg=12,rings=8)
        # stretch along the tangent
        o.rotation_euler=tn.to_track_quat('Y','Z').to_euler()
        o.scale=(r,r*1.6,r)
        objs.append(o)
    return objs
tents=[]
for s,n in ((1,'R'),(-1,'L')):
    tents+=tentacle('Tent_'+n,[(0.10*s,0.10,1.05),(0.40*s,0.30,1.15),(0.46*s,0.52,0.85),(0.30*s,0.52,0.55)],0.105,0.035)
tents+=tentacle('Bang',[(0.0,-0.10,1.10),(0.0,-0.22,1.13),(0.02,-0.30,1.05),(0.03,-0.27,0.98)],0.07,0.03,n=10)

# ---- join into groups for cleanliness ----
def join(objs,name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]
    bpy.ops.object.join(); bpy.context.active_object.name=name
bpy.context.view_layer.objects.active=None
ink_t=[o for o in bpy.data.objects if o.name.startswith(('Tent_','Bang'))]
# need view layer active; join per tentacle
for pre in ('Tent_R','Tent_L','Bang'):
    join([o for o in bpy.data.objects if o.name.startswith(pre+'_')],pre)
for o in list(bpy.data.objects):
    if o.name.startswith('Cheek_'): bpy.data.objects.remove(o)

# ---- lights ----
def area(name,loc,energy,size):
    l=bpy.data.lights.new(name,'AREA'); l.energy=energy; l.size=size
    o=bpy.data.objects.new(name,l); cols['Lights'].objects.link(o); o.location=loc
    t=bpy.data.objects.new(name+'_aim',None)
    return o
target=bpy.data.objects.new('Target',None); target.location=(0,0.05,0.62); cols['Camera'].objects.link(target)
for n,loc,e,s in (('Key',(2.2,-2.6,2.2),220,2.0),('Fill',(-2.6,-2.0,1.0),70,2.5),('Rim',(0.5,2.6,1.9),130,1.5)):
    o=area(n,loc,e,s)
    c=o.constraints.new('TRACK_TO'); c.target=target; c.track_axis='TRACK_NEGATIVE_Z'; c.up_axis='UP_Y'
cam=bpy.data.cameras.new('Cam'); cam.lens=50
co=bpy.data.objects.new('Camera',cam); cols['Camera'].objects.link(co); co.location=(1.0,-2.8,0.95); sc.camera=co
c=co.constraints.new('TRACK_TO'); c.target=target; c.track_axis='TRACK_NEGATIVE_Z'; c.up_axis='UP_Y'

# ---- world / render ----
w=bpy.data.worlds.new('W'); w.use_nodes=True; sc.world=w
bg=w.node_tree.nodes['Background']; bg.inputs['Color'].default_value=(0.6,0.6,0.6,1); bg.inputs['Strength'].default_value=1.0
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=int(os.environ.get('SAMPLES',48))
sc.cycles.use_denoising=True
sc.view_settings.view_transform='Standard'
sc.render.resolution_x=1280; sc.render.resolution_y=960; sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'; sc.render.film_transparent=False
sc.render.filepath=D+'/render/inkling_render.png'

bpy.ops.wm.save_as_mainfile(filepath=D+'/inkling.blend')
bpy.ops.render.render(write_still=True)

# ---- export ----
bpy.ops.object.select_all(action='DESELECT')
dg=bpy.context.evaluated_depsgraph_get(); tris=0; verts=0
for o in cols['Model'].objects:
    o.select_set(True)
    me=o.evaluated_get(dg).to_mesh(); me.calc_loop_triangles(); tris+=len(me.loop_triangles); verts+=len(me.vertices)
bpy.context.view_layer.objects.active=cols['Model'].objects[0]
bpy.ops.export_scene.gltf(filepath=D+'/export/inkling.glb',export_format='GLB',use_selection=True,export_apply=True,export_materials='EXPORT',export_yup=True)
print('TRIS',tris,'VERTS',verts,'OBJS',len(cols['Model'].objects))
