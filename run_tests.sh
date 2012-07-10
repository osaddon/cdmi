#!/bin/sh

pylint -d W0511,I0011,E1101,E0611,F0401 -i y --report no cdmi/*.py

# Make sure the test.conf is in /etc/swift!!

nosetests --with-coverage --cover-html --cover-erase --cover-package=cdmi

pep8 --repeat --statistics --count cdmi

pyflakes cdmi

echo '\n Pychecker report \n****************************************\n'

pychecker -# 99 cdmi/*.py cdmi/cdmiapp/*.py

