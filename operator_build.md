# Operator Helm 차트 빌드 및 배포 가이드

## 개요
Operator는 `whatapagent` CR을 reconcile 합니다. `whatapagent` CR을 사용하기 위해서는 CRD를 먼저 생성해야 하며, 이 CRD는 Operator가 Helm으로 설치될 때 함께 생성됩니다.

## 1. CRD 생성 및 업데이트
`whatapagents` CRD 구조는 Operator 프로젝트에서 관리하며 (`whatap-operator/api/v2alpha1/whatapagent_types.go`), `whatap-operator` 프로젝트에서 아래 명령어를 통해 생성할 수 있습니다.

```bash
make generate
make manifests
```

위 작업이 완료되면 CRD 파일이 생성됩니다 (`whatap-operator/config/crd/bases/monitoring.whatap.com_whatapagents.yaml`).
생성된 YAML 파일을 아래 경로로 복사해야 합니다.
- **원본**: `whatap-operator/config/crd/bases/monitoring.whatap.com_whatapagents.yaml`
- **대상**: `whatap-operator/templates/crd-whatapagents.yaml`

## 2. Helm 차트 패키징 및 배포
`/kubeHelm/charts/whatap-operator/Chart.yaml` 파일의 `version`을 변경한 후, 아래 작업을 수행하면 업데이트된 버전으로 Helm 차트가 배포됩니다.

```shell
# 차트 패키징
helm package charts/whatap-operator

# 인덱스 업데이트
helm repo index --url https://whatap.github.io/helm/ --merge index.yaml .

# Git 배포
git add .
git commit -m "update operator helm chart"
git push
```
