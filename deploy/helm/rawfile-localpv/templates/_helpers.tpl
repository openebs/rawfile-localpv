{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "rawfile-localpv.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "rawfile-localpv.fullname" -}}
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
{{- define "rawfile-localpv.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "rawfile-localpv.labels" -}}
helm.sh/chart: {{ include "rawfile-localpv.chart" . }}
{{ include "rawfile-localpv.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "rawfile-localpv.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rawfile-localpv.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "rawfile-localpv.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "rawfile-localpv.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Some helpers to handle image global information
*/}}
{{- define "rawfile-localpv.controller-image-tag" -}}
{{- $imageTag := .Values.controller.image.tag | default .Values.image.tag | default (printf "v%s" .Chart.AppVersion) }}
{{- printf "%s" $imageTag }}
{{- end }}

{{- define "rawfile-localpv.controller-image-repository" -}}
{{- printf "%s" .Values.controller.image.repository | default .Values.image.repository }}
{{- end }}

{{- define "rawfile-localpv.controller-image" -}}
{{- $imageRegistry := .Values.image.registry | default .Values.global.imageRegistry }}
{{- printf "%s/%s:%s" $imageRegistry (include "rawfile-localpv.controller-image-repository" .) (include "rawfile-localpv.controller-image-tag" .) }}
{{- end }}

{{- define "rawfile-localpv.controller-pull-policy" -}}
{{- printf "%s" (.Values.controller.image.pullPolicy | default .Values.image.pullPolicy | default .Values.global.imagePullPolicy) }}
{{- end }}

{{- define "rawfile-localpv.controller-resources" -}}
{{- toYaml (.Values.controller.resources) }}
{{- end }}

{{- define "rawfile-localpv.node-image-tag" -}}
{{- $imageTag := .Values.node.image.tag | default .Values.image.tag | default (printf "v%s" .Chart.AppVersion) }}
{{- printf "%s" $imageTag }}
{{- end }}

{{- define "rawfile-localpv.node-image-registry" -}}
{{- printf "%s" .Values.image.registry | default .Values.global.imageRegistry }}
{{- end }}

{{- define "rawfile-localpv.node-image-repository" -}}
{{- printf "%s" .Values.node.image.repository | default .Values.image.repository }}
{{- end }}

{{- define "rawfile-localpv.node-image" -}}
{{- $imageRegistry := .Values.image.registry | default .Values.global.imageRegistry }}
{{- printf "%s/%s:%s" $imageRegistry (include "rawfile-localpv.node-image-repository" .) (include "rawfile-localpv.node-image-tag" .) }}
{{- end }}

{{- define "rawfile-localpv.node-pull-policy" -}}
{{- printf "%s" (.Values.node.image.pullPolicy | default .Values.image.pullPolicy | default .Values.global.imagePullPolicy) }}
{{- end }}

{{- define "rawfile-localpv.node-resources" -}}
{{- toYaml (.Values.node.resources) }}
{{- end }}
