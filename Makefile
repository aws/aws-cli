SHELL := /bin/bash
.SILENT:

check_defined = \
   $(strip $(foreach 1,$1, \
	$(call __check_defined,$1,$(strip $(value 2)))))
__check_defined = \
   $(if $(value $1),, \
	$(error Undefined $1$(if $2, ($2))))

$(call check_defined, VERSION, \
   cli version to release)

IMAGE_NAME ?= build-tools/iress-aws-cli-patched
BASE_DOCKER_TAG ?= ${VERSION}

# default variables
TAG ?= local
DOCKER_TAG = $(BASE_DOCKER_TAG).$(GITHASH)
GITHASH := $(shell git rev-parse --short HEAD)

.PHONY: build
build: ## build the container
	echo $(BASE_DOCKER_TAG)
	docker build -t $(IMAGE_NAME):$(TAG) --pull -f Dockerfile --build-arg VERSION=$(BASE_DOCKER_TAG) --build-arg DEFAULT_DOCKER_REPO=$(DEFAULT_DOCKER_REPO) .

.PHONY: verify
verify:
	docker-compose run --rm --entrypoint python verify ./scripts/ci/run-tests

.PHONY: publish-to-artifactory
publish-to-artifactory: ## publish the container image to artifactory
	# login with Docker
	echo "Authenticating as ${DOCKER_REPO_USER} @ ${DEFAULT_DOCKER_REPO}"
	echo "${DOCKER_REPO_PASSWORD}" | docker login -u "${DOCKER_REPO_USER}" --password-stdin "${DEFAULT_DOCKER_REPO}"

	echo "Git Hash - $(GITHASH)"
	echo "Base Docker Tag - $(BASE_DOCKER_TAG)"
	echo "Docker Tag - $(DOCKER_TAG)"

	# tag with major.minor.githash
	docker tag $(IMAGE_NAME):$(TAG) $(DEFAULT_DOCKER_REPO)/$(IMAGE_NAME):$(DOCKER_TAG)
	docker push $(DEFAULT_DOCKER_REPO)/$(IMAGE_NAME):$(DOCKER_TAG)
	docker rmi $(DEFAULT_DOCKER_REPO)/$(IMAGE_NAME):$(DOCKER_TAG) -f

	# tag with major.minor
	docker tag $(IMAGE_NAME):$(TAG) $(DEFAULT_DOCKER_REPO)/$(IMAGE_NAME):$(BASE_DOCKER_TAG)
	docker push $(DEFAULT_DOCKER_REPO)/$(IMAGE_NAME):$(BASE_DOCKER_TAG)
	docker rmi $(DEFAULT_DOCKER_REPO)/$(IMAGE_NAME):$(BASE_DOCKER_TAG) -f

	# tag with latest
	docker tag $(IMAGE_NAME):$(TAG) $(DEFAULT_DOCKER_REPO)/$(IMAGE_NAME):latest
	docker push $(DEFAULT_DOCKER_REPO)/$(IMAGE_NAME):latest
	docker rmi $(DEFAULT_DOCKER_REPO)/$(IMAGE_NAME):latest -f
	
	docker logout $(DEFAULT_DOCKER_REPO)
