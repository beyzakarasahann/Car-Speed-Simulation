// utils/slope.ts
export type Pt = { lat: number; lon: number; ele: number };

const R = 6371000;
const toRad = (x: number) => (x * Math.PI) / 180;

export function haversine(a: Pt, b: Pt) {
  const dLat = toRad(b.lat - a.lat), dLon = toRad(b.lon - a.lon);
  const la1 = toRad(a.lat), la2 = toRad(b.lat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(Math.max(0, Math.min(1, h))));
}

function median5(arr: number[]) {
  if (arr.length < 5) return arr.slice();
  const out = arr.slice();
  for (let i = 2; i < arr.length - 2; i++) {
    const w = [arr[i - 2], arr[i - 1], arr[i], arr[i + 1], arr[i + 2]].sort((a, b) => a - b);
    out[i] = w[2];
  }
  return out;
}

export function resampleRoute(points: Pt[], stepM = 10): Pt[] {
  if (points.length < 2) return points.slice();
  const out: Pt[] = [points[0]];
  let acc = 0;
  for (let i = 1; i < points.length; i++) {
    let a = points[i - 1], b = points[i];
    let seg = haversine(a, b);
    if (seg <= 1e-6) {
      acc += seg;
      continue;
    }
    while (acc + seg >= stepM) {
      const t = (stepM - acc) / seg;
      const lat = a.lat + (b.lat - a.lat) * t;
      const lon = a.lon + (b.lon - a.lon) * t;
      const ele = a.ele + (b.ele - a.ele) * t;
      const p = { lat, lon, ele };
      out.push(p);
      a = p;
      seg = haversine(a, b);
      acc = 0;
    }
    acc += seg;
  }
  return out;
}

export function computeStableSlopeDeg(
  pts: Pt[],
  stepM = 10,
  win = 11,
  deadbandDeg = 0.5,
  emaAlpha = 0.3
) {
  if (pts.length < 3) return { resampled: pts.slice(), slopeDeg: pts.map(() => 0) };

  const rs = resampleRoute(pts, stepM);
  const eleMed = median5(rs.map((p) => p.ele));
  const dist = rs.map((_, i) => i * stepM);

  const half = Math.floor(win / 2);
  const raw: number[] = new Array(rs.length).fill(0);

  // prefix sums for fast local regression
  const px: number[] = [0], py: number[] = [0], pxx: number[] = [0], pxy: number[] = [0];
  for (let i = 0; i < rs.length; i++) {
    const x = dist[i], y = eleMed[i];
    px.push(px[i] + x);
    py.push(py[i] + y);
    pxx.push(pxx[i] + x * x);
    pxy.push(pxy[i] + x * y);
  }

  for (let i = 0; i < rs.length; i++) {
    const l = Math.max(0, i - half), r = Math.min(rs.length - 1, i + half);
    const n = r - l + 1;
    const sx = px[r + 1] - px[l], sy = py[r + 1] - py[l];
    const sxx = pxx[r + 1] - pxx[l], sxy = pxy[r + 1] - pxy[l];
    const varX = sxx - (sx * sx) / n;
    let beta = 0;
    if (varX > 1e-9) {
      const cov = sxy - (sx * sy) / n;
      beta = cov / varX; // ele per meter
    }
    let deg = Math.atan(beta) * (180 / Math.PI);
    if (Math.abs(deg) < deadbandDeg) deg = 0;
    if (deg > 20) deg = 20;
    if (deg < -20) deg = -20;
    raw[i] = deg;
  }

  // EMA
  const out: number[] = new Array(raw.length);
  let ema = raw[0];
  out[0] = ema;
  for (let i = 1; i < raw.length; i++) {
    ema = emaAlpha * raw[i] + (1 - emaAlpha) * ema;
    out[i] = ema;
  }
  return { resampled: rs, slopeDeg: out };
}

export function slopeDegToGradePct(deg: number) {
  return Math.tan((deg * Math.PI) / 180) * 100;
}


