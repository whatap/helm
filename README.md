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
helm install whatap/kube -f custom-values.yaml --namespace whatap-monitoring --create-namespace whatap-agent
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
    └── whatap-kube-agent-*.tgz
```

