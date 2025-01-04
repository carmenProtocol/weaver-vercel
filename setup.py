from setuptools import setup, find_packages

setup(
    name="weaver",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "ccxt==2.4.96",
        "numpy==1.24.3",
        "pandas==2.0.3",
        "python-dotenv==1.0.0",
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "aiohttp==3.9.1",
        "websockets==12.0"
    ],
    python_requires=">=3.9,<3.10",
) 