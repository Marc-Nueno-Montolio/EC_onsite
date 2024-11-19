# Kubernetes Network Troubleshooting

## Network zones

[ActiveGate connectivity](https://docs.dynatrace.com/docs/manage/network-zones/activegate-connectivity)
[OneAgent connectivity](https://docs.dynatrace.com/docs/manage/network-zones/activegate-connectivity)

## Enable network zone

- log on to the shell

edit $HOME/dynatrace/dynakube.yaml
add a line under

`spec:`
`  networkZone: digit.onsite.ws<N>`

add lines for ActiveGate

`spec:`
`  activegate:`
`    customProperties:`
`      value: |`
`        [connectivity]`
`        dnsEntryPoint = https://dynakube-activegate.dynatrace:443/communication`


`kubectl apply -f $HOME/dynatrace/dynakube.yaml`

Check the restarting of activegate and oneagent pods

`kubectl -n dynatrace get pods`

wait a couple of minutes

kill one of the oneagent pods and check again in Dynatrace after a couple of minutes --> alert: Monitoring unavailable

## Troubleshoot the issue

- troubleshoot
- pod logs
- supportarchive
- exec into oneagent pod

`curl -k -v https://dynakube-activegate.dynatrace:443/communication`

DNS is working correct ? isn't it ?

## What went wrong ?

- hostNetworking

We exec into a container in the pod network --> curl works
Oneagent runs privileged on the hostNetwork --> this can't resolve internal addresses

## Fix the issue

- add digit.internet as alternative zone into your networkzone
