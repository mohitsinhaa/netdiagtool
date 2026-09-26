(() => {
  const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 52; // r=52

  const el = (sel) => document.querySelector(sel);
  const terminal = el('#terminal');
  const logCount = el('#logCount');
  let eventCount = 0;

  // ---------------------------------------------------------------- clock
  function tickClock() {
    const now = new Date();
    el('#clock').textContent = now.toLocaleTimeString('en-GB', { hour12: false });
  }
  setInterval(tickClock, 1000);
  tickClock();

  // ------------------------------------------------------------- terminal
  function logLine(text, cls = '') {
    const line = document.createElement('div');
    line.className = `term-line ${cls}`;
    line.textContent = text;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
  }

  function logBlock(lines) {
    const block = document.createElement('div');
    block.className = 'term-block';
    lines.forEach((l) => {
      const line = document.createElement('div');
      line.textContent = l;
      block.appendChild(line);
    });
    terminal.appendChild(block);
    terminal.scrollTop = terminal.scrollHeight;
  }

  function bumpEventCount() {
    eventCount += 1;
    logCount.textContent = `${eventCount} event${eventCount === 1 ? '' : 's'}`;
  }

  function timestamp() {
    return new Date().toLocaleTimeString('en-GB', { hour12: false });
  }

  // --------------------------------------------------------------- gauges
  function setGauge(gaugeId, pct, dangerAt = 85, warnAt = 60) {
    const gauge = el(`#${gaugeId}`);
    const fill = gauge.querySelector('[data-fill]');
    const value = gauge.querySelector('[data-value]');
    const clamped = Math.max(0, Math.min(100, pct));
    const offset = GAUGE_CIRCUMFERENCE * (1 - clamped / 100);
    fill.style.strokeDashoffset = offset;
    let color = 'var(--cyan)';
    if (clamped >= dangerAt) color = 'var(--red)';
    else if (clamped >= warnAt) color = 'var(--amber)';
    fill.style.stroke = color;
    value.textContent = `${clamped.toFixed(0)}%`;
  }

  // ------------------------------------------------------------ sparkline
  const sparkHistory = { up: [], down: [] };
  const SPARK_LEN = 40;

  function pushSpark(key, value) {
    const arr = sparkHistory[key];
    arr.push(value);
    if (arr.length > SPARK_LEN) arr.shift();
    const max = Math.max(1, ...arr);
    const w = 200, h = 36;
    const step = w / (SPARK_LEN - 1);
    const points = arr
      .map((v, i) => {
        const x = i * step;
        const y = h - (v / max) * (h - 4) - 2;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
    document.querySelector(`#spark${key === 'up' ? 'Up' : 'Down'} polyline`)
      .setAttribute('points', points);
  }

  // ------------------------------------------------------ overall status
  function setOverallStatus(state) {
    const pill = el('#overallStatus');
    const dot = pill.querySelector('.dot');
    dot.className = 'dot ' + (state === 'ok' ? 'dot-ok' : state === 'warn' ? 'dot-warn' : 'dot-bad');
    pill.lastChild.textContent =
      state === 'ok' ? ' SYSTEM NOMINAL' : state === 'warn' ? ' ELEVATED LOAD' : ' ATTENTION NEEDED';
  }

  // --------------------------------------------------------- system poll
  async function pollSystem() {
    try {
      const res = await fetch('/api/system');
      const s = await res.json();

      setGauge('gaugeCpu', s.cpu_percent);
      setGauge('gaugeMem', s.mem_percent);
      const primaryDisk = s.disks && s.disks[0];
      setGauge('gaugeDisk', primaryDisk ? primaryDisk.percent : 0);

      el('#netUp').textContent = `${s.net_sent_rate_kbps.toFixed(1)} KB/s`;
      el('#netDown').textContent = `${s.net_recv_rate_kbps.toFixed(1)} KB/s`;
      pushSpark('up', s.net_sent_rate_kbps);
      pushSpark('down', s.net_recv_rate_kbps);

      const hrs = Math.floor(s.uptime_seconds / 3600);
      const mins = Math.floor((s.uptime_seconds % 3600) / 60);
      el('#uptime').textContent = `${hrs}h ${mins}m`;

      const procBody = el('#procBody');
      procBody.innerHTML = '';
      (s.top_processes || []).forEach((p) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${p.pid}</td><td>${p.name}</td><td>${p.cpu_percent.toFixed(1)}</td><td>${p.memory_percent.toFixed(1)}</td>`;
        procBody.appendChild(tr);
      });

      const worst = Math.max(s.cpu_percent, s.mem_percent, primaryDisk ? primaryDisk.percent : 0);
      setOverallStatus(worst >= 85 ? 'bad' : worst >= 60 ? 'warn' : 'ok');
    } catch (e) {
      setOverallStatus('bad');
    }
  }
  pollSystem();
  setInterval(pollSystem, 2000);

  // ------------------------------------------------------------- actions
  function setButtonRunning(action, running) {
    const btn = document.querySelector(`.ctrl-btn[data-action="${action}"]`);
    if (btn) btn.classList.toggle('is-running', running);
  }

  async function runPing(host) {
    setButtonRunning('ping', true);
    logLine(`$ ping ${host}`, 'term-cmd');
    try {
      const res = await fetch('/api/ping', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host, count: 4 }),
      });
      const r = await res.json();
      const lines = [];
      lines.push(`resolved: ${r.resolved_ip || '—'}  method: ${r.method}`);
      lines.push(`sent ${r.sent} / received ${r.received}  loss ${r.loss_pct}%`);
      if (r.min_ms != null) lines.push(`min/avg/max: ${r.min_ms.toFixed(1)} / ${r.avg_ms.toFixed(1)} / ${r.max_ms.toFixed(1)} ms`);
      if (r.error) lines.push(`note: ${r.error}`);
      logBlock(lines);
      logLine(`[${timestamp()}] ping ${host} — ${r.success ? 'REACHABLE' : 'UNREACHABLE'}`, r.success ? 'term-ok' : 'term-err');
    } catch (e) {
      logLine(`[${timestamp()}] ping ${host} — request failed: ${e}`, 'term-err');
    } finally {
      setButtonRunning('ping', false);
      bumpEventCount();
    }
  }

  async function runDns(host) {
    setButtonRunning('dns', true);
    logLine(`$ dns ${host}`, 'term-cmd');
    try {
      const res = await fetch('/api/dns', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host }),
      });
      const r = await res.json();
      const lines = [];
      lines.push(`resolve time: ${r.resolve_time_ms != null ? r.resolve_time_ms + ' ms' : '—'}`);
      lines.push(`ipv4: ${(r.ipv4_addresses || []).join(', ') || '—'}`);
      if ((r.ipv6_addresses || []).length) lines.push(`ipv6: ${r.ipv6_addresses.join(', ')}`);
      if (r.reverse_dns) lines.push(`reverse: ${r.reverse_dns}`);
      if (r.error) lines.push(`error: ${r.error}`);
      logBlock(lines);
      logLine(`[${timestamp()}] dns ${host} — ${r.success ? 'RESOLVED' : 'FAILED'}`, r.success ? 'term-ok' : 'term-err');
    } catch (e) {
      logLine(`[${timestamp()}] dns ${host} — request failed: ${e}`, 'term-err');
    } finally {
      setButtonRunning('dns', false);
      bumpEventCount();
    }
  }

  async function runHttp(url) {
    setButtonRunning('http', true);
    logLine(`$ http ${url}`, 'term-cmd');
    try {
      const res = await fetch('/api/http', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const r = await res.json();
      const lines = [];
      if (r.status_code) lines.push(`status: ${r.status_code} ${r.reason}`);
      lines.push(`response time: ${r.response_time_ms != null ? r.response_time_ms + ' ms' : '—'}`);
      if (r.content_type) lines.push(`content-type: ${r.content_type}`);
      if (r.server_header) lines.push(`server: ${r.server_header}`);
      if (r.tls_valid != null) lines.push(`tls: ${r.tls_valid ? 'valid' : 'invalid'}${r.tls_expires ? ` (expires ${r.tls_expires}, ${r.tls_days_remaining}d)` : ''}`);
      if (r.error) lines.push(`error: ${r.error}`);
      logBlock(lines);
      logLine(`[${timestamp()}] http ${url} — ${r.success ? 'UP' : 'DOWN'}`, r.success ? 'term-ok' : 'term-err');
    } catch (e) {
      logLine(`[${timestamp()}] http ${url} — request failed: ${e}`, 'term-err');
    } finally {
      setButtonRunning('http', false);
      bumpEventCount();
    }
  }

  function renderPortGrid(result) {
    const grid = el('#portGrid');
    grid.innerHTML = '';
    const all = [...result.open_ports.map((p) => ({ ...p, open: true })),
                 ...result.closed_ports.map((p) => ({ ...p, open: false }))]
      .sort((a, b) => a.port - b.port);
    if (!all.length) {
      grid.innerHTML = '<div class="port-empty">No ports scanned</div>';
      return;
    }
    all.forEach((p) => {
      const cell = document.createElement('div');
      cell.className = `port-cell ${p.open ? 'open' : 'closed'}`;
      cell.innerHTML = `<span class="p-num">${p.port}</span><span class="p-svc">${p.service || ''}</span>`;
      grid.appendChild(cell);
    });
  }

  async function runPort(host) {
    setButtonRunning('port', true);
    const portSpec = el('#portSpec').value || 'common';
    logLine(`$ portscan ${host} --ports ${portSpec}`, 'term-cmd');
    try {
      const res = await fetch('/api/portscan', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host, ports: portSpec }),
      });
      const r = await res.json();
      if (r.error) {
        logLine(`[${timestamp()}] portscan ${host} — error: ${r.error}`, 'term-err');
      } else {
        logBlock([`${r.open_ports.length}/${r.scanned} ports open in ${r.duration_ms.toFixed(0)} ms`]);
        logLine(`[${timestamp()}] portscan ${host} — complete`, 'term-ok');
        renderPortGrid(r);
      }
    } catch (e) {
      logLine(`[${timestamp()}] portscan ${host} — request failed: ${e}`, 'term-err');
    } finally {
      setButtonRunning('port', false);
      bumpEventCount();
    }
  }

  async function runAll(target) {
    await runPing(target);
    await runDns(target);
    await runHttp(target);
    await runPort(target);
  }

  document.querySelectorAll('.ctrl-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = el('#targetInput').value.trim();
      if (!target) {
        logLine('enter a host or URL first', 'term-warn');
        return;
      }
      const action = btn.dataset.action;
      if (action === 'ping') runPing(target);
      else if (action === 'dns') runDns(target);
      else if (action === 'http') runHttp(target);
      else if (action === 'port') runPort(target);
      else if (action === 'all') runAll(target);
    });
  });

  el('#targetInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') runAll(el('#targetInput').value.trim());
  });
})();
