'use strict';
// Guided steps (option B): selection -> data/agenda -> confirm and generate.
(() => {
  const flow = document.body.dataset.flow;
  const panels = [1, 2, 3].map(n => document.querySelector(`#step-panel-${n}`));
  const items = [...document.querySelectorAll('#steps > li')];
  const back = document.querySelector('#step-back');
  // Step 1 alone; step 2 keeps step 3 visible so review and generation share one screen.
  const show = n => {
    panels.forEach((panel, i) => { panel.hidden = !(i === n - 1 || (n === 2 && i === 2)); });
    items.forEach((item, i) => item.setAttribute('aria-current', i === n - 1 ? 'step' : 'false'));
    if (back) back.hidden = n === 1;
  };
  if (flow === 'fast-track-infra-2026') {
    document.querySelector('#steps').hidden = true;
    show(3);
  } else {
    show(1);
    const record = document.querySelector('#record');
    record.addEventListener('change', () => { if (!record.value) show(1); });
    back.addEventListener('click', event => { event.preventDefault(); show(1); });
  }
  window.CCAASteps = {show};
})();
