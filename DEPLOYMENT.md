# TripSync：Vercel＋Neon 熟人測試站

這份指南建立獨立的雲端測試環境：前端與後端各一個 Vercel 專案，資料存於 Neon PostgreSQL。沿用平台網址，先不買網域或升級付費方案。本機帳號、開發者登入與旅程不會自動複製到雲端。

本次已準備部署檔案，尚未建立雲端資源或驗證實際雲端部署。介面名稱與免費額度可能變更；以下依 2026-10-28 官方文件整理。

## 1. 準備帳號與程式版本

1. 登入 [GitHub 儲存庫](https://github.com/HYHS1029/TripSync)。
2. 登入或註冊 [Neon](https://console.neon.tech/) 與 [Vercel](https://vercel.com/signup)。帳號密碼、驗證碼及條款確認由你在平台網站完成。
3. 確認 GitHub 的部署來源包含本次 `codex/deploy-vercel-neon` 分支的變更。若要從 `main` 部署，先把這個分支合併進 `main`。不要從仍使用 Next.js 16.3.5 的舊版本建立網站。

Vercel Hobby 限個人、非商業用途。官方人員曾表示可用於探索產品想法及建立原型，但未來營利目標與目前的試用方式是否符合條件，應在採用方案前向 Vercel 確認。遇到付費方案或信用卡／計費要求時，先確認方案與費用。

## 2. 建立 Neon 測試資料庫

1. 在 Neon 建立專案，名稱可填 `tripsync-test`，選 **Free**。
2. 地區選 **AWS Asia Pacific 1 (Singapore)**，與目前兩個 Vercel 設定的 `sin1` 同區，適合這次從台灣連線的熟人測試。
3. 保留專案預設資料庫與角色即可，不需要啟用 Neon Auth；TripSync 已有自己的登入系統。
4. 目前新版介面從 **Branch overview → Postgres database → Computes → Connect** 開啟 **Connection details** 視窗；**Connection pooling** 開關就在 **Connection string** 下方。可取得兩種連線網址：
   - **Pooled / Connection pooling 開啟**：給 Vercel 後端的 `DATABASE_URL` 使用，主機名稱通常含 `-pooler`。
   - **Direct / Connection pooling 關閉**：給下一步 migration 使用，主機名稱不含 `-pooler`。

連線網址包含資料庫密碼，只貼進平台的私密環境變數或下面的隱藏輸入提示；不要貼到聊天、GitHub 或公開文件。保留網址原有的 `sslmode=require`、`channel_binding=require` 等安全參數。程式已能直接接受 Neon 的 `postgresql://` 格式並使用 psycopg 3。

## 3. 在雲端建立 TripSync 資料表

在本機專案的 `backend/` 開啟 Terminal，執行：

```powershell
conda activate tripsync
python scripts/migrate_neon.py
```

提示 `Paste Neon DIRECT connection URL (hidden):` 時貼上 **Direct URL** 並按 Enter。輸入不會顯示在畫面上，網址只保留在該程序記憶體中。

成功時會顯示 `Neon schema migration complete`。這會套用現有五個 migration，建立帳號、旅程、行程與帳務資料表；不會複製本機資料。輔助程式拒絕 localhost、沒有 TLS 的網址，以及 pooled URL，避免把這一步套用到錯誤的本機資料庫。

不要把 migration 放進 Vercel 的每次啟動或每次預覽建置。後續資料結構變更，先備份 Neon 測試資料，再手動執行這個指令。

## 4. 部署 Vercel 後端

在 Vercel 選 **Add New → Project → Import Git Repository**，匯入同一個 TripSync 儲存庫。

| 設定 | 值 |
| --- | --- |
| Project Name | 例如 `tripsync-api-test`，若名稱已被使用則換一個 |
| Root Directory | `backend` |
| Framework Preset | `FastAPI` |
| Python | 部署檔固定為 `3.12` |
| 地區 | 部署檔固定為新加坡 `sin1` |
| Build／Output Directory | 保留框架預設，不要填 `uvicorn` 啟動指令 |

在 **Environment Variables** 設定以下值，先僅供 **Production** 使用：

| 變數 | 內容 |
| --- | --- |
| `DATABASE_URL` | Neon **Pooled URL** |
| `JWT_SECRET_KEY` | 新產生的隨機值，與本機分開、至少 32 字元 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
| `EMAIL_VERIFICATION_ENABLED` | `false`；熟人測試版先不開放寄信驗證，無需設定 SMTP |
| `GOOGLE_MAPS_API_KEY` | 你現有的 Google Maps Demo Key，若先不測地圖可暫留空 |
| `CORS_ALLOW_ORIGINS` | `[]`；目前網頁透過前端伺服器呼叫 API，不需要瀏覽器直連 |

可在自己的 Terminal 產生新的 JWT 金鑰，複製到平台後清除剪貼簿；不需要把結果貼到聊天中：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

按 **Deploy**。成功後記下平台實際提供的 **Production Domain**。後面會把這個完整的 `https://…vercel.app` 網址填到前端。不要使用每次建置都會改變的 deployment URL。

若建置要求安裝所有 Python 套件，`backend/requirements.txt` 已是獨立清單，不需要讀取上層目錄。Vercel 會直接載入 `app/main.py` 的 FastAPI `app`，不需要自行啟動伺服器。

## 5. 保留後端部署保護並讓前端連線

如果後端啟用了 Vercel Authentication／Deployment Protection，直接開啟 API 可能會看到平台登入頁。保留這個保護，依 Vercel 的 **Protection Bypass for Automation** 設定產生專用 Secret，下一步只把它填入前端的伺服器環境變數 `API_PROTECTION_BYPASS`。

前端會在伺服器端加上 `x-vercel-protection-bypass` 標頭，不把這個 Secret 傳給瀏覽器。若後端 Production 本來就沒有這層保護，可暫不設定該變數；TripSync 的使用者 API 仍會驗證登入與旅程權限。

不要為了讓瀏覽器健康檢查通過而把 Secret 改成 `NEXT_PUBLIC_` 或放到網址中。首頁已改由同站 `/api/health` 檢查連線。

## 6. 部署 Vercel 前端

再次 **Add New → Project**，匯入同一個儲存庫，建立另一個專案：

| 設定 | 值 |
| --- | --- |
| Project Name | 例如 `tripsync-web-test` |
| Root Directory | `frontend` |
| Framework Preset | `Next.js` |
| Build Command | 部署檔已設定 `npm run build -- --webpack` |
| Node.js | 選 `24.x`，與目前本機驗證版本相符 |

前端 **Production Environment Variables**：

| 變數 | 內容 |
| --- | --- |
| `API_BASE_URL` | 第 4 步後端實際的 Production Domain，包含 `https://` |
| `API_PROTECTION_BYPASS` | 第 5 步的後端 Automation Secret；未啟用保護時可留空 |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | 現有 Maps Demo Key，若先不測地圖可留空 |
| `NEXT_PUBLIC_GOOGLE_MAP_ID` | `DEMO_MAP_ID` |
| `TRIPSYNC_DEV_LOGIN_ENABLED` | `false` |
| `EMAIL_VERIFICATION_ENABLED` | `false`；隱藏信箱欄位與寄信入口，日後與後端一起啟用 |

不用把 `DATABASE_URL`、`JWT_SECRET_KEY` 或本機開發者帳密填到前端。也不用設定 `NEXT_PUBLIC_API_BASE_URL`；所有 API 請求都由伺服器端處理。瀏覽器用的地圖金鑰會公開，這是 Maps JS 的使用方式；它與資料庫密碼及伺服器 JWT 金鑰不同。

按 **Deploy**。朋友之後使用的是這個前端的 Production Domain。Preview 先不連共用的雲端測試資料庫，之後需要預覽環境時另外建立 Neon 分支與對應設定。

## 7. 分享前的實測

先由你在前端建立一個全新的 TripSync 測試帳號；本機 `developer@example.com` 與先前示範帳號不會存在於雲端。

1. 開啟首頁，確認 `Backend status: ok`，重新整理仍正常。
2. 註冊、登入、登出，確認雲端不顯示「開發者快速登入」。
3. 建立旅程、行程與費用，重新整理並重新登入後資料仍存在。
4. 用另一個測試帳號接受旅伴邀請，確認能協作，並確認非成員無法讀取旅程。
5. 若已設定 Maps Demo Key，實測地點搜尋、地圖與交通時間。Demo Key 用量有每日上限，僅供測試與原型使用。
6. 在手機開啟同一個前端網址，確認表單、日期導覽與帳務可操作。

之後才分享給第一批熟人。信箱驗證已實作但預設停用，先以使用者名稱與密碼註冊／登入、連結邀請旅伴，不需要申請寄信服務或購買網域。保留程式與 migration，日後再依 [EMAIL_VERIFICATION.md](EMAIL_VERIFICATION.md) 開啟前後端開關及設定正式 SMTP。測試站仍沒有忘記密碼和完整的帳號／IP 限流；先告知測試者妥善保管帳密、控制測試對象並保留資料備份。這些是目前產品限制，不因部署而自動補齊。

## 8. 常見問題與更新

- **API／註冊顯示無法連線**：先核對 `API_BASE_URL` 是後端 Production Domain，沒有保留 `localhost`；再檢查後端部署保護與 `API_PROTECTION_BYPASS`。
- **後端資料庫錯誤**：核對 pooled URL、TLS、Neon 專案狀態，並確認第 3 步 migration 成功。
- **地圖空白**：確認前端 `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` 與後端 `GOOGLE_MAPS_API_KEY` 都已設定；修改瀏覽器變數後要重新部署前端。
- **更新程式**：推送到部署追蹤的分支後，Vercel 會重新建置。修改環境變數後也要 Redeploy。
- **要備份資料**：使用 Neon Direct URL 與 `pg_dump` 匯出測試資料，將備份保存到私密位置；不把備份提交至 Git。
- **免費額度用完**：先接受暫停或降低用量，再決定是否升級。不要因為操作提示而自動啟用付費方案。

## 官方參考

- [Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi)
- [Vercel Monorepo](https://vercel.com/docs/monorepos)
- [Vercel Python 版本](https://vercel.com/docs/functions/runtimes/python/python-version)
- [Vercel 部署保護自動化連線](https://vercel.com/docs/deployment-protection/methods-to-bypass-deployment-protection/protection-bypass-automation)
- [Neon 連線池與 Direct URL](https://neon.com/docs/connect/connection-pooling)
- [Neon 免費方案](https://neon.com/pricing)
- [Google Maps Demo Key](https://developers.google.com/maps/demo-key)
