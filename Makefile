SHELL = /bin/sh

.PHONY: publish
publish:
	python3 setup.py sdist --formats=bztar upload
	# python3 setup.py bdist_wheel upload
	rm -rf dist/
	git add -A
	git commit -m "Published `egrep -m1 '^version' saxo.py | cut -b12-18`"
	git tag `egrep -m1 '^version' saxo.py | cut -b12-18`
	git push
	git push --tags

# .PHONY: test
# test:
# 	./saxo test
