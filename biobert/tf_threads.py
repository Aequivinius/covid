#!/usr/bin/env python3
# coding: utf8

# Author: Lenz Furrer, 2019


"""
Read thread settings from env variables and set them in tensorflow.

This module is a simple hook to read settings from env vars
and pass them to TensorFlow.

```sh
$ export TF_INTRA_OP_THREADS=12
$ export TF_INTER_OP_THREADS=12
```

There are two ways to integrate this module with a Python script:
  - simply import this module inside the script
    ```py
    import tf_threads
    ...
    del tf_threads  # only imported for the side effect
    ```

  - run this module as a script, specifying another script
    as the next argument on the command line
    ```sh
    $ ./tf_threads.py ./train.py [training options...]
    ```
"""


import os
import sys
import importlib.util

import tensorflow as tf


intra = int(os.environ.get('TF_INTRA_OP_THREADS', 4))
inter = int(os.environ.get('TF_INTER_OP_THREADS', 4))

try:
    config = tf.ConfigProto()
except AttributeError:
    # Tensorflow 2.x
    tf.config.threading.set_intra_op_parallelism_threads(intra)
    tf.config.threading.set_inter_op_parallelism_threads(inter)
else:
    # Tensorflow 1.x
    from keras.backend.tensorflow_backend import set_session
    config.intra_op_parallelism_threads = intra
    config.inter_op_parallelism_threads = inter
    set_session(tf.Session(config=config))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].endswith('.py'):
        sys.argv.pop(0)
        spec = importlib.util.spec_from_file_location('__main__', sys.argv[0])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
