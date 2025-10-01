이 가이드는 쿠버네티스 환경에 와탭 오퍼레이터를 설치하고, `WhatapAgent` CR을 설정하여 와탭 모니터링을 시작하는 방법을 설명합니다.

### **설치 전 요구 사항**

- 쿠버네티스 클러스터 (v1.19+)
- Helm 3.2 이상
- 와탭 계정 및 라이선스 키

## **설치 방법**

다음 단계에 따라 와탭 오퍼레이터를 설치하고 `WhatapAgent` CR을 생성합니다.

폐쇄망인 경우는 해당 가이드를 참고합니다.

[  **Whatap Operator 폐쇄망 설치 가이드 (yaml)**](https://www.notion.so/Whatap-Operator-yaml-22520702704a80d5b153e88d226b431d?pvs=21)

### 1. 와탭 operator 를 설치합니다.

- 에이전트를 처음 설치하는 사용자는 다음 명령어를 실행해 주세요

    ```bash
    helm repo add whatap https://whatap.github.io/helm/
    helm repo update
    ```


```bash
kubectl create ns whatap-monitoring
export WHATAP_HOST=<수집서버 IP>
export WHATAP_LICENSE=<와탭 라이센스>
export WHATAP_PORT=<와탭 포트>
kubectl create secret generic whatap-credentials --namespace whatap-monitoring --from-literal WHATAP_LICENSE=$WHATAP_LICENSE --from-literal WHATAP_HOST=$WHATAP_HOST --from-literal WHATAP_PORT=$WHATAP_PORT
helm install whatap-operator whatap/whatap-operator --namespace whatap-monitoring
```

혹은 아래와 같이 helm install 명령어로 namespace 와 secret 을 함께 생성할 수 있습니다.

```bash
helm upgrade --install whatap-operator whatap/whatap-operator \
  -n whatap-monitoring --create-namespace \
  --set credentials.create=true \
  --set credentials.license=$WHATAP_LICENSE \
  --set credentials.host=$WHATAP_HOST \
  --set credentials.port=$WHATAP_PORT
```

#### 고급 설정: 이미지 레지스트리 및 Pull Secret

프라이빗 레지스트리를 사용하거나 이미지 태그/풀 정책을 조정해야 하는 경우 values.yaml에서 다음 값을 설정합니다.

```yaml
image:
  repository: public.ecr.aws/whatap/whatap-operator
  tag: latest
  pullPolicy: Always

# 프라이빗 레지스트리 사용 시 설정
imagePullSecret:
  name: <your-docker-registry-secret-name>
```

imagePullSecret이 없다면 다음과 같이 생성할 수 있습니다.
```bash
kubectl -n whatap-monitoring create secret docker-registry <your-docker-registry-secret-name> \
  --docker-server=<REGISTRY> \
  --docker-username=<USERNAME> \
  --docker-password=<PASSWORD> \
  --docker-email=<EMAIL>
```

#### 스케줄링/우선순위 옵션

오퍼레이터 파드의 스케줄링 제약과 우선순위를 제어할 수 있습니다. 값을 지정한 경우에만 템플릿에 렌더링되어 기존 사용자와의 호환성이 유지됩니다.

```yaml
priorityClassName: ""   # 예: system-cluster-critical
nodeName: ""            # 특정 노드 고정 스케줄링이 필요한 경우
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

업그레이드/삭제 명령어:
```bash
# 업그레이드
helm upgrade whatap-operator whatap/whatap-operator -n whatap-monitoring -f values.yaml
# 삭제
helm uninstall whatap-operator -n whatap-monitoring
```

-
- 기존 와탭 쿠버네티스 에이전트 사용자는 다음 명령어를 실행해 에이전트를 설치합니다.

    ```yaml
    kubectl delete ns whatap-monitoring
    kubectl delete clusterrole whatap
    kubectl delete clusterrolebinding whatap
    kubectl create ns whatap-monitoring
    kubectl create secret generic whatap-credentials --namespace whatap-monitoring --from-literal license=$WHATAP_LICENSE --from-literal host=$WHATAP_HOST --from-literal port=$WHATAP_PORT
    helm install whatap-operator whatap/whatap-operator --namespace whatap-monitoring
    ```

    <aside>
    💡

    1. 기존 *yaml* 파일 혹은 helm 방식으로 와탭 쿠버네티스 에이전트를 설치한 경우 Clean Install이 필요합니다. 기존 쿠버네티스 에이전트 삭제 후 Operator 사용을 권장합니다.
    </aside>


- 오퍼레이터는 deployment 로 배포됩니다. 아래의 명령어로 operator 가 정상적으로 배포됐는지 확인합니다.

    ```bash
    kubectl get pods -n whatap-monitoring | grep -i operator
    ```

    - 명령어 실행 결과, `whatap-operator` 파드가 **Running** 상태여야 합니다.

      ![image.png](attachment:16ef86ec-4ad9-4bd2-93d3-efec70952e7c:image.png)


### **2. WhatapAgent CR 생성**

아래의 명령어로 whatapAgent 커스텀 리소스를 생성합니다.

```yaml
kubectl apply -f values.yaml
```

`WhatapAgent` CR은 와탭 에이전트의 배포와 구성을 정의합니다. K8s 에이전트, APM 자동 설치 , 그리고 Open Agent를 통한 오픈메트릭 수집을 설정할 수 있습니다.

### 최소 구성

기본 Kubernetes 모니터링을 위해 Whatap 마스터 에이전트와 노드 에이전트를 활성화하는 최소 구성입니다.

```yaml
apiVersion: monitoring.whatap.com/v2alpha1
kind: WhatapAgent
metadata:
  name: whatap
spec:
  features:
    k8sAgent:
      masterAgent:
        enabled: true
      nodeAgent:
        enabled: true
      gpuMonitoring:
        enabled: false
    openAgent:
      enabled: true 
```

최소 구성으로 설치하게 되면 아래와 같이 whatap-master-agent, whatap-node-agent 가 추가로 설치됩니다.

![image.png](attachment:907f7d53-b3d6-4236-b860-047a1b536a88:image.png)

쿠버네티스 에이전트 설정(자원제약, tolerlation, imagePullSecret)에 대한 자세한 내용은 해당 페이지를 참고해 주세요

[오퍼레이터 k8s 설치시 설정 옵션](https://www.notion.so/k8s-26820702704a80d2bfcfdf61c6ac9e6f?pvs=21)

### **기본 구성**

```yaml

apiVersion: monitoring.whatap.com/v2alpha1
kind: WhatapAgent
metadata:
  name: whatap
spec:
  features:
    ### APM 자동 설치 사용시 주석 해제 - APM 에이전트를 애플리케이션 Pod에 자동으로 주입하여 애플리케이션 성능 모니터링을 활성화합니다.
    # apm:
    #   instrumentation:
    #     targets:
    #       - name: hello-world
    #         enabled: true
    #         language: "java"          # 지원 언어: java, python, nodejs
    #         whatapApmVersions:
    #           java: "2.2.58"          # 사용할 APM 에이전트 버전
    #         namespaceSelector:
    #           matchNames:
    #             - default             # 모니터링할 애플리케이션이 있는 네임스페이스
    #         podSelector:
    #           matchLabels:
    #             app: "hello-world"    # 모니터링할 애플리케이션 Pod의 라벨
    #         config:
    #           mode: default           # APM 에이전트 모드 설정
    
    ### K8s 모니터링시 주석 해제 - Kubernetes 클러스터, 노드, 컨테이너 모니터링을 활성화합니다.
    # k8sAgent:
    #   masterAgent:
    #     enabled: true                 # 마스터 에이전트 활성화 (클러스터 수준 메트릭 수집)
    #   nodeAgent:
    #     enabled: true                 # 노드 에이전트 활성화 (노드 및 컨테이너 수준 메트릭 수집)
    ### GPU 모니터링 사용 시 주석 해제 - NVIDIA GPU 메트릭 수집을 활성화합니다.
    #   gpuMonitoring:
    #     enabled: true                 # GPU 모니터링 활성화 (NVIDIA DCGM-EXPORTER 가 whatap-node-agent 사이드카로 설치됩니다)
    
    ### 오픈메트릭(프로메테우스 형태의 지표수집) 사용 시 주석 해제 - Prometheus 형식의 메트릭을 수집합니다.
    # openAgent:
    #     enabled: true                 # OpenAgent 활성화
    #     targets:
    #       - targetName: kube-apiserver
    #         type: ServiceMonitor      # 대상 유형: ServiceMonitor, PodMonitor, StaticEndpoints
    #         namespaceSelector:
    #           matchNames:
    #             - "default"           # 메트릭을 수집할 네임스페이스
    #         selector:
    #           matchLabels:
    #             component: apiserver  # 메트릭을 수집할 서비스/Pod의 라벨
    #             provider: kubernetes
    #         endpoints:
    #           - port: "https"         # 메트릭 엔드포인트 포트
    #             path: "/metrics"      # 메트릭 경로
    #             interval: "30s"       # 이 엔드포인트의 스크래핑 간격
    #             scheme: "https"       # HTTP 스키마 (http 또는 https)
    #             tlsConfig:
    #               insecureSkipVerify: true  # TLS 인증서 검증 건너뛰기

```

## 다양한 구성 예제

와탭 오퍼레이터는 지원하는 K8s 에이전트와 더불어, APM 자동 설치, 커스텀 메트릭 에이전트 설치를 지원합니다. 아래의 구성예제를 통해 설치할 수 있습니다.

### GPU 모니터링

Kubernetes 모니터링 에이전트를  않고 와탭 노드 에이전트 파드에 DCGM-EXPORTER 컨테이너를 사이드카 형태로 배포합니다.

사용자는 별다른 구성없이 아래 yaml 을 적용하여 수집되는 메트릭스를 GPU 대시보드( 대시보드 > GPU 대시보드) 에서 확인할 수 있습니다.

<aside>
💡

노드 에이전트에 내장된 사이드카가 아니라 직접 DCGM-EXPORTER를 구성하신 경우
[**OpenAgent (오픈에이전트) 구성 가이드**](https://www.notion.so/OpenAgent-20f20702704a806eafbbd50fb442edd7?pvs=21) 를 참고하여 dcgm 오픈메트릭을 수집 할 수 있습니다.

</aside>

- **GPU 자동 설치**

    ```yaml
    apiVersion: monitoring.whatap.com/v2alpha1
    kind: WhatapAgent
    metadata:
      name: whatap
    spec:
      features:
        openAgent:
          enabled: true  # Open Agent 활성화
        k8sAgent:
          masterAgent:
            enabled: true
          nodeAgent:
            enabled: true
          gpuMonitoring:
            enabled: true  # GPU 모니터링 활성화
    ```

  > 참고: 자동설치시 Open Agent가 자동으로 DCGM Exporter를 발견하고 스크래핑합니다.
>

- **GPU 노드 톨러레이션 설정**

  GPU 노드에 테인트가 있는 경우 톨러레이션을 추가해야 합니다.

    ```yaml
    apiVersion: monitoring.whatap.com/v2alpha1
    kind: WhatapAgent
    metadata:
      name: whatap
    spec:
      features:
        k8sAgent:
          nodeAgent:
            enabled: true
            tolerations:
              - key: "nvidia.com/gpu"
                operator: "Exists"
                effect: "NoSchedule"
              - key: "gpu"
                operator: "Exists"
                effect: "NoSchedule"
          gpuMonitoring:
            enabled: true
    ```


### **APM 자동 설치**

Kubernetes 모니터링 에이전트를 활성화하지 않고 쿠버네티스 클러스터에 존재하는 APM을 자동 설치합니다.

자세한 내용은 [APM 자동 설치 구성](https://www.notion.so/APM-1ee20702704a809a9a56c4136718f0df?pvs=21)을 참고해 주세요

```yaml
apiVersion: monitoring.whatap.com/v2alpha1
kind: WhatapAgent
metadata:
  name: whatap
spec:
  features:
    apm:
      instrumentation:
        targets:
          - name: hello-world
            enabled: true
            language: "java"
            whatapApmVersions:
              java: "2.2.58"
            namespaceSelector:
              matchNames:
                - default
            podSelector:
              matchLabels:
                app: "hello-world"
            config:
              mode: default
          - name: "python-fastapi"
            enabled: true
            language: "python"
            whatapApmVersions:
              python: "1.8.10"
            podSelector:
              matchLabels:
                app: "python-app"
            namespaceSelector:
              matchNames:
              - "default"
            # Python 전용 설정값들
            envs:
              app_name: "apm-test"        # 식별을 위한 이름
              app_process_name: "uvicorn"               # 실제 프로세스 이름 (uvicorn, gunicorn, python 등)
              OKIND: "forecast"                         # 분류를 위한 이름 (옵션)
```

### **OpenAgent**

Kubernetes 모니터링 에이전트나 APM 계측을 활성화하지 않고 Prometheus 스타일 메트릭을 수집하기 위한 OpenAgent 컴포넌트만 구성합니다.

자세한 내용은 [OpenAgent 구성](https://www.notion.so/OpenAgent-20f20702704a806eafbbd50fb442edd7?pvs=21)을 참고해 주세요

```yaml
apiVersion: monitoring.whatap.com/v2alpha1
kind: WhatapAgent
metadata:
  name: whatap
spec:
  features:
    openAgent:
        enabled: true
        targets:
          - targetName: kube-apiserver
            type: ServiceMonitor
            namespaceSelector:
              matchNames:
                - "default"
            selector:
              matchLabels:
                component: apiserver
                provider: kubernetes
            endpoints:
            - port: "https"
              path: "/metrics"
              interval: "30s"
              scheme: "https"
              tlsConfig:
                insecureSkipVerify: true
	            metricRelabelConfigs:
	              - source_labels: ["__name__"]
	                regex: "apiserver_request_total"
	                action: "keep"
```

### **Kubernetes 모니터링과 APM 계측 함께 사용**

```yaml
apiVersion: monitoring.whatap.com/v2alpha1
kind: WhatapAgent
metadata:
  name: whatap
spec:
  features:
    apm:
      instrumentation:
        targets:
          - name: hello-world
            enabled: true
            language: "java"
            whatapApmVersions:
              java: "2.2.58"
            namespaceSelector:
              matchNames:
                - default
            podSelector:
              matchLabels:
                app: "hello-world"
            config:
              mode: default
    k8sAgent:
      masterAgent:
        enabled: true
      nodeAgent:
        enabled: true
    openAgent:
        enabled: true
        targets:
          - targetName: kube-apiserver
            type: ServiceMonitor
            namespaceSelector:
              matchNames:
                - "default"
            selector:
              matchLabels:
                component: apiserver
                provider: kubernetes
            endpoints:
            - port: "https"
              path: "/metrics"
              interval: "30s"
              scheme: "https"
              tlsConfig:
	              insecureSkipVerify: true
			        metricRelabelConfigs:
		          - source_labels: ["__name__"]
		            regex: "apiserver_request_total"
		            action: "keep"
```