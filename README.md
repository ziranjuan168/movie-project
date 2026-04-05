# 映准

一个同步豆瓣正在上映片单、允许用户重新打分和发表评论的电影网站。

## 本地运行

```bash
pip install -r requirements.txt
flask --app wsgi init-db
flask --app wsgi sync-movies
python3 wsgi.py
```

默认地址是 `http://127.0.0.1:8000`。

## 关键环境变量

- `SECRET_KEY`: Flask 会话密钥
- `DATABASE_URL`: 数据库连接串，默认是 `instance/movie.db`
- `DOUBAN_CITY`: 豆瓣城市 slug，默认 `beijing`
- `SYNC_INTERVAL_HOURS`: 自动同步周期，默认 `6`
- `AUTO_SYNC_ENABLED`: 是否开启自动同步，默认 `true`

## 部署备注

Render 等生产环境建议使用：

```bash
gunicorn -b 0.0.0.0:$PORT wsgi:app
```

若没有云平台账号，也可以使用 `cloudflared tunnel --url http://127.0.0.1:8000` 暴露公网地址。
