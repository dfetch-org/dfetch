(function () {
  'use strict';

  function init() {
    if (!('IntersectionObserver' in window)) return;

    // Cards (sd-card), feature-grid columns, and band section headings
    var cardEls    = Array.from(document.querySelectorAll('.sd-card'));
    var featureEls = Array.from(document.querySelectorAll('.feature-grid .sd-col'));
    var headingEls = Array.from(document.querySelectorAll(
      '.band-tint > p:first-of-type, .band-mint > p:first-of-type'
    ));

    var all = cardEls.concat(featureEls, headingEls);
    if (!all.length) return;

    // Set initial hidden state via inline style to avoid flash-of-unstyled-content
    all.forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(24px)';
      el.style.transition = 'opacity 0.55s cubic-bezier(0.4,0,0.2,1), transform 0.55s cubic-bezier(0.4,0,0.2,1)';
    });

    function reveal(el, delay) {
      setTimeout(function () {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      }, delay || 0);
    }

    // Compute stagger index for an element within its containing row
    function staggerDelay(el) {
      // Cards live inside .sd-col inside .sd-row — find row siblings
      var row = el.closest('.sd-row');
      if (row) {
        var siblings = Array.from(row.querySelectorAll('.sd-card, .sd-col'));
        var idx = siblings.indexOf(el);
        return Math.max(0, idx) * 90;
      }
      return 0;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        io.unobserve(entry.target);
        reveal(entry.target, staggerDelay(entry.target));
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    all.forEach(function (el) { io.observe(el); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
