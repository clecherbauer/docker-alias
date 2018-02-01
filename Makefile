all: dependencies compile

dependencies:
	@echo download dependencies...
	@docker-compose run --rm go-docker go get -u github.com/smallfish/simpleyaml
	@docker-compose run --rm go-docker go get -u github.com/davecgh/go-spew/spew

compile:
	@echo compiling...
	@docker-compose run --rm go-docker go build -v
