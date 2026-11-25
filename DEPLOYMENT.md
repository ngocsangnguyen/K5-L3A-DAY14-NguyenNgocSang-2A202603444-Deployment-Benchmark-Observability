# Deployment information — CP6

## Trạng thái

Đã deploy source local lên Railway, không commit. Public URL: https://agent-production-a04c3e95.up.railway.app. Redis cloud đã nối thành công; /ready 200. Kết quả thực gọi URL: reports/cp6_public_checks.json.

## Nền tảng chính: Railway

Chọn Railway vì CLI upload trực tiếp code local, không cần commit. Agent cần một Redis trong cùng project. Railway build từ 06-lab-complete/Dockerfile, start command dùng PORT do nền tảng cấp và health check /health.

## Biến môi trường

| Biến | Giá trị / cách đặt |
|---|---|
| ENVIRONMENT | production |
| AGENT_API_KEY | Sinh riêng và đặt trên nền tảng; không ghi giá trị vào tài liệu |
| REDIS_URL | Reference tới REDIS_URL của service Redis trong project |
| RATE_LIMIT_PER_MINUTE | 10 |
| DAILY_BUDGET_USD | 1.0 |
| LOG_LEVEL | INFO |
| PORT | Dùng giá trị nền tảng cấp |

## Lệnh deploy (chạy trong 06-lab-complete)

```bash
railway login
railway init
railway add --database redis
# Tạo/link service agent và đặt các biến trên trong project.
railway up
railway domain
```

## Tự kiểm tra sau deploy

Đặt `BASE` như lệnh bên dưới; `AGENT_API_KEY` lấy từ environment, không chép key vào ảnh.

```bash
BASE=https://agent-production-a04c3e95.up.railway.app
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

Yêu cầu lần lượt 200 / 200 / 401 / 200. Đã xác nhận thực tế 200 / 200 / 401 / 200.

## Ảnh minh chứng

- [Dashboard Railway](screenshots/dashboard.png) — project `day14-production-agent`, agent và Redis Online.
- [Service chạy](screenshots/running.png) — response `/health` từ URL public.
- [Kết quả test](screenshots/test.png) — bốn HTTP checks và response thật, không có API key.

Người học đăng nhập trực tiếp trong cửa sổ Edge dành cho chụp ảnh; ảnh được chụp bằng Playwright theo sự cho phép của người học. Không dùng ảnh local thay ảnh cloud. Docker local đã được dọn sau lab; service cloud giữ lại để Lab Coach kiểm tra. Chỉ xoá cloud sau khi được chấm.
