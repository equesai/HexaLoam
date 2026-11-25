/**
 * HexaLoam Gait Selector
 * Progressive enhancement for the locomotion gait viewer.
 * Switches between Tripod, Ripple, and Wave panels without auto-playing.
 */
(function () {
  'use strict';

  function initTabViewer(viewer) {
    var tabs = viewer.querySelectorAll('.gait-tab');
    var panels = viewer.querySelectorAll('.gait-panel');
    if (!tabs.length || !panels.length) return;

    // Mark viewer as JS enhanced so CSS hides inactive panels
    viewer.classList.add('js-ready');

    tabs.forEach(function (tab, index) {
      tab.tabIndex = tab.getAttribute('aria-selected') === 'true' ? 0 : -1;
      tab.addEventListener('keydown', function (event) {
        var nextIndex = {
          ArrowRight: (index + 1) % tabs.length,
          ArrowLeft: (index + tabs.length - 1) % tabs.length,
          Home: 0,
          End: tabs.length - 1
        }[event.key];
        if (nextIndex === undefined) return;
        event.preventDefault();
        tabs[nextIndex].focus();
        tabs[nextIndex].click();
      });
      tab.addEventListener('click', function () {
        var targetId = tab.getAttribute('data-target');
        if (!targetId) return;

        // Update tab states
        tabs.forEach(function (t) {
          var isMatch = t === tab;
          t.tabIndex = isMatch ? 0 : -1;
          t.classList.toggle('active', isMatch);
          t.setAttribute('aria-selected', isMatch ? 'true' : 'false');
        });

        // Update panel states and pause any playing video in inactive panels
        panels.forEach(function (panel) {
          var isMatch = panel.id === targetId;
          panel.classList.toggle('active', isMatch);
          if (!isMatch) {
            var video = panel.querySelector('video');
            if (video && !video.paused) {
              video.pause();
            }
          }
        });
      });
    });
  }

  function initAllViewers() {
    document.querySelectorAll('.gait-viewer').forEach(initTabViewer);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllViewers);
  } else {
    initAllViewers();
  }
})();
