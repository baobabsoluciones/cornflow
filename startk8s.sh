#!/bin/bash
# start minikube service
minikube start
# take short time
sleep 1
# enable minikube docker env for pull images
eval $(minikube docker-env)
# take short time
sleep 1
# build cornflow image
docker build -t cornflow:1.0 .
# build airflow custom image
docker build -t airflow4corn:1.0 ./kubecornflow
# create all configmap
kubectl apply -f kubecornflow/cornflowdb-configmap.yaml
kubectl apply -f kubecornflow/airflowdb-configmap.yaml
# create all services
kubectl apply -f kubecornflow/cornflowdb-service.yaml
kubectl apply -f kubecornflow/cornflow-service.yaml
kubectl apply -f kubecornflow/airflowdb-service.yaml
kubectl apply -f kubecornflow/airflow-service.yaml
# create volumes
kubectl apply -f kubecornflow/cornflowdb-storage.yaml
kubectl apply -f kubecornflow/airflowdb-storage.yaml
# create deployments
kubectl apply -f kubecornflow/cornflowdb-deployment.yaml
kubectl apply -f kubecornflow/cornflow-deployment.yaml
kubectl apply -f kubecornflow/airflowdb-deployment.yaml
kubectl apply -f kubecornflow/airflow-deployment.yaml
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
#kubectl port-forward podid --address 0.0.0.0 8080:8080 &

# destroy all resources and stop minikube cluster
#kubectl delete -f kubecornflow/cornflowdb-configmap.yaml
#kubectl delete -f kubecornflow/cornflowdb-service.yaml
#kubectl delete -f kubecornflow/cornflowdb-deployment.yaml
#kubectl delete -f kubecornflow/cornflow-service.yaml
#kubectl delete -f kubecornflow/airflow-service.yaml
#kubectl delete -f kubecornflow/airflowdb-deployment.yaml
#kubectl delete -f kubecornflow/airflowdb-service.yaml
#kubectl delete -f kubecornflow/airflowdb-configmap.yaml
#kubectl delete -f kubecornflow/airflow-deployment.yaml
#kubectl delete -f kubecornflow/cornflow-deployment.yaml
#kubectl delete -f kubecornflow/cornflowdb-storage.yaml
#kubectl delete -f kubecornflow/airflowdb-storage.yaml
#minikube stop
#docker system prune -af