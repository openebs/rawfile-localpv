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

{{- define "rawfile-localpv.controller-resources" -}}
{{- toYaml (.Values.controller.resources) }}
{{- end }}

{{- define "rawfile-localpv.controller-external-resizer-resources" -}}
{{- toYaml (.Values.controller.externalResizer.resources) }}
{{- end }}

{{- define "rawfile-localpv.node-resources" -}}
{{- toYaml (.Values.node.resources) }}
{{- end }}

{{- define "rawfile-localpv.node-driver-registrar-resources" -}}
{{- toYaml (.Values.node.driverRegistrar.resources) }}
{{- end }}

{{- define "rawfile-localpv.node-external-provisioner-resources" -}}
{{- toYaml (.Values.node.externalProvisioner.resources) }}
{{- end }}

{{- define "rawfile-localpv.node-external-snapshotter-resources" -}}
{{- toYaml (.Values.node.externalSnapshotter.resources) }}
{{- end }}

{{- define "rawfile-localpv.node-snapshot-controller-resources" -}}
{{- toYaml (.Values.node.snapshotController.resources) }}
{{- end }}

{{- define "rawfile-localpv.node-kubelet-path" -}}
{{- printf "%s/" (.Values.node.kubeletPath | trimSuffix "/") -}}
{{- end }}

{{- define "rawfile-localpv.metadata-dir-path" -}}
{{- tpl .Values.node.metadataDirPath . }}
{{- end }}

{{- define "rawfile-localpv.pool-volumes" -}}
{{- range $name, $pool := .Values.node.storagePools }}
- name: pool-{{ $name }}
  hostPath:
    path: {{ tpl $pool.path . }}
    type: DirectoryOrCreate
{{- end }}
{{- end }}

{{- define "rawfile-localpv.pool-volume-mounts" -}}
{{- range $name, $pool := .Values.node.storagePools }}
- name: pool-{{ $name }}
  mountPath: {{ tpl $pool.path . }}
{{- end }}
{{- end }}


{{/*
Creates the image URL ie registry/repository:tag
*/}}
{{- define "rawfile-localpv.common.image" -}}
{{- $registryName := ((.global).imageRegistry) | default ((.imageRoot).registry) | default ((.csiSideCars).registry) | trimSuffix "/" -}}
{{- $repositoryName := .imageRoot.repository -}}
{{- $separator := ":" -}}
{{- $chartVersion := .chartVersion -}}
{{- $termination := .imageRoot.tag | default (printf "v%s" $chartVersion) | toString -}}
{{- if $registryName }}
    {{- printf "%s/%s%s%s" $registryName $repositoryName $separator $termination -}}
{{- else }}
    {{- printf "%s%s%s"  $repositoryName $separator $termination -}}
{{- end }}
{{- end }}

{{/*
Concatenates imagepullsecrets and handles different formats (example - secret or - name: secret)
*/}}
{{- define "rawfile-localpv.common.pullSecrets" -}}
{{- $names := list -}}
{{- with .Values.global.imagePullSecrets -}}
  {{- range . -}}
    {{- if kindIs "map" . }}
      {{- if and (hasKey . "name") (not (empty .name)) -}}
        {{ $names = append $names .name }}
      {{- end -}}
    {{- else if not (empty .) -}}
      {{ $names = append $names . -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
{{- with .Values.imagePullSecrets -}}
  {{- range . }}
    {{- if kindIs "map" . -}}
      {{- if and (hasKey . "name") (not (empty .name)) -}}
        {{- $names = append $names .name }}
      {{- end -}}
    {{- else if not (empty .) -}}
      {{- $names = append $names . -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
{{- $names = uniq $names -}}
{{- if $names -}}
{{- range $names }}
- name: {{ . }}
{{- end -}}
{{- end -}}
{{- end -}}
