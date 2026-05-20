# DTO 인터페이스 정의서

> **작성일**: 1일차  
> **작성자**: 이진석  
> **합의 대상**: 박정우  
> **상태**: 합의 완료 후 서명란 기입 요망

---

## 개요

본 문서는 3대 에이전트(Data → Analysis → Action) 간의 데이터 전달 규격을 정의합니다.  
양측 개발자는 이 문서를 기준으로 독립적으로 개발을 진행하며,  
**이 문서의 내용을 변경할 경우 반드시 상대방과 사전 협의 후 수정해야 합니다.**

---

## DTO 1: DataDTO

**전달 방향**: `Data Agent (이진석)` → `Analysis Agent (박정우)`  
**Python 구현체**: `dto/schemas.py > DataDTO`

### JSON 포맷

```json
{
  "timestamp": "2024-01-15T09:00:00.123456",
  "day": 1,
  "daily_sales": 142.0,
  "current_stock": 380.0,
  "lead_time_days": 7.0,
  "weather_index": 0.830,
  "macro_trend": 1.120
}
```

### 필드 명세

| 필드명 | 타입 | 단위 | 설명 | 예시 |
|---|---|---|---|---|
| `timestamp` | string | ISO 8601 | 데이터 생성 시각 | `"2024-01-15T09:00:00"` |
| `day` | int | 일 | 시뮬레이션 경과 일수 (1부터 시작) | `1` |
| `daily_sales` | float | 개 | 당일 판매량 (결측치·노이즈 보정 완료) | `142.0` |
| `current_stock` | float | 개 | 당일 마감 재고 수준 | `380.0` |
| `lead_time_days` | float | 일 | 현재 조달 기간 (Mock API 수집값) | `7.0` |
| `weather_index` | float | - | 날씨 지수 (기준 1.0 / 범위 0.3~2.0) | `0.830` |
| `macro_trend` | float | - | 거시경제 지수 (기준 1.0 / 범위 0.5~1.8) | `1.120` |

### 보정 규칙 (이진석 담당)

- **결측치**: 최근 7일 이동평균으로 대체
- **이상치**: 3σ 룰 적용, 범위 초과 시 경계값으로 클리핑
- **스트레스 이벤트**: TimeSimulator 주입값 반영 후 전달

---

## DTO 2: InventorySignalDTO

**전달 방향**: `Analysis Agent (박정우)` → `Action Agent (이진석)`  
**Python 구현체**: `dto/schemas.py > InventorySignalDTO`

### JSON 포맷

```json
{
  "timestamp": "2024-01-15T09:01:00.654321",
  "day": 1,
  "safety_stock": 95.0,
  "reorder_point": 210.0,
  "optimal_order_qty": 300.0,
  "confidence_level": 0.95,
  "alert_level": "NORMAL"
}
```

### 필드 명세

| 필드명 | 타입 | 단위 | 설명 | 예시 |
|---|---|---|---|---|
| `timestamp` | string | ISO 8601 | 연산 완료 시각 | `"2024-01-15T09:01:00"` |
| `day` | int | 일 | 시뮬레이션 경과 일수 (DataDTO와 동일) | `1` |
| `safety_stock` | float | 개 | 확률론적 안전재고 (SS) | `95.0` |
| `reorder_point` | float | 개 | 동적 발주점 (ROP) | `210.0` |
| `optimal_order_qty` | float | 개 | 총비용 최소화 최적 발주량 | `300.0` |
| `confidence_level` | float | - | 연산 신뢰도 (범위 0.0~1.0) | `0.95` |
| `alert_level` | string | - | 재고 경보 수준 (아래 규칙 참조) | `"NORMAL"` |

### alert_level 규칙 (박정우 담당)

| 값 | 조건 | Action Agent 동작 |
|---|---|---|
| `"NORMAL"` | 현재 재고 > ROP | 발주 없음 |
| `"WARNING"` | 현재 재고 ≤ ROP | 발주 실행 + 방어 시나리오 리포트 발행 |
| `"CRITICAL"` | 현재 재고 ≤ SS | 즉시 긴급 발주 + 비상 리포트 발행 |

---

## 에이전트 파이프라인 흐름

```
[Data Agent]          [Analysis Agent]         [Action Agent]
이진석 담당            박정우 담당               이진석 담당

collect(day)    →     analyze(DataDTO)    →    execute(InventorySignalDTO)
     │                      │                          │
  DataDTO               InventorySignalDTO        order_list.json
  반환                    반환                     발주 실행
```

---

## 합의 사항

- [ ] DataDTO 필드 명세 확인 (박정우)
- [ ] InventorySignalDTO 필드 명세 확인 (이진석)
- [ ] alert_level 3단계 기준 합의
- [ ] 이 문서 기준으로 개발 착수 합의

---

## 변경 이력

| 날짜 | 변경 내용 | 변경자 |
|---|---|---|
| 1일차 | 최초 작성 | 이진석 |
