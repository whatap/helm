# kube-agent Helm Chart 배포 및 설치 가이드

## chart 설치

1. 와탭 Helm 레포지터리 추가
helm repo add whatap https://whatap.github.io/helm/
helm repo update

2. custom-values.yaml 파일 생성, 와탭 설치에 필요한 기본 설정
```yaml
containerRuntime= #docker, containerd, crio 중 선택 kubectl get nodes -o wide 명령어 CONTAINER-RUNTIME 의 값 참고
whatap.license= # WHATAP-LICNESE-KEY
whatap.host= # WHATAP-SERVER-HOST
whatap.port= # WHATAP-PORT
```
```yaml
## 예제 custom-value.yaml
containerRuntime: "docker" #docker, containerd, crio 중 선택 kubectl get nodes -o wide 명령어 CONTAINER-RUNTIME 의 값 참고
whatap:
  license: "x423h2197u810-x1jh0prkj2ofme-z2v3cc6u6r6fjk"
  host: "15.165.146.117"
  port: "6600"
```

3. 에이전트 어플리케이션 설치
```shell
helm install <release-name> whatap/kube -f custom-values.yaml
(ex: helm install whatap-kube-agent whatap/kube -f custom-values.yaml)
```

--- 

## 배포

### 1. 차트 검사- 차트 형식, 문법 사전테스트
```shell
helm lint charts/kube
```

> ==> Linting .
1 chart(s) linted, 0 chart(s) failed

### 2. 차트 디버깅- 실제 어플리케이션 배포시 문제 발생 여부 체크
```shell
helm install <release-name> charts/kube --dry-run --debug
```
(ex: helm install whatap-kube-agent charts/kube --dry-run --debug)

### 3. 차트 패키징
```shell
helm package charts/kube/
```

### 3.현재 디렉토리에 있는 Helm 차트로부터 인덱스 파일 생성
```shell
helm repo index --url https://whatap.github.io/helm/ .
```
---
## 추가 옵션 설정
# Whatap 모니터링 구성 가이드

와탭 쿠버네티스 에이전트를 설정하기 위한 `values.yaml` 파일 설정 항목입니다.

### 주요 설정 항목
`values.yaml` 파일에서 사용자가 수정할 수 있는 주요 설정 항목 
Whatap, 컨테이너 런타임 선택, 에이전트 배포를 위한 `daemonSet`,`deployment`에 대한 옵션 설명

| Key | Type | Default Value | Description |
|-----|------|---------------|-------------|
| `whatap.license` | String | `# <license-key>` | Whatap 모니터링을 위한 라이선스 키입니다. |
| `whatap.host` | String | `# <whatap-server-host>` | Whatap 서버의 호스트 주소입니다. |
| `whatap.port` | Int | `# <whatap-server-port>` | Whatap 서버의 포트 번호입니다. |
| `containerRuntime` | String | `"docker"` | 사용 중인 컨테이너 런타임. `"docker"`, `"containerd"`, `"crio"` 중 선택. |
| `daemonSet.name` | String | `whatap-node-agent` | DaemonSet의 이름. |
| `daemonSet.label` | String | `whatap-node-agent` | DaemonSet에 지정할 라벨. |
| `daemonSet.initContainers.nodeDebugger.enabled` | Bool | `true` | Whatap 노드 디버거 초기 컨테이너 활성화 여부. |
| `daemonSet.containers.nodeHelper.image` | String | `whatap/kube_mon` | nodeHelper 컨테이너의 이미지. |
| `daemonSet.containers.nodeHelper.requests.memory` | String | `100Mi` | nodeHelper 메모리 요청량. |
| `daemonSet.containers.nodeHelper.requests.cpu` | String | `100m` | nodeHelper CPU 요청량. |
| `daemonSet.containers.nodeHelper.limits.memory` | String | `350Mi` | nodeHelper 메모리 제한량. |
| `daemonSet.containers.nodeHelper.limits.cpu` | String | `200m` | nodeHelper CPU 제한량. |
| `daemonSet.containers.nodeAgent.image` | String | `whatap/kube_mon` | nodeAgent 컨테이너의 이미지. |
| `daemonSet.containers.nodeAgent.requests.memory` | String | `300Mi` | nodeAgent 메모리 요청량. |
| `daemonSet.containers.nodeAgent.requests.cpu` | String | `100m` | nodeAgent CPU 요청량. |
| `daemonSet.containers.nodeAgent.limits.memory` | String | `350Mi` | nodeAgent 메모리 제한량. |
| `daemonSet.containers.nodeAgent.limits.cpu` | String | `200m` | nodeAgent CPU 제한량. |
| `namespace.name` | String | `whatap-monitoring` | Whatap 모니터링을 위한 네임스페이스 이름. |
| `serviceAccount.name` | String | `whatap` | Whatap 모니터링을 위한 서비스 계정 이름. |

## 구성 예시

여기서는 `values.yaml` 파일 내에서 몇 가지 핵심 구성을 수정하는 방법을 보여줍니다.

### Whatap 기본 설정

```yaml
whatap:
  license: "여기에 라이선스 키를 입력하세요"
  host: "whatap-server.example.com"
  port: 12345


--- 
## 차트 구조
```
└── kube
    ├── Chart.yaml
    ├── README.md
    ├── index.yaml
    ├── templates
    │   ├── clusterrole.yaml
    │   ├── clusterrolebinding.yaml
    │   ├── configmap-master.yaml
    │   ├── configmap-node.yaml
    │   ├── daemonset.yaml
    │   ├── deployment.yaml
    │   ├── namespace.yaml
    │   ├── service.yaml
    │   └── serviceaccount.yaml
    ├── values.yaml
    └── kube-*.tgz
```