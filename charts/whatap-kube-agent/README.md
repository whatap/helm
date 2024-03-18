## HELM 

## 증명
helm lint .

helm install <release-name> . --dry-run --debug
(ex: helm install whatap-kube-agent . --dry-run --debug)

## Helm 으로 agent 설치 
helm install <release-name> .

## chart update
helm upgrade <release-name> .