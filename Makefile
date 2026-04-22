.PHONY: demo test

demo:
	vhs docs/demo/demo.tape

test:
	uv run pytest
