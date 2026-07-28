#########
### DOCKER LOCAL
#########

#To run this make sure that you have the line under local in the dockerfile uncommented

build_container_local:
	docker build --tag=$$IMAGE:dev .


run_container_local:
	docker run -it -e PORT=8000 -p 8000:8000 $$IMAGE:dev


#########
# ----- Build the dataset + model artifacts (run before Docker build) ---
#########



#########
## DOCKER DEPLOYMENT GCP
#########

#IMPORTANT: GO TO DOCKERFILE AND ADD THE PORT VARIABLE (uncomment the line under GCP deployment)

# Step 1 ( ONLY FIRST TIME)
allow_docker_push:
	gcloud auth configure-docker $$GCP_REGION-docker.pkg.dev

# Step 2 ( ONLY FIRST TIME)
create_artifacts_repo:
	gcloud artifacts repositories create $$ARTIFACTSREPO --repository-format=docker \
	--location=$$GCP_REGION --description="Repository for storing images"

# Step 3 -> windows or mac with intel chip
build_for_production:
	docker build -t  $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$ARTIFACTSREPO/$$IMAGE:prod .

### Step 3 (⚠️ MAC M chip (sillicon chips) SPECIFICALLY)
#m_chip_build_image_production:
	docker build --platform linux/amd64 -t $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$ARTIFACTSREPO/$$IMAGE:prod .

## Step 4
push_image_production:
	docker push $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$ARTIFACTSREPO/$$IMAGE:prod

# Step 5
deploy_to_cloud_run:
	gcloud run deploy --image $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$ARTIFACTSREPO/$$IMAGE:prod --memory $$MEMORY --region $$GCP_REGION



# ----- One-shot: build, push and deploy in a single command -------------

deploy_all: build_for_production push_image_production deploy_to_cloud_run




# Disabling the Service
# Adjust the service's configuration to scale down to zero instances.
# This way, no resources will be used, and you won't incur charges for active instances.
cloud_run_disable_service:
	gcloud run services update $$INSTANCE --min-instances=0

# Delete the Service
cloud_run_delete_service:
	gcloud run services delete $$INSTANCE

# Delete repository to not have costs
cloud_run_delete_repository:
	gcloud artifacts repositories delete $ARTIFACTSREPO --location=$GCP_REGION
