# Whatap Operator Helm Chart - Usage Guide

이 문서는 Whatap Operator Helm 차트를 설치하고 구성하는 방법을 설명합니다. 이전 작업에서 추가된 스케줄링/우선순위 옵션과 이미지 풀 시크릿 설정 방법을 포함합니다.

## 사전 요구사항
- Kubernetes 1.20+
- Helm v3.2+
- 1.9.7 이하 차트에서 최초 마이그레이션 시 `--take-ownership`을 지원하는 Helm 필요 (3.18.2 검증)
- 클러스터에 설치할 네임스페이스 (예: whatap)

## Helm 저장소 추가
```bash
helm repo add whatap https://whatap.github.io/helm/
helm repo update
```

## 설치 개요
Whatap Operator는 CRD(WhatapAgent)를 관리하고, Whatap 에이전트 리소스의 생성/업데이트를 담당합니다. 설치 시 다음 값을 설정할 수 있습니다:
- 이미지 레지스트리 및 태그
- 이미지 풀 시크릿 (private registry)
- Pod 우선순위, 스케줄링 제약 (priorityClassName, nodeName, nodeSelector, tolerations, affinity)
- Whatap 접속 자격(라이선스/호스트/포트) 시크릿 생성 여부

## 빠른 시작 (values 없이 기본 설치)
```bash
# 네임스페이스가 없다면 생성
kubectl create namespace whatap

# 기본값으로 설치 (시크릿은 직접 준비해야 함)
helm install whatap-operator whatap/whatap-operator -n whatap
```

기본 설치의 경우, 오퍼레이터가 사용할 `whatap-credentials` 시크릿을 미리 만들어야 합니다. 아래 ‘자격 시크릿 준비’ 섹션을 참고하세요.

## 자격 시크릿 준비
오퍼레이터는 다음 키를 가진 Secret(`whatap-credentials`)을 사용합니다.
- WHATAP_LICENSE
- WHATAP_HOST
- WHATAP_PORT

### 1) Helm으로 자동 생성
values.yaml에서 `credentials.create: true`로 설정하고 값을 입력하면, 설치 시 시크릿이 자동으로 생성됩니다.

values.yaml 예시:
```yaml
credentials:
  create: true
  license: "<YOUR_LICENSE_KEY>"
  host: "<whatap-server-host>"
  port: 6600
```

설치:
```bash
helm install whatap-operator whatap/whatap-operator -n whatap -f values.yaml
```

### 2) kubectl로 수동 생성
이미 존재하는 인프라 기준으로 수동 생성도 가능합니다.
```bash
kubectl -n whatap create secret generic whatap-credentials \
  --from-literal=WHATAP_LICENSE="<YOUR_LICENSE_KEY>" \
  --from-literal=WHATAP_HOST="<whatap-server-host>" \
  --from-literal=WHATAP_PORT="6600"
```
그 다음 기본 설치를 진행합니다.

## 이미지 및 레지스트리 설정
values.yaml 예시:
```yaml
image:
  repository: public.ecr.aws/whatap/whatap-operator
  tag: 3.0.26
  digest: "" # 선택 사항. 설정 시 repository:tag@digest 형식으로 고정
  pullPolicy: Always

# 프라이빗 레지스트리 사용 시
imagePullSecret:
  name: <your-docker-registry-secret-name>
```

`image.digest`를 비워두면 tag만 사용하고, 값을 지정하면 `repository:tag@digest` 형식으로 이미지를 고정합니다.

Secret이 없다면 다음과 같이 생성할 수 있습니다.
```bash
kubectl -n whatap create secret docker-registry <your-docker-registry-secret-name> \
  --docker-server=<REGISTRY> \
  --docker-username=<USERNAME> \
  --docker-password=<PASSWORD> \
  --docker-email=<EMAIL>
```

## 스케줄링/우선순위 옵션
다음 옵션은 필요할 때만 렌더링되며, 설정하지 않으면 기본값이 적용되지 않습니다(백워드 호환성 유지).
```yaml
priorityClassName: ""   # 예: system-cluster-critical
nodeName: ""            # 특정 노드에 고정 스케줄링이 필요한 경우
nodeSelector: {}         # 예: { kubernetes.io/os: linux }
affinity: {}             # 표준 K8s Affinity 스키마
tolerations: []          # 표준 K8s Toleration 리스트
```
예시:
```yaml
priorityClassName: "high-priority"
nodeSelector:
  nodepool: system

affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: kubernetes.io/os
              operator: In
              values: ["linux"]

tolerations:
  - key: "node-role.kubernetes.io/control-plane"
    effect: NoSchedule
```

## 설치/업그레이드/삭제 명령

신규 설치와 일반 업그레이드는 동일한 명령을 사용할 수 있습니다.

```bash
helm upgrade --install whatap-operator whatap/whatap-operator \
  --namespace whatap \
  --create-namespace \
  -f values.yaml \
  --atomic \
  --wait
```

### 1.9.7 이하에서 최초 업그레이드

1.9.7 이하 차트는 이미 존재하는 ServiceAccount, RBAC, ConfigMap, Service를 `lookup`으로 렌더링에서 제외했습니다. 1.9.8부터 해당 리소스를 Helm manifest에 항상 포함하므로 최초 마이그레이션에서만 기존 리소스의 소유권을 인수합니다.

```bash
helm upgrade --install whatap-operator whatap/whatap-operator \
  --version 1.9.8 \
  --namespace whatap \
  -f values.yaml \
  --take-ownership \
  --atomic \
  --wait
```

이후 업그레이드에서는 `--take-ownership`이 필요하지 않습니다. `--take-ownership`은 기존 리소스가 동일한 Whatap 설치에 속한다는 것을 확인한 경우에만 사용하십시오. 다른 release나 외부 자동화가 관리하는 리소스라면 아래 `managedResources` 옵션으로 해당 그룹을 비활성화해야 합니다. 업그레이드 전에는 `helm get manifest`와 관련 리소스를 백업하십시오.

### 1.9.9 RBAC 변경 안내

1.9.9부터 operator, K8s Agent, OpenAgent의 기본 `nonResourceURLs`는 `["*"]`이며 verbs도 `["*"]`입니다. 이는 kube-apiserver의 모든 non-resource endpoint에 접근할 수 있는 넓은 권한입니다.

OpenAgent는 `WhatapAgent` CR의 `spec.features.openAgent.nonResourceURLs`에 필요한 경로만 명시해 최소 권한으로 좁힐 수 있습니다. 예: `["/metrics", "/healthz"]`. K8s Agent 또는 operator RBAC를 별도 정책으로 관리하려면 `managedResources.rbac: false`를 설정하고 필요한 ClusterRole과 ClusterRoleBinding을 외부에서 모두 제공하십시오.

### 외부 관리 리소스 사용

ServiceAccount, RBAC, agent 시작 스크립트 ConfigMap 또는 master Service를 Helm 외부에서 관리할 때만 해당 `managedResources` 값을 `false`로 설정합니다. 기본값은 모두 `true`이며, 일반 사용자는 변경하지 않습니다.

```yaml
managedResources:
  serviceAccounts: false
  rbac: false
  agentConfigMaps: false
  masterService: false
```

외부 관리로 비활성화한 리소스는 operator 설치 전에 동일한 이름으로 준비해야 합니다.

- 삭제
```bash
helm uninstall whatap-operator -n whatap
```

## DCGM ConfigMap과 메트릭 설정 (차트 1.9.12)

`dcgmExporter.configMap`으로 `dcgm-exporter-csv` ConfigMap의 생성 여부와
`whatap-gpu.csv` 내용을 설정합니다. Operator 이미지나 WhatapAgent CRD 변경은 필요하지 않습니다.
이 옵션을 생략하면 기존과 동일하게 ConfigMap을 생성하고 기본 메트릭 목록도 유지합니다.

### GPU가 없는 클러스터에서 ConfigMap 생성하지 않기

기존 Helm values 파일에 아래 부분을 추가합니다.

```yaml
dcgmExporter:
  configMap:
    enabled: false
```

이 값은 **ConfigMap 생성만** 제어합니다. GPU 노드를 자동으로 탐지하거나
`WhatapAgent` CR의 `spec.features.k8sAgent.gpuMonitoring.enabled`를 변경하지 않습니다.
GPU 수집을 사용하는 설치에서는 `enabled: true`를 유지하거나, 같은 네임스페이스에
`dcgm-exporter-csv` / `whatap-gpu.csv`를 외부에서 제공해야 합니다.

주의: 기존 release가 관리하던 ConfigMap을 `true`에서 `false`로 바꾸면 Helm upgrade가
해당 ConfigMap을 **삭제할 수 있습니다**. GPU 수집 중에 단순히 false로 바꾸지 마십시오.
외부 관리로 전환할 때에는 먼저 소유권 이전과 exporter의 참조를 확인해야 합니다.

### 기본 메트릭을 유지하면서 추가하기

```yaml
dcgmExporter:
  configMap:
    extraMetrics: |
      DCGM_FI_DEV_APP_SM_CLOCK, gauge, Application SM clock frequency (in MHz).
      DCGM_FI_DEV_APP_MEM_CLOCK, gauge, Application memory clock frequency (in MHz).
```

기본 CSV 뒤에 지정한 행을 추가합니다. 한 줄은 `DCGM 필드명, 타입, 설명` 형식이며,
이미 활성화된 필드를 다시 추가하지 마십시오. 필드 지원 여부는 exporter 버전과 GPU에 따라 다릅니다.

### 기본 목록 전체를 교체하기

```yaml
dcgmExporter:
  configMap:
    customMetrics: |
      DCGM_FI_DEV_GPU_UTIL, gauge, GPU utilization (in %).
      DCGM_FI_DEV_FB_USED, gauge, Used framebuffer memory (in MiB).
    extraMetrics: ""
```

이 예시는 두 메트릭만 남기는 최소 예시입니다. 제외한 기본 메트릭을 사용하는 GPU 화면과
알림은 데이터가 나오지 않을 수 있습니다. 필요한 지표와 label을 확인한 후 사용하십시오.

- `customMetrics` 미설정/빈 문자열/공백만 입력: 기존 기본 목록 사용.
- `customMetrics`와 `extraMetrics`를 모두 설정: 사용자 목록 뒤에 추가 목록을 붙임.
- 설정값은 Helm 템플릿으로 실행하지 않고 CSV 문자열 그대로 사용.
- 기본 목록으로 복구: 두 문자열을 `""`로 비우고 다시 적용.
- `enabled`는 따옴표 없는 `true`/`false`, 메트릭은 위처럼 YAML 블록 문자열 사용.

### 적용 후 확인

1. 실제 release 이름과 namespace를 확인하고 현재 values/manifest를 안전한 경로에 백업합니다.
   values에는 인증정보가 포함될 수 있으므로 출력·공유하지 마십시오.
2. 로컬 차트 또는 게시가 확인된 차트 버전으로 `helm template`을 먼저 실행해 ConfigMap을 확인합니다.
   현재 운영 values는 유지하고 위 설정 부분만 병합해 Helm upgrade를 진행합니다.
3. `dcgm-exporter-csv`의 `data.whatap-gpu.csv`가 의도한 목록인지 확인합니다.
4. CSV는 `subPath`로 마운트되므로 ConfigMap 수정만으로 실행 중 exporter에 반영되지 않습니다.
   작업 시간에 **dcgm-exporter 컨테이너가 있는 실제 DaemonSet**을 확인한 뒤 롤링 재시작하고
   rollout 완료를 확인합니다. Operator Pod만 재시작하는 것으로 대체하지 마십시오.
5. exporter 로그의 CSV/필드 오류, `/metrics`의 추가 지표, 와탭 화면의 기존·추가 지표를 확인합니다.

## CRD
차트는 `WhatapAgent` CRD를 포함하여 설치합니다. Helm이 CRD를 설치/관리하며, 오퍼레이터가 해당 리소스를 감시합니다.

### 1.9.15: Operator 3.0.26과 APM 자동 주입 진단

차트 `1.9.15`의 기본 이미지는 Operator `3.0.26`입니다. **values와 템플릿 구조는 1.9.12와 같고, CRD는 1.9.14와 같습니다.**
바뀐 파일은 `Chart.yaml`(차트 버전과 `appVersion`)과 `values.yaml`(`image.tag` 기본값)뿐입니다.

Operator 3.0.26은 kube-apiserver가 APM 자동 주입 웹훅을 호출하지 못하는 상황을 기록합니다. 이때 Pod는 APM 없이 생성되고, 오류는 kube-apiserver 로그에만 남았습니다.

- Operator가 5분마다 dry-run으로 웹훅 호출을 점검합니다. 연속 2회 실패하면 kube-apiserver가 돌려준 오류(예: 프록시가 TLS를 가로채 생긴 x509 오류)를 WhatapAgent 이벤트 `APMInjectionWebhookUnreachable`과 Operator 로그에 남깁니다. 복구되면 `APMInjectionWebhookRecovered` 이벤트를 남깁니다.
- APM 대상인데 웹훅을 거치지 않고 생성된 Pod에는 `APMInjectionMissing` 경고 이벤트를 남깁니다. 원인을 고친 뒤 해당 Pod를 재시작해야 APM이 주입됩니다.
- Operator가 만드는 MutatingWebhookConfiguration `whatap-webhook`에 점검용 항목 `apm-probe.monitoring.whatap.com`이 추가됩니다. `monitoring.whatap.com/apm-webhook-probe` 라벨이 있는 Pod에만 적용되므로 애플리케이션 Pod에는 영향이 없습니다.

```bash
kubectl describe whatapagent whatap
kubectl get events -A --field-selector reason=APMInjectionMissing
```

`managedResources.rbac: false`로 RBAC를 직접 관리한다면 Operator ServiceAccount에 아래 권한을 추가하십시오.
Pod `create` 권한이 없으면 웹훅 호출 점검만 건너뛰고 로그를 남깁니다.

- Pod: `create` (dry-run 점검)
- Namespace: `get`, `list`, `watch`

```bash
helm repo update
helm upgrade whatap-operator whatap/whatap-operator \
  --namespace whatap --version 1.9.15 --reuse-values \
  --set-string image.tag=3.0.26 --set-string image.digest= \
  --atomic --wait
```

`--reuse-values`를 쓰면 이전 이미지 태그가 남으므로 위처럼 태그를 명시합니다. release/namespace는 실제 설치 이름으로 바꾸십시오.

### 1.9.14: Operator 3.0.25와 `agentVersion` 기본값 변경

차트 `1.9.14`의 기본 이미지는 Operator `3.0.25`입니다. **values와 템플릿 구조는 1.9.12와 같습니다.**
바뀐 파일은 다음 세 가지뿐입니다.

- `Chart.yaml`: 차트 버전과 `appVersion`
- `values.yaml`: `image.tag` 기본값
- `templates/crd-whatapagents.yaml`: `spec.features.kubeVirt.targets[].agentVersion`의 `default: 2.9.25`를 지우고 설명을 바꿨습니다. 다른 필드는 바뀌지 않았습니다.

Operator 3.0.25에서 바뀐 KubeVirt 동작은 다음과 같습니다.

- VM을 지우면 그 VM용 cloud-init Secret(`whatap-kv-*`)을 Operator가 5~10분 안에 지웁니다. 3.0.24 이하에서 남은 Secret도 함께 정리됩니다.
- `agentVersion`을 생략하면 VM을 만들 때 Operator 기본 버전(3.0.25 기준 2.9.25)을 씁니다. Operator를 올리면 생략한 대상은 새 기본 버전을 따릅니다.
  1.9.13 CRD로 만든 CR에는 `agentVersion: 2.9.25`가 저장돼 있습니다. Operator 기본 버전을 따르게 하려면 `kubectl edit whatapagent whatap`으로 해당 줄을 지우십시오.

`managedResources.rbac: false`로 RBAC를 직접 관리한다면 Operator ServiceAccount에 아래 권한을 추가하십시오.
Secret `list` 권한이 없으면 `kubeVirt`를 쓰지 않아도 정리 점검 실패 로그가 1시간에 한 번 남습니다. 다른 동작에는 영향이 없습니다.

- Secret: `create`, `get`, `patch`, `list`, `delete`
- `kubevirt.io`의 `virtualmachines`, `virtualmachineinstances`: `list`

```bash
helm repo update
helm upgrade whatap-operator whatap/whatap-operator \
  --namespace whatap --version 1.9.14 --reuse-values \
  --set-string image.tag=3.0.25 --set-string image.digest= \
  --atomic --wait
```

`--reuse-values`를 쓰면 이전 이미지 태그가 남으므로 위처럼 태그를 명시합니다. release/namespace는 실제 설치 이름으로 바꾸십시오.

### 1.9.13: Operator 3.0.24와 CRD 필드 추가

차트 `1.9.13`의 기본 이미지는 Operator `3.0.24`입니다. **values와 템플릿 구조는 1.9.12와 같습니다.**
바뀐 파일은 다음 세 가지뿐입니다.

- `Chart.yaml`: 차트 버전과 `appVersion`
- `values.yaml`: `image.tag` 기본값
- `templates/crd-whatapagents.yaml`: 필드 추가만 있습니다. 기존 필드의 삭제나 변경은 없습니다.

차트를 내려받아 직접 수정해 사용한다면 기존 수정분은 그대로 두고 위 이미지 태그와 CRD 파일만 반영하면 됩니다.

CRD에 추가된 `WhatapAgent` 필드는 다음과 같습니다.

- `spec.features.kubeVirt`: 라벨을 붙여 새로 만드는 KubeVirt VM에 첫 부팅 때 서버 에이전트를 자동 설치합니다.
  동작 방식은 [whatap-operator 문서](https://github.com/whatap/whatap-operator/blob/master/docs/kubevirt-server-agent.md),
  설정 예시는 [whatap-operator 예제](https://github.com/whatap/whatap-operator/blob/master/examples/kubevirt-server-agent.yaml)를 참고하십시오.
- `spec.features.networkAgent`: 네트워크 수집기 DaemonSet 관리
- Operator가 이미 지원하지만 1.9.12 이하 차트 CRD에 빠져 있던 필드
  - `apm.instrumentation.targets[].config`의 `mountPath`, `pluginConfigMapRef`, `volumeName`
  - `k8sAgent.gpuMonitoring`의 `relabelConfigs[]`, `metricRelabelConfigs[]`에 있는 `sourceLabels`, `targetLabel`
  - `openAgent.targets[]`의 `relabelConfigs[]`, `endpoints[].metricRelabelConfigs[]`에 있는 `sourceLabels`, `targetLabel`
  - `openAgent.targets[].endpoints[].authorization`

새 기능은 CR에서 켜야 동작하며 기본값은 꺼져 있습니다. 기존 CR은 수정 없이 그대로 동작합니다.
1.9.12 이하 CRD에서는 위 필드가 스키마에 없어 저장할 때 제거되었습니다. 이 필드를 쓰려면 CRD를 업그레이드한 뒤 CR을 다시 적용하십시오.
`managedResources.rbac: false`로 RBAC를 직접 관리하는 경우, 새 기능을 켜지 않으면 추가 권한이 필요 없습니다. `kubeVirt`를 켤 때는
Operator ServiceAccount에 Secret `create`, `get` 권한을 추가하십시오. VM 네임스페이스에 cloud-init Secret을 만들고 읽기 때문입니다.

```bash
helm repo update
helm upgrade whatap-operator whatap/whatap-operator \
  --namespace whatap --version 1.9.13 --reuse-values \
  --set-string image.tag=3.0.24 --set-string image.digest= \
  --atomic --wait
kubectl explain whatapagent.spec.features.kubeVirt
```

`--reuse-values`를 쓰면 이전 이미지 태그가 남으므로 위처럼 태그를 명시합니다. release/namespace는 실제 설치 이름으로 바꾸십시오.
Operator 3.0.21~3.0.23의 APM 자동 계측 수정(Python custom 연결 환경변수·자동 로딩 경로 보존, Node.js `NODE_OPTIONS`/`NODE_PATH` 보존)도 함께 적용됩니다.
이 수정은 새로 만들어지거나 재시작되는 Pod부터 반영됩니다.

### 1.9.11: GPU pod-resources 호스트 경로 설정

Operator `3.0.20`과 차트 `1.9.11`부터 기존 `WhatapAgent` CR의
`spec.features.k8sAgent.gpuMonitoring.podResourcesPath`를 설정할 수 있습니다.
이 값은 Helm values가 아닌 **WhatapAgent CR 설정**입니다. 이미지와 CRD를 함께 업그레이드해야 하며,
`--reuse-values`로 이전 이미지 태그 또는 digest가 남지 않도록 명시합니다.

```bash
helm repo update
helm upgrade whatap-operator whatap/whatap-operator \
  --namespace whatap --version 1.9.11 --reuse-values \
  --set-string image.tag=3.0.20 --set-string image.digest= \
  --atomic --wait
kubectl explain whatapagent.spec.features.k8sAgent.gpuMonitoring.podResourcesPath
```

위 release/namespace는 실제 설치 이름으로 바꾸십시오. private registry는 같은 버전의 이미지를 먼저 준비하고,
digest 고정이 필요하면 빈 값 대신 **새 이미지의 digest**를 지정하십시오. 1.9.7 이하 설치는 위의 최초 마이그레이션 절차도 따릅니다.

GPU 노드에서 `/repo.p/kubelet/pod-resources/kubelet.sock`이 존재하는 것을 확인한 경우,
기존 CR의 설정에 아래 부분만 병합합니다(전체 설치용 CR이 아닙니다).

```yaml
spec:
  features:
    k8sAgent:
      gpuMonitoring:
        enabled: true
        podResourcesPath: /repo.p/kubelet/pod-resources
```

- 소켓 파일이나 kubelet 루트가 아닌 **pod-resources 디렉터리의 절대 경로**를 지정합니다.
- 미설정/빈 문자열이면 기존 `/var/lib/kubelet/pod-resources`를 사용합니다.
- 호스트 볼륨만 바뀌며 exporter 내부 마운트는 `/var/lib/kubelet/pod-resources`(읽기 전용)로 유지됩니다.
- 공통/GPU 전용 DaemonSet 모두 적용됩니다. 경로 변경은 해당 Pod의 롤링 업데이트를 유발하므로 노드별 경로와 권한을 먼저 확인하십시오.
- 적용 후 CR 값, DaemonSet의 `pod-gpu-resources` hostPath, exporter 로그와 GPU/Pod 매핑 지표를 확인하십시오.

## 값 목록 요약
현재 차트에서 사용하는 주요 값은 다음과 같습니다. (charts/whatap-operator/values.yaml 참조)
```yaml
namespace: ""
managedResources:
  serviceAccounts: true
  rbac: true
  agentConfigMaps: true
  masterService: true

image:
  repository: public.ecr.aws/whatap/whatap-operator
  tag: 3.0.26
  digest: ""
  pullPolicy: Always

imagePullSecret:
  name: # <registry secret name>

priorityClassName: ""
nodeName: ""
nodeSelector: {}
affinity: {}
tolerations: []

credentials:
  create: false
  # Secret name is fixed to 'whatap-credentials'
  license: ""
  host: ""
  port: 6600
```

## 트러블슈팅
- 오퍼레이터 Pod가 ImagePullBackOff 상태
  - private registry 사용 시 `imagePullSecret.name` 설정을 확인하세요.
- 시크릿 누락으로 CrashLoopBackOff
  - `credentials.create: true`로 자동 생성하거나, `whatap-credentials` 시크릿이 네임스페이스에 존재하는지 확인하세요.
- 스케줄링 불가 (Pending)
  - nodeSelector/affinity/tolerations 설정이 클러스터 상태와 맞는지 확인하세요.

## 라이선스
이 저장소의 라이선스 정책을 따릅니다.
