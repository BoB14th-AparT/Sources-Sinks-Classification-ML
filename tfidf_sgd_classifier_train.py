# 1. 필요한 라이브러리 임포트
import pandas as pd
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
import scipy.sparse as sp
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, log_loss, confusion_matrix, ConfusionMatrixDisplay, classification_report
import matplotlib.pyplot as plt
from tqdm.notebook import tqdm
from sklearn.utils import shuffle

# CSV 파일 경로 설정
CSV_PATH = "/content/gdrive/MyDrive/Colab Notebooks/BoB/BoB_2nd_Android/source_sink_neither.csv"

# 2. 데이터 로드 및 라벨 전처리
print("Loading and preprocessing data...")
df = pd.read_csv(CSV_PATH, sep=',', engine='python', on_bad_lines='skip')

# 'labels' 컬럼 이름을 'role'로 변경 (일관성 유지)
if 'labels' in df.columns:
    df.rename(columns={'labels': 'role'}, inplace=True)
elif 'label' in df.columns:
    df.rename(columns={'label': 'role'}, inplace=True)
else:
    print("Warning: Neither 'labels' nor 'label' column found. Ensure the label column is named 'role' or adjust the code.")

# SOURCE, SINK, NEITHER 값을 소문자로 변환
df['role'] = df['role'].replace({'SOURCE': 'source', 'SINK': 'sink', 'NEITHER': 'neither'})

# 필요한 라벨만 유지 (source, sink, neither)
df_filtered = df[df['role'].isin(['source', 'sink', 'neither'])].copy()

print("Data loaded and filtered.")
display(df_filtered.head())
print("\nClass distribution after filtering:")
display(df_filtered['role'].value_counts())

# 입력(X)과 라벨(y) 분리
X_text = df_filtered['api_path']
y = df_filtered['role']

# 3. 학습/검증/테스트 데이터 분할 (70:15:15 비율, 계층적 분리)
print("\nSplitting data into 70:15:15 train/val/test sets with stratification...")
X_train_text, X_temp_text, y_train, y_temp = train_test_split(
    X_text, y, test_size=0.30, random_state=42, stratify=y)

X_val_text, X_test_text, y_val, y_test = train_test_split(
    X_temp_text, y_temp, test_size=0.50, random_state=42, stratify=y_temp)

print("Data splitting complete.")
print("\nSplit data shapes:")
print("X_train_text:", X_train_text.shape)
print("y_train:", y_train.shape)
print("X_val_text:", X_val_text.shape)
print("y_val:", y_val.shape)
print("X_test_text:", X_test_text.shape)
print("y_test:", y_test.shape)

print("\n--- Class Distribution in Splits ---")
print("Training Set (y_train):")
print(y_train.value_counts())
print("\nValidation Set (y_val):")
print(y_val.value_counts())
print("\nTest Set (y_test):")
print(y_test.value_counts())

# 4. TF-IDF Vectorization
print("\nApplying TF-IDF vectorization...")
tfidf_vectorizer = TfidfVectorizer()

# 학습 데이터로 fit 후 모든 데이터셋 transform
X_train = tfidf_vectorizer.fit_transform(X_train_text)
X_val = tfidf_vectorizer.transform(X_val_text)
X_test = tfidf_vectorizer.transform(X_test_text)

print("TF-IDF vectorization complete.")
print("\nShape of TF-IDF features:")
print("X_train:", X_train.shape)
print("X_val:", X_val.shape)
print("X_test:", X_test.shape)

# 5. 클래스 가중치 계산
print("\nCalculating class weights...")
classes = np.unique(y_train)
class_weights_array_balanced = compute_class_weight('balanced', classes=classes, y=y_train)
class_weights_balanced = dict(zip(classes, class_weights_array_balanced))
print("Calculated Balanced Class Weights:")
print(class_weights_balanced)

# --- 'sink' 클래스 가중치 수동 증가 ---
class_weights_manual = class_weights_balanced.copy()
class_weights_manual['sink'] = class_weights_balanced['sink'] * 1.5
print("\nManually Adjusted Class Weights (increasing 'sink' weight):")
print(class_weights_manual)

# 실제 학습에 사용할 가중치 선택
# class_weights_to_use = class_weights_balanced # 균형 가중치 사용
class_weights_to_use = class_weights_manual # 수동 조정 가중치 사용

# 6. SGDClassifier 설정 (loss='log_loss')
print("\nSGDClassifier 설정 중 (loss='log_loss')...")

# --- 조정 가능한 하이퍼파라미터 ---
LEARNING_RATE = 0.01  # 학습률 감소
ALPHA = 0.0001         # 정규화 강도
NUM_EPOCHS = 300       # Epoch 수
MINI_BATCH_SIZE = 128  # 미니배치 크기
# -------------------------------

sgd_clf = SGDClassifier(loss='log_loss', warm_start=True, max_iter=1, random_state=42,
                        learning_rate='constant', eta0=LEARNING_RATE, alpha=ALPHA,
                        class_weight=class_weights_to_use)

print("SGDClassifier defined.")
print(f"  Loss Function: log_loss")
print(f"  Learning Rate: constant (eta0={LEARNING_RATE})")
print(f"  Regularization (alpha): {ALPHA}")
print(f"  Number of Epochs: {NUM_EPOCHS}")
print(f"  Mini-batch Size: {MINI_BATCH_SIZE}")
print(f"  Class Weights Used: {class_weights_to_use}")

# 7. 수동 학습 루프 실행 및 성능 측정
print("\nStarting manual training loop...")

# 학습/검증 정확도 및 LogLoss 저장 리스트
train_acc_history = []
val_acc_history = []
train_logloss_history = []
val_logloss_history = []

# Epoch 반복 수행
for epoch in tqdm(range(NUM_EPOCHS), desc="Training Epochs"):
    # 매 epoch마다 데이터 셔플
    X_train_shuffled, y_train_shuffled = shuffle(X_train, y_train, random_state=42 + epoch)

    # Mini-batch SGD 업데이트
    for i in range(0, X_train_shuffled.shape[0], MINI_BATCH_SIZE):
        X_mini_batch = X_train_shuffled[i:i + MINI_BATCH_SIZE]
        y_mini_batch = y_train_shuffled[i:i + MINI_BATCH_SIZE]

        # 첫 epoch 첫 batch에서는 classes 제공해야 함
        if epoch == 0 and i == 0:
            sgd_clf.partial_fit(X_mini_batch, y_mini_batch, classes=classes)
        else:
            sgd_clf.partial_fit(X_mini_batch, y_mini_batch)

    # Epoch 후 성능 평가
    y_train_pred_epoch = sgd_clf.predict(X_train)
    y_val_pred_epoch = sgd_clf.predict(X_val)

    # 정확도 계산
    train_acc_epoch = accuracy_score(y_train, y_train_pred_epoch)
    val_acc_epoch = accuracy_score(y_val, y_val_pred_epoch)

    # LogLoss 계산
    try:
        y_train_proba_epoch = sgd_clf.predict_proba(X_train)
        y_val_proba_epoch = sgd_clf.predict_proba(X_val)

        train_logloss_epoch = log_loss(y_train, y_train_proba_epoch, labels=classes)
        val_logloss_epoch = log_loss(y_val, y_val_proba_epoch, labels=classes)

    except ValueError as e:
        print(f"Could not calculate LogLoss for epoch {epoch + 1}: {e}")
        train_logloss_epoch = np.nan
        val_logloss_epoch = np.nan

    # 기록 저장
    train_acc_history.append(train_acc_epoch)
    val_acc_history.append(val_acc_epoch)
    train_logloss_history.append(train_logloss_epoch)
    val_logloss_history.append(val_logloss_epoch)

    # Epoch 결과 출력
    tqdm.write(f"Epoch {epoch + 1}/{NUM_EPOCHS} -> Acc T/V: {train_acc_epoch:.4f}/{val_acc_epoch:.4f} | LogLoss T/V: {train_logloss_epoch:.4f}/{val_logloss_epoch:.4f}")

print("\nTraining loop finished.")

# 8. Epoch별 Accuracy 및 LogLoss 그래프 출력
print("\nPlotting accuracy and LogLoss history...")

# Accuracy 그래프
plt.figure(figsize=(10, 5))
plt.plot(range(1, NUM_EPOCHS + 1), train_acc_history, label='Train Accuracy')
plt.plot(range(1, NUM_EPOCHS + 1), val_acc_history, label='Validation Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.title('Accuracy over Epochs')
plt.legend()
plt.grid(True)
plt.show()

# LogLoss 그래프
plt.figure(figsize=(10, 5))
plt.plot(range(1, NUM_EPOCHS + 1), train_logloss_history, label='Train LogLoss')
plt.plot(range(1, NUM_EPOCHS + 1), val_logloss_history, label='Validation LogLoss')
plt.xlabel('Epoch')
plt.ylabel('LogLoss')
plt.title('LogLoss over Epochs')
plt.legend()
plt.grid(True)
plt.show()

print("Plotting complete.")

# 9. 최종 테스트 성능 평가 및 Confusion Matrix 출력
print("\nFinal Performance Evaluation and Confusion Matrices (on Test Set)...")

# 테스트 데이터 예측
y_test_pred = sgd_clf.predict(X_test)
y_test_proba = sgd_clf.predict_proba(X_test)

# 최종 테스트 성능
final_test_acc = accuracy_score(y_test, y_test_pred)
final_test_logloss = log_loss(y_test, y_test_proba, labels=classes)

print(f"\nFinal Test Accuracy: {final_test_acc:.4f}")
print(f"Final Test LogLoss: {final_test_logloss:.4f}")

# Confusion Matrix 출력용 클래스
display_classes = classes

# 학습셋 Confusion Matrix (마지막 epoch 기준)
print("\nConfusion Matrix for Training Set (Last Epoch):")
cm_train = confusion_matrix(y_train, y_train_pred_epoch, labels=display_classes)
cmd_train = ConfusionMatrixDisplay(confusion_matrix=cm_train, display_labels=display_classes)
fig_train, ax_train = plt.subplots(figsize=(8, 6))
cmd_train.plot(ax=ax_train, cmap=plt.cm.Blues)
plt.title("Confusion Matrix for Training Set (Last Epoch)")
plt.tight_layout()
plt.savefig('confusion_matrix_train.png')
plt.show()

# 검증셋 Confusion Matrix
print("\nConfusion Matrix for Validation Set (Last Epoch):")
cm_val = confusion_matrix(y_val, y_val_pred_epoch, labels=display_classes)
cmd_val = ConfusionMatrixDisplay(confusion_matrix=cm_val, display_labels=display_classes)
fig_val, ax_val = plt.subplots(figsize=(8, 6))
cmd_val.plot(ax=ax_val, cmap=plt.cm.Blues)
plt.title("Confusion Matrix for Validation Set (Last Epoch)")
plt.tight_layout()
plt.savefig('confusion_matrix_val.png')
plt.show()

# 테스트셋 Confusion Matrix
print("\nConfusion Matrix for Test Set:")
cm_test = confusion_matrix(y_test, y_test_pred, labels=display_classes)
cmd_test = ConfusionMatrixDisplay(confusion_matrix=cm_test, display_labels=display_classes)
fig_test, ax_test = plt.subplots(figsize=(8, 6))
cmd_test.plot(ax=ax_test, cmap=plt.cm.Blues)
plt.title("Confusion Matrix for Test Set")
plt.tight_layout()
plt.savefig('confusion_matrix_test.png')
plt.show()

# 테스트셋 정밀도/재현율/ F1 포함 보고서 출력
print("\nClassification Report for Test Set:")
print(classification_report(y_test, y_test_pred, labels=display_classes))

print("\nConfusion Matrices generated and saved.")
