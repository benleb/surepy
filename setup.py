# coding=utf-8

from setuptools import setup

setup(name='surepy',
      # version='0.2.0',
      license='MIT',
      url='http://github.com/benleb/surepy',
      author='Ben Lebherz',
      author_email='git@benleb.de',
      description='Library to interact with the flaps & doors from Sure Petcare',
      long_description=open('README.md').read(),
      long_description_content_type='text/markdown',
      packages=['surepy'],
      zip_safe=False,
      platforms='any',
      setup_requires=["setuptools_scm"],
      use_scm_version={
          "version_scheme": "python-simplified-semver",
          "local_scheme": lambda v: "",
      },
      install_requires=list(val.strip() for val in open('requirements.txt')),
      classifiers=[
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ]
      )
