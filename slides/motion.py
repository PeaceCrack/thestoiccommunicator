"""Deterministic motion. Every animation is paused and driven by one CSS variable, --t
(seconds into the loop). Rendering frame k sets --t = k / fps, so frames are exact and a
still image is just the frame at T_STILL, where everything has finished revealing.
"""

LOOP_S = 4.0
T_STILL = 3.6
STAGGER_S = 0.32
FPS = 12

_RUN = f"{LOOP_S}s linear infinite both paused"
_DELAY = f"calc(var(--i, 0) * {STAGGER_S}s - var(--t) * 1s)"

CSS = f"""
@property --n {{ syntax: '<integer>'; inherits: false; initial-value: 0; }}
@property --p {{ syntax: '<number>'; inherits: false; initial-value: 0; }}
@keyframes rise {{ 0% {{ opacity: 0; transform: translateY(34px); }} 10%, 100% {{ opacity: 1; transform: none; }} }}
@keyframes grow {{ 0% {{ transform: scaleX(0); }} 18%, 100% {{ transform: scaleX(1); }} }}
@keyframes growy {{ 0% {{ transform: scaleY(0); }} 18%, 100% {{ transform: scaleY(1); }} }}
@keyframes pop {{ 0%, 4% {{ transform: scale(0); }} 12% {{ transform: scale(1.2); }} 16%, 100% {{ transform: scale(1); }} }}
@keyframes strike {{ 0%, 6% {{ transform: scaleX(0); }} 14%, 100% {{ transform: scaleX(1); }} }}
@keyframes count {{ 0% {{ --n: 0; }} 35%, 100% {{ --n: var(--to); }} }}
@keyframes ring {{ 0% {{ --p: 0; }} 35%, 100% {{ --p: var(--to); }} }}
@keyframes type {{ 0% {{ clip-path: inset(0 100% 0 0); }} 14%, 100% {{ clip-path: inset(0 0 0 0); }} }}
@keyframes dash {{ to {{ stroke-dashoffset: -96; }} }}
@keyframes drift {{ 0%, 100% {{ transform: translate(0, 0); }} 50% {{ transform: translate(24px, -30px); }} }}
@keyframes spin {{ 0%, 100% {{ transform: rotate(0deg); }} 50% {{ transform: rotate(18deg); }} }}
@keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}

.seq > * {{ animation: rise {_RUN}; animation-delay: {_DELAY}; }}
.grow {{ transform-origin: left center; animation: grow {_RUN}; animation-delay: {_DELAY}; }}
.growy {{ transform-origin: center bottom; animation: growy {_RUN}; animation-delay: {_DELAY}; }}
.pop {{ animation: pop {_RUN}; animation-delay: {_DELAY}; }}
.strike-line {{ transform-origin: left center; animation: strike {_RUN}; animation-delay: {_DELAY}; }}
.count {{ animation: count {_RUN}; animation-delay: calc(-1s * var(--t)); counter-reset: n var(--n); }}
.count::after {{ content: counter(n); }}
.ring {{ animation: ring {_RUN}; animation-delay: calc(-1s * var(--t)); }}
.type {{ animation: type {_RUN}; animation-delay: {_DELAY}; }}
.dash {{ stroke-dasharray: 18 14; animation: dash {_RUN}; animation-delay: calc(-1s * var(--t)); }}
.cursor {{ animation: blink 1s linear infinite both paused; animation-delay: calc(-1s * var(--t)); }}
.art-svg .drift {{ animation: drift {_RUN}; animation-delay: calc(var(--i, 0) * -0.7s - var(--t) * 1s); }}
.art-svg .spin {{ transform-box: fill-box; transform-origin: center;
  animation: spin {_RUN}; animation-delay: calc(var(--i, 0) * -1.3s - var(--t) * 1s); }}
"""
