# 車路士情報站 Chelsea Blues Hub

自動抓取車路士官方新聞 + 訓練圖集，生成網頁情報站。

## 原理（同 ChuhaiWiki 一类嘅 AI 聚合打法）
```
chelseafc.com 官方 JSON API
        │  (零破解、零登录)
        ▼
scripts/fetch.py 抓取
        │  1. 列表 API 拉 50 條新聞
        │  2. 標題關鍵詞識別圖集（training gallery 等）
        │  3. 圖集詳情頁正則提取 img.chelseafc.com 圖片
        │  4. Cloudinary URL 加參數壓縮下載
        ▼
data/news.json + images/*.jpg
        │
        ▼
index.html 靜態渲染（純前端，無需伺服器）
```

## 數據源
- 列表：`GET https://www.chelseafc.com/en/api/news/listing/7rJyiGvKIDGe6kNF0jRwJ5?pageSize=50&pageNum=0`
- 圖片：Cloudinary（`res.cloudinary.com/chelsea-production`），URL 加 `w_1200,q_auto,f_auto` 可壓縮
- 中文版：`https://www.chelseafc.com/zh/news/latest-news`

## 本地運行
```bash
python3 scripts/fetch.py          # 抓取 → data/news.json + images/
python3 -m http.server 8000       # 本地預覽
# 開 http://localhost:8000
```

## 部署（GitHub Pages 免費）
1. 推到 GitHub repo
2. Settings → Pages → Source 選 `main` 分支根目錄
3. Actions 每 6 小時自動抓取並提交
4. 訪問 `https://<你的用戶名>.github.io/<repo名>/`

## 目錄結構
```
chelsea-news/
├── index.html                  # 前端頁面（純靜態）
├── scripts/fetch.py            # 抓取腳本
├── data/news.json              # 抓取結果（含中英翻譯）
└── .github/workflows/fetch.yml # GitHub Actions 定時任務
```

## 圖片方案
圖集圖片**不落地 repo**，改為直接引用官方 Cloudinary 直鏈（加 `w_1200,q_auto,f_auto` 壓縮），repo 永遠輕量，零存儲成本。

## 圖集識別關鍵詞
`training gallery` `gallery` `match gallery` `open training` `behind the scenes` `colney` `in pictures` `best pictures` `day as a blue`

## 注意
- 圖片版權歸車路士足球會及原作者，僅供個人收藏，勿商用
- 官方 API 未公開文檔，參數可能變動，若失效需重新抓 `data-props` 裡嘅 `apiUrl`
