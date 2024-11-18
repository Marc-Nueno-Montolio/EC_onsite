## Create a Metric and Event from log queries

In this lab we will simulate a real world application problem by enabling a problem pattern on our EasyTravel application. The goal is to force authentication errors on our easyTravel frontend service which will be visible in our logging. Dynatrace will natively see theses errors within our server-side services and mark the transactions as failure. We want to build a log query that identifies authentication errors and measure the number of errors with a log metric. Futher we will create a new problem-generating log event from this same query. 

### Step 1: Get URL to enable login errors


1. Check which pods are running in the easytravel namespace

```
kubectl get pods -n easytravel
NAME                                     READY   STATUS      RESTARTS   AGE
angular-frontend-69b9f4759c-rfspm        1/1     Running     0          20m
angular-loadgenerator-7b4b65c8fc-t644v   1/1     Running     0          20m
backend-7868959697-68cjf                 1/1     Running     0          20m
backend-7868959697-9ltzf                 1/1     Running     0          20m
mongodb-68c9f687dd-k6rcn                 1/1     Running     0          20m
mongodb-contentcreator                   0/1     Completed   0          20m
nginx-8587466f65-5dvfv                   1/1     Running     0          20m
```

2. Enable login authentication problems executing a curl request in any of the backend service pods
```
kubectl exec backend-7868959697-9ltzf -- curl "localhost:8080/services/ConfigurationService/setPluginEnabled?name=LoginProblems"
```

3. You can check enabled problem generation plugins with
```
kubectl exec backend-7868959697-9ltzf -- curl "localhost:8080/services/ConfigurationService/getEnabledPluginNames"
```

### Step 2: Query for login errors

1. With the problem scenario enabled, all logins will fail with an exception. Navigate to the log viewer and query for log level `error`. ![[loginerrors.png]]

2. Build a query that will filter specifically for login errors on the easytravel backend pod. Below is an example of a basic query: ![[easytrade-login-errors-query.jpg]]

3. In order to build a reliable metric, we'll need to make our query more specific. Switch to the advanced query mode and paste in the provided query below:

```
status="error" AND content=" LoginException occurred when processing Login transaction" AND k8s.pod.name="angular-frontend*"
```

![backendloginerrors](../../assets/images/backendloginerrors.png)

### Step 3: Create a metric

1. Now that our query is specific to login errors and will dynamically look at any easytravel-backend pod name we can reliably create a metric. Directly from the log viewer click on the button 'Create Metric'.

![createmetric](../../assets/images/createmetric.png)

Selecting create metric will transition your UI to the settings -> Logs -> Log Metrics screen.

![[setting-up-log-metric 1.png]]

2. Define the key and measurement. The log key can be anything you want, however it's good practice to create a key name that's descriptive to the metric. We'll use:

```
log.backend.login.errors.count
```

For any log metric you have the option of measuring the 'occurance of log records' or 'attribute'. For this case, we will leave the default selection of 'Occurance of log records'. Measuring 'attribute' would be the collection of measures for the attribute value of log records that match the query. If you select this option, you need to also set Attribute to the attribute whose values will be gauged..

![[measure.png]]

3. Save changes for this metric
![[savechanges.png]]


### Step 4 Create a new log exception metric with added dimension

1. We're now going to modify our query slightly to remove the pod name and query for errors on any pod. Click 'create metric' and copy the query below to paste into the metric definition.

```
status="error" AND content=" LoginException occurred when processing Login transaction"
```
2. Define the metric key

![logerrorkey](../../assets/images/logerrorkey.png)

3. Add a dimension to the metric. We want dt.entity.process_group as our dimension. This will measure the number of occurnaces from our query per process group

![Dimension](../../assets/images/dimension.png)

4. Click save changes

### Step 5: Add metrics to our dashboard

1. Open the dashboard that we created in the previous section and add a new graph tile.

2. Configure the tile and add the metric key `log.backend.login.errors.count`. Change the aggregation to `sum`.

3. Add another new graph tile and add the metric key `log.errors.login`. Change the aggregation to `sum` and split by `Process Group`

![dashboard](../../assets/images/dashboard.png)

### Step 6: Create a custom event

1. Navigate to the log settings of your tenant. Settings -> Logs -> Log Events to create a new log event

2. Using our same query from earlier we'll create a log event to alert us if the entry is found. 

```
status="error" AND content=" LoginException occurred when processing Login transaction" AND k8s.pod.name="angular-frontend*"
```

We'll configure the event as shown below:

![LoginEvent](../../assets/images/LoginErrorEvent.png)