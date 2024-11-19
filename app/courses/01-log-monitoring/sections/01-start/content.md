# Getting Started

We have set up for you an AKS cluster with the easytrade demo application which is monitored by Dynatrace Operator.

We have also added custom log-generating scripts that push logs to each participant's Dynatrace tenant. This setup will allow you to work with a variety of log types during this workshop.

By the end of the workshop, you’ll be able to master log ingestion, filtering, processing, and Dynatrace Pattern Language.

___
## Components Overview

- **Easytravel Application**: A K8s microservices based refreshed version of the popular EasyTravel application.

- **Dynatrace Operator**: Installed in the AKS cluster, the Dynatrace Operator enables fullstack kubernetes monitoring. It deploys containerized Active Gates and OneAgent pods as daemonsets to monitor the workloads running in the cluster. 
  Check out more on the [Dynatrace Operator Documentation](https://docs.dynatrace.com/docs/setup-and-configuration/setup-on-k8s/installation) 
  ![<img src="media/images/dynatrace-operator.png" width=200 />](media/images/dynatrace-operator.png){width=50%}

- **Dynatrace Tenant**: Each participant has a dedicated Dynatrace tenant / environment. 
  You can access it from the tools section in the navigation menu on the top.

- **Log-Generating Scripts**: Custom scripts push additional demo logs to each participant’s Dynatrace tenant. These logs simulate a variety of activities and system behaviors, giving you more comprehensive data to analyze.

___
## Pre-requisites
### 1. Restart EasyTravel deployment pods
Due to the way in which the Operator is deployed, the pods need to be restarted to ensure that the OneAgent pods can correctly inject into the workloads.

Please, connect to your vm console and execute the following command to delete all pods in easytravel namespace.
```
kubectl delete --all pods --namespace=easytravel 
```
After the pods are deleted, they will be restarted automatically by the Deployments.

Then, go to the tools section and open your Dynatrace tenant. You should be able to see the easytravel namespace in the dynakube cluster.

### 2. Enable Kubernetes Event Monitoring and Alerts

Using the left-hand navigation panel, select infrastructure and kubernetes. Drill into the dynakube cluster.

On the cluster overview page you will find a ... menu in the top right corner. Select this menu and click settings

Scroll to the bottom of this page and enable the switch Monitor Events and Opt in to the Kubernetes events integration for analysis and alerting

![Kubernetes Events Settings](media/images/monitor-k8s-events.png){width=80%}

### 4. Configure Log Monitoring Sources

By EC decision, autodetected logs are not ingested by default. We need to configure the log sources which will be ingested in our environment.

The configuration is based on rules that use matchers for hierarchy, log path, and process groups. These rules determine which log files among those detected by OneAgent, either automatically or defined as custom log sources, are ingested. (Please note generic ingested logs do not take these rules into account.)

- From the left hand navigation panel, under the manage section select settings.

- Scroll down and expand the Log Monitoring category. Choose Log sources and storage sub-menu.

- Click on the `Add rule` button.

- Adding rules allows us to select whether we want to ingest or avoid log ingestion for log records that match certain criteria. 
    - Name the rule `Include K8s Logs`
    - Add a matcher for k8s namespace name In this case we want to monitor logs from the easytravel and easytrade applications.
    - Save the rule.

  ![Add rule](media/images/add-rule.png){width=80%}

*NOTE - choosing this setting will automatically ingest every log from every monitored source in your environment and will be subject to DDU consumption.*


___


With this setup, you are now ready to proceed with log ingestion and begin exploring filtering, processing, and pattern recognition using Dynatrace Pattern Language.