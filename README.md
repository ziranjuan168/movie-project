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

免费实例可能休眠，因此当前项目除了后台线程同步，还会在首页和详情页访问时按过期时间自动触发一次刷新。

若没有云平台账号，也可以使用 `cloudflared tunnel --url http://127.0.0.1:8000` 暴露公网地址。

## 数据库迁移

项目现在支持逻辑快照导出和导入，不依赖 Render 专有格式。迁库时只需要准备旧库和新库两个 `DATABASE_URL`。

导出当前数据库：

```bash
DATABASE_URL="旧库连接串" flask --app wsgi export-data --output backups/movie-data.json
```

初始化新数据库并导入：

```bash
DATABASE_URL="新库连接串" flask --app wsgi init-db
DATABASE_URL="新库连接串" flask --app wsgi import-data --input backups/movie-data.json --replace
```

如果只想把快照合并到现有库，而不是整库覆盖：

```bash
DATABASE_URL="目标库连接串" flask --app wsgi import-data --input backups/movie-data.json --merge
```

快照会保留电影、评论、时间戳和评分数据；导入到 Postgres 时还会自动修正自增序列，避免迁移后新评论插入失败。
