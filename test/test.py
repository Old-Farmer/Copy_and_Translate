# test script
import timeit
import paths
import sys
sys.path.append(paths.root_path)
from selextrans.trans import Start, ProcessText

def TestFunc1():
  '''
  '''
  text = 'Bigtable is a distributed storage system for managing\n \
  structured data that is designed to scale to a very large \n\
  size: petabytes of data across thousands of commodity\n \
  servers. Many projects at Google store data in Bigtable, \
  including web indexing, Google Earth, and Google Finance. These applications place very different demands\n \
  on Bigtable, both in terms of data size (from URLs to\n \
  web pages to satellite imagery) and latency requirements\n \
  (from backend bulk processing to real-time data serving). \n \
  Despite these varied demands, Bigtable has successfully \n \
  provided a flexible, high-performance solution for all of \n \
  these Google products. In this paper we describe the simple data model provided by Bigtable, which gives clients  \n \
  dynamic control over data layout and format, and we describe the design and implementation of Bigtable.'

  result = timeit.repeat(stmt="ProcessText(text)", number=100, globals=globals())
  print(result)

def TestlangidPerformence():
  '''
  This test show that the first call of lang.classify is always slow
  '''
  import langid
  import time

  begin = time.time()
  langid.set_languages
  _, _ = langid.classify('你好我是强者' * 10)
  end = time.time()

  print(f'First: {end - begin} s')

  begin = time.time()
  _, _ = langid.classify('你好我是强者' * 10)
  end = time.time()

  print(f'Second: {end - begin} s')