{{/* vim: set filetype=mustache: */}}

{{/*
Allow other namespace
*/}}

{{- define "whatap-kube-agent.namespace" -}}
{{- if .Values.namespaceOverride }}
{{- .Values.namespaceOverride }}
{{- else }}
{{- default "whatap-monitoring" }}
{{- end }}
{{- end }}