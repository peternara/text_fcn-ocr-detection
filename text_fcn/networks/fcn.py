from __future__ import absolute_import
from six.moves import range

import tensorflow as tf

from text_fcn import tf_utils
from text_fcn.networks.vgg_net import create_vgg_net


def create_fcn(placeholder, keep_prob, classes):
    """
    Setup the main conv/deconv network
    """
    with tf.variable_scope('inference'):
        vgg_net = create_vgg_net(placeholder)
        conv_final = vgg_net['conv5_4']
        output = tf_utils.max_pool_2x2(conv_final)

        conv_shapes = [
            [7, 7, 512, 4096],
            [1, 1, 4096, 4096],
            [1, 1, 4096, classes]
        ]

        for i, conv_shape in enumerate(conv_shapes):
            with tf.variable_scope('conv%d' % (i + 6)):
                W = tf_utils.weight_variable(conv_shape)
                b = tf_utils.bias_variable(conv_shape[-1:])
                output = tf_utils.conv2d_basic(output, W, b)
            with tf.variable_scope('relu%d' % (i + 6)):
                if i < 2:
                    output = tf.nn.relu(output)
                    tf_utils.add_activation_summary(output, collections=['train'])
                    output = tf.nn.dropout(output, keep_prob=keep_prob)

        pool4 = vgg_net['pool4']
        pool3 = vgg_net['pool3']

        deconv_shapes = [
            tf.shape(pool4),
            tf.shape(pool3),
            tf.stack([
                tf.shape(placeholder)[0], tf.shape(placeholder)[1],
                tf.shape(placeholder)[2], classes
            ])
        ]

        W_shapes = [
            [4, 4, pool4.get_shape()[3].value, classes],
            [4, 4, pool3.get_shape()[3].value, pool4.get_shape()[3].value],
            [16, 16, classes, pool3.get_shape()[3].value]
        ]

        b_shapes = [[shape[2]] for shape in W_shapes]

        strides = [2, 2, 8]

        for i in range(3):
            with tf.variable_scope('deconv%d' % (i + 1)):
                W = tf_utils.weight_variable(W_shapes[i])
                b = tf_utils.bias_variable(b_shapes[i])
                output = tf_utils.conv2d_transpose_strided(
                    output, W, b,
                    output_shape=deconv_shapes[i], stride=strides[i])
            with tf.variable_scope('skip%d' % (i + 1)):
                if i < 2:
                    output = tf.add(output, vgg_net['pool%d' % (4 - i)])

        prediction = tf.argmax(output, dimension=3, name='prediction')
    return tf.expand_dims(prediction, dim=3), output
