/* Passive diagnostics for all Craft Suite Web apps. Never reloads or touches user files. */
(() => {
  'use strict';
  const app = location.pathname.match(/\/apps\/([a-z]+)\/v?[^/]+\//);
  if (!app) return;
  const key = 'craft-suite-diagnostics:' + app[1];
  let events = [];
  try { events = JSON.parse(sessionStorage.getItem(key) || '[]'); if (!Array.isArray(events)) events = []; } catch { events = []; }
  const record = (type, detail = '') => {
    events.push({time: new Date().toISOString(), type, detail: String(detail).slice(0, 300)});
    events = events.slice(-30);
    try { sessionStorage.setItem(key, JSON.stringify(events)); } catch {}
  };
  const nav = performance.getEntriesByType('navigation')[0];
  const reloaded = nav && nav.type === 'reload';
  record('load', nav?.type || 'unknown');
  window.addEventListener('error', e => record('error', e.message || 'resource error'));
  window.addEventListener('unhandledrejection', e => record('rejection', String(e.reason)));
  window.addEventListener('pagehide', e => record('pagehide', e.persisted ? 'bfcache' : 'navigation'));
  window.addEventListener('pageshow', e => { if (e.persisted) record('pageshow', 'bfcache restore'); });
  document.addEventListener('visibilitychange', () => record('visibility', document.visibilityState));
  document.addEventListener('webglcontextlost', () => record('webglcontextlost'), true);
  document.addEventListener('webglcontextrestored', () => record('webglcontextrestored'), true);
  // Never reload automatically, retry failed work, or replace the app's canvas.
  if (reloaded) {
    const show = () => {
      if (!document.body || document.getElementById('craft-suite-reload-note')) return;
      const note = document.createElement('div');
      note.id = 'craft-suite-reload-note';
      Object.assign(note.style, {position:'fixed',bottom:'14px',right:'14px',zIndex:'2147483647',maxWidth:'300px',padding:'11px 12px',borderRadius:'10px',background:'#20262c',color:'white',font:'13px/1.5 system-ui,sans-serif',boxShadow:'0 2px 12px #0004'});
      const message = document.createElement('span');
      message.textContent = '瀏覽器重新載入咗呢個 App。如果文件未儲存，請檢查內容並盡快匯出備份。';
      const close = document.createElement('button');
      close.type = 'button'; close.textContent = '關閉';
      Object.assign(close.style, {marginLeft:'10px',padding:'4px 8px',cursor:'pointer'});
      close.addEventListener('click', () => note.remove());
      note.append(message, close);
      document.body.append(note);
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', show, {once:true});
    else show();
  }
  // Developers can inspect sessionStorage key craft-suite-diagnostics:<app>, if needed.
})();
