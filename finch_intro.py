"""
finch_intro.py  -  animated Finch bird for Streamlit.
Updated with app background color (#0b0f19) and banner/portal integration.
"""
import streamlit as st
import streamlit.components.v1 as components

_MARKER = "finch-splash-marker"

_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  html, body { height:100%; margin:0; background:__BG__; overflow:hidden; }
  #bird { position:absolute; left:0; top:0; will-change:transform;
          filter:drop-shadow(0 12px 24px rgba(18,196,170,.25)); }
  #bird svg { display:block; width:100%; height:100%; overflow:visible; }
  .ring { position:absolute; left:50%; top:50%; width:200px; height:200px; margin:-100px 0 0 -100px;
          border:3px solid #EFA94E; border-radius:50%; opacity:0; pointer-events:none; }
  .ring.go { animation:ring 1.1s ease-out forwards; }
  .ring.go.r2 { animation-delay:.18s; border-color:#12C4AA; }
  @keyframes ring { 0%{transform:scale(.3);opacity:.9} 100%{transform:scale(3.2);opacity:0} }
  #arrow { transform-box:fill-box; transform-origin:0% 100%; }
  #arrow.pop { animation:pop .7s cubic-bezier(.3,1.6,.5,1); }
  @keyframes pop { 0%{transform:scale(1)} 40%{transform:scale(1.22) rotate(-4deg)} 100%{transform:scale(1)} }
  button { position:absolute; left:50%; bottom:10px; transform:translateX(-50%);
           background:transparent; color:#EFA94E; border:1.5px solid #EFA94E; border-radius:999px;
           padding:6px 16px; font-size:12px; cursor:pointer; opacity:0; transition:opacity .5s;
           display:__BTN__; }
  button.show { opacity:1; }
</style></head>
<body class="__MARKER__">
<div class="ring"></div><div class="ring r2"></div>
<div id="bird">
  <svg viewBox="510 115 435 350" xmlns="http://www.w3.org/2000/svg">
    <g stroke="#FFFFFF" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">
      <g id="wing">
        <path d="M591,121 L710,236 L583,182 Z" fill="#0E8783"/>
        <path d="M517,168 L583,182 L710,236 L636,284 L592,264 Q540,232 517,168 Z" fill="#12A9A1"/>
        <path d="M541,263 Q600,268 636,284 L634,342 Q592,298 541,263 Z" fill="#169A92"/>
      </g>
      <path d="M553,452 L634,342 Q642,374 662,405 Q622,456 578,460 Q560,458 553,452 Z" fill="#0E7B7A"/>
      <path d="M710,236 L662,405 Q642,374 634,342 L636,284 Z" fill="#0F9D93"/>
      <path d="M710,236 L742,284 L778,300 L812,312 Q808,382 735,398 Q700,406 662,405 Z" fill="#12C4AA"/>
      <path d="M738,284 L778,300 L760,312 L742,296 Z" fill="#12C4AA"/>
      <path d="M727,216 Q736,186 772,176 Q806,170 820,196 L848,209 L822,224 Q816,246 800,262 Q785,278 760,278 Q736,270 724,246 Q722,230 727,216 Z" fill="#EFA94E"/>
      <g id="arrow">
        <polyline points="750,298 773,321 912,181" fill="none" stroke="#FFFFFF" stroke-width="30" stroke-linejoin="miter" stroke-linecap="butt"/>
        <polyline points="750,298 773,321 912,181" fill="none" stroke="#EFA94E" stroke-width="27" stroke-linejoin="miter" stroke-linecap="butt"/>
        <path d="M937,150 L882,163 L922,204 Z" fill="#EFA94E"/>
      </g>
    </g>
    <circle cx="788" cy="205" r="7" fill="#0A1A33"/>
  </svg>
</div>
<button id="replay">Replay Animation</button>
<script>
(function () {
  var bird = document.getElementById('bird'), wing = document.getElementById('wing'),
      arrow = document.getElementById('arrow'), btn = document.getElementById('replay'),
      rings = document.querySelectorAll('.ring');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var DURATION = 3.4, W, H, size, bh, start = null, last = 0, phase = 0, landed = false, started = false;

  function layout() {
    W = window.innerWidth; H = window.innerHeight;
    size = Math.max(140, Math.min(W * 0.4, H * 0.7, 340));
    bh = size * 350 / 435;
    bird.style.width = size + 'px'; bird.style.height = bh + 'px';
  }
  function bez(p, a, b, c) { var u = 1 - p; return u*u*a + 2*u*p*b + p*p*c; }
  function pos(p) { return [bez(p, -size, W*0.28, W*0.5), bez(p, H*0.32, -H*0.12, H*0.5)]; }
  function smooth(a, b, x) { var t = Math.max(0, Math.min(1, (x-a)/(b-a))); return t*t*(3-2*t); }
  function place(x, y, tilt) {
    bird.style.transform = 'translate(' + (x - size/2) + 'px,' + (y - bh/2) + 'px) rotate(' + tilt + 'deg)';
  }
  function setWing(d) { wing.setAttribute('transform', 'rotate(' + d + ' 710 236)'); }
  function land() {
    landed = true;
    arrow.classList.remove('pop'); void arrow.getBoundingClientRect(); arrow.classList.add('pop');
    rings.forEach(function (r) { r.classList.remove('go'); void r.offsetWidth; r.classList.add('go'); });
    btn.classList.add('show');
  }
  function frame(ts) {
    if (start === null) { start = ts; last = ts; }
    var dt = Math.min((ts - last) / 1000, 0.05); last = ts;
    var t = (ts - start) / 1000, p = Math.min(t / DURATION, 1);
    if (p < 1) {
      var e = 1 - Math.pow(1 - p, 2.2), a = pos(e), b = pos(Math.min(e + 0.01, 1));
      var heading = Math.atan2(b[1]-a[1], b[0]-a[0]) * 180 / Math.PI;
      var tilt = Math.max(-25, Math.min(25, heading * 0.55)) * (1 - smooth(0.6, 1, p));
      tilt -= 14 * Math.sin(Math.PI * smooth(0.72, 1, p));
      place(a[0], a[1] + Math.sin(t * 7) * 10 * (1 - p), tilt);
      phase += 2 * Math.PI * (11 - 5 * p) * dt;
      var amp = p < 0.82 ? 1 : Math.max(0, 1 - (p - 0.82) / 0.18);
      setWing(amp * (Math.sin(phase) * 26 + 10));
    } else {
      if (!landed) land();
      place(W * 0.5, H * 0.5 + Math.sin(t * 2.2) * 3, 0);
      setWing(0);
    }
    requestAnimationFrame(frame);
  }
  function go() {
    layout(); start = reduce ? -1e9 : null; phase = 0; landed = false; btn.classList.remove('show');
    if (!started) { started = true; requestAnimationFrame(frame); }
  }
  btn.addEventListener('click', go);
  window.addEventListener('resize', layout);
  go();
})();
</script>
</body></html>"""


def show_finch_intro(mode: str = "splash", height: int = 240, bg: str = "#0b0f19") -> None:
    """Render the animated Finch bird with app matching background (#0b0f19)."""
    if mode == "splash":
        if st.session_state.get("_finch_intro_done"):
            return
        st.session_state["_finch_intro_done"] = True
        st.markdown(
            f"""<style>
            iframe[srcdoc*="{_MARKER}"] {{
                position: fixed !important; inset: 0 !important;
                width: 100vw !important; height: 100vh !important;
                z-index: 999999; border: 0; pointer-events: none;
                animation: finchFade 6.2s forwards;
            }}
            @keyframes finchFade {{
                0%, 80% {{ opacity: 1; visibility: visible; }}
                100%    {{ opacity: 0; visibility: hidden; }}
            }}
            </style>""",
            unsafe_allow_html=True,
        )
        html = _HTML.replace("__BTN__", "none")
        components.html(html.replace("__BG__", bg).replace("__MARKER__", _MARKER), height=1)
    else:
        html = _HTML.replace("__BTN__", "block")
        components.html(html.replace("__BG__", bg).replace("__MARKER__", "finch-banner"),
                        height=height, scrolling=False)