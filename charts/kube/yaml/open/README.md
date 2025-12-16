# Whatap Open Agent 단독 배포 매뉴얼

이 디렉터리에는 Helm 없이 Open Agent를 배포할 수 있는 기본 YAML(`open-agent.yaml`)과 사용 방법이 포함되어 있습니다.

## 포함 리소스
- (옵션) Namespace: `whatap-monitoring`
- Secret: `whatap-credentials` (WHATAP_LICENSE/WHATAP_HOST/WHATAP_PORT)
- ServiceAccount: `whatap-open-agent-sa`
- ClusterRole/ClusterRoleBinding: `whatap-open-agent-role` / `whatap-open-agent-role-binding`
- ConfigMap: `whatap-open-agent-config` (scrape_config.yaml 포함)
- Deployment: `whatap-open-agent`

## 사용 방법
1) YAML 준비
   - `open-agent.yaml`을 열어 다음을 환경에 맞게 수정합니다.
     - `Namespace` 이름(기본: `whatap-monitoring`). 이미 존재하는 네임스페이스를 쓰려면 Namespace 리소스 블록을 삭제하거나 이름을 변경하세요.
     - Secret `whatap-credentials`의 `WHATAP_LICENSE`, `WHATAP_HOST`, `WHATAP_PORT` 값을 실제 값으로 입력합니다.
       - 이미 동일한 이름의 Secret을 갖고 있다면 `open-agent.yaml`의 Secret 리소스 블록을 삭제하고, Deployment의 `secretKeyRef.name`을 기존 시크릿 이름과 동일하게 두면 됩니다.
     - ConfigMap `scrape_config.yaml` 내 `targets`를 수집 대상에 맞게 조정합니다.
       - 기본은 kube-apiserver 수집(ServiceMonitor 방식, namespaceSelector/selector/endpoint를 환경에 맞게 변경).
       - TLS 검증을 켜려면 `tlsConfig.insecureSkipVerify: false`로 두고 필요한 경우 CA/클라이언트 인증서를 추가하십시오.

2) 배포
   ```bash
   # 네임스페이스를 변경했다면 -n <NAMESPACE> 로 맞춰 주세요.
   kubectl apply -f open-agent.yaml
   ```

3) 확인
   ```bash
   kubectl get pods -n whatap-monitoring -l name=whatap-open-agent
   kubectl logs -n whatap-monitoring deploy/whatap-open-agent -c whatap-open-agent --tail=100
   ```

## 추가 커스터마이징 힌트
- 리소스/레플리카: Deployment의 `replicas`, `resources`를 조정하세요.
- 네트워크: 필요 시 `tolerations`, `affinity`, `nodeSelector`를 Deployment spec에 추가할 수 있습니다.
- 추가 타겟: ConfigMap `targets` 배열에 `PodMonitor`, `ServiceMonitor`, `StaticEndpoints` 예시를 open.md의 가이드대로 확장 가능합니다.
- 이미지 태그: `public.ecr.aws/whatap/open_agent:<tag>`로 변경 가능합니다.