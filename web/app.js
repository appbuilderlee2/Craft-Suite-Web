'use strict';
let catalogue = [], category = 'all';
const grid = document.querySelector('#apps');
const search = document.querySelector('#search');
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}
function render() {
  const term = search.value.trim().toLocaleLowerCase();
  const shown = catalogue.filter(app => (category === 'all' || app.category === category) && `${app.name} ${app.label} ${app.description}`.toLocaleLowerCase().includes(term));
  grid.replaceChildren(...shown.map(app => {
    const card = element('article', 'card');
    card.style.setProperty('--app-color', app.color);
    const main = element('div', 'card-main');
    const mark = element('div', 'mark', app.mark); mark.setAttribute('aria-hidden', 'true');
    const copy = element('div', 'card-copy');
    const version = app.version ? `版本 ${app.version} · ${app.publishedAt.slice(0, 10)}` : '尚未部署';
    copy.append(element('h2', '', app.name), element('p', 'description', app.description), element('p', 'version', version));
    main.append(mark, copy);
    const launch = element('a', 'launch', app.path ? '開啟 App' : '尚未部署');
    if (app.path && /^apps\/[a-z]+\/v?[0-9][a-zA-Z0-9._-]*\/$/.test(app.path)) {
      launch.href = `./${app.path}${app.id === 'wordcraft' && /^((?!chrome|chromium|crios|fxios).)*safari/i.test(navigator.userAgent) ? '?webgl' : ''}`; launch.target = '_blank'; launch.rel = 'noopener noreferrer';
      launch.setAttribute('aria-label', `開啟 ${app.name}（新分頁）`);
    } else { launch.setAttribute('aria-disabled', 'true'); }
    card.append(main, launch); return card;
  }));
  document.querySelector('#empty').hidden = shown.length !== 0;
  document.querySelector('#status').textContent = term || category !== 'all' ? `顯示 ${shown.length} 個工具` : '';
}
search.addEventListener('input', render);
document.querySelectorAll('[data-category]').forEach(button => button.addEventListener('click', () => {
  category = button.dataset.category;
  document.querySelectorAll('[data-category]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  render();
}));
fetch('./versions.json', {cache: 'no-store'}).then(response => {
  if (!response.ok) throw new Error('Catalogue unavailable');
  return response.json();
}).then(data => {
  catalogue = data.apps; render();
  document.querySelector('#build-info').textContent = data.builtAt ? `網站部署：${new Date(data.builtAt).toLocaleString('zh-Hant', {timeZone: 'Australia/Adelaide'})}（阿德萊德時間）` : '本地介面預覽 · 尚未下載官方 App';
}).catch(() => {
  document.querySelector('#status').textContent = '暫時無法讀取工具清單，請重新整理頁面或查看 GitHub 部署紀錄。';
});
