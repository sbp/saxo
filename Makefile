SHELL = /bin/sh

.PHONY: publish
publish:
	python3 setup.py sdist --formats=bztar upload
	python3 setup.py bdist_wheel upload
	rm -rf build/
	rm -rf dist/
	rm -rf saxo.egg-info/
	git add -A
	git commit -m "Published `cat version`"
	git tag `cat version`
	git push
	git push --tags
