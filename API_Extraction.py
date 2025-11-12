from androguard.misc import AnalyzeAPK
import json
import csv
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('androguard')
logger.setLevel(logging.INFO)

def extract_all_apis(apk_path):
    """APK에서 모든 API 호출을 추출"""
    
    print(f"Analyzing: {apk_path}")
    a, d, dx = AnalyzeAPK(apk_path)
    
    api_calls = []
    
    # 모든 메서드 분석
    for method_analysis in dx.get_methods():
        method = method_analysis.method 
        class_name = method.get_class_name()
        method_name = method.get_name()
        
        # 외부 API 호출 찾기
        for _, call, _ in method_analysis.get_xref_to() :
            called_class = call.get_class_name()
            called_method = call.get_name()
            called_descriptor = call.get_descriptor()
            
            api_calls.append({
                'caller_class': class_name,
                'caller_method': method_name,
                'called_class': called_class,
                'called_method': called_method,
                'descriptor': called_descriptor,
                'full_call': f"{called_class}->{called_method}{called_descriptor}"
            })
    
    return api_calls

def save_to_csv(api_calls, output_file):
    """CSV 파일로 저장"""
    
    if not api_calls:
        print("No API calls found")
        return
    
    keys = api_calls[0].keys()
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(api_calls)
    
    print(f"Saved to CSV: {output_file}")

def save_to_json(api_calls, output_file):
    """JSON 파일로 저장"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(api_calls, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to JSON: {output_file}")

def get_api_statistics(api_calls):
    """API 호출 통계"""
    
    stats = {
        'total_calls': len(api_calls),
        'unique_apis': len(set(call['full_call'] for call in api_calls)),
        'unique_classes': len(set(call['called_class'] for call in api_calls)),
    }
    
    # 가장 많이 호출된 API
    api_counts = defaultdict(int)
    for call in api_calls:
        api_counts[call['full_call']] += 1
    
    stats['top_10_apis'] = sorted(api_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return stats

# 사용 예제
if __name__ == "__main__":
    apk_path = "<.apk_path>"  # APK 파일 경로
    
    # API 추출
    api_calls = extract_all_apis(apk_path)
    
    # CSV 저장
    save_to_csv(api_calls, "api_calls.csv")
    
    # JSON 저장
    save_to_json(api_calls, "api_calls.json")
    
    # 통계 출력
    stats = get_api_statistics(api_calls)
    print(f"\n=== Statistics ===")
    print(f"Total API calls: {stats['total_calls']}")
    print(f"Unique APIs: {stats['unique_apis']}")
    print(f"Unique classes: {stats['unique_classes']}")
    print(f"\nTop 10 most called APIs:")
    for api, count in stats['top_10_apis']:
        print(f"  {count:4d} - {api}")
