{{/*
Expand the name of the chart.
*/}}
{{- define "cornflow.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "cornflow.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "cornflow.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "cornflow.labels" -}}
helm.sh/chart: {{ include "cornflow.chart" . }}
{{ include "cornflow.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "cornflow.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cornflow.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "cornflow.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "cornflow.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "cornflow.postgresql.fullname" -}}
{{- printf "%s-%s" .Release.Name "postgresql" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Name of the Secret with the cornflow keys (FERNET_KEY and SECRET_BI_KEY):
cornflow.keys.existingSecret if set, otherwise <release>-cornflow-keys, created by this chart.
*/}}
{{- define "cornflow.keysSecretName" -}}
{{- if (.Values.cornflow.keys).existingSecret }}
{{- .Values.cornflow.keys.existingSecret }}
{{- else }}
{{- printf "%s-cornflow-keys" .Release.Name }}
{{- end }}
{{- end }}

{{/*
Fails the render when a cornflow key is set in cornflow.env: the keys come from the
keys Secret, and a second definition of the same variable in the pod would be ambiguous.
*/}}
{{- define "cornflow.validateKeys" -}}
{{- $env := .Values.cornflow.env | default dict }}
{{- range $name := list "FERNET_KEY" "SECRET_KEY" "SECRET_BI_KEY" }}
{{- if hasKey $env $name }}
{{- fail (printf "cornflow.env.%s is not allowed. FERNET_KEY and SECRET_BI_KEY come from a Kubernetes Secret: the one this chart generates on install, or your own with cornflow.keys.existingSecret. SECRET_KEY is not needed: FERNET_KEY takes precedence. Remove %s from cornflow.env; to keep the key you already use, store it in your own Secret (keys FERNET_KEY and SECRET_BI_KEY) and set cornflow.keys.existingSecret (see the chart README)." $name $name) }}
{{- end }}
{{- end }}
{{- end }}
