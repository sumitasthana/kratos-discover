from setuptools import setup, find_packages

setup(
    name="kratos-discover",
    version="0.1.0",
    description="Finds and extracts risks and associated controls in regulatory documents",
    author="Sumit Asthana",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        "langchain>=0.1.0",
        "langgraph>=0.0.1",
        "pydantic>=2.0",
        "pyyaml>=6.0",
        "python-docx>=0.8.11",
        "pypdf>=3.0",
        "beautifulsoup4>=4.12",
        "lxml>=4.9",
        "structlog>=23.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "kratos-discover=cli:main",
        ],
    },
)
