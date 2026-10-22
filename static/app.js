// Tampilan web sederhana untuk mencoba endpoint POST /ask

let role = 'Sales_Staff';

const ROLE_HINT = {
  Sales_Staff: 'Role <b>Sales_Staff</b> hanya boleh mengakses data unit, sales contract, dan billing. Akses GL_Journals ditolak.',
  Management: 'Role <b>Management</b> boleh mengakses semua data, termasuk GL_Journals (jurnal keuangan).',
};

const $ = (id) => document.getElementById(id);

// ---------- Pilih role ----------
function setRole(newRole) {
  role = newRole;
  document.querySelectorAll('.role-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.role === role);
  });
  $('role-hint').innerHTML = ROLE_HINT[role];
  $('role-badge').textContent = 'Role: ' + role;
  $('role-badge').className = 'badge ' + (role === 'Management' ? 'role-mgmt' : 'role-sales');
  $('result').classList.add('hidden'); // hasil lama disembunyikan, karena role-nya beda
}

document.querySelectorAll('.role-btn').forEach((btn) => {
  btn.addEventListener('click', () => setRole(btn.dataset.role));
});

// ---------- Tombol Soal 1-5 ----------
document.querySelectorAll('.preset-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.preset-btn').forEach((b) => b.classList.remove('selected'));
    btn.classList.add('selected');
    $('question').value = btn.dataset.q;
    $('question').focus();
    $('result').classList.add('hidden');
  });
});

// ---------- Kirim pertanyaan ----------
$('query-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const question = $('question').value.trim();
  if (!question) return;

  $('loading').classList.remove('hidden');
  $('result').classList.add('hidden');
  $('submit-btn').disabled = true;
  const start = performance.now();

  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'user_role': role },
      body: JSON.stringify({ question }),
    });
    const json = await res.json();
    const time = Math.round(performance.now() - start);

    if (res.ok) {
      showResult(json, time);
    } else {
      showError(json.status === 'ditolak' ? 'Permintaan ditolak' : 'Terjadi kesalahan', json.message || 'Error ' + res.status);
    }
  } catch (err) {
    showError('Gagal menghubungi server', err.message);
  } finally {
    $('loading').classList.add('hidden');
    $('submit-btn').disabled = false;
  }
});

function showResult(json, time) {
  $('alert').classList.add('hidden');
  ['answer-card', 'sql-card', 'table-card'].forEach((id) => $(id).classList.remove('hidden'));

  $('answer').textContent = json.answer;
  $('exec-time').textContent = time + ' ms';
  $('sql').textContent = json.sql;
  $('row-count').textContent = json.total_rows;
  renderTable(json.data);

  $('result').classList.remove('hidden');
}

function showError(title, message) {
  ['answer-card', 'sql-card', 'table-card'].forEach((id) => $(id).classList.add('hidden'));

  // pakai textContent supaya pesan tidak dibaca sebagai HTML
  $('alert').innerHTML = '';
  const strong = document.createElement('strong');
  strong.textContent = title;
  $('alert').append(strong, document.createTextNode(message));
  $('alert').classList.remove('hidden');

  $('result').classList.remove('hidden');
}

function renderTable(rows) {
  const head = $('table-head');
  const body = $('table-body');
  head.innerHTML = '';
  body.innerHTML = '';

  if (!rows || rows.length === 0) {
    body.innerHTML = '<tr><td class="empty">Tidak ada data.</td></tr>';
    return;
  }

  const columns = Object.keys(rows[0]);

  const trHead = document.createElement('tr');
  columns.forEach((col) => {
    const th = document.createElement('th');
    th.textContent = col;
    trHead.appendChild(th);
  });
  head.appendChild(trHead);

  rows.forEach((row) => {
    const tr = document.createElement('tr');
    columns.forEach((col) => {
      const td = document.createElement('td');
      const value = row[col];
      td.textContent = value === null || value === undefined ? '-' : value;
      if (typeof value === 'string' && value.startsWith('Rp ')) td.classList.add('money');
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

// ---------- Salin SQL ----------
$('copy-btn').addEventListener('click', () => {
  navigator.clipboard.writeText($('sql').textContent).then(() => {
    $('copy-btn').textContent = 'Tersalin!';
    setTimeout(() => ($('copy-btn').textContent = 'Salin SQL'), 1500);
  });
});

// ---------- Info database & model ----------
fetch('/info')
  .then((res) => res.json())
  .then((info) => {
    $('db-name').textContent = 'Database: ' + info.database;
    $('model-name').textContent = 'Model AI: ' + info.model;
  })
  .catch(() => {});

setRole('Sales_Staff');
