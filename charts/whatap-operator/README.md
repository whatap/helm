# Whatap Operator Helm Chart - Usage Guide

이 문서는 Whatap Operator Helm 차트를 설치하고 구성하는 방법을 설명합니다. 이전 작업에서 추가된 스케줄링/우선순위 옵션과 이미지 풀 시크릿 설정 방법을 포함합니다.

## 사전 요구사항
- Kubernetes 1.20+
- Helm v3.2+
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
  tag: latest
  pullPolicy: Always

# 프라이빗 레지스트리 사용 시
imagePullSecret:
  name: <your-docker-registry-secret-name>
```
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
- 설치
```bash
helm install whatap-operator whatap/whatap-operator -n whatap -f values.yaml
```
- 업그레이드
```bash
helm upgrade whatap-operator whatap/whatap-operator -n whatap -f values.yaml
```
- 삭제
```bash
helm uninstall whatap-operator -n whatap
```

## CRD
차트는 `WhatapAgent` CRD를 포함하여 설치합니다. Helm이 CRD를 설치/관리하며, 오퍼레이터가 해당 리소스를 감시합니다.

## 값 목록 요약
현재 차트에서 사용하는 주요 값은 다음과 같습니다. (charts/whatap-operator/values.yaml 참조)
```yaml
namespace: ""
image:
  repository: public.ecr.aws/whatap/whatap-operator
  tag: latest
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
