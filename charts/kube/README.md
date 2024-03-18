## whatap-kube-helm

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
    └── whatap-kube-agent-1.5.7.tgz
```


### 파일 설명

- **clusterrole.yaml**: 클러스터 역할 정의
- **clusterrolebinding.yaml**: 클러스터 역할 바인딩
- **configmap-master.yaml**: 마스터 노드의 설정을 포함하는 ConfigMap
- **configmap-node.yaml**: 워커 노드의 설정을 포함하는 ConfigMap
- **daemonsets.yaml**: whatap-node-agent
- **deployment.yaml**: whatap-master-agent 
- **namespace.yaml**: 네임스페이스를 정의
- **service.yaml**: 서비스를 정의
- **serviceaccount.yaml**: 서비스 계정을 정의

## 증명
helm lint .

helm install <release-name> . --dry-run --debug
(ex: helm install whatap-kube-agent . --dry-run --debug)

## Helm 으로 agent 설치 
helm install <release-name> .

## chart update
helm upgrade <release-name> .

## chart repo - githubPages
helm repo add whatap-kube https://whatap.github.io/whatap-kube-helm/charts/whatap-kube-agent/

