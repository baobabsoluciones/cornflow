#!/bin/bash

# start minikube service
minikube start
# take short time
sleep 1
# enable minikube docker env for pull images
eval $(minikube docker-env)
# take short time
sleep 1
# create all configmap
kubectl apply -f cornflowdb-configmap.yaml
# create all services
kubectl apply -f cornflowdb-service.yaml
kubectl apply -f cornflow-service.yaml
# create volumes
kubectl apply -f cornflowdb-storage.yaml
# create deployments
kubectl apply -f cornflowdb-deployment.yaml
kubectl apply -f cornflow-deployment.yaml
# take long time
sleep 30
# show pods
kubectl get pods
# take short time
sleep 1
# show services
kubectl get svc
# take short time
sleep 1
# expose to all created services
#kubectl port-forward podid --address 0.0.0.0 5000:5000 &

# for destroying all resources and stop minikube cluster paste uncommented next lines
#kubectl delete -f cornflowdb-configmap.yaml
#kubectl delete -f cornflowdb-service.yaml
#kubectl delete -f cornflowdb-deployment.yaml
#kubectl delete -f cornflow-service.yaml
#kubectl delete -f cornflow-deployment.yaml
#kubectl delete -f cornflowdb-storage.yaml
#minikube stop
#docker system prune -af
