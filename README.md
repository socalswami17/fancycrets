## fancycrets
A hello-world kubernetes operator written in kopf.

### Vision
Operate on specified annotation updates to a secret object: auto-generate/update secret data as specified in the 
annotations.

This operator implements a naive solution to the use case: as a devops engineer I want to deploy in a "kubey" way,
with minimal config repetition, minimal custom code, and minimal clutter:
* many (over 10) similar legacy (ec2 container) apps, 
* each getting variations of many (over 30) similar secrets from runtime env vars, 
* (some variations requiring more formatting power than go templating), 
* to a few (dev, preprod, prod) multi-tenant kubernetes/argo user environments, 
* while remaining a cluster "user", not "administrator" (i.e. without defining a CRD)

In this way, I could get away with managing only four actual "normalized" secrets (e.g. "common", "dev", "preprod", 
and "prod", sync'ed from hashicorp vault using external-secrets), and ~30 sets of secret annotation specs, 
each containing ~30 keys...the operator would auto-generate/update the per-env, per-app secret data whenever a 
supported annotation is updated.  See example/hello-secrets.yaml and the Example section below for a simple 
one-environment example.

### TODO
* exception handling
* tox/pytest unit tests
* the kopf test runner

### References
* [the kopf github](https://github.com/nolar/kopf)
* [this medium post](https://medium.com/@akash94thakur/kubernetes-operator-in-python-6e986b0aabd3)
* [the kopf docs](https://kopf.readthedocs.io/en/stable/)

## Installation/Usage

### Pre-Requisites

* kubernetes in docker

### Operator
In a python virtualenv:
```bash
$ venv/bin/pip install -U pip -r requirements.txt
$ venv/bin/kopf run src/handlers.py
[2024-11-29 11:55:21,190] kopf.activities.star [INFO    ] Activity 'configure' succeeded.
[2024-11-29 11:55:21,191] kopf._core.engines.a [INFO    ] Initial authentication has been initiated.
[2024-11-29 11:55:21,197] kopf.activities.auth [INFO    ] Activity 'login_via_client' succeeded.
[2024-11-29 11:55:21,197] kopf._core.engines.a [INFO    ] Initial authentication has finished.
```

### Example
1. Create the three example secrets as written: common, env1 and env1-swamibot. 
Note env1-swamibot has one data key, and some commented-out annotations. Subsequently when we update its annotations, 
the new operator will patch the data, by querying common and env1, and formatting per the annotations.
```bash
$ kubectl apply -f examples/hello-secrets.yaml
secret/common configured
secret/env1 configured
secret/env1-swamibot configured

$ kubectl get secrets/env1-swamibot -o yaml
apiVersion: v1
data:
  INIT_KEY: aW5pdFZhbHVl
kind: Secret
metadata:
  annotations:
    kopf.zalando.org/last-handled-configuration: ...
    kubectl.kubernetes.io/last-applied-configuration: ...
...
```
2. Modify the yaml for env1-swamibot to specify the annotations recognized by the new operator.
```bash
$ vim examples/hello-secrets.yaml
  annotations: #{}
    "fancycrets.secretSource.0": "common"
    "fancycrets.secretSource.1": "env1"
    "fancycrets.secretFormat.COMMON_TOKEN": "{commonKey}"
    "fancycrets.secretFormat.ENV_TOKEN": "https://external-service.test/?static_token={envKey}"
```
3. Update env1-swamibot with kubectl.
```bash
$ kubectl apply -f examples/hello-secrets.yaml
secret/common unchanged
secret/env1 unchanged
secret/env1-swamibot configured
```
4. Read env1-swamibot and note its new data.
```bash
$ kubectl get secrets/env1-swamibot -o yaml
apiVersion: v1
data:
  COMMON_TOKEN: Y29tbW9uVmFsdWU=
  ENV_TOKEN: aHR0cHM6Ly9leHRlcm5hbC1zZXJ2aWNlLnRlc3QvP3N0YXRpY190b2tlbj1lbnYxVmFsdWU=
  INIT_KEY: aW5pdFZhbHVl
kind: Secret
metadata:
  annotations:
    fancycrets.secretFormat.COMMON_TOKEN: '{commonKey}'
    fancycrets.secretFormat.ENV_TOKEN: https://external-service.test/?static_token={envKey}
    fancycrets.secretSource.0: common
    fancycrets.secretSource.1: env1
    kopf.zalando.org/last-handled-configuration: ...
    kubectl.kubernetes.io/last-applied-configuration: ...
...
```

This can be extended to a matrix of (apps to deploy) x (environments to deploy). In the handler's log output and 
`update_secret()` in src/handlers.py you can see the operator did the following:
1. Determine if the update includes any supported annotations, and if so
2. Call `make_patch()` to do the following:
   1. Get/create a kubernetes client, query any specified secrets
   2. Create a patch dict using the secret data and specified formatting
3. Get/create a kubernetes client, patch self's data (which causes another call to the update handler, but it
avoids recursion by only _reading_ its annotations and _writing_ data)
