"use client";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import Link from "next/link";

const CustomMap = dynamic(() => import("@/components/CustomMap"), { ssr: false });

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0B0F13] text-white">
      {/* Navbar */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#0E1420]/80 backdrop-blur">
        <div className="mx-auto max-w-7xl px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded bg-gradient-to-br from-emerald-400 to-sky-500 shadow-md" />
            <span className="font-semibold tracking-wide">Car Speed Simulator</span>
          </div>
          <nav className="hidden md:flex items-center gap-2 text-sm text-white/80">
            <a href="#demo" className="px-3 py-1.5 rounded-full border border-white/10 hover:border-white/30 hover:text-white bg-white/0 hover:bg-white/[0.06] transition">Simulator</a>
            <a href="#tech" className="px-3 py-1.5 rounded-full border border-white/10 hover:border-white/30 hover:text-white bg-white/0 hover:bg-white/[0.06] transition">Tech</a>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative">
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, ease: "easeOut" }}
          className="mx-auto max-w-7xl px-6 py-16 md:py-20">
          <h1 className="text-3xl md:text-5xl font-semibold leading-tight bg-gradient-to-r from-emerald-300 to-sky-400 bg-clip-text text-transparent">Car Speed Simulator</h1>
          <p className="mt-4 text-white/70 max-w-2xl">Simulate vehicle speed along real-world routes with elevation-aware target planning, EKF-corrected GPS, and a C++ physics engine for realistic acceleration, braking and gearing.</p>
          <div className="mt-6">
            <a href="#demo" className="inline-flex items-center gap-2 rounded-md bg-gradient-to-r from-emerald-400 to-sky-400 px-5 py-2.5 font-medium text-black shadow-md hover:shadow-lg active:brightness-95 transition">Launch Simulator</a>
          </div>
        </motion.div>
      </section>

      {/* Demo: Map + HUD */}
      <section id="demo" className="py-8 md:py-12">
        <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.35, ease: "easeOut" }}
          className="mx-auto max-w-7xl px-6 grid lg:grid-cols-2 gap-8">
          {/* Map Card */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.06] shadow-2xl overflow-hidden backdrop-blur-sm">
            <div className="px-5 py-3 border-b border-white/10 text-xs uppercase tracking-wider text-white/60">Simulation</div>
            <div className="p-0">
              {/* Responsive map container */}
              <div className="relative w-full rounded-none">
                {/* Mobile: 65vh height; Tablet/Desktop: aspect 16/9 with min-heights */}
                <div className="relative w-full h-[65vh] md:h-auto md:aspect-[16/9] md:min-h-[480px] lg:min-h-[560px] xl:min-h-[640px]">
                  <div className="absolute inset-0">
                    <CustomMap />
                  </div>
                </div>
              </div>
            </div>
            {/* Tip box */}
            <div className="px-5 py-3 bg-black/20 backdrop-blur-sm border-t border-white/10">
              <div className="text-xs text-white/60 flex items-center gap-2">
                <span className="text-emerald-400">💡</span>
                <span>Tip: Zoom in to see the vehicle movements clearly</span>
              </div>
            </div>
          </div>

          {/* HUD Card */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.06] shadow-2xl overflow-hidden backdrop-blur-sm">
            <div className="px-5 py-3 border-b border-white/10 text-xs uppercase tracking-wider text-white/60">Telemetry</div>
            <div className="p-6 space-y-6 text-sm text-white/80">
              <div className="grid grid-cols-2 gap-3">
                <KPI label="Current speed" valueSlot="current" suffix="km/h" accent="emerald" />
                <KPI label="Target speed" valueSlot="target" suffix="km/h" accent="sky" />
              </div>
              <div className="space-y-2">
                <Metric label="Acceleration" slot="accel" />
                <Metric label="Heading" slot="heading" />
                <Metric label="Roll/Pitch" slot="rp" />
              </div>
              <div className="border-t border-white/10 pt-4">
                <div className="text-[11px] text-white/50 mb-2 uppercase tracking-wider">Road profile</div>
                <div className="space-y-2">
                  <Metric label="Elevation" slot="elevation" />
                  <Metric label="Slope" slot="slope" />
                  <Metric label="Road Grade" slot="grade" />
                  <Metric label="Curvature" slot="curve" />
                </div>
              </div>
              {/* Environmental factors section removed - no real data available */}
              <ProgressBar />
              <ErrorBanner />
            </div>
          </div>
        </motion.div>
      </section>

      {/* Technology */}
      <section id="tech" className="py-12 md:py-16">
        <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.35 }}
          className="mx-auto max-w-7xl px-6 grid md:grid-cols-3 gap-6 text-white/80">
          <TechCard title="EKF Fusion" desc="Extended Kalman filter for smoother GPS and motion estimates." />
          <TechCard title="Elevation-aware Speeds" desc="Elevation and road grade inform target speed planning." />
          <TechCard title="C++ Physics Engine" desc="Realistic acceleration/braking and gear logic drive speed tracking." />
        </motion.div>
      </section>



      {/* Footer */}
      <footer className="border-t border-white/10 py-6 text-center text-xs text-white/50">
        <div className="mx-auto max-w-7xl px-6 flex items-center justify-center">
          <span className="text-white">Made by Beyza Karaşahan</span>
        </div>
      </footer>
    </div>
  );
}

function KPI({ label, valueSlot, suffix, accent }: { label: string; valueSlot: string; suffix: string; accent: "emerald" | "sky" }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }} className="rounded-lg bg-black/40 p-4">
      <div className="text-xs text-white/60">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className={`text-2xl font-semibold ${accent === "emerald" ? "text-emerald-400" : "text-sky-400"}`} id={`kpi-${valueSlot}`}>0.0</span>
        <span className="text-xs text-white/50">{suffix}</span>
      </div>
    </motion.div>
  );
}

function Metric({ label, slot }: { label: string; slot: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <div className="text-white/60">{label}</div>
      <div className="text-white/80" id={`metric-${slot}`}>—</div>
    </div>
  );
}

function ProgressBar() {
  return (
    <div>
      <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden">
        <div className="h-2 bg-gradient-to-r from-emerald-500 to-sky-500 w-[0%]" id="progress-bar" />
      </div>
      <div className="mt-1 flex justify-between text-xs text-white/50">
        <span id="progress-left">0m</span>
        <span id="progress-right">0m</span>
      </div>
    </div>
  );
}

function ErrorBanner() {
  return (
    <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}
      className="hidden" id="error-banner">
      <div className="mt-2 rounded bg-red-500/15 border border-red-400/30 text-red-300 px-3 py-2 text-xs">
        Error fetching route. Please try again.
      </div>
    </motion.div>
  );
}

function TechCard({ title, desc }: { title: string; desc: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.25 }}
      className="rounded-xl border border-white/10 bg-white/5 p-6 shadow-lg">
      <div className="text-white font-semibold">{title}</div>
      <div className="mt-2 text-white/70 text-sm leading-relaxed">{desc}</div>
    </motion.div>
  );
}
