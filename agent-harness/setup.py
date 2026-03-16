from setuptools import setup, find_namespace_packages

setup(
    name='cli-anything-flomo',
    version='0.1.0',
    description='CLI harness for flomo - A production-ready command-line interface',
    author='CLI-Anything',
    author_email='support@cli-anything.dev',
    url='https://github.com/cli-anything/flomo-cli',
    packages=find_namespace_packages(include=['cli_anything.*']),
    install_requires=[
        'click>=8.0',
        'requests>=2.28.0',
    ],
    entry_points={
        'console_scripts': [
            'cli-anything-flomo=cli_anything.flomo.flomo_cli:main',
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
        'Programming Language :: Python :: 3.12',
    ],
    keywords='cli flomo notes memo productivity',
    long_description=open('README.md').read() if __import__('os').path.exists('README.md') else '',
    long_description_content_type='text/markdown',
)
