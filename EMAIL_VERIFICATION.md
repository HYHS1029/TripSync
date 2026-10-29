# 帳號與電子郵件驗證

信箱綁定與驗證已實作，但目前保留為後續功能，預設停用，不隨熟人測試版開放。朋友使用使用者名稱與密碼註冊、登入，並透過邀請連結加入旅程，不需要寄信服務或自有網域。尚未提供忘記密碼，請先告知測試者妥善保管帳密。

後端與前端的伺服器環境變數均以 `EMAIL_VERIFICATION_ENABLED=false` 停用。關閉時，註冊頁不收集 Email、帳號頁隱藏寄信入口、驗證頁回傳 404；前端 Server Actions 與後端寄信／確認 API 都會拒絕直接呼叫。即使仍留有 SMTP 設定，也不會開啟寄信。既有帳號、旅程、待驗證資料與已驗證信箱不會被刪除；既有已驗證信箱仍可作為登入識別值。

之後要啟用時，將前後端兩處都設為 `EMAIL_VERIFICATION_ENABLED=true`，並重新啟動或部署。開啟後 Email 為選填，完成驗證後才能作為登入識別值；使用者名稱維持區分大小寫。

## 手動啟用本機測試

1. 啟動原本的 PostgreSQL，以及選用的 Mailpit 收信服務：

   ```powershell
   docker compose up -d db
   docker compose --profile mail up -d mailpit
   ```

2. 在 `backend/.env` 設定以下欄位，保留原本的資料庫與 JWT 設定：

   ```dotenv
   FRONTEND_URL=http://localhost:3000
   EMAIL_VERIFICATION_ENABLED=true
   EMAIL_VERIFICATION_EXPIRE_MINUTES=30
   SMTP_HOST=127.0.0.1
   SMTP_PORT=1025
   SMTP_SECURITY=none
   SMTP_FROM_EMAIL=noreply@tripsync.example
   ```

3. 同時在 `frontend/.env.local` 設定 `EMAIL_VERIFICATION_ENABLED=true`。在 `backend/` 啟用 `tripsync` Python 環境，執行 `python -m alembic upgrade head`，再啟動／重新啟動後端與前端。
4. 註冊或使用**使用者名稱**登入，開啟「我的帳號」，填入 Email 與目前密碼，點選「寄送驗證信」。註冊時填入 Email 不會自動寄信，登入後才主動申請。
5. 開啟 [本機測試信箱](http://localhost:8025)，點選信中的驗證連結。登入提出申請的相同帳號，再按「確認驗證信箱」。成功後帳號頁顯示「已驗證」，即可使用 Email 登入。

Mailpit 攔截測試信件，不會寄到真實信箱；SMTP 與收信介面均僅綁定 `127.0.0.1`。容器重建會清空信件，最多保留 100 封。

本機保留 Mailpit 寄信設定與已套用的 migration，但目前前後端開關均設為 `false`。需要測試時再手動啟用，完成後可關閉開關；修改設定後須重啟。

## 舊帳號與資料遷移

`e53a9c2d7f01` migration 將舊 `email` 移至 `pending_email`，原有帳號 ID、使用者名稱、密碼與旅程關係保留。舊 Email 從未驗證，不會自動視為可信；升級後請先使用使用者名稱登入，再完成驗證。

未驗證信箱不占用唯一綁定名額。只有確認成功後才寫入唯一索引保護的 `users.email`；已被另一帳號驗證綁定的地址無法再次綁定，不會合併或覆寫帳號。

降版前每個帳號都須有可還原的唯一 Email；存在未填信箱或重複待驗證地址時，migration 會拒絕降版，避免刪除帳號或捏造地址。

## API 與安全設計

| 操作 | API | 條件／結果 |
| --- | --- | --- |
| 註冊 | `POST /users` | `email` 可省略；填入時只存為待驗證地址 |
| 登入 | `POST /auth/login` | `identifier`＋`password`；保留舊 `email` 輸入別名，仍須符合新驗證政策 |
| 寄送／重寄／更換 | `POST /auth/email-verification/request` | Bearer 登入、`email`、目前 `password`；成功回傳 202 |
| 確認 | `POST /auth/email-verification/confirm` | Bearer 登入、`token`；必須為提出申請的同一帳號 |
| 帳號狀態 | `GET /users/me` | nullable `email`、`email_verified_at`、`pending_email`；不回傳驗證碼或雜湊 |

- `secrets.token_urlsafe(32)` 產生 256 位元隨機驗證碼。資料庫只存帶用途前綴的 SHA-256 雜湊，預設 30 分鐘到期。
- 每帳號只保留一筆待驗證資料，重寄覆蓋舊雜湊。寄信請求以使用者列鎖序列化；確認以帶帳號、雜湊與期限條件的 `UPDATE ... RETURNING` 原子消耗，防止重播及併發重複使用。
- 連結使用設定的 `FRONTEND_URL`，不採用請求 Host。驗證碼放在 URL fragment，瀏覽器讀取後移除，再由按鈕提交；GET 或郵件掃描器不會直接消耗驗證碼。
- 登入往返透過 `HttpOnly`、`SameSite=Lax`、正式版 `Secure` Cookie 暫存，路徑限 `/verify-email`，不放入登入 URL 或 localStorage；完成或登出時清除。
- 更換信箱要求目前密碼，並向原信箱寄申請通知；確認新信箱前，原信箱仍可登入。寄信失敗回滾待驗證變更，原連結維持原期限。
- SMTP 在回應前完成，沒有額外背景執行緒或佇列。SMTP 與資料庫不共享交易，少數情況可能已收信但資料庫提交失敗，此時需重寄。
- Email 沿用 `EmailStr` 的格式與網域正規化，本地部分維持大小寫，不移除 Gmail 的點或 `+`。寄送限額保守地將收件地址轉小寫，避免大小寫變體繞過限制。

## 限流與複雜度

`auth_rate_limits` 以主鍵 upsert 作為跨程序共享的固定時間窗計數器，資料庫原子更新，拒絕時回傳 429 與 `Retry-After`。鍵以 HMAC 雜湊，不保存明碼信箱或使用者名稱。

| 範圍 | 限額 |
| --- | --- |
| 登入 | 每帳號 20 次／5 分鐘，兩種登入方式共用；未知識別值另計 |
| 寄信前密碼驗證 | 每帳號 10 次／10 分鐘 |
| 寄信 | 每帳號 1 次／分鐘、5 次／小時；每收件信箱 3 次／小時 |
| 驗證提交 | 每帳號 10 次／10 分鐘 |

帳號與信箱使用唯一索引，查詢為 O(log N)，每帳號待驗證資料 O(1)。每次更新固定數量的限流紀錄，並透過到期索引最多清理 100 筆過期計數，不掃描全部使用者或累積驗證碼歷史。時間窗邊界可能集中使用相鄰兩窗額度；仍需部署層的 IP／流量防護與註冊濫用管理。

## 正式寄信

選定 SMTP 服務後，設定供應商提供的 `SMTP_HOST`、`SMTP_PORT`、`SMTP_USERNAME`、`SMTP_PASSWORD`、`SMTP_FROM_EMAIL`，並將 `FRONTEND_URL` 改為正式前端 HTTPS origin。

`SMTP_SECURITY=starttls` 通常使用 587，`ssl` 通常使用 465，依供應商設定。僅允許 loopback SMTP 使用 `none`；外部連線必須驗證 TLS 憑證。部署平台需確認 SMTP 出站連線可用，供應商要求的寄件網域驗證與 SPF／DKIM 也需完成。寄信憑證不得放入 `NEXT_PUBLIC_` 或版本控制。

## 驗證

在 `backend/` 執行：

```powershell
python -m unittest discover -s tests -q
python tests/check_email_postgres.py
```

121 項後端測試包含 18 項信箱／SMTP 測試，也驗證預設停用、停用後阻擋直接呼叫，以及重新啟用時保留原流程。PostgreSQL 檢查只允許本機資料庫，在該測試程序暫時開啟驗證，在隨機獨立 schema 套用完整 migration，驗證舊帳號、單次消耗、唯一信箱競態及限流競態，最後清除該 schema。

HTTP 測試：在 `backend/` 執行 `python tests/serve_e2e.py`，在 `frontend/` 建置後，設定 `$env:API_BASE_URL='http://127.0.0.1:8001'`，執行 `npm run start -- --hostname 127.0.0.1 --port 3001`。前後端均維持預設關閉時，先於 `backend/` 驗證熟人版：

```powershell
python tests/check_email_disabled_frontend.py
python tests/check_frontend_flow.py
```

需要回歸測試保留的寄信功能時，啟動 Mailpit，前後端的測試程序均設定 `$env:EMAIL_VERIFICATION_ENABLED='true'`，並在記憶體 API 程序設定 `$env:FRONTEND_URL='http://localhost:3001'`，再執行 `python tests/check_email_frontend.py`。這些測試只寫入記憶體 API，信件留在本機 Mailpit，不修改一般本機環境的開關。

找回密碼、MFA 與完整多裝置 session 撤銷仍是後續功能，信箱驗證不代表已提供帳號恢復或雙因素保護。
