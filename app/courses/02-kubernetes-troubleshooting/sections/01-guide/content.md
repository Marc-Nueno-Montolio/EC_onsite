# Kubernetes Troubleshooting Workshop

## What is kubernetes ?

Scalable dynamic container runtime platform

![Kubernetes Cluster Architecture](media/kubernetes-cluster-architecture.svg){width=100%}


## Dynatrace operator

[Dynatrace Docs - How it works](https://docs.dynatrace.com/docs/ingest-from/setup-on-k8s/how-it-works)

Operator components

- Dynatrace operator
- Dynatrace webhook
- Dynatrace CSI Driver (not in ClassifFullStack) 

Dynakube components

- Dynatrace OneAgent
- Dynatrace ActiveGate

EdgeConnect components

- Dynatrace EdgeConnect (SaaS/Platform)


![<img src="media/ClassicFullStack.png" width=200 />](media/ClassicFullStack.png){width=100%}

## dynakube.yaml

- Demo the environment - show the dynakube.yaml

```
kubectl get ns 
kubectl -n dynatrace get dynakubes 
kubectl -n dynatrace get pods 
kubectl -n dynatrace get svc 
```

## troubleshooting guide

[Dynatrace Docs - Troubleshooting](https://docs.dynatrace.com/docs/ingest-from/setup-on-k8s/installation/troubleshooting)

- Demo the commands




