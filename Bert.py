from torch.utils.data import DataLoader
import math
from sentence_transformers import SentenceTransformer,  SentencesDataset, LoggingHandler, losses, models
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from sentence_transformers.readers import STSBenchmarkDataReader
import logging
from datetime import datetime
import sys

#print debug information to stdout
logging.basicConfig(format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO,
                    handlers=[LoggingHandler()])

model_name ='bert-base-uncased'

# Read the dataset
train_batch_size = 16
num_epochs = 4
model_save_path = 'output/training_stsbenchmark_'+model_name.replace("/", "-")+'-'+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
sts_reader = STSBenchmarkDataReader('Data/stsbenchmark', normalize_scores=True)

# Use Huggingface/transformers model (like BERT, RoBERTa, XLNet, XLM-R) for mapping tokens to embeddings
word_embedding_model = models.Transformer(model_name)

# Apply mean pooling to get one fixed sized sentence vector
pooling_model = models.Pooling(word_embedding_model.get_word_embedding_dimension(),
                               pooling_mode_mean_tokens=True,
                               pooling_mode_cls_token=False,
                               pooling_mode_max_tokens=False)

model = SentenceTransformer(modules=[word_embedding_model, pooling_model])

# Convert the dataset to a DataLoader ready for training
logging.info("Read STSbenchmark train dataset")
train_data = SentencesDataset(sts_reader.get_examples('sts-train.csv'), model)
train_dataloader = DataLoader(train_data, shuffle=True, batch_size=train_batch_size)
train_loss = losses.CosineSimilarityLoss(model=model)


logging.info("Read STSbenchmark dev dataset")
evaluator = EmbeddingSimilarityEvaluator.from_input_examples(sts_reader.get_examples('sts-dev.csv'), name='sts-dev')


# Configure the training. We skip evaluation in this example
warmup_steps = math.ceil(len(train_data)*num_epochs/train_batch_size*0.1) #10% of train data for warm-up
logging.info("Warmup-steps: {}".format(warmup_steps))


# Train the model
model.fit(train_objectives=[(train_dataloader, train_loss)],
          evaluator=evaluator,
          epochs=num_epochs,
          evaluation_steps=1000,
          warmup_steps=warmup_steps,
          output_path=model_save_path)

# Load the stored model and evaluate its performance on STS benchmark dataset

model = SentenceTransformer(model_save_path)
test_evaluator = EmbeddingSimilarityEvaluator.from_input_examples(sts_reader.get_examples('sts-test.csv'), name='sts-test')
test_evaluator(model, output_path=model_save_path)