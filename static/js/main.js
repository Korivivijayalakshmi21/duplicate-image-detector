/* DupliDetect - Main JavaScript */

// Sidebar toggle
function toggleSidebar() {
  const s = document.getElementById('sidebar');
  const o = document.getElementById('sidebarOverlay');
  if (s) { s.classList.toggle('open'); if (o) o.classList.toggle('show'); }
}

document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss alerts
  document.querySelectorAll('.dd-alert').forEach(a => {
    setTimeout(() => { try { bootstrap.Alert.getOrCreateInstance(a).close(); } catch(e){} }, 6000);
  });

  // Confirm delete
  document.querySelectorAll('.dd-delete-form').forEach(f => {
    f.addEventListener('submit', e => {
      if (!confirm('Delete this image? This cannot be undone.')) e.preventDefault();
    });
  });

  // Auto-submit filter selects
  document.querySelectorAll('.dd-auto-submit').forEach(el => {
    el.addEventListener('change', function () { this.closest('form').submit(); });
  });

  // Search debounce
  const si = document.getElementById('searchInput');
  if (si) {
    let t;
    si.addEventListener('input', function () {
      clearTimeout(t);
      t = setTimeout(() => this.closest('form').submit(), 500);
    });
  }

  // Upload dropzone
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('imageUploadInput');
  const fileList  = document.getElementById('fileList');
  const info      = document.getElementById('uploadInfo');

  if (dropzone && fileInput) {
    dropzone.addEventListener('click', function (e) {
      if (!e.target.closest('button')) fileInput.click();
    });
    dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', e => { if (!dropzone.contains(e.relatedTarget)) dropzone.classList.remove('drag-over'); });
    dropzone.addEventListener('drop', e => {
      e.preventDefault(); dropzone.classList.remove('drag-over');
      if (e.dataTransfer.files.length) {
        const dt = new DataTransfer();
        Array.from(e.dataTransfer.files).forEach(f => dt.items.add(f));
        fileInput.files = dt.files;
        renderFiles(fileInput.files);
      }
    });
    fileInput.addEventListener('change', () => renderFiles(fileInput.files));

    function renderFiles(files) {
      if (!fileList) return;
      const allowed = ['image/jpeg','image/png','image/webp'];
      let html = '', total = 0;
      Array.from(files).forEach(f => {
        total += f.size;
        const ok = allowed.includes(f.type);
        html += `<div class="dd-file-item">
          <i class="fas fa-image ${ok ? 'text-primary' : 'text-danger'}"></i>
          <span class="dd-file-name">${esc(f.name)}</span>
          <span class="dd-file-size">${fmtBytes(f.size)}</span>
          <span class="badge ${ok ? 'bg-success' : 'bg-danger'} ms-auto">${ok ? 'OK' : 'Invalid'}</span>
        </div>`;
      });
      fileList.innerHTML = html;
      if (info) { info.textContent = `${files.length} file(s) · ${fmtBytes(total)}`; info.classList.remove('d-none'); }
      const t2 = dropzone.querySelector('.dd-dropzone-title');
      if (t2) t2.textContent = `${files.length} file(s) selected`;
    }

    function fmtBytes(b) {
      if (b >= 1048576) return (b/1048576).toFixed(1)+' MB';
      if (b >= 1024)    return (b/1024).toFixed(1)+' KB';
      return b+' B';
    }
    function esc(s) { const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
  }
});
