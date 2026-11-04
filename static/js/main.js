// ─── TOPBAR SCROLL EFFECT ──────────────────────────────────────────────────
const topbar = document.getElementById('topbar');
if (topbar) {
  window.addEventListener('scroll', () => {
    topbar.style.boxShadow = window.scrollY > 10
      ? '0 4px 30px rgba(0,0,0,0.4)' : '';
  });
}

// ─── ANIMATE NUMBERS ───────────────────────────────────────────────────────
function animateNumber(el, target, duration = 1000) {
  const start = performance.now();
  const from = 0;
  const update = (time) => {
    const progress = Math.min((time - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(from + (target - from) * ease);
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

document.querySelectorAll('.sc-num').forEach(el => {
  const val = parseInt(el.textContent);
  if (!isNaN(val)) {
    el.textContent = '0';
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) {
        animateNumber(el, val);
        obs.disconnect();
      }
    });
    obs.observe(el);
  }
});

// ─── DELETE SCAN FUNCTION ──────────────────────────────────────────────────
async function deleteScan(scanId) {
  if (!confirm('Are you sure you want to delete this scan? This action cannot be undone.')) {
    return;
  }

  try {
    const response = await fetch(`/api/delete-scan/${scanId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    const data = await response.json();

    if (response.ok) {
      alert('Scan deleted successfully');
      location.reload();
    } else {
      alert('Error: ' + (data.error || 'Failed to delete scan'));
    }
  } catch (error) {
    alert('Network error: ' + error.message);
  }
}
