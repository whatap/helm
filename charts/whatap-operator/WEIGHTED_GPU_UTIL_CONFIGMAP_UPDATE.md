# DCGM_FI_DEV_WEIGHTED_GPU_UTIL 메트릭 ConfigMap 추가

## 개요

whatap-operator Helm 차트의 `gpu-configmap.yaml`에 `DCGM_FI_DEV_WEIGHTED_GPU_UTIL` 메트릭을 추가했습니다. 이 메트릭은 NVIDIA MIG(Multi-Instance GPU) 환경에서 정확한 GPU 사용률 모니터링을 위해 개발된 새로운 메트릭입니다.

## 변경사항

### 파일: `templates/gpu-configmap.yaml`

**추가된 메트릭**:
```yaml
DCGM_FI_DEV_WEIGHTED_GPU_UTIL, gauge, Weighted GPU utilization for MIG and non-MIG devices (ratio 0.0-1.0). # code 9003
```

**위치**: Utilization 섹션 (line 42)
**메트릭 타입**: gauge
**단위**: 비율 (0.0 ~ 1.0)
**코드**: 9003

## 메트릭 설명

### 기능
- **MIG 모드 GPU**: MIG 인스턴스별 `DCGM_FI_PROF_GR_ENGINE_ACTIVE` 값을 가중치 계산하여 전체 GPU 사용률 도출
- **일반 GPU**: 기존 `DCGM_FI_DEV_GPU_UTIL` 값을 0-1 비율로 변환

### 계산 방식

#### MIG 모드 (DCGM_FI_DEV_MIG_MODE="1")
```
DCGM_FI_DEV_WEIGHTED_GPU_UTIL = Σ(DCGM_FI_PROF_GR_ENGINE_ACTIVE × slice_ratio)

where:
slice_ratio = compute_slices / DCGM_FI_DEV_MIG_MAX_SLICES
compute_slices = GPU_I_PROFILE에서 추출 (예: "1g.5gb" → 1, "2g.10gb" → 2)
```

#### 일반 모드 (DCGM_FI_DEV_MIG_MODE="0")
```
DCGM_FI_DEV_WEIGHTED_GPU_UTIL = DCGM_FI_DEV_GPU_UTIL / 100
```

## 사용법

### 1. Helm 차트 배포
```bash
helm upgrade --install whatap-operator ./charts/whatap-operator \
  --namespace whatap-monitoring \
  --create-namespace
```

### 2. ConfigMap 확인
```bash
kubectl get configmap dcgm-exporter-csv -n whatap-monitoring -o yaml
```

### 3. DCGM-Exporter에서 메트릭 확인
```bash
# DCGM-Exporter Pod에서 메트릭 확인
kubectl exec -n whatap-monitoring <dcgm-exporter-pod> -- curl localhost:9400/metrics | grep DCGM_FI_DEV_WEIGHTED_GPU_UTIL
```

## 예상 출력

### MIG 환경
```prometheus
DCGM_FI_DEV_WEIGHTED_GPU_UTIL{
  gpu="1",
  UUID="GPU-9dadccd1-6248-ac2a-6e85-0af3fdfeef3c",
  device="nvidia1",
  modelName="NVIDIA A100-SXM4-40GB",
  DCGM_FI_DEV_MIG_MODE="1",
  calculation_method="weighted_sum"
} 0.322663
```

### 일반 GPU 환경
```prometheus
DCGM_FI_DEV_WEIGHTED_GPU_UTIL{
  gpu="0",
  UUID="GPU-d6215468-e63a-57fa-8e41-ef2ea1e698a5",
  device="nvidia0",
  modelName="NVIDIA A100-SXM4-40GB",
  DCGM_FI_DEV_MIG_MODE="0",
  calculation_method="direct"
} 0.770000
```

## Prometheus 쿼리 예시

### 전체 클러스터 평균 GPU 사용률
```promql
avg(DCGM_FI_DEV_WEIGHTED_GPU_UTIL)
```

### MIG 모드 GPU만 조회
```promql
DCGM_FI_DEV_WEIGHTED_GPU_UTIL{calculation_method="weighted_sum"}
```

### 노드별 GPU 사용률
```promql
avg by (node) (DCGM_FI_DEV_WEIGHTED_GPU_UTIL)
```

### GPU 사용률 90% 이상인 GPU 찾기
```promql
DCGM_FI_DEV_WEIGHTED_GPU_UTIL > 0.9
```

## 관련 메트릭

이 새로운 메트릭은 다음 기존 메트릭들과 함께 사용됩니다:

- `DCGM_FI_DEV_MIG_MODE`: MIG 모드 상태 확인
- `DCGM_FI_DEV_MIG_MAX_SLICES`: MIG 최대 슬라이스 수
- `DCGM_FI_PROF_GR_ENGINE_ACTIVE`: MIG 인스턴스별 엔진 활성도
- `DCGM_FI_DEV_GPU_UTIL`: 일반 GPU 사용률

## 호환성

- **DCGM-Exporter**: 새로운 메트릭 구현이 필요 (별도 구현 완료)
- **GPU 모델**: A100, H100 등 MIG 지원 GPU
- **MIG 프로필**: 1g.5gb, 2g.10gb, 3g.20gb, 4g.20gb, 7g.40gb
- **Kubernetes**: 모든 버전 호환

## 문제 해결

### ConfigMap이 업데이트되지 않는 경우
```bash
# ConfigMap 강제 업데이트
kubectl delete configmap dcgm-exporter-csv -n whatap-monitoring
helm upgrade whatap-operator ./charts/whatap-operator -n whatap-monitoring
```

### 메트릭이 나타나지 않는 경우
1. DCGM-Exporter가 새 버전으로 업데이트되었는지 확인
2. ConfigMap이 올바르게 마운트되었는지 확인
3. DCGM-Exporter 로그에서 에러 메시지 확인

---

**업데이트 일시**: 2025년 1월  
**관련 이슈**: MIG 환경에서의 GPU 사용률 모니터링 개선  
**의존성**: DCGM-Exporter에 DCGM_FI_DEV_WEIGHTED_GPU_UTIL 메트릭 구현 필요