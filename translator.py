import os
import pandas as pd
import openai
from glob import glob
from dotenv import load_dotenv

MODELS = {
    "1": {"name": "gpt-4o-mini", "description": "GPT-4o-mini (빠르고 경제적)"},
    "2": {"name": "gpt-4o", "description": "GPT-4o (더 정확하고 상세함)"}
}

PROMPT_TEMPLATE = {
    "user": """
    Instruction:
    다음 한글 문장들을 {target_lang}로 번역해주세요. 원문 내용과 문맥을 유지하는 걸 최우선으로 해주시고, 고유명사의 경우엔 널리 사용되는 {target_lang} 표현을 사용해주세요.
    응답은 처리하기 편하게 다른 말 없이 바로 번역된 문장들만 말해주세요.

    번역할 문장:
    {text}
    """
}

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

def get_user_preferences():
    """사용자로부터 모델과 목표 언어 선택받기"""
    # 모델 선택
    print("\n=== 번역 모델 선택 ===")
    for key, model in MODELS.items():
        print(f"{key} - {model['description']}")
    
    while True:
        model_choice = input("모델을 선택하세요 (1 또는 2): ").strip()
        if model_choice in MODELS:
            break
        print("잘못된 선택입니다. 다시 선택해주세요.")
    
    # 목표 언어 선택
    print("\n=== 목표 언어 선택 ===")
    print("예시: 영어, English, 일본어, Japanese, 중국어, Chinese 등")
    target_lang = input("목표 언어를 입력하세요: ").strip()
    
    return MODELS[model_choice]["name"], target_lang

def translate_texts(texts, model_name, target_lang):
    # 유효한 텍스트만 필터링
    valid_texts = []
    for text in texts:
        if isinstance(text, str):
            if text.strip():
                valid_texts.append(text)
    
    # 100개씩 배치로 나누기
    batch_size = 100
    all_translations = []
    
    for i in range(0, len(valid_texts), batch_size):
        batch = valid_texts[i:i + batch_size]
        print(f"배치 {i//batch_size + 1}/{(len(valid_texts) + batch_size - 1)//batch_size} 번역 중...")
        
        # 배치의 문장들을 하나의 문자열로 결합
        numbered_texts = []
        for j, text in enumerate(batch):
            numbered_text = f"{j+1}. {text}"
            numbered_texts.append(numbered_text)
        combined_text = "\n".join(numbered_texts)
        
        try:
            prompt = PROMPT_TEMPLATE["user"].format(
                text=combined_text,
                target_lang=target_lang
            )
            
            response = openai.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": f"당신은 한국어를 {target_lang}로 번역하는 전문 번역가입니다."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 번역 결과 파싱
            translated_text = response.choices[0].message.content.strip()
            translations = translated_text.split('\n')
            
            # 번호 제거 및 공백 제거
            parsed_translations = []
            for t in translations:
                if '. ' in t:
                    cleaned_text = t.split('. ', 1)[1].strip()
                else:
                    cleaned_text = t.strip()
                parsed_translations.append(cleaned_text)
            
            all_translations.extend(parsed_translations)
            print(f"배치 {i//batch_size + 1} 번역 완료!")
            
        except Exception as e:
            print(f"배치 {i//batch_size + 1} 번역 중 오류 발생: {e}")
            all_translations.extend(["번역 오류"] * len(batch))
    
    # 최종 결과 생성
    result = []
    valid_idx = 0
    for text in texts:
        if isinstance(text, str) and text.strip():
            if valid_idx < len(all_translations):
                translated_text = all_translations[valid_idx]
                result.append(translated_text)
            else:
                result.append("번역 오류")
            valid_idx += 1
        else:
            result.append("")
    
    return result

def process_excel_files():
    # 사용자 설정 가져오기
    model_name, target_lang = get_user_preferences()
    print(f"\n선택된 설정: 모델={model_name}, 목표 언어={target_lang}")
    
    excel_files = glob('camelliaag-contexts-causal-lm-ko.xlsx')
    
    if not excel_files:
        print("처리할 엑셀 파일을 찾을 수 없습니다.")
        return
        
    for file_path in excel_files:
        try:
            print(f"파일 처리 시작: {file_path}")
            df = pd.read_excel(file_path, header=0)
            print(f"데이터 크기: {df.shape}")
            
            texts = df.iloc[:, 1].tolist()
            print(f"번역할 총 문장 수: {len(texts)}")
            print(f"시작 문장: {texts[0]}")
            
            translated_texts = translate_texts(texts, model_name, target_lang)
            
            try:
                existing_df = pd.read_excel(file_path.replace('.xlsx', f'_translated_{target_lang}.xlsx'))
            except FileNotFoundError:
                print("기존 번역 파일이 없어 새로 생성합니다.")
                existing_df = df.copy()
                existing_df[f'{target_lang} 번역'] = ""
            
            existing_df.iloc[:, -1] = translated_texts
            
            output_path = file_path.replace('.xlsx', f'_translated_{target_lang}.xlsx')
            existing_df.to_excel(output_path, index=False)
            print("번역 파일 저장 완료")
            
        except Exception as e:
            print(f"파일 처리 중 오류 발생 ({file_path}): {e}")

if __name__ == "__main__":
    process_excel_files()