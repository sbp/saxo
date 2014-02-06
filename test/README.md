# saxo tests

Basic testing is done using:

    ./saxo test

Testing whether pip installation works is done using:

    test/pip-installation

And testing individual commands is done by:

    test/commands

These should be periodically checked using:

    for name in $(find commands -type f | grep -v _)
    do grep -m 1 $name test/shell-commands &> /dev/null || echo $name
    done
