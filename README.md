# Craft Suite Web

13 個官方 Craft Web App，一個繁體中文入口。非官方專案，不隸屬 ArtCraft。

預定網址：https://appbuilderlee2.github.io/Craft-Suite-Web/

## 工作方式

- 小型靜態 HTML/CSS/JavaScript 首頁，搜尋及分類，桌面／手機響應式版面。
- Actions 下載 `storytold/<app>` 正式 Release 的 Web ZIP，核對 SHA256SUMS.txt
  及 GitHub asset digest（如有），安全解壓並檢查 HTML 依賴、WASM、原生檔及總容量。
- App 使用版本化子目錄 `apps/<app>/<tag>/`，避免相同檔名混用新舊快取。
  `apps/<app>/` 另有穩定重導頁；首頁直接連到鎖定版本，使用新分頁。
- 所有 13 個 App 成功後才上傳單一 Pages artifact；失敗不發布不完整網站。
- 官方程式本體不修改、不重新編譯，所有授權文件保留。入口圖示為自製 monogram。
- 不把大型 binary 提交到 Git；dist 與下載快取都不納入版本控制。

## 第一次部署

1. Repo Settings → Pages → Build and deployment → Source 選 **GitHub Actions**。
   Workflow 會嘗試啟用 Pages；若 token 無權限，須由擁有人執行這一步。
2. Actions → **Update and deploy Craft Suite Web** → Run workflow。
3. 所有下載、檢查及 deploy job 完成後開啟上述網址。

## 更新及回退

- 每日 17:47 UTC 自動檢查（阿德萊德夏令時間 04:17、標準時間 03:17）；
  GitHub 排程可能延遲，公開 Repo 長期無活動時可能停用排程，需在 Actions 重新啟用。
- 排程若版本 fingerprint 相同，不重新部署。push／手動執行則會重新部署。
- 手動立即更新：Actions → Run workflow，`use_lock` 保持 false。
- 鎖定某 App：編輯 `config/apps.json` 的 `pin`，填官方完整 tag，例如 `v0.10.1`。
  `null` 代表自動跟隨最新正式版。這裡的正式版指 GitHub 非 prerelease 的純數字 tag，
  不代表產品已離開 alpha 開發階段。
- 全套回退：下載舊成功 run 的 `release-lock` artifact，把 `release-lock.json` 放進 Repo，
  手動執行時勾選 `use_lock`。artifact 保留 30 日，重要版本請自行保留 lock。
- 部署後 `versions.json` 記錄官方版本、checksum、發行日期、實際容量。
- 若官方刪除舊 Release／資產，無法保證歷史 lock 可重建；cache 不是永久備份。

## 本地檢查

Python 3.12，無第三方套件：

```bash
python -m unittest discover -s tests -v
python scripts/build.py --preview
python -m http.server 8080 --directory dist
```

`--preview` 只顯示介面，沒有假 App 入口。完整下載：

```bash
python scripts/build.py
```

可在環境提供 GitHub Actions 的 GITHUB_TOKEN 避免 API rate limit；不要放入檔案或網站。

## 限制及安全

- Pages 1 GB 限制下，本專案 900 MiB 即停止部署。檔案必須在整體部署容量內；
  日後官方體積變大，須檢視容量而不是略過安全檢查。
- 這是本地瀏覽器工具入口，沒有加入雲端儲存、跨裝置同步、協作伺服器或 AI 後端。
- 不宣稱所有 App 在 iPhone／Safari 功能完整；需逐個瀏覽器實測，尤其影音格式、WebGPU、
  Worker、錄音及匯出。來源的 `_headers` 不會令 GitHub Pages 自動加自訂 HTTP headers。
- 同 origin 的 LocalStorage／IndexedDB／OPFS／Cache Storage 共用，子路徑不隔離。
  亦包含同一 `appbuilderlee2.github.io` 的其他網站；重要文件請匯出備份。
- 不設全域 Service Worker，以免干預上游 App、其他 Pages 專案或批量刪除快取。
  第一版不承諾全套離線／PWA；個別上游 App 的 SW 行為由該 App 決定。
- 不強制重載已開啟文件；部署移除舊版本後，舊分頁的延遲載入資產可能失效，更新前匯出。
- 發行 checksums 驗證完整性，不等同安全審計；上游官方帳戶被入侵等供應鏈風險仍存在。

詳見 [ATTRIBUTION.md](ATTRIBUTION.md)。
