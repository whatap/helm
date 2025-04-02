{{- if not .Values.allowUse }}
{{- fail "This chart is currently disabled for user usage. Set allowUse=true in values.yaml to enable it." }}
{{- end }}