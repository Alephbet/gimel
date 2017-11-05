#!/usr/bin/env python

from setuptools import setup, find_packages
import os

try:
    from pypandoc import convert

    def read_md(readme_file):
        return convert(readme_file, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")

    def read_md(readme_file):
        with open(readme_file, 'r') as f:
            return f.read()

requires = [
    'awscli>=1.10.21',
    'jmespath>=0.9.0',
    'boto3>=1.3.0',
    'click>=6.6',
    'redis>=2.10.5'
]

setup(
    name='gimel',
    version=open(os.path.join('gimel', 'VERSION')).read().strip(),
    description='Run your own A/B testing backend on AWS Lambda',
    long_description=read_md('README.md'),
    author='Yoav Aner',
    author_email='yoav@gingerlime.com',
    url='https://github.com/Alephbet/gimel',
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    zip_safe=False,
    entry_points="""
        [console_scripts]
        gimel=gimel.cli:cli
    """,
    install_requires=requires,
    license=open("LICENSE").read(),
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ),
)
