/* processingModal.js - provides showProcessingModal, updateProgress, hideProcessingModal */
(function(window){
  let modal, fgCircle, percentEl, phaseEl, intervalId;
  const phases = ['Uploading','Segmenting','Classifying','Done'];

  function init(){
    modal = document.getElementById('processingModal');
    if(!modal) return;
    fgCircle = modal.querySelector('.progress-ring .fg');
    percentEl = modal.querySelector('.progress-percent');
    phaseEl = modal.querySelector('.phase');
  }

  function setCircle(percent){
    const radius = fgCircle.r.baseVal.value;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percent/100) * circumference;
    fgCircle.style.strokeDasharray = `${circumference - offset} ${circumference}`;
  }

  let currentPercent = 0;
  function showProcessingModal(){
    if(!modal) init();
    if(!modal) return;
    modal.style.display = 'flex';
    currentPercent = 0;
    updateUI(currentPercent);
    // auto-progress simulation
    clearInterval(intervalId);
    intervalId = setInterval(()=>{
      // speed changes by phase
      if(currentPercent < 25) currentPercent += Math.random()*3 + 1; // uploading
      else if(currentPercent < 60) currentPercent += Math.random()*2 + 0.6; // segmenting
      else if(currentPercent < 90) currentPercent += Math.random()*1.2 + 0.4; // classifying
      else currentPercent += Math.random()*0.6 + 0.2; // finishing
      if(currentPercent > 99.5) currentPercent = 99.5; // wait for backend to set 100
      updateUI(Math.round(currentPercent));
    }, 200);
  }

  function updateUI(pct){
    if(!modal) return;
    percentEl.textContent = pct + '%';
    setCircle(pct);
    // set phase
    let phaseName = phases[0];
    if(pct >= 0 && pct < 25) phaseName = phases[0];
    else if(pct < 60) phaseName = phases[1];
    else if(pct < 90) phaseName = phases[2];
    else phaseName = phases[3];
    phaseEl.textContent = phaseName;
    // update step classes
    const stepEls = modal.querySelectorAll('.phase-steps .step');
    stepEls.forEach((el, idx)=>{
      el.classList.toggle('active', idx === (phaseName==='Uploading'?0:(phaseName==='Segmenting'?1:(phaseName==='Classifying'?2:3))));
    });
  }

  function updateProgress(step){
    // step can be one of phases or percentage number
    if(!modal) init();
    if(!modal) return;
    if(typeof step === 'number'){
      const p = Math.max(0, Math.min(100, Math.round(step)));
      updateUI(p);
    } else if(typeof step === 'string'){
      const idx = phases.indexOf(step);
      const map = [10, 40, 75, 100];
      const p = idx>=0?map[idx]:0;
      updateUI(p);
    }
  }

  function hideProcessingModal(){
    if(!modal) init();
    if(!modal) return;
    clearInterval(intervalId);
    updateUI(100);
    setTimeout(()=>{
      modal.style.display = 'none';
      // reset circle
      setCircle(0);
    }, 350);
  }

  // expose
  window.showProcessingModal = showProcessingModal;
  window.updateProgress = updateProgress;
  window.hideProcessingModal = hideProcessingModal;

})(window);
