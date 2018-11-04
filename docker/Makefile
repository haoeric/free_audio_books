NAME=audio_books_crawler
TAG=1.0.0
REGISTRY=012532289196.dkr.ecr.ap-southeast-2.amazonaws.com/$(NAME)

all: build push

build:
	docker build -t $(NAME):$(TAG) -t $(NAME):latest -f Dockerfile ..
	docker tag $(NAME):latest $(REGISTRY):latest
	docker tag $(NAME):$(TAG) $(REGISTRY):$(TAG)

push:
	docker push $(REGISTRY):$(TAG)
	docker push $(REGISTRY):latest
