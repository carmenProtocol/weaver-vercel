from setuptools import setup, find_packages

setup(
    name="weaver",
    version="0.1.0",
    description="Automated cryptocurrency trading strategy",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        'ccxt>=3.0.0',
        'python-dotenv>=0.19.0',
        'numpy>=1.21.0',
        'pandas>=1.3.0',
        'SQLAlchemy>=1.4.0',
        'ta-lib>=0.4.24',
        'requests>=2.26.0',
        'python-dateutil>=2.8.2',
        'pytz>=2021.3',
        'aiohttp>=3.8.0',
        'websockets>=10.0',
        'prometheus-client>=0.12.0'
    ],
    python_requires='>=3.8',
) 