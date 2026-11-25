
# Benchmark & Observability Report — Day 14

Mọi con số bên dưới lấy từ JSON, CSV, trace và screenshot thực chạy trong repo.

**Họ tên:** Nguyễn Ngọc Sang
**Ngày chạy:** 2026-11-25 (GMT+7)
**Môi trường:** CP7 được chạy lại trên Windows host, Python 3.11; agent v1/v2 và load-test client cùng chạy trên host từ workspace OneDrive. Tài nguyên máy và tác vụ nền có thể ảnh hưởng latency. Load test dùng `MOCK_ERROR_RATE=0.01`; eval dùng mặc định `MOCK_ERROR_RATE=0.01` và retry một lần. `MOCK_SLOW_RATE` được ghi riêng cho ba lượt tail-latency. CP8 chạy trong Docker Desktop WSL2; không suy luận latency từ 23 câu eval.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Đo nhóm 95% request; theo ngưỡng mặc định load_test.py |
| Error rate `/ask` | ≤ 2% | Theo ngưỡng mặc định load_test.py; gồm lỗi HTTP và kết nối |
| Accuracy trên golden dataset | ≥ 100% sau sửa KB | Phải đạt 23/23, không regression; quality gate CI ví dụ 85% |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.02 | 200.1 | 240.1 | 1703.2 | 0.67% | PASS |
| 10 | 35.18 | 199.6 | 512.8 | 1724.9 | 2.33% | FAIL |
| 50 | 41.41 | 563.4 | 2891.5 | 3962.7 | 0.67% | FAIL |
| 100 | 36.57 | 1441.3 | 5563.4 | 6077.4 | 0.67% | FAIL |

**Nhận xét:** RPS không tăng tuyến tính: concurrency 100 có throughput thấp hơn 50 (36.57 so với 41.41 req/s), trong khi p95 tăng từ 240.1 ms ở concurrency 1 lên 5563.4 ms ở 100. Client và agent cùng dùng tài nguyên host; scheduling, HTTP, logging và giới hạn máy có thể làm tăng hàng chờ thay vì năng lực xử lý. Chỉ concurrency 1 đạt cả hai SLO; concurrency 10 vi phạm cả p95 lẫn error rate, còn 50/100 vi phạm p95. Cần đo trên môi trường tách biệt client/server trước khi suy rộng thành công suất production. Những hàng FAIL là kết quả thật, không phải lý do bỏ file report.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 251.0 | 547.3 | 616.5 |
| 0.03 (mặc định) | 285.4 | 591.8 | 1725.9 |
| 0.1 | 367.0 | 1703.4 | 1732.4 |

**Nhận xét:** Khi slow rate từ 0 lên 0.1, p95 tăng từ 547.3 ms lên 1703.4 ms và p99 từ 616.5 ms lên 1732.4 ms; average tăng ít hơn, từ 251.0 ms lên 367.0 ms. Percentile cao nhạy hơn với nhóm request chậm; average che khuất tail latency. Mỗi lượt chỉ có 300 request, nên jitter và tính ngẫu nhiên của mock làm các kết quả có biến thiên; cả ba lượt đều vượt SLO p95 500 ms.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 1/23 (4.35%) | 21/23 (91.30%) | 23/23 (100.00%) |
| Avg tokens / câu | 57.7 | 108.8 | 113.0 |
| Tổng cost (USD) | 0.000412 | 0.000757 | 0.000785 |
| Cost / câu đúng (USD) | 0.00041235 | 3.607e-05 | 3.413e-05 |
| Quality gate | FAIL | PASS | PASS |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm tài liệu JWT về token, chữ ký và hết hạn |
| scaling-03 | cpu, memory, custom metrics | Thêm tài liệu HPA về CPU, memory và custom metrics |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:** v2 thêm retrieval/context nên dùng nhiều token hơn và tổng cost cao hơn v1, nhưng cost/câu đúng giảm rõ rệt. Cost/câu đúng tính đến cả độ chính xác: chỉ nhìn cost/câu có thể đánh giá nhầm một agent rẻ nhưng trả lời sai là hiệu quả. Bản sửa KB đạt 23/23 so với 21/23 ban đầu, không regression. `eval_v2.json` được giữ nguyên làm baseline trước khi sửa KB; `eval_v1.json` và `eval_v2_fixed.json` là lần chạy CP7 hiện tại. Các số cost là chi phí mô phỏng do mock tính, không phải hóa đơn LLM thật. Không dùng p95 từ eval để kết luận hiệu năng vì chỉ có 23 câu.

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [x] [Dashboard Grafana khi có tải](screenshots/grafana-dashboard.png): 10.1 req/s, error 19.49%, p95 2.97s, 2 instance tại lúc chụp trong thí nghiệm fault injection.
- [x] [Trace chậm trong Jaeger](screenshots/jaeger-slow-trace.png).
- [x] [Trace lỗi trong Jaeger](screenshots/jaeger-error-trace.png): mở span chat, tab Details, thấy event `exception`.
- [x] [Hai alert cùng firing trong Prometheus](screenshots/prometheus-alert-firing.png): `AgentHighErrorRate` và `AgentHighLatencyP95`.

Stack chạy bằng project `k5-day14-observability`; smoke test `/health` và `/ask` 200, `/metrics` qua Nginx 404 trong [cp8_smoke.json](reports/cp8_smoke.json). Unit test rule bằng promtool báo SUCCESS trong [cp8_promtool.txt](reports/cp8_promtool.txt). Dockerfile đặt `PYTHONUSERBASE=/home/agent/.local` để Python tìm đúng packages đã copy cho user agent. Ảnh là UI thật, chụp bằng Playwright sau khi người học cho phép fallback vì CUA timeout.

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | AgentHighErrorRate | 168.7 giây | Error rate /ask |
| B | `MOCK_SLOW_RATE=0.3` | AgentHighLatencyP95 | 229.4 giây | p95/p99 và LLM latency |
| C | `LLM_MODEL=mock-llm-large` | Không chạy; đã chọn A và B | — | Kỳ vọng cost burn rate tăng; chưa đo |
| D | `docker pause` 1 instance | Không chạy | — | Kỳ vọng Instances up giảm; chưa đo |
| E | `AGENT_VERSION=v1` | Không chạy fault này trong stack; eval v1 đã chạy riêng | — | Chất lượng phát hiện bằng eval |

A và B được áp dụng **cùng một lượt** trên 2 instance, Locust 30 users / spawn 5 / 8 phút. Vì vậy đây là thí nghiệm kết hợp, chưa cô lập ảnh hưởng riêng từng biến. Trước khi bắt đầu, hai alert lỗi/latency đều inactive. Mốc đổi cấu hình là 08:54:42 UTC; thời gian đo gồm recreate container, ramp-up, cửa sổ rate 1 phút, chu kỳ scrape/evaluation và `for`. Poll mỗi khoảng 5 giây, nên thời điểm ghi là lần đầu quan sát firing, không phải độ chính xác dưới giây. Timeline và trạng thái cùng firing: [cp8_chaos.json](reports/cp8_chaos.json). `AgentInstanceDown` từng firing khi recreate target (57.6s), không tính là thí nghiệm D. Hai rule mục tiêu đều pending từ 08:56:22 UTC rồi đủ `for: 1m` / `for: 2m` mới firing. Ngưỡng alert 5% / 1s khác SLO benchmark 2% / 500ms ở mục 1.

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?** Metrics hạ tầng chỉ đo tốc độ, lỗi HTTP và chi phí; câu trả lời sai vẫn có thể HTTP 200. Cần eval định kỳ trên golden dataset, quality gate so baseline, theo dõi chất lượng/feedback và có thể sampled online eval. Không khẳng định đã chạy thí nghiệm E nếu chưa có bằng chứng.

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: `da2ef3a961f1af318a25fbec20b33d85`.
- Tổng thời gian: 1733.560 ms.
- Span con xử lý chiếm nhiều thời gian nhất: `chat mock-llm-small` (1699.686 ms, 98.05% tổng thời gian); retrieval 14.752 ms. Các span cha `POST /ask` và `agent.run` bao toàn bộ công việc nên dài hơn span chat, không phải các bước xử lý độc lập để cộng vào nhau.
- Cách chọn: tìm log `llm_call` có `llm_ms` lớn nhất trong mẫu tối đa 2000 dòng log gần nhất mỗi instance, rồi mở đúng trace đó; không khẳng định đây là request chậm nhất toàn bộ lịch sử.
- Dòng log tương ứng (grep theo `trace_id`):

```json
{"ts":"2026-11-25T08:57:06.274868+00:00","level":"INFO","service":"observable-agent","instance":"c9402ffe2b80","event":"llm_call","trace_id":"da2ef3a961f1af318a25fbec20b33d85","span_id":"cd407ff991a04e04","request_id":"da39c355a26a","model":"mock-llm-small","agent_version":"v2","input_tokens":95,"output_tokens":55,"cost_usd":0.000047,"llm_ms":1698.6}
```

Trace lỗi: `b52382e1c2d179ed7b67c662d59bb9a9`, tổng 109.052 ms, chat 82.258 ms. Event `exception` ghi `utils.mock_llm.LLMError` với message `Upstream LLM error: 503 Service Unavailable (mock)`. Dòng log khớp:

```json
{"ts":"2026-11-25T08:56:54.189306+00:00","level":"INFO","service":"observable-agent","instance":"c9402ffe2b80","event":"llm_error","trace_id":"b52382e1c2d179ed7b67c662d59bb9a9","span_id":"06f1a58274c3657d","request_id":"81da86344853","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

JSON log giữ nguyên các trường/giá trị, chỉ bỏ khoảng trắng khi trình bày. Bằng chứng: [tóm tắt trace và log](reports/cp8_trace_evidence.json), [slow trace gốc](reports/jaeger_slow_trace.json), [error trace gốc](reports/jaeger_error_trace.json). Lấy log Docker cả stdout và stderr vì Python logging ghi stderr. Dữ liệu trace lấy bằng API v3 theo [schema chính thức Jaeger](https://github.com/jaegertracing/jaeger-idl/blob/main/swagger/api_v3/query_service.openapi.yaml), không sửa nội dung span.

### 4.4 Trả lời Exercise 7.4

Snapshot query tại **08:59:00 UTC**, trong lượt 2 instance / 30 users với hai fault trên, nằm ở `chaos_2` trong [cp8_dashboard_metrics.json](reports/cp8_dashboard_metrics.json):

1. p95 = 1.906s, avg = 0.631s. Nhóm request chậm kéo percentile cao lên khoảng 3 lần avg; average không mô tả tốt trải nghiệm nhóm đuôi. Grafana chụp ở thời điểm khác với cửa sổ trượt nên p95 2.97s trong ảnh không phải số ở snapshot này.
2. Hai instance nhận 7.258 và 7.676 req/s, khoảng 48.6% / 51.4%; traffic gần đều, không tuyệt đối bằng nhau. Snapshot `scale_3` giữ thêm số đo 3 instance trong benchmark riêng.
3. Input 894.255 tokens/s > output 465.635 tokens/s vì input gồm câu hỏi và context truy xuất, còn output là câu trả lời ngắn. Khi xem biểu đồ stacked, chiều cao đường phía trên có thể là tổng cộng dồn; đọc giá trị từng series hoặc query PromQL để so sánh.
4. `GET http://localhost:8080/metrics` trả 404 do Nginx chặn endpoint quan sát ở cổng public. Prometheus scrape trực tiếp `agent:8000/metrics` trong mạng Compose; API key của `/ask` không thay thế việc hạn chế lộ metrics.

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 14.05 | 3000 | 10000 | 11000 | 404/1619 (24.95%) |
| 3 | 33.99 | 270 | 6900 | 11000 | 132/4241 (3.11%) |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

Lấy **hàng POST `/ask`**, không lấy Aggregated có lẫn health check, từ [scale_1_stats.csv](benchmark-results/scale_1_stats.csv) và [scale_3_stats.csv](benchmark-results/scale_3_stats.csv). RPS tính tất cả request hoàn tất, gồm request lỗi. CSV cũng được giữ ở `production/benchmark-results/` đúng đường dẫn checkpoint. Cùng 100 users, spawn 10, 2 phút, error rate mock 0.01 và slow rate 0.03; mỗi agent bị giới hạn 0.5 CPU / 256 MiB. Metadata [scale 1](reports/scale_1_environment.json) và [scale 3](reports/scale_3_environment.json) xác nhận số container trước/sau lần lượt 1/1 và 3/3.

Lệnh tái hiện sau khi stack đã build (chạy trong `production/`, lần lượt đặt N=1 và N=3):

```bash
N=1 # Chạy xong lượt này thì đổi thành N=3 và chạy lại.
docker compose -p k5-day14-observability up -d --no-build --scale agent="$N"
# Kiểm tra số replica, đợi discovery/scrape khoảng 15 giây.
docker compose -p k5-day14-observability run --no-deps --rm locust -f /mnt/locust/locustfile.py --host http://nginx --headless -u 100 -r 10 -t 2m --csv /mnt/results/scale_${N}
```

`--no-deps` cần thiết: nếu bỏ, `compose run` có thể reconcile service phụ thuộc về `deploy.replicas: 2`, làm phép đo nhãn 1/3 sai số replica. Các lượt sai replica đã bị loại trước khi ghi bộ CSV cuối. Lượt 3 instance bị nhiễu bởi grader chạy đồng thời cũng được đo lại sau khi grader dừng; bảng dùng lần cuối. Không build/chấm readiness đồng thời với hai lượt đo cuối, nhưng tất cả container vẫn dùng chung Docker VM với stack quan sát.

Throughput tăng khoảng 2.42 lần, p95 giảm 31%; p99 vẫn 11 giây. Cả hai cấu hình đều FAIL SLO latency và error ở mục 1. Scale giúp giảm hàng chờ nhưng chưa giải quyết được tail. Bằng chứng lỗi ở [scale_1_failures.csv](benchmark-results/scale_1_failures.csv): 387 lỗi 504 và 17 lỗi 503; ở [scale_3_failures.csv](benchmark-results/scale_3_failures.csv): 88 lỗi 504, 42 lỗi 503 và 2 lỗi 502. CPU cap, scheduling/I/O của VM, queue và timeout Nginx là các yếu tố cần điều tra; một trace chat 1.7s không đủ để quy mọi p95 6.9–10s cho LLM. Cần đối chiếu CPU/throttling/queue với trace trên máy riêng để xác định nút thắt chắc chắn. Lỗi 504 do Nginx tạo có thể không được đếm trong metric HTTP của agent, nên không lấy error panel của agent thay error rate phía client. Locust exit 1 vì có request lỗi là kết quả đo, không phải bỏ qua failures.

---

## 6. Kết luận

- 3 điều học được từ kết quả:
  1. Average có thể che tail latency; phải đọc percentile và SLO.
  2. Accuracy và cost/câu đúng bổ sung cho metrics hạ tầng.
  3. Benchmark phụ thuộc môi trường; tăng concurrency không đảm bảo tăng throughput.
- Nếu đưa agent này lên production thật: thêm metrics/alert ở Nginx hoặc synthetic check từ ngoài để thấy 502/504, histogram thời gian chờ queue, chất lượng trả lời và ngân sách chi phí thực. Cost guard lab kiểm trước rồi ghi cost sau response nên là giới hạn chi tiêu có thể vượt nhẹ khi nhiều request đồng thời; cần reservation/reconciliation nếu yêu cầu hard cap.
- Đã thu thập bằng chứng trước khi trả `.env` observability về trạng thái ban đầu và dừng stack local bằng đúng project name. Service Railway được giữ Online để kiểm tra bài.
