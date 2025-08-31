from setuptools import setup

package_name = 'rqt_bag_filter'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['plugin.xml', 'package.xml']),
    ],
    install_requires=['pyyaml'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='RQt plugin to play rosbag with topic filtering and YAML profiles',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'rqt_gui_plugins': [
            'bag_filter = rqt_bag_filter.bag_filter_plugin:BagFilterPlugin',
        ],
    },
)
