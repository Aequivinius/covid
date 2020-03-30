#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Copyright 2018 The Google AI Language Team Authors.
BASED ON Google_BERT.
@Author:zhoukaiyin
"""

import pickle
from pathlib import Path

import tensorflow as tf
from tensorflow.python.ops import math_ops

import modeling
import tokenization



# ----------------------------- FLAGS ------------------------------------------

flags = tf.flags

FLAGS = flags.FLAGS


flags.DEFINE_string(
    "configuration", None, "The configuration to run"
)

flags.DEFINE_string(
    "task_name", "NER", "The name of the task to train."
)

flags.DEFINE_string(
    "data_dir", None,
    "The input-data dir.",
)

flags.DEFINE_string(
    "output_dir", None,
    "The output directory where the predictions will be written."
)

flags.DEFINE_string(
    "input_text", None,
    "File with input text in CoNLL format.",
)

flags.DEFINE_string(
    "tf_record", None,
    "File for preprocessed input records.",
)

flags.DEFINE_string(
    "bert_config_file", None,
    "The config json file corresponding to the pre-trained BERT model."
)

flags.DEFINE_string("vocab_file", None,
                    "The vocabulary file that the BERT model was trained on.")

flags.DEFINE_string(
    "init_checkpoint", None,
    "Initial checkpoint (usually from a pre-trained BERT model)."
)

flags.DEFINE_bool(
    "do_lower_case", False,
    "Whether to lower case the input text."
)

flags.DEFINE_integer(
    "max_seq_length", 128,
    "The maximum total input sequence length after WordPiece tokenization."
)

flags.DEFINE_bool("use_tpu", False, "Whether to use TPU or GPU/CPU.")

flags.DEFINE_bool("do_preprocess", False,
                  "Whether to write a .tf_record file to disk.")
flags.DEFINE_bool("do_predict", False,
                  "Whether to run the model in inference mode on the test set.")

flags.DEFINE_integer("batch_size", 8, "Total batch size.")

flags.DEFINE_integer("save_checkpoints_steps", 1000,
                     "How often to save the model checkpoint.")

flags.DEFINE_integer("iterations_per_loop", 1000,
                     "How many steps to make in each estimator call.")

tf.flags.DEFINE_string("master", None, "[Optional] TensorFlow master URL.")

flags.DEFINE_integer(
    "num_tpu_cores", 8,
    "Only used if `use_tpu` is True. Total number of TPU cores to use.")


# ------------------------- FUNCTIONS ------------------------------------------


def pred_path(suffix):
    """Construct a path in the output directory."""
    base = Path(FLAGS.tf_record).name
    path = Path(FLAGS.output_dir, base).with_suffix(suffix)
    return path


class InputExample:
    """A single training/test example for simple sequence classification."""

    def __init__(self, guid, text, label=None):
        """Constructs a InputExample.

        Args:
          guid: Unique id for the example.
          text_a: string. The untokenized text of the first sequence. For single
            sequence tasks, only this sequence must be specified.
          label: (Optional) string. The label of the example. This should be
            specified for train and dev examples, but not for test examples.
        """
        self.guid = guid
        self.text = text
        self.label = label


class DataProcessor:
    """Base class for data converters for sequence classification data sets."""

    def get_labels(self):
        """Gets the list of labels for this data set."""
        raise NotImplementedError()

    @classmethod
    def _read_data(cls, input_file):
        """Read BIO data."""
        with open(input_file) as f:
            words = []
            labels = []
            for line in f:
                line = line.strip()
                if line.startswith('# doc_id ='):
                    continue
                if line:
                    word = line.split()[0]
                    words.append(word[:50])  # truncate extremely long words
                    labels.append('O')
                else:
                    while len(words) > 30:
                        l = list(filter(None, labels[:30]))
                        w = list(filter(None, words[:30]))
                        yield (l, w)
                        words = words[30:]
                        labels = labels[30:]

                    if not words:
                        continue
                    l = list(filter(None, labels))
                    w = list(filter(None, words))
                    yield (l, w)
                    words = []
                    labels = []
        if words:
            l = list(filter(None, labels))
            w = list(filter(None, words))
            yield (l, w)


class NerProcessor(DataProcessor):

    def get_examples(self, tsv_path):
        return self._create_example(self._read_data(tsv_path), "test")

    def get_labels(self, config='iob'):
        """Get all output labels."""
        # Aliases.
        config = dict(
            bioes='iobes',
            spans='iobes',
            pretrain='pretraining',
            pretrained_ids='pretraining',
        ).get(config, config)
        return getattr(self, f'_get_labels_{config}')()

#* -----------------------------------------------------------------------------

    #? IOB FORMAT
    @staticmethod
    def _get_labels_iob():
        return ["B", "I", "O", "X", "[CLS]", "[SEP]"]

#* -----------------------------------------------------------------------------

    #? BIOES FORMAT -->  num_labels = 9 = 1*4 + 4 + 1   Joseph
    @staticmethod
    def _get_labels_iobes():
        return ["B", "I", "O", "X", "[CLS]", "[SEP]", "E", "S"]

#* -----------------------------------------------------------------------------

    #? IDS FORMAT -->  CHEBI num_labels = ...-> = 481   Joseph
    def _get_labels_ids(self):
        path_to_data = Path(FLAGS.data_dir, 'tag_set.txt')
        return self._get_id_tagset(path_to_data)

    def _get_labels_pretraining(self):
        path_to_data = Path(FLAGS.data_dir, 'tag_set_pretrained.txt')
        return self._get_id_tagset(path_to_data)

    @staticmethod
    def _get_id_tagset(path):
        with open(path, encoding='utf-8') as f:
            tag_set = [line.rstrip() for line  in f]

        tag_set.append("X")
        tag_set.append("[CLS]")
        tag_set.append("[SEP]")

        return tag_set


#* -----------------------------------------------------------------------------

    # #? GLOBAL BIOES FORMAT -->  num_labels = 10*4 + 4 + 1 = 45 Joseph
    @staticmethod
    def _get_labels_global():
        return ["B-CHEBI", "I-CHEBI", "E-CHEBI", "S-CHEBI",
                "B-CL", "I-CL", "E-CL", "S-CL",
                "B-GO_BP", "I-GO_BP", "E-GO_BP", "S-GO_BP",
                "B-GO_CC", "I-GO_CC", "E-GO_CC", "S-GO_CC",
                "B-GO_MF", "I-GO_MF", "E-GO_MF", "S-GO_MF",
                "B-MOP", "I-MOP", "E-MOP", "S-MOP",
                "B-NCBITaxon", "I-NCBITaxon", "E-NCBITaxon", "S-NCBITaxon",
                "B-PR", "I-PR", "E-PR", "S-PR",
                "B-SO", "I-SO", "E-SO", "S-SO",
                "B-UBERON", "I-UBERON", "E-UBERON", "S-UBERON",
                "O", "X", "[CLS]", "[SEP]"]

#* -----------------------------------------------------------------------------

    @staticmethod
    def _create_example(lines, set_type):
        for i, (label, text) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            yield InputExample(guid=guid, text=text, label=label)


def convert_single_example(example,
                           max_seq_length, tokenizer, token_file):
    tokens = []
    for word in example.text:
        token = tokenizer.tokenize(word)
        tokens.extend(token)
    ntokens = ['[CLS]', *tokens[:max_seq_length-2], '[SEP]']
    input_ids = tokenizer.convert_tokens_to_ids(ntokens)
    input_mask = [1] * len(input_ids)
    if len(input_ids) < max_seq_length:
        padding = [0] * (max_seq_length-len(input_ids))
        input_ids.extend(padding)
        input_mask.extend(padding)
    assert len(input_ids) == max_seq_length
    assert len(input_mask) == max_seq_length
    segment_ids = label_ids = [0] * max_seq_length
    feature = dict(
        input_ids=create_int_feature(input_ids),
        input_mask=create_int_feature(input_mask),
        segment_ids=create_int_feature(segment_ids),
        label_ids=create_int_feature(label_ids),
    )

    if len(tokens) > max_seq_length - 2:
        # If the sequence was truncated, re-insert the missing tokens now.
        # They are formatted as a space-separated list appended to the last
        # included token, such that alignment stays intact.
        ntokens[-2] = ' '.join(tokens[max_seq_length-3:])
    for token in ntokens:
        token_file.write(token)
        token_file.write('\n')
    return feature


def create_int_feature(values):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=values))


def file_based_convert_examples_to_features(
        examples, max_seq_length, tokenizer,
        output_path, token_path):
    writer = tf.python_io.TFRecordWriter(output_path)
    token_file = open(token_path, 'w', encoding='utf-8')
    for (ex_index, example) in enumerate(examples):
        if ex_index % 5000 == 0:
            tf.logging.info("Writing example %d" % ex_index)
        feature = convert_single_example(example,
                                         max_seq_length, tokenizer, token_file)
        tf_example = tf.train.Example(
            features=tf.train.Features(feature=feature))
        writer.write(tf_example.SerializeToString())
    token_file.close()


def file_based_input_fn_builder(input_file, seq_length, is_training, drop_remainder):
    name_to_features = {
        "input_ids": tf.FixedLenFeature([seq_length], tf.int64),
        "input_mask": tf.FixedLenFeature([seq_length], tf.int64),
        "segment_ids": tf.FixedLenFeature([seq_length], tf.int64),
        "label_ids": tf.FixedLenFeature([seq_length], tf.int64),
    }

    def _decode_record(record, name_to_features):
        example = tf.parse_single_example(record, name_to_features)
        for name in list(example.keys()):
            t = example[name]
            if t.dtype == tf.int64:
                t = tf.to_int32(t)
            example[name] = t
        return example

    def input_fn(params):
        batch_size = params["batch_size"]
        d = tf.data.TFRecordDataset(input_file)
        if is_training:
            d = d.repeat()
            d = d.shuffle(buffer_size=100)
        d = d.apply(tf.contrib.data.map_and_batch(
            lambda record: _decode_record(record, name_to_features),
            batch_size=batch_size,
            drop_remainder=drop_remainder
        ))
        return d
    return input_fn


# ----------------------------- Create Model -----------------------------------

def create_model(bert_config, is_training, input_ids, input_mask,
                 segment_ids, labels, num_labels, use_one_hot_embeddings):
    model = modeling.BertModel(
        config=bert_config,
        is_training=is_training,
        input_ids=input_ids,
        input_mask=input_mask,
        token_type_ids=segment_ids,
        use_one_hot_embeddings=use_one_hot_embeddings
    )

    output_layer = model.get_sequence_output()

    hidden_size = output_layer.shape[-1].value

    output_weight = tf.get_variable(
        "output_weights", [num_labels, hidden_size],
        initializer=tf.truncated_normal_initializer(stddev=0.02)
    )
    output_bias = tf.get_variable(
        "output_bias", [num_labels], initializer=tf.zeros_initializer()
    )
    with tf.variable_scope("loss"):
        if is_training:
            output_layer = tf.nn.dropout(output_layer, keep_prob=0.9)
        output_layer = tf.reshape(output_layer, [-1, hidden_size])
        logits = tf.matmul(output_layer, output_weight, transpose_b=True)
        logits = tf.nn.bias_add(logits, output_bias)
        logits = tf.reshape(logits, [-1, FLAGS.max_seq_length, num_labels])
        # mask = tf.cast(input_mask,tf.float32)
        # loss = tf.contrib.seq2seq.sequence_loss(logits,labels,mask)
        # return (loss, logits, predict)
        ##########################################################################
        log_probs = tf.nn.log_softmax(logits, axis=-1)
        one_hot_labels = tf.one_hot(labels, depth=num_labels, dtype=tf.float32)
        per_example_loss = -tf.reduce_sum(one_hot_labels * log_probs, axis=-1)
        loss = tf.reduce_sum(per_example_loss)
        probabilities = tf.nn.softmax(logits, axis=-1)
        predict = tf.argmax(probabilities, axis=-1)
        return (loss, per_example_loss, logits, log_probs, predict)
        ##########################################################################


def model_fn_builder(bert_config, num_labels, init_checkpoint, use_tpu,
                     use_one_hot_embeddings):
    def model_fn(features, labels, mode, params):
        input_ids = features["input_ids"]
        input_mask = features["input_mask"]
        segment_ids = features["segment_ids"]
        label_ids = features["label_ids"]
        is_training = False

        total_loss, per_example_loss, logits, log_probs, predicts = create_model(
            bert_config, is_training, input_ids, input_mask, segment_ids, label_ids,
            num_labels, use_one_hot_embeddings)
        tvars = tf.trainable_variables()
        scaffold_fn = None
        if init_checkpoint:
            (assignment_map, initialized_variable_names) = \
                modeling.get_assignment_map_from_checkpoint(tvars, init_checkpoint)
            if use_tpu:
                def tpu_scaffold():
                    tf.train.init_from_checkpoint(init_checkpoint, assignment_map)
                    return tf.train.Scaffold()
                scaffold_fn = tpu_scaffold
            else:
                tf.train.init_from_checkpoint(init_checkpoint, assignment_map)

        output_spec = tf.contrib.tpu.TPUEstimatorSpec(
            mode=mode,
            predictions={"prediction": predicts, "log_probs": log_probs},
            scaffold_fn=scaffold_fn
        )
        return output_spec
    return model_fn

# -------------------------------- Main ----------------------------------------

def main(_):
    tf.logging.set_verbosity(tf.logging.INFO)
    processors = {
        "ner": NerProcessor
    }

    task_name = FLAGS.task_name.lower()
    if task_name not in processors:
        raise ValueError("Task not found: %s" % (task_name))
    processor = processors[task_name]()
    token_path = Path(FLAGS.tf_record).with_suffix(".tokens")

    if FLAGS.do_preprocess or not Path(FLAGS.tf_record).exists():
        tokenizer = tokenization.FullTokenizer(
            vocab_file=FLAGS.vocab_file, do_lower_case=FLAGS.do_lower_case)
        predict_examples = processor.get_examples(FLAGS.input_text)
        file_based_convert_examples_to_features(predict_examples,
                                                FLAGS.max_seq_length, tokenizer,
                                                FLAGS.tf_record, token_path)
    if not FLAGS.do_predict:
        return

    label_list = processor.get_labels(FLAGS.configuration)
    bert_config = modeling.BertConfig.from_json_file(FLAGS.bert_config_file)

    if FLAGS.max_seq_length > bert_config.max_position_embeddings:
        raise ValueError(
            "Cannot use sequence length %d because the BERT model "
            "was only trained up to sequence length %d" %
            (FLAGS.max_seq_length, bert_config.max_position_embeddings))

    tpu_cluster_resolver = None
    if FLAGS.use_tpu and FLAGS.tpu_name:
        tpu_cluster_resolver = tf.contrib.cluster_resolver.TPUClusterResolver(
            FLAGS.tpu_name, zone=FLAGS.tpu_zone, project=FLAGS.gcp_project)

    is_per_host = tf.contrib.tpu.InputPipelineConfig.PER_HOST_V2

    run_config = tf.contrib.tpu.RunConfig(
        cluster=tpu_cluster_resolver,
        master=FLAGS.master,
        model_dir=FLAGS.data_dir,
        save_checkpoints_steps=FLAGS.save_checkpoints_steps,
        tpu_config=tf.contrib.tpu.TPUConfig(
            iterations_per_loop=FLAGS.iterations_per_loop,
            num_shards=FLAGS.num_tpu_cores,
            per_host_input_for_training=is_per_host))

    model_fn = model_fn_builder(
        bert_config=bert_config,
        num_labels=len(label_list)+1,
        init_checkpoint=FLAGS.init_checkpoint,
        use_tpu=FLAGS.use_tpu,
        use_one_hot_embeddings=FLAGS.use_tpu)

    estimator = tf.contrib.tpu.TPUEstimator(
        use_tpu=FLAGS.use_tpu,
        model_fn=model_fn,
        config=run_config,
        train_batch_size=FLAGS.batch_size,
        eval_batch_size=FLAGS.batch_size,
        predict_batch_size=FLAGS.batch_size)

    with open(Path(FLAGS.data_dir, 'label2id.pkl'), 'rb') as rf:
        label2id = pickle.load(rf)
        id2label = {value: key for key, value in label2id.items()}

    if FLAGS.use_tpu:
        # Warning: According to tpu_estimator.py Prediction on TPU is an
        # experimental feature and hence not supported here
        raise ValueError("Prediction in TPU not supported")
    predict_drop_remainder = True if FLAGS.use_tpu else False
    predict_input_fn = file_based_input_fn_builder(
        input_file=FLAGS.tf_record,
        seq_length=FLAGS.max_seq_length,
        is_training=False,
        drop_remainder=predict_drop_remainder)

    sent_lengths = []
    with open(token_path, 'r') as reader:
        for line in reader:
            tok = line.strip()
            if tok == '[CLS]':
                slen = 0
            slen += 1
            if tok == '[SEP]':
                sent_lengths.append(slen)

    result = estimator.predict(input_fn=predict_input_fn)
    tf.logging.info('Serializing predictions...')
    output_predict_file = pred_path(suffix=".labels")
    id_conf = ('ids', 'pretrain', 'pretrained_ids')
    outside_symbol = 'O-NIL' if FLAGS.configuration in id_conf else 'O'
    with open(output_predict_file, 'w') as p_writer:
        for pidx, (prediction, slen) in enumerate(zip(result, sent_lengths)):
            if not pidx % 5000:
                tf.logging.info('Writing prediction %d', pidx)
            output_line = "\n".join(  # change 0 predictions to 'O'
                id2label.get(id, outside_symbol)
                for id in prediction['prediction'][:slen])
            p_writer.write(output_line + "\n")


if __name__ == "__main__":
    tf.app.run()
