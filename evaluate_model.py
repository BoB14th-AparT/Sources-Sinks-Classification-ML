## 새로운 API 데이터 분류 코드
import pickle
import os

MODEL_SAVE_PATH = "./sgd_model.pkl"
VECTORIZER_SAVE_PATH = "./tfidf_vectorizer.pkl"

# 모델과 벡터라이저 로드
print("\n--- 모델 및 벡터라이저 로드 시작 ---")
try:
    with open(MODEL_SAVE_PATH, 'rb') as f:
        sgd_clf = pickle.load(f)
    print(f"SGDClassifier 모델 로드 완료: {MODEL_SAVE_PATH}")

    with open(VECTORIZER_SAVE_PATH, 'rb') as f:
        tfidf_vectorizer = pickle.load(f)
    print(f"TfidfVectorizer 로드 완료: {VECTORIZER_SAVE_PATH}")
except FileNotFoundError as e:
    print(f"오류: 저장된 모델 또는 벡터라이저 파일을 찾을 수 없습니다. 경로를 확인하세요: {e}")
    exit()
print("--- 로드 완료 ---")

# 1. 분류할 새로운 데이터 CSV 파일 경로 지정 
NEW_DATA_PATH = "./extracted_api_paths.csv"

# 2. 새로운 데이터 로드
try:
    df_new_data = pd.read_csv(NEW_DATA_PATH, sep=',', engine='python', on_bad_lines='skip')
    print(f"새로운 데이터 로드 완료. 총 {len(df_new_data)}개의 API 경로.")
except FileNotFoundError:
    print(f"오류: 파일을 찾을 수 없습니다. 경로를 확인하세요: {NEW_DATA_PATH}")
    exit()

if 'api_path' not in df_new_data.columns:
    print("오류: 데이터프레임에 'api_path' 컬럼이 없습니다. 컬럼명을 확인하세요.")
    exit()

X_new_text = df_new_data['api_path']

# 3. TF-IDF 변환 (훈련에 사용된 Vectorizer 사용)
print("\nTF-IDF 변환 중...")
X_new = tfidf_vectorizer.transform(X_new_text)
print(f"변환된 특성 행렬 크기: {X_new.shape}")

# 4. 훈련된 모델로 예측 수행
print("\n모델 예측 수행 중...")
y_new_pred = sgd_clf.predict(X_new)
y_new_proba = sgd_clf.predict_proba(X_new)

# 5. 결과 정리
classes = sgd_clf.classes_

max_proba = np.max(y_new_proba, axis=1)
proba_df = pd.DataFrame(y_new_proba, columns=[f"proba_{c}" for c in classes])

df_result = pd.concat([df_new_data.reset_index(drop=True), proba_df], axis=1)
df_result['predicted_label'] = y_new_pred
df_result['confidence'] = max_proba

print("\n--- 최종 분류 결과 ---")
display(df_result.head(10))

# 결과를 새로운 CSV 파일로 저장하고 싶다면
df_result.to_csv('predicted_api_data.csv', index=False)