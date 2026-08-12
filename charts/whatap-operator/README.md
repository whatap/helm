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
  tag: 3.0.15
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

## CRD
차트는 `WhatapAgent` CRD를 포함하여 설치합니다. Helm이 CRD를 설치/관리하며, 오퍼레이터가 해당 리소스를 감시합니다.

## nonResourceURLs 권한 설정
OpenAgent가 kube-apiserver 자체의 비리소스 경로(`/metrics`, `/metrics/slis` 등)를 스크랩해야 하는 경우, `WhatapAgent` CR에서 부여할 경로를 지정할 수 있습니다.

```yaml
spec:
  features:
    openAgent:
      nonResourceURLs: ["/metrics", "/metrics/slis"]   # 생략 시 ["/metrics"]
```

이때 오퍼레이터 자신의 ClusterRole이 해당 경로의 상위집합을 보유해야 합니다. 쿠버네티스 RBAC은 자신이 갖지 않은 권한을 위임하는 것을 차단하기 때문입니다(escalation prevention). 오퍼레이터 권한은 아래 값으로 조절합니다.

```yaml
rbac:
  operator:
    nonResourceURLs: ["*"]      # 기본값. ["/metrics"] 등으로 축소 가능
```

두 값이 어긋나면 오퍼레이터가 OpenAgent용 ClusterRole 생성에 실패하고, `WhatapAgent` 리소스의 `status.conditions`에 부족한 경로가 표시됩니다.

> 이 설정은 **접근 권한**이며 수집 대상과는 별개입니다. 수집할 대상과 경로는 `targets` / `endpoints[].path`에서 지정합니다. 애플리케이션 Pod 메트릭 수집에는 이 권한이 필요하지 않습니다.

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
  tag: 3.0.15
  digest: ""
  pullPolicy: Always

imagePullSecret:
  name: # <registry secret name>

priorityClassName: ""
nodeName: ""
nodeSelector: {}
affinity: {}
tolerations: []

rbac:
  operator:
    nonResourceURLs: ["*"]

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
