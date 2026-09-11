"""Setup script for SQL Data Lake Builder."""

from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='sql-data-lake-builder',
    version='1.0.0',
    description='Extract sports data from websites and generate SQL schemas',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Data Lake Team',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'beautifulsoup4==4.12.2',
        'lxml==4.9.3',
        'pandas==2.1.3',
        'numpy==1.26.2',
        'requests==2.31.0',
        'pyyaml==6.0.1',
        'pydantic==2.5.0',
        'click==8.1.7',
        'python-dotenv==1.0.0',
        'tabulate==0.9.0',
        'openpyxl==3.10.10',
    ],
    entry_points={
        'console_scripts': [
            'sql-data-lake-builder=cli:cli',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
