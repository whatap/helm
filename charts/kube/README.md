## whatap-kube-helm

## 차트 구조도
charts/
└── kube/
└── templates/
├── clusterrole.yaml
├── clusterrolebinding.yaml
├── configmap-master.yaml
├── configmap-node.yaml
├── daemonsets.yaml
├── deployment.yaml
├── namespace.yaml
├── service.yaml
└── serviceaccount.yaml

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

