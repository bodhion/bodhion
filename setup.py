from setuptools import setup

setup(
    name='bodhion',
    version='1.0.0',
    description='Crypto trading bot',
    url='https://github.com/bodhion/bodhion',
    author='bodhion',
    author_email='bodhion@bodhion.com',
    license='MIT',
    packages=['bodhion'],
    install_requires=['cryptobt', 'backtrader', 'pika'],
)