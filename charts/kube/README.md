# kube 차트 DCGM 설정 가이드

차트 1.13.3의 `dcgmExporter.configMap` 옵션으로 DCGM 메트릭을 추가하거나 전체 목록을 교체할 수 있습니다.
기존 기본값과 기본 메트릭 목록, 이미지와 ConfigMap 이름은 변경하지 않습니다.

이 문서는 Helm values 설정입니다. whatap-operator 사용자는 해당 차트의 README를 참고하십시오.

## GPU 수집을 사용하지 않는 클러스터

기존 옵션을 그대로 사용합니다. 기본값도 false입니다.

```yaml
addon:
  gpu:
    enabled: false
```

DCGM exporter 컨테이너와 `dcgm-exporter-csv` ConfigMap을 모두 생성하지 않습니다.
차트가 GPU 노드 유무를 자동으로 탐지하지는 않습니다.

## 기본 메트릭을 유지하면서 추가

기존 설치 values 파일에 다음 부분만 병합합니다.

```yaml
addon:
  gpu:
    enabled: true
dcgmExporter:
  configMap:
    extraMetrics: |
      DCGM_FI_DEV_APP_SM_CLOCK, gauge, Application SM clock frequency (in MHz).
      DCGM_FI_DEV_APP_MEM_CLOCK, gauge, Application memory clock frequency (in MHz).
```

기본 `whatap-gpu.csv` 뒤에 지정한 CSV 행이 추가됩니다. 한 줄은 `DCGM 필드명, 타입, 설명` 형식입니다.
이미 활성화된 필드는 중복 추가하지 마십시오. 필드 지원 여부는 exporter 버전과 GPU에 따라 다릅니다.

## 메트릭 목록 전체 교체

```yaml
addon:
  gpu:
    enabled: true
dcgmExporter:
  configMap:
    customMetrics: |
      DCGM_FI_DEV_GPU_UTIL, gauge, GPU utilization (in %).
      DCGM_FI_DEV_FB_USED, gauge, Used framebuffer memory (in MiB).
    extraMetrics: ""
```

위 예시는 두 지표만 남기는 최소 예시입니다. 제외한 기본 메트릭을 사용하는 기존 GPU 화면과
알림은 데이터가 나오지 않을 수 있습니다. 필요한 지표와 label을 확인한 후 사용하십시오.

- `customMetrics` 미설정/빈 문자열/공백만 입력: 기존 기본 목록 사용.
- `customMetrics`와 `extraMetrics`를 모두 설정: 사용자 목록 뒤에 추가 목록을 붙임.
- 두 문자열의 앞뒤 공백과 개행을 제거하고 목록 사이에는 개행을 넣음.
- 설정값은 Helm 템플릿으로 실행하지 않고 CSV 문자열 그대로 사용.
- 기본 목록으로 복구: 두 문자열을 `""`로 비우고 다시 적용.
- `enabled`는 따옴표 없는 `true`/`false`, 메트릭은 위처럼 YAML 블록 문자열 사용.

## 외부에서 관리하는 ConfigMap 사용

```yaml
addon:
  gpu:
    enabled: true
dcgmExporter:
  configMap:
    enabled: false
```

GPU 수집은 유지하되 Helm에서 DCGM ConfigMap만 생성하지 않습니다.
동일 namespace에 `dcgm-exporter-csv`라는 ConfigMap과 `whatap-gpu.csv` 키를 외부에서 제공해야 합니다.
이름·키·마운트 경로는 기존과 동일하며, 이 설정은 exporter를 비활성화하지 않습니다.

주의: 기존 release가 관리하던 ConfigMap을 `true`에서 `false`로 바꾸면 Helm upgrade가 해당 ConfigMap을
**삭제할 수 있습니다**. 수집 중인 설치에서 단순히 false로 전환하지 말고, 소유권 이전과 exporter의
참조를 먼저 확인하십시오. GPU를 사용하지 않는 경우에는 위의 `addon.gpu.enabled: false`를 사용합니다.

## 기본값

```yaml
dcgmExporter:
  configMap:
    enabled: true
    customMetrics: ""
    extraMetrics: ""
```

`addon.gpu.enabled`도 true여야 ConfigMap이 생성됩니다. 새 옵션이 없는 기존 values도 기존 동작을 유지합니다.

## 적용과 확인

1. 실제 release 이름과 namespace를 확인하고 현재 values/manifest를 안전한 경로에 백업합니다.
   values에는 인증정보가 포함될 수 있으므로 출력·공유하지 마십시오.
2. 로컬 차트 또는 게시가 확인된 차트 버전으로 `helm template`을 먼저 실행합니다.
   기존 운영 values를 유지하고 위 설정 부분만 병합해 Helm upgrade를 진행합니다.
3. `dcgm-exporter-csv`의 `data.whatap-gpu.csv`가 의도한 목록인지 확인합니다.
4. CSV가 `subPath`로 마운트되므로 ConfigMap 수정만으로 실행 중 exporter에 반영되지 않습니다.
   작업 시간에 dcgm-exporter 컨테이너가 포함된 실제 node-agent DaemonSet을 확인한 뒤
   롤링 재시작하고 rollout 완료를 확인합니다. 같은 Pod의 agent/helper도 함께 재시작됩니다.
5. exporter 로그의 CSV/필드 오류, `/metrics`의 추가 지표, 와탭 화면의 기존·추가 지표를 확인합니다.

이 차트는 CSV 문자열을 구성하며, 실제 GPU가 해당 필드를 수집할 수 있는지는 배포 환경에서 확인해야 합니다.
