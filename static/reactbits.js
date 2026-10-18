/* reactbits.js - dependency-free ReactBits-style effects. Exposes window.RB only. */
(function () {
  'use strict';

  var RM = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  var reduced = function () { return !!(RM && RM.matches); };
  var rafs = new WeakMap();

  // Run fn(el) once the element is 20% visible (immediately if no IntersectionObserver).
  function onView(el, fn) {
    if (!('IntersectionObserver' in window)) return fn(el);
    var io = new IntersectionObserver(function (es) {
      if (es[0].isIntersecting) { io.disconnect(); fn(el); }
    }, { threshold: 0.2 });
    io.observe(el);
  }

  // Eased count from the element's current number to `to` (~900ms). Non-numeric text counts as 0.
  function countUp(el, to) {
    to = Number(to);
    if (!el || isNaN(to)) return;
    var from = parseFloat(String(el.textContent).replace(/[^0-9.-]/g, ''));
    if (isNaN(from)) from = 0;
    cancelAnimationFrame(rafs.get(el) || 0);
    if (reduced()) { el.textContent = String(Math.round(to)); return; }
    var t0 = performance.now();
    (function step(now) {
      var p = Math.min(1, (now - t0) / 900), e = 1 - Math.pow(1 - p, 3);
      el.textContent = String(Math.round(from + (to - from) * e));
      rafs.set(el, p < 1 ? requestAnimationFrame(step) : 0);
    })(t0);
  }

  function initCount(el) {
    var to = Number(el.getAttribute('data-to'));
    if (isNaN(to)) return;
    if (reduced()) { el.textContent = String(to); return; }
    el.textContent = '0';
    onView(el, function () { countUp(el, to); });
  }

  // Split into words, each animates in with a 60ms stagger.
  function blurText(el) {
    var text = el.textContent.trim();
    if (!text || reduced()) return;
    var words = text.split(/\s+/);
    el.textContent = '';
    words.forEach(function (w, i) {
      var s = document.createElement('span');
      s.textContent = w;
      s.style.transitionDelay = i * 60 + 'ms';
      el.appendChild(s);
      if (i < words.length - 1) el.appendChild(document.createTextNode(' '));
    });
    el.classList.add('rb-blur');
    onView(el, function () { el.classList.add('is-in'); });
  }

  // Pointer-relative glow: CSS reads --mx / --my.
  function spotlight(el) {
    el.addEventListener('pointermove', function (e) {
      var r = el.getBoundingClientRect();
      el.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      el.style.setProperty('--my', (e.clientY - r.top) + 'px');
    });
  }

  // Drifting dots with faint links. Runs only while visible on screen and tab shown.
  function particles(cv) {
    var ctx = cv.getContext('2d'), rm = reduced(), N = 60, LINK = 110;
    var W = 0, H = 0, last = 0, raf = 0, running = false, onScreen = true, dots = [];
    if (getComputedStyle(cv.parentNode).position === 'static') cv.parentNode.style.position = 'relative';
    for (var i = 0; i < N; i++) dots.push({
      x: Math.random(), y: Math.random(),
      vx: (Math.random() - 0.5) * 0.02, vy: (Math.random() - 0.5) * 0.02,
      r: 0.6 + Math.random() * 1.2, a: 0.15 + Math.random() * 0.35
    });

    function size() {
      var dpr = window.devicePixelRatio || 1, r = cv.getBoundingClientRect();
      W = r.width; H = r.height;
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function render(dt) {
      ctx.clearRect(0, 0, W, H);
      dots.forEach(function (d) {
        d.x = (d.x + d.vx * dt + 1) % 1; d.y = (d.y + d.vy * dt + 1) % 1;
      });
      for (var i = 0; i < N; i++) for (var j = i + 1; j < N; j++) {
        var a = dots[i], b = dots[j], dx = (a.x - b.x) * W, dy = (a.y - b.y) * H;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < LINK) {
          ctx.strokeStyle = 'rgba(255,255,255,' + (0.12 * (1 - dist / LINK)).toFixed(3) + ')';
          ctx.beginPath(); ctx.moveTo(a.x * W, a.y * H); ctx.lineTo(b.x * W, b.y * H); ctx.stroke();
        }
      }
      dots.forEach(function (d) {
        ctx.fillStyle = 'rgba(255,255,255,' + d.a + ')';
        ctx.beginPath(); ctx.arc(d.x * W, d.y * H, d.r, 0, Math.PI * 2); ctx.fill();
      });
    }

    function frame(now) {
      if (!cv.isConnected) return destroy();
      var dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      render(dt);
      raf = requestAnimationFrame(frame);
    }
    function start() {
      if (running || rm || document.hidden || !onScreen) return;
      running = true; size(); last = performance.now();
      raf = requestAnimationFrame(frame);
    }
    function stop() { running = false; cancelAnimationFrame(raf); }
    function sync() {
      if (document.hidden || !onScreen) stop(); else start();
    }
    function onResize() { size(); if (!running) render(0); }
    function destroy() {
      stop();
      io.disconnect();
      document.removeEventListener('visibilitychange', sync);
      window.removeEventListener('resize', onResize);
    }

    var io = new IntersectionObserver(function (es) { onScreen = es[0].isIntersecting; sync(); });
    io.observe(cv);
    document.addEventListener('visibilitychange', sync);
    window.addEventListener('resize', onResize);
    onResize();
  }

  // Initialize every matching node under root (idempotent via data-rb-done-<type>).
  function init(root) {
    root = root || document;
    var sets = [
      ['spotlight', '[data-rb="spotlight"]', spotlight],
      ['countup', '[data-rb="countup"][data-to]', initCount],
      ['blur-text', '[data-rb="blur-text"]', blurText],
      ['particles', 'canvas[data-rb="particles"]', particles]
    ];
    sets.forEach(function (s) {
      var nodes = Array.prototype.slice.call(root.querySelectorAll(s[1]));
      if (root.matches && root.matches(s[1])) nodes.unshift(root);
      nodes.forEach(function (el) {
        var key = 'rbDone' + s[0].replace(/(^|-)(\w)/g, function (_, __, c) { return c.toUpperCase(); });
        if (el.dataset[key]) return;
        el.dataset[key] = '1';
        s[2](el);
      });
    });
  }

  window.RB = { init: init, countUp: countUp };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(document); });
  } else {
    init(document);
  }
})();
