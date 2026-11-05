import sys, json, math, numpy as np
d = sys.argv[1]
items = {o[4][11:19]: o for o in json.load(open(f"{d}/items.json"))}
bbox = (34.555, 47.497, 34.640, 47.532); W, H = 639, 389
mx = (bbox[2]-bbox[0])*111320*math.cos(math.radians(47.515))/W; my = (bbox[3]-bbox[1])*111320/H
def px(lat, lon): return ((lon-bbox[0])/(bbox[2]-bbox[0])*W, (bbox[3]-lat)/(bbox[3]-bbox[1])*H)
def bil(a, x, y):
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int); fx, fy = x-x0, y-y0
    g = lambda yy, xx: a[yy, xx]
    return g(y0,x0)*(1-fx)*(1-fy)+g(y0,x0+1)*fx*(1-fy)+g(y0+1,x0)*(1-fx)*fy+g(y0+1,x0+1)*fx*fy
pts = {"CT1": (47.52165, 34.56962), "CT2": (47.52216, 34.5677)}
R_TOP = 26.0
for n in sys.argv[2:]:
    o = items[n]; el, az = o[2], o[3]; a = np.load(f"{d}/{n}.npy").astype(float)[1]
    sa = math.radians(az+180); out = []
    for k, (la, lo) in pts.items():
        x0, y0 = px(la, lo); s = np.arange(100, 700, 2.0)
        v = np.mean([bil(a, x0+(s*math.sin(sa)+w*math.cos(sa))/mx, y0-(s*math.cos(sa)-w*math.sin(sa))/my) for w in (-10, 0, 10)], 0)
        dark = np.median(v[(s > 150) & (s < 280)])
        i = np.argmax((s > 250) & (v > dark + 0.5*(np.median(v[(s > 450)]) - dark)))  # first crossing halfway to the ground beyond
        L = s[i]; Hm = (L - R_TOP)*math.tan(math.radians(el))
        out.append(f"{k} tip {L:.0f} m -> H {Hm:.0f} m")
    print(n, f"el {el:5.2f}", " | ".join(out))
