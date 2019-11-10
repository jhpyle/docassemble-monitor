# docassemble-monitor

This [Docker] image provides an API for monitoring a [**docassemble**]
implementation on a [Kubernetes] cluster deployed with the
[**docassemble** Helm chart].

## API endpoints

* `/api/v1/config`: returns information about the configuration of the
  cluster (without secret keys).
* `/api/v1/pods`: returns information about the status of the pods in
  the cluster.
* `/api/v1/deployments`: returns information about the status of the
  deployments in the cluster.
* `/api/v1/health`: returns information about the health of the cluster.
* `/api/v1/status`: returns information about the status of the cluster.
* `/api/v1/install_ready`: returns 200 (reserved for future use).
* `/api/v1/install_complete`: returns 200 when system is ready,
  400 otherwise.
* `/api/v1/pre_upgrade_ready`: returns 200 (reserved for future use).
* `/api/v1/pre_upgrade_complete`: returns 200 (reserved for future use).
* `/api/v1/post_upgrade_ready`: returns 200 (reserved for future use).
* `/api/v1/post_upgrade_complete`: returns 200 when system is ready,
  400 otherwise.

[**docassemble**]: https://docassemble.org
[**docassemble** Helm chart]: https://github.com/jhpyle/charts
[Helm]: https://helm.sh/
[Kubernetes]: https://kubernetes.io/
[Docker]: https://www.docker.com/
