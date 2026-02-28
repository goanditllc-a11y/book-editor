/* ============================================================
   app.js — Book Editor & Rater frontend helpers
   ============================================================ */

// ---------------------------------------------------------------------------
// Drag-and-drop upload zone
// ---------------------------------------------------------------------------
(function initDropZone() {
  const zone = document.getElementById('dropZone');
  const input = document.getElementById('fileInput');
  const content = document.getElementById('dropZoneContent');
  const fileInfo = document.getElementById('dropZoneFile');
  const fileName = document.getElementById('dropZoneFileName');
  const fileSize = document.getElementById('dropZoneFileSize');
  const form = document.getElementById('uploadForm');
  const uploadBtn = document.getElementById('uploadBtn');
  const progress = document.getElementById('uploadProgress');

  if (!zone || !input) return;

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function showFile(file) {
    content.classList.add('d-none');
    fileInfo.classList.remove('d-none');
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);
    zone.classList.add('has-file');
  }

  zone.addEventListener('click', function (e) {
    if (e.target !== uploadBtn && !uploadBtn.contains(e.target)) {
      input.click();
    }
  });

  input.addEventListener('change', function () {
    if (input.files && input.files[0]) {
      showFile(input.files[0]);
    }
  });

  zone.addEventListener('dragover', function (e) {
    e.preventDefault();
    zone.classList.add('drag-over');
  });

  zone.addEventListener('dragleave', function () {
    zone.classList.remove('drag-over');
  });

  zone.addEventListener('drop', function (e) {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      // Transfer file to the hidden input via DataTransfer
      try {
        const dt = new DataTransfer();
        dt.items.add(files[0]);
        input.files = dt.files;
      } catch (_) {
        // DataTransfer not supported in all browsers — fallback gracefully
      }
      showFile(files[0]);
    }
  });

  // Show progress bar on form submit
  if (form) {
    form.addEventListener('submit', function () {
      if (input.files && input.files[0]) {
        if (progress) progress.classList.remove('d-none');
        if (uploadBtn) {
          uploadBtn.disabled = true;
          uploadBtn.textContent = 'Uploading & Analysing…';
        }
      }
    });
  }
})();

// ---------------------------------------------------------------------------
// Star rendering helper (used inline in templates too)
// ---------------------------------------------------------------------------
function renderStars(rating) {
  const full = Math.floor(rating);
  const half = (rating - full) >= 0.4;
  const empty = 5 - full - (half ? 1 : 0);
  return '⭐'.repeat(full) + (half ? '✨' : '') + '☆'.repeat(empty);
}

// Render all star display elements
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.star-display[data-rating]').forEach(function (el) {
    el.textContent = renderStars(parseFloat(el.dataset.rating) || 0);
  });
});
