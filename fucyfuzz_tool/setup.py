#!/usr/bin/env python
"""
Fucyfuzz
==============
- A friendly automotive security exploration tool, initiated as part of the research project HEAVENS (HEAling
  Vulnerabilities to ENhance Software Security and Safety), now a stand-alone project.
- A zero-knowledge tool that can be dropped onto an automotive network and collect information regarding what
  services and vulnerabilities exist.
"""

from setuptools import find_packages, setup

version = "0.7"
dl_version = "master" if "dev" in version else "v{}".format(version)

print(r"""---------------------------------------
 Installing Fucyfuzz version {0}
---------------------------------------
""".format(version))

setup(
    name="fucyfuzz",
    version=version,
    author="Kasper Karlsson",
    # author_email="TBD",
    description="A friendly automotive security exploration tool",
    long_description=__doc__,
    url="https://github.com/CaringCaribou/fucyfuzz/",
    download_url="https://github.com/CaringCaribou/fucyfuzz/tarball/{}".format(dl_version),
    license="GPLv3",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "python-can"
    ],
    entry_points={
        "console_scripts": [
            "cc.py=fucyfuzz.fucyfuzz:main",
            "fucyfuzz=fucyfuzz.fucyfuzz:main", 
        ],
        "fucyfuzz.modules": [
            "dcm = fucyfuzz.modules.dcm",
            "doip = fucyfuzz.modules.doip",
            "dump = fucyfuzz.modules.dump",
            "fuzzer = fucyfuzz.modules.fuzzer",
            "lenattack = fucyfuzz.modules.lenattack",
            "listener = fucyfuzz.modules.listener",
            "send = fucyfuzz.modules.send",
            "test = fucyfuzz.modules.test",
            "uds_fuzz = fucyfuzz.modules.uds_fuzz",
            "uds = fucyfuzz.modules.uds",
            "xcp = fucyfuzz.modules.xcp",
        ]
    }
)

print(r"""-------------------------------------------------------------------
 Installation completed, run `fucyfuzz --help` to get started
-------------------------------------------------------------------
""")
