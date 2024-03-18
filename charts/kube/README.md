# kube-agent Helm Chart 배포 및 설치 가이드

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
## chart 설치

1. 와탭 Helm 레포지터리 추가
helm repo add whatap https://repo.whatap.io/helm
helm repo update

2. values.yaml 파일 생성, 와탭 설치에 필요한 기본 설정
```yaml
containerRuntime= #docker, containerd, crio 중 선택 kubectl get nodes -o wide 명령어 CONTAINER-RUNTIME 의 값 참고
whatap.license= # WHATAP-LICNESE-KEY
whatap.host= # WHATAP-SERVER-HOST
whatap.port= # WHATAP-PORT
```

helm install whatap-agent \
-f charts/kube/values.yaml \
--namespace whatap-monitoring --create-namespace \
--set whatap.port=$whatap_port \



## 배포
WORK_DIR = {PROJECT_}/charts/kube

### 1. 차트 검사- 차트 형식, 문법 사전테스트
```shell
helm lint .
```

> ==> Linting .
1 chart(s) linted, 0 chart(s) failed

### 2. 차트 디버깅- 실제 어플리케이션 배포시 문제 발생 여부 체크
```shell
helm install <release-name> . --dry-run --debug
```
(ex: helm install whatap-kube-agent . --dry-run --debug)

### 3. 차트 패키징
```shell
helm package .
```

### 3.현재 디렉토리에 있는 Helm 차트로부터 인덱스 파일 생성
```shell
helm repo index .
```

### 4. 인덱스 파일 repo 업데이트
```shell
tsh aws s3 cp ./index.yaml s3://repo.whatap.io/helm/index.yaml --acl public-read
tsh aws s3 cp ./whatap-kube-agent-0.0.2.tgz s3://repo.whatap.io/helm/whatap-kube-agent-0.0.2.tgz
```



