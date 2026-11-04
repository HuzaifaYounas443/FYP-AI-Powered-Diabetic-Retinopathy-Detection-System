// ─── SCAN PAGE JAVASCRIPT ─────────────────────────────────────────────────

const SEVERITY_COLORS = ['#22c55e','#84cc16','#f59e0b','#f97316','#ef4444'];
const PROB_COLORS = ['rgba(34,197,94,0.7)','rgba(132,204,22,0.7)','rgba(245,158,11,0.7)','rgba(249,115,22,0.7)','rgba(239,68,68,0.7)'];

// ─── DROP ZONE SETUP ───────────────────────────────────────────────────────
const dropZone = document.getElementById('dropZone');
const imageInput = document.getElementById('imageInput');
const dzContent = document.getElementById('dzContent');
const dzPreview = document.getElementById('dzPreview');
const previewImg = document.getElementById('previewImg');
const previewName = document.getElementById('previewName');
const dzRemove = document.getElementById('dzRemove');

dropZone.addEventListener('click', (e) => {
  if (!dzPreview.classList.contains('hidden') && e.target !== dzRemove && !dzRemove.contains(e.target)) return;
  if (dzPreview.classList.contains('hidden')) imageInput.click();
});

dzContent.addEventListener('click', (e) => { e.stopPropagation(); imageInput.click(); });

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

imageInput.addEventListener('change', () => {
  if (imageInput.files[0]) handleFile(imageInput.files[0]);
});

dzRemove.addEventListener('click', (e) => {
  e.stopPropagation();
  imageInput.value = '';
  dzContent.classList.remove('hidden');
  dzPreview.classList.add('hidden');
});

function handleFile(file) {
  const allowed = ['image/png','image/jpeg','image/jpg','image/tiff','image/bmp'];
  if (!allowed.includes(file.type)) {
    alert('Please upload a valid image file (PNG, JPG, JPEG, TIFF, BMP)');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewName.textContent = file.name;
    dzContent.classList.add('hidden');
    dzPreview.classList.remove('hidden');
  };
  reader.readAsDataURL(file);

  // Update file input
  const dt = new DataTransfer();
  dt.items.add(file);
  imageInput.files = dt.files;
}

// ─── FORM SUBMIT / ANALYZE ─────────────────────────────────────────────────
const scanForm = document.getElementById('scanForm');
const uploadPanel = document.getElementById('uploadPanel');
const resultsPanel = document.getElementById('resultsPanel');
const loadingPanel = document.getElementById('loadingPanel');

scanForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  if (!imageInput.files[0]) {
    alert('Please select a retinal image to analyze.');
    return;
  }

  // Show loading
  uploadPanel.classList.add('hidden');
  loadingPanel.classList.remove('hidden');
  resultsPanel.classList.add('hidden');

  // Animate loading steps
  const steps = ['ls1','ls2','ls3','ls4'];
  const delays = [0, 800, 1600, 2400];
  steps.forEach((id, i) => {
    setTimeout(() => {
      document.querySelectorAll('.ls-step').forEach(s => s.classList.remove('active'));
      const el = document.getElementById(id);
      if (el) {
        el.classList.add('active');
        el.querySelector('i').className = 'fa-solid fa-spinner fa-spin';
        // Mark previous as done
        if (i > 0) {
          const prev = document.getElementById(steps[i-1]);
          if (prev) {
            prev.classList.remove('active');
            prev.classList.add('done');
            prev.querySelector('i').className = 'fa-solid fa-check';
          }
        }
      }
    }, delays[i]);
  });

  const fd = new FormData(scanForm);

  try {
    const res = await fetch('/api/analyze', { method: 'POST', body: fd });
    const data = await res.json();

    if (data.error) {
      alert('Error: ' + data.error);
      loadingPanel.classList.add('hidden');
      uploadPanel.classList.remove('hidden');
      return;
    }

    // Small delay then show results
    setTimeout(() => {
      loadingPanel.classList.add('hidden');
      showResults(data);
    }, 500);

  } catch (err) {
    alert('Network error. Please try again.');
    loadingPanel.classList.add('hidden');
    uploadPanel.classList.remove('hidden');
  }
});

function showResults(data) {
  resultsPanel.classList.remove('hidden');

  const color = SEVERITY_COLORS[data.severity_level] || '#38bdf8';

  // Main result
  document.getElementById('rcLevel').textContent = data.severity_level;
  document.getElementById('rcLabel').textContent = 'Stage';
  document.getElementById('rmConf').textContent = data.confidence.toFixed(1) + '%';
  document.getElementById('rmStatus').textContent = data.severity_label;
  document.getElementById('rmStatus').style.color = color;

  const circle = document.getElementById('resultCircle');
  circle.style.borderColor = color;
  document.getElementById('rcLevel').style.color = color;

  // Probability bars
  const probBars = document.getElementById('probBars');
  probBars.innerHTML = '';
  const probs = data.ensemble_probabilities || {};
  Object.entries(probs).forEach(([label, pct], i) => {
    const item = document.createElement('div');
    item.className = 'prob-bar-item';
    item.innerHTML = `
      <div class="pb-label">
        <span>${label}</span>
        <span style="font-family:var(--mono);font-size:12px">${pct.toFixed(1)}%</span>
      </div>
      <div class="pb-bar">
        <div class="pb-fill" style="width:0%;background:${PROB_COLORS[i]}"></div>
      </div>`;
    probBars.appendChild(item);
    setTimeout(() => {
      item.querySelector('.pb-fill').style.width = pct + '%';
    }, 50 + i * 80);
  });

  // Model cards
  const modelCards = document.getElementById('modelCards');
  modelCards.innerHTML = '';
  const preds = data.model_predictions || {};
  Object.entries(preds).forEach(([name, pred]) => {
    const card = document.createElement('div');
    card.className = 'model-card-item';
    card.innerHTML = `
      <div class="mc-name">${name.replace(/_/g,'-')}</div>
      <div class="mc-label" style="color:${SEVERITY_COLORS[pred.level]}">${pred.label}</div>
      <div class="mc-conf">${(pred.confidence * 100).toFixed(1)}% conf.</div>`;
    modelCards.appendChild(card);
  });

  // Grad-CAM visualization
  const gradcamSection = document.getElementById('gradcamSection');
  const gradcamImg = document.getElementById('gradcamImg');
  const gradcamCaption = document.getElementById('gradcamCaption');
  if (gradcamSection && gradcamImg && gradcamCaption) {
    if (data.gradcam_url) {
      gradcamImg.src = data.gradcam_url;
      gradcamCaption.textContent = `Grad-CAM visualization for ${data.severity_label}. Bright regions indicate where the model focused most.`;
      gradcamSection.classList.remove('hidden');
    } else {
      gradcamSection.classList.add('hidden');
    }
  }

  // Recommendations
  document.getElementById('recBox').textContent = data.recommendations;

  // Action buttons
  const viewReportBtn = document.getElementById('viewReportBtn');
  // Link to PDF download report
  viewReportBtn.href = `/report/download/${data.scan_id}`;

  const sendEmailBtn = document.getElementById('sendEmailBtn');
  const emailInput = scanForm.querySelector('input[name="patient_email"]');
  if (emailInput && emailInput.value.trim()) {
    sendEmailBtn.classList.remove('hidden');
    sendEmailBtn.onclick = () => quickSendEmail(data.scan_id, sendEmailBtn);
  }

  if (data.demo_mode) {
    const note = document.createElement('div');
    note.style = 'padding:8px 24px; font-size:12px; color:#f59e0b; background:rgba(245,158,11,0.08); border-top:1px solid rgba(245,158,11,0.15);';
    note.textContent = '⚠ Demo mode: Model files not found. Showing simulated results.';
    resultsPanel.appendChild(note);
  }

  // Scroll to results
  resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function quickSendEmail(scanId, btn) {
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending…';
  const emailStatus = document.getElementById('emailStatus');
  try {
    const res = await fetch(`/api/send-report/${scanId}`, { method: 'POST' });
    const data = await res.json();
    emailStatus.classList.remove('hidden');
    if (data.success) {
      emailStatus.style.color = '#22c55e';
      emailStatus.textContent = '✓ Report emailed to patient successfully';
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Sent';
    } else {
      emailStatus.style.color = '#ef4444';
      emailStatus.textContent = '✗ ' + (data.error || 'Failed to send email');
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send to Patient';
    }
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send to Patient';
  }
}

function resetScan() {
  resultsPanel.classList.add('hidden');
  loadingPanel.classList.add('hidden');
  uploadPanel.classList.remove('hidden');

  // Reset form
  scanForm.reset();
  imageInput.value = '';
  dzContent.classList.remove('hidden');
  dzPreview.classList.add('hidden');

  // Reset loading steps
  document.querySelectorAll('.ls-step').forEach((s, i) => {
    s.classList.remove('active', 'done');
    const icons = ['fa-spinner fa-spin','fa-circle','fa-circle','fa-circle'];
    s.querySelector('i').className = 'fa-solid ' + icons[i];
  });

  uploadPanel.scrollIntoView({ behavior: 'smooth' });
}
