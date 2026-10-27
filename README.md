# TripSync

多人旅行協作平台，集中管理旅程、旅伴、地圖行程與記帳分帳。目前完成帳號、旅程 CRUD、旅伴邀請／管理、每日活動，以及地圖串接與記帳分帳第一版；地圖需要另設定 Google 服務。

本文件依據 2026-10-28 的程式碼與本機環境整理。

## 專案文件

- [功能、架構、API 與後續開發順序](docs/PROJECT_OVERVIEW.md)
- [每個檔案的用途與修改位置](docs/FILE_GUIDE.md)
- [註冊／登入設計、API 與測試方法](docs/AUTHENTICATION.md)
- [旅程管理架構、程式碼與測試](docs/TRIP_MANAGEMENT.md)
- [旅伴協作、每日行程與資安設計](docs/COLLABORATION_AND_ITINERARY.md)
- [核心功能開發順序與驗收條件](docs/ROADMAP.md)
- [地圖排行程、交通時間與記帳分帳需求](docs/MAP_AND_EXPENSES.md)
- [地圖與帳務第一版：設定、使用、API 與驗證](docs/MAPS_AND_LEDGER.md)
- [先前的需求與開發對話](https://chatgpt.com/share/6ad89323-5460-83ee-9757-d83a84f39fad)

## 目前完成的功能

| 範圍 | 目前狀態 |
| --- | --- |
| 前端 | 註冊、登入、帳號頁、旅程列表、日期導覽、行程／地圖、旅伴管理、記帳與結算 |
| API | `GET /health`、`GET /health/db`、`POST /users`、`POST /auth/login`、`GET /users/me` |
| 帳號註冊 | 首頁／登入頁入口、註冊表單、確認密碼、輸入驗證、Argon2id 密碼雜湊、重複帳號提示 |
| 登入 | 密碼驗證、30 分鐘 JWT、HttpOnly Cookie、過期／無效 token 拒絕 |
| 旅程 | 五支 /trips CRUD API、建立者自動加入、成員讀取與擁有者管理權限 |
| 旅伴 | 七天單次邀請、撤銷、加入、成員列表、退出與移除 |
| 每日行程 | 活動 CRUD、分類、住宿期間、上下排序、目的地時區、Google 地點搜尋／地圖／交通串接（需設定金鑰） |
| 記帳與分帳 | 單一旅程幣別、付款人／負擔人、均分／自訂、活動關聯、結算建議、部分還款及撤銷、歷史成員 |
| 資料庫 | PostgreSQL、原有五個資料表加上 Expense／ExpenseShare／Settlement、四個 Alembic migration |
| 開發環境 | 前後端各自啟動，Docker Compose 執行 PostgreSQL |

地圖、地點搜尋、交通查詢及記帳分帳已可操作。本機 Maps Demo Key 已在全站 `no-referrer` 下通過真實地圖、景點搜尋、標記及交通路線驗證，未開啟計費或修改 Cloud 金鑰限制，詳見[第一版設定與狀態](docs/MAPS_AND_LEDGER.md)。Demo Key 供開發／原型測試；投票、正式金鑰與正式部署尚未完成。可從首頁點「註冊」建立帳號，登入後進入 `/trips`。開啟旅程可安排每日活動，從「旅伴與邀請」邀請朋友，從「記帳與分帳」管理開銷。目前尚無收信驗證。

## 本機啟動

目前使用 Windows PowerShell、Conda 環境 `tripsync`（本機確認為 Python 3.10.21）與 Node.js（本機確認為 24.21.0）。

首次準備 Python 套件時，在專案根目錄執行：

```powershell
cd D:\TripSync
conda activate tripsync
python -m pip install -r requirements.txt
```

Python 套件以根目錄 `requirements.txt` 為唯一來源；`backend/requirements.txt` 引用相同清單。登入新增的 PyJWT 也包含在其中。

設定 `backend/.env`，格式參考 `backend/.env.example`：`DATABASE_URL` 須符合 PostgreSQL 連線設定，`JWT_SECRET_KEY` 必須使用自己的隨機金鑰（至少 32 字元），`ACCESS_TOKEN_EXPIRE_MINUTES` 預設為 30。可用以下指令產生金鑰，再寫入本機 `.env`：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

本次已替現有本機環境產生金鑰並存入忽略的 `.env`；不會寫入版本控制。變更金鑰或期限後需重啟後端。

設定 `frontend/.env.local`，也可參考 `frontend/.env.example`：

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
API_BASE_URL=http://localhost:8000
```

先開啟 Docker Desktop，再於根目錄啟動資料庫：

```powershell
cd D:\TripSync
docker compose up -d
docker compose ps
```

在後端 Terminal 執行：

```powershell
cd D:\TripSync\backend
conda activate tripsync
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

`alembic upgrade head` 會套用尚未執行的 migration；首次建立資料庫或新增 migration 後需要執行。

在另一個 Terminal 執行：

```powershell
cd D:\TripSync\frontend
npm ci
npm run dev -- --webpack
```

`npm ci` 用於首次安裝或鎖定檔變更後，日常開發可直接執行 `npm run dev`。

### 地圖開發設定

開發與原型測試可使用 [Google Maps Demo Key](https://developers.google.com/maps/demo-key)，不需信用卡或計費帳戶；有每日 API 用量限制，達上限會暫停至配額重設。正式上線須另設定標準金鑰、來源限制與計費。

在原有 `backend/.env` 下方新增：

```dotenv
GOOGLE_MAPS_API_KEY=YOUR_DEMO_KEY
```

在原有 `frontend/.env.local` 下方新增：

```dotenv
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=YOUR_DEMO_KEY
NEXT_PUBLIC_GOOGLE_MAP_ID=DEMO_MAP_ID
```

Demo Key 測試階段可在兩個位置使用同一組金鑰，正式環境應分開設定前後端金鑰。`NEXT_PUBLIC_` 金鑰會出現在瀏覽器程式中；`.env`、`.env.local` 和建置結果均不納入 Git，請勿把實際金鑰寫入原始碼。

修改金鑰後重啟後端；前端 dev 需重啟，production 需重新 build／start。本機已驗證 Demo Key 能在原有全站 `no-referrer` 下顯示地圖、景點標記與交通路線。這不代表其他標準金鑰的來源限制也已驗證。

操作方式：在活動表單搜尋並選取實際地點，儲存後會在當日地圖顯示標記；住宿可填退房日，交通區可選方式與出發時間。從活動點「記一筆費用」可關聯行程，並在「記帳與分帳」查看分攤與還款。

| 用途 | 網址 |
| --- | --- |
| 前端 | [http://localhost:3000](http://localhost:3000) |
| 註冊頁 | [http://localhost:3000/register](http://localhost:3000/register) |
| 登入頁 | [http://localhost:3000/login](http://localhost:3000/login) |
| 我的帳號 | [http://localhost:3000/account](http://localhost:3000/account) |
| 我的旅程 | [http://localhost:3000/trips](http://localhost:3000/trips) |
| API 健康檢查 | [http://localhost:8000/health](http://localhost:8000/health) |
| 資料庫健康檢查 | [http://localhost:8000/health/db](http://localhost:8000/health/db) |
| Swagger API 文件 | [http://localhost:8000/docs](http://localhost:8000/docs) |

結束當日開發時，在前後端 Terminal 各按 `Ctrl+C`；如需暫停資料庫，在根目錄執行 `docker compose stop`，既有 volume 會保留。

### 建立旅程時覺得慢

`npm run dev` 會在首次開啟路由時編譯。建立旅程後會轉到每日行程頁，因此等待時間也包含目標頁面的編譯與資料讀取。2026-10-23 的開發伺服器紀錄中，建立旅程的 Server Action 約 60 ms，但第一次每日行程頁請求約 6.6 秒，其中 `next.js` 約 6.4 秒；之後相同頁面請求約 140 ms。`next.js` 是框架處理時間，包含編譯，不能全部當作資料庫寫入時間。這些是本機單次觀察，不代表正式環境效能保證。

要比較預先建置後的速度，可保持目前前後端開發服務運作，另外在 `frontend/` 執行：

```powershell
cd D:\TripSync\frontend
npm run build
npm run start -- --hostname 127.0.0.1 --port 3001
```

開啟 [http://localhost:3001](http://localhost:3001)，重新登入後比較建立旅程與新增活動；後端與資料庫仍需運作，也會使用相同資料。這是本機 production 模式預覽，尚未公開部署。程式碼修改後需重新 build；結束預覽時按 `Ctrl+C`。

排查方式與相關檔案見 [FILE_GUIDE.md 第 17 節](docs/FILE_GUIDE.md#17-建立旅程的等待時間與排查位置)。

## 驗證

在 `backend/` 執行 `python -m unittest discover -s tests -v`，93 項測試使用記憶體資料庫。在 `frontend/` 執行 `npm run lint`、`npx tsc --noEmit --incremental false`、`npm test` 與 `npm run build -- --webpack`（本機 Turbopack CSS 子程序啟動失敗，Webpack 已驗證）。HTTP 表單整合測試與隔離的 PostgreSQL 競態檢查見[地圖與帳務驗證](docs/MAPS_AND_LEDGER.md#6-驗證與預覽)。

## 後續開發起點

地圖與帳務第一版已完成，並已用 Maps Demo Key 驗證真實地圖與交通路線。接著依使用回饋安排進階行程、多幣別或投票，詳見[開發順序](docs/ROADMAP.md)。公開產品化前須更換正式金鑰、驗證來源限制，並完成信箱驗證、找回密碼、完整限流、HTTPS 部署與安全驗收；已實作防護與待辦見[資安說明](docs/COLLABORATION_AND_ITINERARY.md#9-已加入的防護與產品化前待辦)。
