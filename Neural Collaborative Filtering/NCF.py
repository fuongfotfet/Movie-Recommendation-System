import os
import sys
import shutil
import numpy as np
import pandas as pd

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

df = movielens.load_pandas_df(
    size=MOVIELENS_DATA_SIZE,
    header=["userID", "itemID", "rating", "timestamp"]
)


last_100_user_ids = df['userID'].drop_duplicates().tail(100)
df_test_last_100 = df[df['userID'].isin(last_100_user_ids)]
df = df[~df['userID'].isin(last_100_user_ids)]
print(df)
# Sort DataFrame by userID
df_test_last_100 = df_test_last_100.sort_values(by='userID')
df = df.sort_values(by='userID')

print(df_test_last_100)
#take info about the last 100 userID and store it in a new df, remove it from original df
train, test = python_chrono_split(df, 0.75)

test = test[test["userID"].isin(train["userID"].unique())]
test = test[test["itemID"].isin(train["itemID"].unique())]

leave_one_out_test = test.groupby("userID").last().reset_index()

train_file = "data/train.csv"
test_file = "data/test.csv"
leave_one_out_test_file = "data/leave_one_out_test.csv"
train.to_csv(train_file, index=False)
test.to_csv(test_file, index=False)
leave_one_out_test.to_csv(leave_one_out_test_file, index=False)

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

model.load(neumf_dir='NeuMF_trained_model1')

model.user2id = data.user2id
model.item2id = data.item2id
model.id2user = data.id2user
model.id2item = data.id2item

predictions = [[row.userID, row.itemID, model.predict(row.userID, row.itemID)]
               for (_, row) in test.iterrows()]


predictions = pd.DataFrame(predictions, columns=['userID', 'itemID', 'prediction'])
predictions.head()

df_test_last_100.to_csv("data/test_last_100_user.csv", index=False)

# Get the last interaction of each user in df_test_last_100 and store it in a new DataFrame
df_last_interaction = df_test_last_100.groupby('userID').last().reset_index()

print(df_last_interaction)

# Save df_last_interaction to CSV
df_last_interaction.to_csv("data/last_interaction_test_last_100_user.csv", index=False)

df_test_last_100 = df_test_last_100[~df_test_last_100.set_index(['userID', 'itemID']).index.isin(df_last_interaction.set_index(['userID', 'itemID']).index)]
print(df_test_last_100)

with Timer() as test_time:

    users, items, preds = [], [], []
    item = list(train.itemID.unique())
    for user in train.userID.unique():
        user = [user] * len(item)
        users.extend(user)
        items.extend(item)
        preds.extend(list(model.predict(user, item, is_list=True)))

    all_predictions = pd.DataFrame(data={"userID": users, "itemID":items, "prediction":preds})

    merged = pd.merge(train, all_predictions, on=["userID", "itemID"], how="outer")
    all_predictions = merged[merged.rating.isnull()].drop('rating', axis=1)

print("Took {} seconds for prediction.".format(test_time.interval))

all_predictions['prediction'] = all_predictions['prediction'] * 4 + 1
all_predictions.head()


def calculate_hr_ndcg(model, data, top_k=TOP_K):
    ndcgs = []
    hit_ratio = []

    for b in data.test_loader():
        user_input, item_input, labels = b
        output = model.predict(user_input, item_input, is_list=True)
        output_df = pd.DataFrame({'prediction': output, 'itemID': item_input})
        top_k_predictions = output_df.sort_values(by='prediction', ascending=False).head(top_k)
        output = np.squeeze(output)
        rank = sum(output >= output[0])
        if rank <= top_k:
            ndcgs.append(1 / np.log(rank + 1))
            hit_ratio.append(1)
        else:
            ndcgs.append(0)
            hit_ratio.append(0)

    eval_ndcg = np.mean(ndcgs)
    eval_hr = np.mean(hit_ratio)
    return eval_hr, eval_ndcg

# Evaluate model
eval_hr, eval_ndcg = calculate_hr_ndcg(model, data)
print("HR:\t%f" % eval_hr)
print("NDCG:\t%f" % eval_ndcg)

new_user_data123 = df_test_last_100[df_test_last_100['userID'] == 820]
print(new_user_data123)

min_rating = new_user_data123['rating'].min()
max_rating = new_user_data123['rating'].max()

# Áp dụng công thức chuẩn hóa
new_user_data123['rating_normalized'] = (new_user_data123['rating'] - min_rating) / (max_rating - min_rating)

print(new_user_data123)

# Chuẩn hóa giá trị rating của df_last_interaction
min_rating_interaction = df_last_interaction['rating'].min()
max_rating_interaction = df_last_interaction['rating'].max()

# Áp dụng công thức chuẩn hóa
df_last_interaction['rating_normalized'] = (df_last_interaction['rating'] - min_rating_interaction) / (max_rating_interaction - min_rating_interaction)

print(df_last_interaction)


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


# Tính vector đại diện người dùng mới
user_embedding = calculate_user_embedding(new_user_data123, model)
user_embedding


print("User Embedding from Weighted Pooling:", user_embedding)
print("Mean Value of Embedding:", user_embedding.mean())
print("Standard Deviation of Embedding:", user_embedding.std())


new_user_id = 820

if new_user_id not in model.user2id:
    new_user_index = len(model.user2id)  # Gán chỉ số mới
    model.user2id[new_user_id] = new_user_index
    model.id2user[new_user_index] = new_user_id

print(f"Updated user2id: {model.user2id}")

def predict_ratings_for_new_user(user_id, user_embedding, model, train_data, top_k=10):
    unseen_items = set(model.id2item.keys()) - set(train_data[train_data['userID'] == user_id]['itemID'])
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


# Dự đoán và lấy kết quả
predictions_df = predict_ratings_for_new_user(new_user_id, user_embedding, model, train)
predictions_df


def generate_and_check_predictions(new_user_id, model, top_k=TOP_K):
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
    predictions_df = predict_ratings_for_new_user(new_user_id, user_embedding, model, new_user_data, top_k=top_k)

    # Check if df_last_interaction is in the top-k predictions
    last_interaction = df_last_interaction[df_last_interaction['userID'] == new_user_id]
    if not last_interaction.empty:
        item_id = last_interaction.iloc[0]['itemID']
        if item_id in predictions_df['itemID'].values:
          return True
        else:
          return False
    else:
      return False

correct_recommendations = 0
for user_id in df_test_last_100['userID'].unique():
    if generate_and_check_predictions(user_id, model):
        correct_recommendations += 1

print(f"Number of correct recommendations: {correct_recommendations} out of 100")


