from distutils.core import setup
setup(name='bein',
      version='0.96',
      url='http://madhadron.com/bein',
      description='Miniature LIMS and workflow manager for bioinformatics',
      author='Fred Ross',
      author_email='madhadron@gmail.com',
      packages=['bein'],
      scripts=['beinclient'],
      classifiers=['Topic :: System :: Shells', 'Topic :: Scientific/Engineering :: Bio-Informatics']
      )
