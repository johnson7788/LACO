# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Functions and classes related to optimization (weight updates)."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import re
import tensorflow as tf


def create_optimizer(loss, init_lr, num_train_steps, num_warmup_steps, use_tpu,
                     layerwise_lr_decay_power=-1, n_transformer_layers=None):
  """Creates an optimizer training op."""
  global_step = tf.compat.v1.train.get_or_create_global_step()

  learning_rate = tf.constant(value=init_lr, shape=[], dtype=tf.float32)

  # Implements linear decay of the learning rate.
  learning_rate = tf.compat.v1.train.polynomial_decay(
      learning_rate,
      global_step,
      num_train_steps,
      end_learning_rate=0.0,
      power=1.0,
      cycle=False)

  # Implements linear warmup. I.e., if global_step < num_warmup_steps, the
  # learning rate will be `global_step/num_warmup_steps * init_lr`.
  if num_warmup_steps:
    global_steps_int = tf.cast(global_step, tf.int32)
    warmup_steps_int = tf.constant(num_warmup_steps, dtype=tf.int32)

    global_steps_float = tf.cast(global_steps_int, tf.float32)
    warmup_steps_float = tf.cast(warmup_steps_int, tf.float32)

    warmup_percent_done = global_steps_float / warmup_steps_float
    warmup_learning_rate = init_lr * warmup_percent_done

    is_warmup = tf.cast(global_steps_int < warmup_steps_int, tf.float32)
    learning_rate = (
        (1.0 - is_warmup) * learning_rate + is_warmup * warmup_learning_rate)
  if layerwise_lr_decay_power > 0:
    learning_rate = _get_layer_lrs(learning_rate, layerwise_lr_decay_power,
                                   n_transformer_layers)
  # It is recommended that you use this optimizer for fine tuning, since this
  # is how the model was trained (note that the Adam m/v variables are NOT
  # loaded from init_checkpoint.)
  optimizer = AdamWeightDecayOptimizer(
      learning_rate=learning_rate,
      weight_decay_rate=0.01,
      beta_1=0.9,
      beta_2=0.999,
      epsilon=1e-6,
      exclude_from_weight_decay=["LayerNorm", "layer_norm", "bias"])

  if use_tpu:
    optimizer = tf.compat.v1.tpu.CrossShardOptimizer(optimizer)

  tvars = tf.compat.v1.trainable_variables()
  grads = tf.gradients(ys=loss, xs=tvars)

  # This is how the model was pre-trained.
  (grads, _) = tf.clip_by_global_norm(grads, clip_norm=1.0)

  train_op = optimizer.apply_gradients(
      zip(grads, tvars), global_step=global_step)

  # Normally the global step update is done inside of `apply_gradients`.
  # However, `AdamWeightDecayOptimizer` doesn't do this. But if you use
  # a different optimizer, you should probably take this line out.
  new_global_step = global_step + 1
  train_op = tf.group(train_op, [global_step.assign(new_global_step)])
  return train_op


class AdamWeightDecayOptimizer(tf.compat.v1.train.Optimizer):
  """A basic Adam optimizer that includes "correct" L2 weight decay."""

  def __init__(self,
               learning_rate,
               weight_decay_rate=0.0,
               beta_1=0.9,
               beta_2=0.999,
               epsilon=1e-6,
               exclude_from_weight_decay=None,
               name="AdamWeightDecayOptimizer"):
    """Constructs a AdamWeightDecayOptimizer."""
    super(AdamWeightDecayOptimizer, self).__init__(False, name)

    self.learning_rate = learning_rate
    self.weight_decay_rate = weight_decay_rate
    self.beta_1 = beta_1
    self.beta_2 = beta_2
    self.epsilon = epsilon
    self.exclude_from_weight_decay = exclude_from_weight_decay

  def _apply_gradients(self, grads_and_vars, learning_rate):
    """See base class."""
    assignments = []
    for (grad, param) in grads_and_vars:
      if grad is None or param is None:
        continue

      param_name = self._get_variable_name(param.name)

      m = tf.compat.v1.get_variable(
          name=param_name + "/adam_m",
          shape=param.shape.as_list(),
          dtype=tf.float32,
          trainable=False,
          initializer=tf.compat.v1.zeros_initializer())
      v = tf.compat.v1.get_variable(
          name=param_name + "/adam_v",
          shape=param.shape.as_list(),
          dtype=tf.float32,
          trainable=False,
          initializer=tf.compat.v1.zeros_initializer())

      # Standard Adam update.
      next_m = (
          tf.multiply(self.beta_1, m) + tf.multiply(1.0 - self.beta_1, grad))
      next_v = (
          tf.multiply(self.beta_2, v) + tf.multiply(1.0 - self.beta_2,
                                                    tf.square(grad)))
      update = next_m / (tf.sqrt(next_v) + self.epsilon)

      # Just adding the square of the weights to the loss function is *not*
      # the correct way of using L2 regularization/weight decay with Adam,
      # since that will interact with the m and v parameters in strange ways.
      #
      # Instead we want ot decay the weights in a manner that doesn't interact
      # with the m/v parameters. This is equivalent to adding the square
      # of the weights to the loss with plain (non-momentum) SGD.
      if self.weight_decay_rate > 0:
        if self._do_use_weight_decay(param_name):
          update += self.weight_decay_rate * param

      update_with_lr = learning_rate * update
      #tf.logging.info("   update_with_lr = %s" % (update_with_lr))
      next_param = param - update_with_lr

      assignments.extend(
          [param.assign(next_param),
           m.assign(next_m),
           v.assign(next_v)])

    return assignments


  def apply_gradients(self, grads_and_vars, global_step=None, name=None):
    #tf.logging.info("self.grads_and_vars = %s" % (grads_and_vars))
    if isinstance(self.learning_rate, dict):
      key_to_grads_and_vars = {}
      for grad, var in grads_and_vars:
        #tf.logging.info("grad = %s, var = %s" % (grad, var))
        update_for_var = False
        for key in self.learning_rate:
          # tf.logging.info("key = %s" % (key))
          if key in var.name:
            update_for_var = True
            if key not in key_to_grads_and_vars:
              key_to_grads_and_vars[key] = []
            key_to_grads_and_vars[key].append((grad, var))
        #if not update_for_var:
          #tf.logging.info("update_for_var is False, var= %s" % (var))
          #raise ValueError("No learning rate specified for variable", var)
      assignments = []
      for key, key_grads_and_vars in key_to_grads_and_vars.items():
        #tf.logging.info("key = %s" % (key))
        #tf.logging.info("key_grads_and_vars = %s" % (key_grads_and_vars))
        assignments += self._apply_gradients(key_grads_and_vars,
                                             self.learning_rate[key])
    else:
      assignments = self._apply_gradients(grads_and_vars, self.learning_rate)
    return tf.group(*assignments, name=name)

  def _do_use_weight_decay(self, param_name):
    """Whether to use L2 weight decay for `param_name`."""
    if not self.weight_decay_rate:
      return False
    if self.exclude_from_weight_decay:
      for r in self.exclude_from_weight_decay:
        if re.search(r, param_name) is not None:
          return False
    return True

  def _get_variable_name(self, param_name):
    """Get the variable name from the tensor name."""
    m = re.match("^(.*):\\d+$", param_name)
    if m is not None:
      param_name = m.group(1)
    return param_name

def _get_layer_lrs(learning_rate, layer_decay, n_layers):
  """Have lower learning rates for layers closer to the input."""
  key_to_depths = collections.OrderedDict({
      "/embeddings/": 0,
      "/embeddings_project/": 0,
      "task_specific/": n_layers + 2,
  })
  for layer in range(n_layers):
    key_to_depths["encoder/layer_" + str(layer) + "/"] = layer + 1
  return {
      key: learning_rate * (layer_decay ** (n_layers + 2 - depth))
      for key, depth in key_to_depths.items()
  }