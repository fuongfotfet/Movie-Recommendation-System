# -*- coding: utf-8 -*-
"""final real.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1-qyzJg8nh4XMfBtlqfUo5yevC45_A4y3
"""

pip install numpy pandas tensorflow recommenders

import tensorflow as tf

#check eager enable
tf.executing_eagerly()

from google.colab import drive
drive.mount('/content/drive')

!pip install "pandera>=0.5.0,<0.17"

import os
import sys
import shutil
import numpy as np
import pandas as pd

tf.get_logger().setLevel('ERROR') # only show error messages

from recommenders.utils.timer import Timer
from recommenders.models.ncf.ncf_singlenode import NCF
from recommenders.models.ncf.dataset import Dataset as NCFDataset
from recommenders.datasets import movielens
from recommenders.datasets.python_splitters import python_chrono_split
from recommenders.evaluation.python_evaluation import (
    map, ndcg_at_k, precision_at_k, recall_at_k
)
from recommenders.utils.constants import SEED as DEFAULT_SEED
from recommenders.utils.notebook_utils import store_metadata

# top k items to recommend
TOP_K = 10

# Select MovieLens data size: 100k, 1m, 10m, or 20m
MOVIELENS_DATA_SIZE = '100k'

# Model parameters
EPOCHS = 100
BATCH_SIZE = 256

SEED = DEFAULT_SEED  # Set None for non-deterministic results

train_file = "/content/drive/MyDrive/train (1).csv"
test_file = "/content/drive/MyDrive/test (1).csv"
leave_one_out_test_file = "/content/drive/MyDrive/leave_one_out_test.csv"

data = NCFDataset(train_file=train_file, test_file=leave_one_out_test_file, seed=SEED, overwrite_test_file_full=True)

model = NCF(
    n_users=data.n_users,
    n_items=data.n_items,
    model_type="NeuMF",
    n_factors=4,
    layer_sizes=[16, 8, 4],
    n_epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    learning_rate=1e-3,
    verbose=10,
    seed=SEED
)

model.load(neumf_dir='/content/drive/MyDrive/NeuMF_trained_model1')

model.user2id = data.user2id
model.item2id = data.item2id
model.id2user = data.id2user
model.id2item = data.id2item

df_test_last_100 = pd.read_csv("/content/drive/MyDrive/test_last_100_user (2).csv")
# Get the last interaction of each user in df_test_last_100 and store it in a new DataFrame
df_last_interaction = df_test_last_100.groupby('userID').last().reset_index()
# Save df_last_interaction to CSV
df_last_interaction.to_csv("./last_interaction_test_last_100_user.csv", index=False)

df_test_last_100 = df_test_last_100[~df_test_last_100.set_index(['userID', 'itemID']).index.isin(df_last_interaction.set_index(['userID', 'itemID']).index)]

min_rating_interaction = df_last_interaction['rating'].min()
max_rating_interaction = df_last_interaction['rating'].max()

df_last_interaction['rating_normalized'] = (df_last_interaction['rating'] - min_rating_interaction) / (max_rating_interaction - min_rating_interaction)

def calculate_user_embedding(history, model):
    embeddings = []
    weights = []  # Danh sách trọng số (ratings)

    for _, row in history.iterrows():
        if row['itemID'] in model.item2id:  # Kiểm tra nếu itemID tồn tại trong từ điển
            item_idx = model.item2id[row['itemID']]  # Lấy index của item

            # Lấy embedding từ phần GMF
            item_embedding_gmf = model.sess.run(model.embedding_gmf_Q)[item_idx]
            # Lấy embedding từ phần MLP
            item_embedding_mlp = model.sess.run(model.embedding_mlp_Q)[item_idx]

            # Kết hợp embedding từ GMF và MLP
            item_embedding = np.concatenate([item_embedding_gmf, item_embedding_mlp])

            embeddings.append(item_embedding)
            weights.append(row['rating_normalized'])  # Sử dụng rating làm trọng số

    if embeddings:
        # Tính trung bình có trọng số
        user_embedding = np.average(embeddings, axis=0, weights=weights)
    else:
        user_embedding = np.zeros(model.embedding_gmf_Q.shape[1] + model.embedding_mlp_Q.shape[1])  # Trả về vector 0 nếu không có

    return user_embedding

movies = pd.read_csv('/content/drive/MyDrive/movies.csv')
# Tách tên phim và năm phát hành
movies['release_year'] = movies['title'].str.extract(r'\((\d{4})\)', expand=False)
movies['movie_title'] = movies['title'].str.replace(r'\(\d{4}\)', '', regex=True).str.strip()

# Hàm dự đoán cải tiến
def predict_ratings_for_new_user(new_user_id, user_embedding, model, train_data, top_k=10):

    if new_user_id not in model.user2id:
        new_user_index = len(model.user2id)  # Gán chỉ số mới
        model.user2id[new_user_id] = new_user_index
        model.id2user[new_user_index] = new_user_id
    unseen_items = set(model.id2item.keys()) - set(train_data[train_data['userID'] == new_user_id]['itemID'])
    print(f"Unseen items: {len(unseen_items)}")

    predictions = []
    for item_id in unseen_items:
        if item_id in model.item2id:  # Kiểm tra nếu item_id có trong item2id
            item_idx = model.item2id[item_id]
            # Lấy embedding từ phần GMF
            item_embedding_gmf = model.sess.run(model.embedding_gmf_Q)[item_idx]
            # Lấy embedding từ phần MLP
            item_embedding_mlp = model.sess.run(model.embedding_mlp_Q)[item_idx]

            # Kết hợp embedding từ GMF và MLP
            item_embedding = np.concatenate([item_embedding_gmf, item_embedding_mlp])

            # Tính toán điểm dự đoán
            prediction = np.dot(user_embedding, item_embedding)
            predictions.append({'itemID': item_id, 'prediction': prediction})

    if not predictions:
        print("No predictions generated. Please check unseen items and model.item2id mapping.")
        return pd.DataFrame(columns=['itemID', 'prediction'])

    # Tạo DataFrame từ danh sách dự đoán
    predictions_df = pd.DataFrame(predictions)
    # predictions_df['prediction'] = predictions_df['prediction'].clip(1, 5)

    # Sắp xếp theo điểm dự đoán và lấy top K
    top_k_predictions = predictions_df.sort_values(by='prediction', ascending=False).head(top_k+10)
    return top_k_predictions

def final(new_user_id, model, top_k = TOP_K):

    if new_user_id not in model.user2id:
        new_user_index = len(model.user2id)  # Gán chỉ số mới
        model.user2id[new_user_id] = new_user_index
        model.id2user[new_user_index] = new_user_id

    # Generate new user data and embedding
    new_user_data = df_test_last_100[df_test_last_100['userID'] == new_user_id]

    min_rating = new_user_data['rating'].min()
    max_rating = new_user_data['rating'].max()
    new_user_data['rating_normalized'] = (new_user_data['rating'] - min_rating) / (max_rating - min_rating)

    user_embedding = calculate_user_embedding(new_user_data, model)

    # Predict ratings for new user
    predictions_df = predict_ratings_for_new_user(new_user_id, user_embedding, model, new_user_data, top_k=top_k-10)

    predictions_df = predictions_df.merge(movies[['item_id', 'movie_title', 'release_year']],
                                          how='left',
                                          left_on='itemID',
                                          right_on='item_id')
    predictions_df = predictions_df[['itemID', 'movie_title', 'release_year']]
    print(predictions_df)

final(822, model)